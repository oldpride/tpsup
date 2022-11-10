#!/usr/bin/env perl

package TPSUP::AUTOSYS;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
      autorep_J
      autorep_q_J
      get_autorep_J_format
      get_dependency
      get_univ_patterns
      print_autorep_J_header
      print_autorep_J_job
      print_autorep_q_J_job
      print_job_csv
      query_jobs_superset
      load_autosys_cfg
      wait_job
      update_tally
      count_error_in_result
      resolve_jobs
      parse_cmdline_jobs
);
      
use Carp;
use Data::Dumper;
$Data::Dumper::Sortkeys = 1;  # this sorts the Dumper output!
$Data::Dumper::Terse = 1;     # print without "$VAR1="

use TPSUP::UTIL qw(get_in_fh
                   get_out_fh
                   close_in_fh
                   get_homedir_by_user
                   get_setting_from_env
);

use TPSUP::Expression;
use POSIX qw(strftime);

sub parse_cmdline_jobs {
   my ($ARGV, $opt) = @_;

   my $verbose = $opt->{verbose};

   # case-insensitive qr//
   my   $MatchPattern =   $opt->{MatchPattern} ? qr/$opt->{MatchPattern}/i   : undef;
   my $ExcludePattern = $opt->{ExcludePattern} ? qr/$opt->{ExcludePattern}/i : undef;

   my @supported_flags = qw(offtrack wait_offtrack);
   my $support_flag;
   for my $f (@supported_flags) {
      $support_flag->{uc($f)} ++;
   }

   my @jobs;
   my @jobFlags;
   
   if ($opt->{JFlag}) {
      @jobs = @$ARGV;
   } else {
      for my $file (@$ARGV) {
         my $ifh = get_in_fh($file);
   
         while (my $line = <$ifh>) {
            chomp $line;
   
            $line =~ s/^[^0-9a-zA-Z.#\%_-]+//;     # trim spaces or bad chars at beginning
            $line =~  s/[^0-9a-zA-Z.#\%_-]+$//;    # trim spaces or bad chars at end
   
            next if $line =~ /^\s*$/;     # skip blank lines
            next if $line =~ /^\s*#/;     # skip comment
   
            next if $line eq '';

            my @a = split /\s+/, $line;
            my $job = shift @a;
   
            my $v_by_k = {job=>$job};
   
            for my $pair (@a) {
               if ($pair =~ /^(.+?)=(.+)/) {
                  my $key = uc($1); # convert to uppercase to make flag case-insensitive
                  my $value = $2;
   
                  croak "flag='$key' in $pair is not supported" if !$support_flag->{$key};
   
                  $v_by_k->{$key} = $value;
               } else {
                  confess "bad format key=value '$pair' at line: $line";
               }
            }

            push @jobs, $job;
            push @jobFlags, $v_by_k;
         }
   
         close_in_fh($ifh);
   
         if ($ifh == \*STDIN && -t STDIN) {
            print STDERR "done reading STDIN\n";
         }
      }
   }

   #$verbose && print __FILE__, __LINE__, ": jobFlags = ", Dumper(\@jobFlags);

   my $seen;
   my @jobs2;
   my @jobFlags2;
   for my $job (@jobs) {
     my $v_by_k = shift @jobFlags;
     next if defined   $MatchPattern && $job !~   /$MatchPattern/ && $job =~ /\%/;
     next if defined $ExcludePattern && $job =~ /$ExcludePattern/;
     $seen->{$job} ++;
     push @jobs2,     $job; # dup is allowed here in case user wants to run a job twice.
     push @jobFlags2, $v_by_k; 
   }

   return (\@jobs2, $seen, \@jobFlags2);
}

sub get_autosys_fh {
   my ($input, $opt) = @_;

   my $in_fh;

   if ($input =~ /file=(.+)/) {
      my $file = $1;
      $in_fh = get_in_fh($file);
   } elsif ($input =~ /command=(.+)/) {
      my $cmd = $1;
      print STDERR "cmd=$cmd\n" if !$opt->{AutosysQuiet};
      open $in_fh, "$cmd |";

      # don't bomb out here, just print an error. let the caller to handle it.
      print STDERR "cmd='$cmd' failed: $!" if ! $in_fh;
   } else {
      require Carp::Always;
      confess "unknown input='$input'";
   }

   return $in_fh;
}


sub autorep_J {
   my ($input, $opt) = @_;

   my $result;

   # goal is to convert $input into an array of strings and then parse them
   my $autorep_array;

   if (!$input) {
      my $UnivPatterns = get_setting_from_env('UNIV_PATTERNS', 'TPAUTOSYS', get_homedir_by_user() . "/.tpautosys");
      $input = "command=autorep -J $UnivPatterns";
   } elsif (ref($input) eq 'ARRAY') {
      $autorep_array = $input;
   } elsif ($input =~ /^string=(.*)/s) {
      my @array = split /\n/, $2;
      $autorep_array = \@array;
   } elsif ($input !~ /^(file|command)=/) {
      # $input is a pattern
      $input = "command=autorep -J $input";
   }

   if (!$autorep_array) {
      # now $input is "file=..." or "command=..."
      my $in_fh = get_autosys_fh($input, $opt);
   
      if (!$in_fh) {
         return $result;
      }
   
      while (<$in_fh>) {
         my $line = $_;
         chomp $line;

         push @$autorep_array, $line
      }
      
      close_in_fh($in_fh);
   }

   # now we have $autorep_array, let's parse it
   # Job Name           Last Start           Last End             ST/Ex Run/Ntry Pri/Xit
   # _________________ ____________________ ____________________ _____ ________ _______
   # Nightly_Download   05/21/2010 11:27:31  05/21/2010 11:27:33  SU    197/1    0
   # Watch_4_file       05/21/2010 11:27:32  05/21/2010 11:27:33  SU    197/1    0
   # filter_data        05/21/2010 11:27:32  05/21/2010 11:27:33  SU    197/1    0
   # update_DBMS        05/21/2010 11:27:32  05/21/2010 11:27:33  SU    197/1    0
   # test_job1_iced     -----                05/21/2010 11:27:33  OI    197/1    0
   # test_job2_iced     -----                -----                OI    197/1    0
   # test_job3_failed   05/21/2010 11:27:32  05/21/2010 11:27:33  FA    197/1    0
   # test_job4_run      05/21/2010 11:27:32  ----                 RU    197/1    0
   # test_job5_hold     05/21/2010 11:27:32  05/21/2010 11:27:33  OH    197/1    0

   if (!$opt->{AutorepInputHasNoHeader}) {
      my $skip = 3;

      for (my $i=0; $i<$skip; $i++) {
         shift @$autorep_array;
      }
   }
   
   my $last_by_indentLength;
   for my $line (@$autorep_array) {
      if ( $line =~ /^(\s*)(\S+?)\s+?(\S.{18})\s+?(\S.{18})\s+?(\S+)\s+/ ) {
         @{$result->{$2}}{qw(JobName LastStart LastEnd Status)} = ($2, $3, $4, $5);
         my $indent = $1;
         my $job    = $2;

         my $indentLength = length($indent);

         if ($indentLength) {
            my $parent = $last_by_indentLength->{$indentLength-1};

            if ($parent) {
               push @{$result->{$parent}->{status_box_children}}, $job; 
               $result->{$job}->{status_box_parent} = $parent; 
            }
         }

         $last_by_indentLength->{$indentLength} = $job;  
      } else {
         print STDERR "unsupported format at line: $line\n";
      }
   }

   return $result;
}

my $need_by_expression_input;

sub expression_need {
   my ($expression, $opt) = @_;

   return       $need_by_expression_input->{$expression}
      if exists $need_by_expression_input->{$expression};

   my $status_has = {
      LastStart => 1,
      LastEnd   => 1,
      Status    => 1,
   };

   my $either_has = {
      JobName => 1, 
   };

   my @a = split /\$/, $expression;
   my $need;

   my @postponed;

   for my $str (@a) {
      # has to start with at least 3 alphabets 
      if ($str =~ /^([a-zA-Z]{3,})/) {
         my $attr = $1;
         if ($either_has->{$attr}) {
             push @postponed, $attr;         
         } elsif ($status_has->{$attr}) {
            # check whether status query result already has this.
            # if yes, we don't have to use job detail. 
            $need->{status} = 1; 
            if ($opt->{verbose}) {
               print STDERR "need job status to find \$$attr in '$expression'\n";
            }
         } else {
            $need->{detail} = 1; 
            if ($opt->{verbose}) {
               print STDERR "need job detail to find \$$attr in '$expression'\n";
            }
         }
      }
   }

   if (!$need->{status} && !$need->{detail} && @postponed) {
      # default to use detail. it is static data, maybe faster to get.
      $need->{detail} = 1;
   }

   $need_by_expression_input->{$expression} = $need;

   return $need;
}

sub autorep_q_J {
   my ($input, $opt) = @_;

   if (!$input) {
      my $UnivPatterns = get_setting_from_env('UNIV_PATTERNS', 'TPAUTOSYS', get_homedir_by_user() . "/.tpautosys");
      $input = "command=autorep -q -J $UnivPatterns";
   } elsif ($input !~ /(file|command)=/) {
      # $input is a pattern
      $input = "command=autorep -q -J $input";
   }

   my $in_fh = get_autosys_fh($input, $opt);

   # /* ---------- test_box1 -------------*/
   # 
   # insert_job: test_box1 job_type: BOX
   # machine: juno
   # data_conditions: 0
   # owner: jerry@juno
   # condition: s(test_job3)
   # permission:
   # alarm_if_fail: 1
   #
   # /* ---------- test_job1 -------------*/
   # 
   # insert_job: test_job1 job_type: CMD
   # box_name: test_box1
   # command: sleep 60
   # machine: juno
   # owner: jerry@juno
   # permission:
   # alarm_if_fail: 1
   # profile: /etc/profile

   my $result;
   my $current_JobName;

   while (<$in_fh>) {
      my $line = $_;
      chomp $line;

      if ( $line =~ /^\s*([a-zA-Z]\S*?):(.*)/ ) {
         my $attr = $1;
         my $rest = $2;

         $rest =~ s/^\s+// if $rest;
         if ($attr eq 'insert_job') {
            my @a = split /\s+/, $rest;
            $current_JobName = shift(@a);
            if (@a != 2 && $a[0] ne 'job_type:') {
               confess "unexpected format at insert_job line: $line\n" .
                       "expecting: insert_job: .... job_type: ...\n";
            } else {
               $result->{$current_JobName}->{JobName}    = $current_JobName;
               $result->{$current_JobName}->{job_type}   = $a[1];
               $result->{$current_JobName}->{defination} = "$line\n";
            }
         } else {
            if (!$current_JobName) {
               confess "unexpected line before insert_job: $line\n";
            }

            # remove wrapping quotes, in
            #     command: "sleep 100 &"
            # we replace 
            #             "sleep 100 &"
            # with
            #              sleep 100 &
            $rest =~ s/^\s*"(.+)"\s*$/$1/;
            $result->{$current_JobName}->{$attr} = $rest;
            $result->{$current_JobName}->{defination} .= "$line\n";

            if ($attr eq 'box_name') {
               my $box_name = $rest;
               push @{$result->{$box_name}->{detail_box_children}}, $current_JobName;
            }
         }
      }
   }
   
   close_in_fh($in_fh);

   return $result;
}


sub get_cache_file {
   my ($pattern, $opt) = @_;

   my $sub_filename = $pattern;

   # replace space with _
   $sub_filename =~ s/[ ][ ]+/ /g;
   $sub_filename =~ s/[ ]/_/g;

   my $file  = get_homedir_by_user();

   my $QuerySwitch = $opt->{QuerySwitch} ? $opt->{QuerySwitch} : '-q -J';
   
   if ( $QuerySwitch eq '-q -J' || $QuerySwitch eq '-J -q' ) {
      $file .= "/autorep_q_J_";
      $QuerySwitch = "-q -J"; # normalize
   } elsif ( $QuerySwitch eq '-J' ) {
      $file .= "/autorep_J_";
   } else {
      confess "unsupported QuerySwitch=$QuerySwitch";
   }
       
   $file .= "$sub_filename" . ".txt";

   if (!need_refresh($file, $opt)) {
      $opt->{verbose} && print STDERR "we will use cached $file\n";

      if (-z $file) {
         print STDERR "Cache file $file has zero size. If it shouldn't be zero, delete it or wait for it to expire\n";
      }
      return $file;
   }

   my $cmd = "autorep $QuerySwitch $pattern > $file";
   $opt->{verbose} && print STDERR "running cmd=$cmd\n";
   system($cmd);
   confess "cmd=$cmd failed: $!" if $?;

   return $file;
}

sub need_refresh {
   my ($file, $opt) = @_;
   if ($opt->{Refresh}) {
      $opt->{verbose} && print STDERR "\$opt->{Refresh}=$opt->{Refresh}\n";
      return 1;
   }

   if (! -f $file) {
      $opt->{verbose} && print STDERR "$file doesn't exist yet\n";
      return 1;
   }

   my ($dev,$ino,$mode,$nlink,$uid,$gid,$rdev,$size,$atime,$mtime,$ctime,$blksize,$blocks) = lstat($file);
   my $now_sec = time();
   my $expire_sec = defined($opt->{CacheExpire}) ? $opt->{CacheExpire} : 3600 * 12;

   my $staleness = $now_sec - $mtime;

   if ($staleness > $expire_sec) {
      $opt->{verbose} && print STDERR "$file (staleness=$now_sec-$mtime=$staleness) expired after $expire_sec seconds\n";
      return 1;
   #} else {
   #   print STDERR "$file (staleness=$now_sec-$mtime=$staleness<$expire_sec) not expired\n";
   }

   return 0;
}


sub get_univ_patterns {
    my ($opt) = @_;
    return $opt->{UnivPatterns} if $opt->{UnivPatterns};
    return get_setting_from_env('UNIV_PATTERNS', 'TPAUTOSYS', get_homedir_by_user() . "/.tpautosys");
}


sub find_needed_patterns {
   my ($jobs2, $patterns, $opt) = @_;

   my @jobs;

   my $type = ref $jobs2;
   if ($type eq 'ARRAY') {
      @jobs = @$jobs2;
   } elsif ($type eq 'HASH') {
      @jobs = keys %$jobs2;
   } else {
      # default to string of jobs, separated by coma ','
      @jobs = split /,/, $jobs2;
   }

   my $need_pattern;
   my $pattern_by_job;

   for my $pattern (@$patterns) {
      # change % to .*,  _ to . 
      my $regex = $pattern;
      $regex =~ s/\%/.*/g;
      $regex =~ s/_/./g;

      my $compiled = qr/$regex/;

      for my $job (@jobs) {
         if ($job =~ /$compiled/) {
            $need_pattern->{$pattern} ++;
            $pattern_by_job->{$job} = $pattern;
         }
      }
   }

   for my $job (@jobs) {
      if (!exists $pattern_by_job->{$job}) {
         print STDERR "WARN: job $job is not converted by ", join(",", @$patterns), "\n";
      }
   }

   my @needed_patterns = keys %$need_pattern;

   return \@needed_patterns;
}


my $cumulative = {                      # all knowledge so far, 
   job_hash => {},                      # hash key is job name
   seen_file => {},                     # user provided files loaded so far
   seen_status_pattern => {},           # patterns run by autorep -J so far
   seen_detail_pattern => {},           # patterns run by autorep -J -q so far
   status_pattern_time => {},           # last time updated
   detail_pattern_time => {},           # last time updated
};    

my $last_result = {};   # after applied JobExps on $cumulative 
my $last_exp = '';      # JobExps converted into a string

sub query_jobs_superset {
   # this returns not lonly the jobs' info, but their supersets' info
   # for example,
   #    given 
   #        $jobs = 'P1_APP1_JOB1,P1_APP2_JOB1,P2_APP3_JOB1'
   #    this function will return all info of 
   #        P1% and P2%
    
   my ($jobs, $opt) = @_;

   my $need_job_detail = 1;
   my $need_job_status = 1;

   if ($opt->{StatusOnly}) {
      $need_job_detail = 0;
      if (exists $opt->{JobExps}) {
         for my $exp (@{$opt->{JobExps}}) {
            my $need = expression_need($exp, $opt);
            $need_job_detail = $need->{detail};
         }
      }
   } elsif ($opt->{DetailOnly}) {
      $need_job_status = 0;
      if (exists $opt->{JobExps}) {
         for my $exp (@{$opt->{JobExps}}) {
            my $need = expression_need($exp, $opt);
            $need_job_status = $need->{status};
         }
      }
   }

   $opt->{verbose} && print STDERR "need_job_detail=$need_job_detail, need_job_status=$need_job_status\n";

   my $DetailFiles  = $opt->{DetailFiles};
   my $StatusFiles  = $opt->{StatusFiles};
   my $UnivPatterns;

   if ( (!$DetailFiles && $need_job_detail) || (!$StatusFiles && $need_job_status) ) {
      # figure out $UnivPatterns from job prefix
      my @joblist;

      my $type = ref $jobs;
      if ($type eq 'ARRAY') {
         @joblist = @$jobs;
      } elsif ($type eq 'HASH') {
         @joblist = keys %$jobs;
      } else {
         # default to string of jobs, separated by coma ','
         @joblist = split /[ ,]+/, $jobs;
      }

      # these are extra jobs used by adep
      my $ExtJobs = $opt->{ExtJobs};
      if (!$ExtJobs) {
         my $cfg = load_autosys_cfg();
         $ExtJobs = $cfg->{"dependency.ExtJobs"};
      }

      if ($ExtJobs) {
         push @joblist, split /[ ,]+/, $ExtJobs;
      }

      my $seen_pattern;
      for my $j (@joblist) {
         my ($prefix, $junk) = split /_/, $j, 2;
         my $pattern = ($prefix =~ /\%$/) ? $prefix : "$prefix\%";
         $seen_pattern->{$pattern} ++;
      }

      $UnivPatterns = join(",", sort(keys %$seen_pattern));
   }
   
   my $meta;
   $meta->{updated} = 0;

   my $new_detail_ref = {};
   my $new_status_ref = {};

   if ($need_job_detail) {
      if ($DetailFiles) {
         for my $file (split /,/, $DetailFiles) {
            if ($cumulative->{seen_file}->{$file}) {
               next;
            }
            $cumulative->{seen_file}->{$file} ++;

            $file =~ s/\s+//;
            $file =~ s/\s+$//;
            my $new = autorep_q_J("file=$file", $opt);
   
            next if ! $new;

            $meta->{updated} ++;
            #$new_detail_ref = $new;
            $new_detail_ref = {%$new_detail_ref, %$new};
         }
      } elsif ($UnivPatterns) {
         # APP1%,APP2%
         my @patterns = split /,/, $UnivPatterns;

         for my $pattern (@patterns) {
            if ($cumulative->{seen_detail_pattern}->{$pattern}) {
               my $now_sec = time();
               my $mtime = $cumulative->{detail_pattern_time}->{$pattern};
               $mtime = 0 if !$mtime;
               my $expire_sec = defined($opt->{DetailExpire}) ? $opt->{DetailExpire} : 3600 * 12;
               my $staleness = $now_sec - $mtime;

               if ($staleness < $expire_sec) {
                  next;
               }
            }
            $cumulative->{seen_detail_pattern}->{$pattern} ++;

            my $file = get_cache_file($pattern, {QuerySwitch=>'-q -J',
                                                 CacheExpire=>$opt->{DetailExpire},
                                                 %$opt,
                                      });  
   
            $cumulative->{detail_pattern_time}->{$pattern} = time();

            my $new = autorep_q_J("file=$file", $opt);
   
            next if ! $new;
   
            $meta->{updated} ++;
            #$new_detail_ref = $new;
            $new_detail_ref = {%$new_detail_ref, %$new};
         }
      } else {
         confess "don't know how to find universe: neither DetailFiles nor UnivPatterns is defined.";
      }
   }
   
   if ($need_job_status) {
      if ($StatusFiles) {
         for my $file (split /,/, $StatusFiles) {
            if ($cumulative->{seen_file}->{$file}) {
               next;
            }
            $cumulative->{seen_file}->{$file} ++;

            $file =~ s/\s+//;
            $file =~ s/\s+$//;
            my $new = autorep_J("file=$file", $opt);
   
            next if ! $new;
   
            $meta->{updated} ++;
            #$new_status_ref = $new;
            $new_status_ref = {%$new_status_ref, %$new};
         }
      } elsif ($UnivPatterns) {
         # APP1%,APP2%
         my @patterns = split /,/, $UnivPatterns;

         for my $pattern (@patterns) {
            if ($cumulative->{seen_status_pattern}->{$pattern}) {
               my $now_sec = time();
               my $mtime = $cumulative->{status_pattern_time}->{$pattern};
               $mtime = 0 if !$mtime;
               my $expire_sec = defined($opt->{StatusExpire}) ? $opt->{StatusExpire} : 3600 * 12;
               my $staleness = $now_sec - $mtime;

               if ($staleness < $expire_sec) {
                  next;
               }
            }
            $cumulative->{seen_status_pattern}->{$pattern} ++;

            my $file = get_cache_file($pattern, {QuerySwitch=>'-J',
                                                 CacheExpire=>$opt->{StatusExpire},
                                                 %$opt,
                                      });  
   
            $cumulative->{status_pattern_time}->{$pattern} = time();

            my $new = autorep_J("file=$file", $opt);
   
            next if ! $new;
   
            $meta->{updated} ++;
            #$new_status_ref = $new;
            $new_status_ref = {%$new_status_ref, %$new};
         }
      } else {
         confess "don't know how to find universe: neither StatusFiles nor UnivPatterns is defined.";
      }
   }

   my  $new_exp = $opt->{JobExps} ? join(";", @{$opt->{JobExps}}) : '';

   my $return_ref;

   if ( $meta->{updated} || $new_exp ne $last_exp) {
      if ($meta->{updated}) {
         my $seen_new_job;
         for my $job (keys %$new_status_ref) {
            $seen_new_job->{$job} ++;
         }
         for my $job (keys %$new_detail_ref) {
            $seen_new_job->{$job} ++;
         }
             
         # $opt->{verbose} && print "cumulative = ", Dumper($cumulative);

         # merge new result to the cumulative 
         for my $job (keys %$seen_new_job) {
            my $cum = exists $cumulative->{job_hash}->{$job} ? 
                             $cumulative->{job_hash}->{$job} : {};
   
            my $ns = exists $new_status_ref->{$job} ? $new_status_ref->{$job} : {};
            my $nd = exists $new_detail_ref->{$job} ? $new_detail_ref->{$job} : {};

            my $r = {%$cum, %$ns, %$nd};
   
            $r->{JobName} = $job;
   
            $meta->{new}->{$job} = $r;
            $cumulative->{job_hash}->{$job}  = $r;
         }
      }

      if ($opt->{JobExps} && @{$opt->{JobExps}}) {
         #print Dumper($opt->{JobExps});
         #exit 0;
         my $warn = $opt->{verbose} ? 'use' : 'no';
      
         my @matchExps = map {
            my $compiled = eval "$warn warnings; no strict; package TPSUP::Expression; sub { $_ } ";
            $@ ? (die "Bad match expression '$_' : $@") : $compiled;
         } @{$opt->{JobExps}};
      
         FILTER_JOB:
         for my $job (keys %{$cumulative->{job_hash}}) {
            my $r = $cumulative->{job_hash}->{$job};

            next if ! defined $r;
      
            if (@matchExps) {
               if ($opt->{ValidateVars}) {
                  for my $var (@{$opt->{ValidateVars}}) {
                     if (! defined $r->{$var}) {
                        carp "$job: '$var' is not defined. skipped r = " . Dumper($r);
                        next FILTER_JOB; 
                     }
                  }
               }
               TPSUP::Expression::export_var($r, {RESET=>1});
               for my $e (@matchExps) {
                  if (! $e->()) {
                     next FILTER_JOB;
                  }
               }
            }
      
            $return_ref->{$job} = $r;
         }
      } else {
         $return_ref = $cumulative->{job_hash};
      }
   
      $last_result = $return_ref;
      $last_exp    = $last_exp;
   } else {
      $return_ref = $last_result;
   }

   # https://perlmaven.com/wantarray
   # wantarray will return
   #   undef: if the function was called in VOID context
   #   false: other than undef if the function was called in SCALAR context
   #   true:  if the function was called in LIST context.
   if (wantarray) {
      return ($return_ref, $meta);
   } elsif (defined wantarray) {
      return $return_ref;
   } 
}


sub update_parent_child_mapping {
   my ($children_by_parent, $children_by_box, $update_ref, $opt) = @_;

   my $updated = 0;

   for my $job (keys %$update_ref) {
      my $r = $update_ref->{$job};
   
      if (!$r->{start_times} || !$opt->{IgnoreConditionWhenStartTimesDefined}) {
          # if a job has both condition and start_times defined, then
          # they both have to be true so that the job can run by itself.
          # therefore, at certain situation, this 'condition' should not
          # not be treated as a dependency, for example, when start_times is
          # not true.
          for my $cond_job (condition_to_jobs($r->{condition})) {
             push @{$children_by_parent->{$cond_job}}, $job;
          }
      } 
   
      if ($r->{box_name}) {
         push @{$children_by_box->{$r->{box_name}}}, $job;
      } 

      $updated ++;
   }

   if ($updated && $opt->{verbose}) {
      print STDERR "parent_child mapping is updated\n";

      print STDERR "children_by_parent=", Dumper($children_by_parent);
      print STDERR "children_by_box=",    Dumper($children_by_box);
   }

   return ($children_by_parent, $children_by_box);
}


sub get_dependency {
   my ($job2, $opt) = @_;

   my $all_ref = query_jobs_superset($job2, $opt);

   # $opt->{verbose} && print STDERR "query_jobs_superset opt=", Dumper($opt);

   $opt->{verbose} && print STDERR "all=", Dumper($all_ref);

   if (! $all_ref->{$job2}) {
      print STDERR "$job2 is not part of universe\n";
      return undef;
   }

   my $children_by_parent = {};
   my $children_by_box    = {};
   update_parent_child_mapping($children_by_parent, $children_by_box, $all_ref, $opt);

   my $warn = $opt->{verbose} ? 'use' : 'no';

   my $matchExps;
   if ($opt->{DepExps} && @{$opt->{DepExps}}) {
      @$matchExps = map {
         my $compiled = eval "$warn warnings; no strict; package TPSUP::Expression; sub { $_ } ";
         $@ ? (die "Bad match expression '$_' : $@") : $compiled;
      } @{$opt->{DepExps}};
   }

   my $max_depth = 100;
   my $dependency;
   my $seen;

   push @{$dependency->{'self'}}, { detail => $all_ref->{$job2},
                                    serial => [0],
                                    reason => 'self',
                                  };
   $seen->{up}->{$job2} ++;
   $seen->{down}->{$job2} ++;

   for my $updown (qw(up down)) {
      my @todo = ([ [], $job2, 'self' ]);

      TODO:
      while (@todo) {
         my $cur = pop @todo;
         my ($serial, $job, $reason) = @$cur;
         # $serial is the index of current dependency, 0 is self
         # $reason is why we are here, eg, self, box, condition

         $opt->{verbose} && print "trace dependency([@[$serial]], $job, $updown, $reason)\n";

         # this updates all_ref
         my $meta;
         ($all_ref, $meta)  = query_jobs_superset($job, $opt);
         if ($meta->{updated}) {
            # update mapping only when there is a update in the jobs
            update_parent_child_mapping($children_by_parent,
                                        $children_by_box, 
                                        $meta->{new}, 
                                        $opt);
         }

         my $r = $all_ref->{$job};

         if ($reason ne 'self') {
            my $dep =  { detail => $r,
                         serial => $serial,
                         reason => $reason,
                       };
            if ($r) {
               if ($matchExps) {
                  TPSUP::Expression::export_var($r, {RESET=>1});
                  for my $e (@$matchExps) {
                     if (! $e->()) {
                        next TODO;
                     }
                  }
               }
         
               $opt->{verbose} && print "\nsaved a '$updown' dep = ", Dumper($dep), "\n";
               push @{$dependency->{$updown}}, $dep;
            } else {
               # this job is outside the UNIV_PATTERNS
               $r->{JobName} = $job;
      
               $opt->{verbose} && print "\nsaved a '$updown' dep = ", Dumper($dep), "\n";
               push @{$dependency->{$updown}}, $dep;
               next TODO;
            };
         }
   
         # just in case we got into a dead loop
         my $depth = scalar(@$serial);
         croak "exceeded max depth $max_depth" if $depth > $max_depth;
   
         my @next_level;
   
         my $box_name = $all_ref->{$job}->{box_name};
         if ($box_name) {
            # this job is in a box
   
            push @next_level, ['box_parent', [$box_name]];
         }
   
         # handle condition relationship
         if ($updown eq 'up') {
            if ($all_ref->{$job}->{start_times} 
                && $opt->{IgnoreConditionWhenStartTimesDefined}) {
               # if a job has both condition and start_times defined, then
               # they both have to be true so that the job can run by itself.
               # therefore, at certain situation, this 'condition' should not
               # not be treated as a dependency, for example, when start_times is
               # not true.
               push @next_level, ['condition', []];
            } else {
               push @next_level, ['condition', 
                               [condition_to_jobs($all_ref->{$job}->{condition})]
                              ];
                              # condition_to_jobs() return empty array if no condition defined.
            }
         } else {
            # now $updown eq 'down'
            if ($children_by_parent->{$job}) {
               push @next_level, ['condition', $children_by_parent->{$job}];
            }
         }
   
         if ($children_by_box->{$job}) {
            # this job is a box
            # for this example, one box has two children
            #    test_box1
            #     test_job1
            #     test_job2
            # when we look for the downstream dependency of test_job1, we should get
            #    test_job1, self
            #      test_box1, box_parent
            # not
            #    test_job1, self
            #      test_box1, box_parent
            #        test_job2, box_child
            # the following 'if' takes care of this.
            if ($reason ne "box_parent") {
               push @next_level, ['box_child', $children_by_box->{$job}];
            }
         }

         my $i = 1;
   
         for my $reason_jobs (@next_level) {
            my ($rsn, $jobs) = @$reason_jobs;
   
            for my $j (@$jobs) {
               if (!$seen->{$updown}->{$j}) {
                  $seen->{$updown}->{$j} = 1;
                  
                  push @todo, [[@$serial, $i], $j, $rsn];
                  $i++;
               } 
            }
         } 
      }
   }

   return $dependency;
}


sub condition_to_jobs {
   my ($condition, $opt) = @_;

   my @jobs;

   return @jobs if !$condition;

    # condition: s(${ENV}-ETL-EDW_DIM_DUMMY_RECORDS,0) and n(${ENV}-ETL-EDW_DIM_ACCOUNT_HIST_LV_stub,0)
    # s(test_job3,0) and n(test_job4)

    my @a = split /[(]/, $condition;
    shift @a;  #throw away the first element

    for my $s (@a) {
       # jobname is trailed by , or )
       # s(test_job3,0)
       # n(test_job4)

       my ($job, $rest) = split /[,)]/, $s, 2;
       push @jobs, $job;
   }

   return @jobs;
}

sub get_autorep_J_format {
   return "%-50s %-19s %-19s %s\n";
}

sub print_autorep_J_header {
   printf get_autorep_J_format(), "Job Name", "Last Start", "Last End", "Status";
   printf "\n";
   printf get_autorep_J_format(), "-"x50,     "-"x19,        "-"x19,    "-"x2;
}


sub print_autorep_J_job {
   my ($info, $job, $indent, $opt) = @_;

   my $NotFoundMsg = defined $opt->{NotFoundMsg} ? $opt->{NotFoundMsg} : "not found";

   if (!$info->{$job}) {
      printf get_autorep_J_format(), $indent.$job, $NotFoundMsg, "", "";
      return;
   }
  
   printf get_autorep_J_format(),
      $indent.$job, $info->{$job}->{LastStart}, $info->{$job}->{LastEnd}, $info->{$job}->{Status};

   if (exists $info->{$job}->{status_box_children}) {
      for my $child (@{$info->{$job}->{status_box_children}}) {
         print_autorep_J_job($info, $child, $indent . " ", $opt);
      }
   }
}


sub print_autorep_q_J_job {
   my ($info, $job, $indent, $opt) = @_;

   my $NotFoundMsg = defined $opt->{NotFoundMsg} ? $opt->{NotFoundMsg} : "not found";

   if (!$info->{$job}->{defination}) {
      print $indent, $job, " $NotFoundMsg\n\n";
      return;
   }
  
   print $indent, join("\n$indent", split(/\n/, $info->{$job}->{defination})), "\n\n";

   if (exists $info->{$job}->{detail_box_children}) {
      for my $child (@{$info->{$job}->{detail_box_children}}) {
         print_autorep_q_J_job($info, $child, $indent . " ", $opt);
      }
   }
}


sub print_job_csv {
   my ($info, $job, $fields, $opt) = @_;

   my $type = ref($fields);
   $type = "" if ! defined $type;
   confess "fields type='$type' is not supported. must be ARRAY. fields=", Dumper($fields)
      if $type ne 'ARRAY';
   
   my $delimiter = $opt->{delimiter} ? $opt->{delimiter} : ',';
   print join($delimiter, @{$info->{$job}}{@$fields}), "\n";
}


sub load_autosys_cfg {
   my ($opt) = @_;

   my $homedir = (getpwuid($<))[7];
   my $hiddendir = "$homedir/.tpsup";
   my $default_cfg_file = "$hiddendir/autosys.cfg";
  
   my $cfg_file;

   if ($opt->{AutoCfgFile}) {
      $cfg_file = $opt->{AutoCfgFile};
   } else {
      $cfg_file = $default_cfg_file;
   }

   my $cfg;

   if (! -f $cfg_file ) {
      if ($cfg_file eq $default_cfg_file) {
         return $cfg; 
      } else {
         die "$cfg_file doesn't exist\n";
      }
   }

   my $in_fh = get_in_fh($cfg_file);

   while (<$in_fh>) {
      my $line = $_;
      chomp $line;
      if ( $line =~ /^\s*(\S+)\s*?=\s*(.+)$/) {
         $cfg->{$1} = $2;
      }
   }

   close_in_fh($in_fh);

   return $cfg;

}


sub wait_job {
   my ($job, $before_result, $opt) = @_;

   my @subjobs  = sort(keys %$before_result);
   my $subcount = scalar(@subjobs);
   my $sub_start = strftime("%T", localtime(time()));
   my $start_sec = time();

   for my $j (@subjobs) {
      if ($before_result->{$j}->{Status} eq 'RU') {
         print "WARN: subjob $j was in $before_result->{$j}->{Status} mode\n";
      }
   }

   my $interval = 10;            # sleep interval increment
   my $interval_limit = 60;      # sleep interval max
   my $sub_interval = $interval; # sleep interval starting value

   sleep(1); # sleep one sec to let fast-running job have time update the status

   my $autorep_cmd = "autorep -J $job";

   while (1) {
      my $sub_run = 0;
      my $sub_err = 0;

      my $after_result = autorep_J("command=$autorep_cmd");

      # mark the main job as sometimes we only pass $after_result without $job
      $after_result->{$job}->{IsMainJob} = 1;   

      for my $j (@subjobs) {
         if ( $before_result->{$j}->{Status}    ne $after_result->{$j}->{Status}    ||
              $before_result->{$j}->{LastStart} ne $after_result->{$j}->{LastStart} ||
              $before_result->{$j}->{LastEnd}   ne $after_result->{$j}->{LastEnd}   ){
            if ($after_result->{$j}->{Status} =~ /^(SU|TE|FA)$/) {
               $sub_run ++;
            }
            if ($after_result->{$j}->{Status} =~ /^(TE|FA)$/) {
               $sub_err ++;
            }
         }
      }

      if ($sub_run < $subcount && $sub_err == 0 ) {
         my $now_sec = time();
         my $total_sec = $now_sec - $start_sec;
         print "Only $sub_run of $subcount subjobs complete since $sub_start ($total_sec sec). sleep for $sub_interval\n";
         sleep $sub_interval;
         $sub_interval += 10;
         $sub_interval = $interval_limit if $sub_interval > $interval_limit;
      } else {
         return $after_result;
         last;
      }
   }
}


sub update_tally {
   my ($tally, $job_result, $opt) = @_;

   my @subjobs = sort(keys %$job_result);

   if ($opt->{PrintTally}) {
      print_autorep_J_header();

      for my $row (@$tally) {
         printf get_autorep_J_format(), @$row;
      }
   }

   # try to restore the original autorep -J format, starting with the main job
   for my $j (@subjobs) {
      if ($job_result->{$j}->{IsMainJob}) {
         my $row = [$j, $job_result->{$j}->{LastStart}, $job_result->{$j}->{LastEnd}, $job_result->{$j}->{Status}];
         push @$tally, $row;

         if ($opt->{PrintTally}) {
            printf get_autorep_J_format(), @$row;
         }
         last;
      }
   }

   # then list the rest jobs with indent
   for my $j (@subjobs) {
      # skip the main job as it was already printed.
      next if $job_result->{$j}->{IsMainJob};

      # add indent
      my $row = ["  $j", $job_result->{$j}->{LastStart}, $job_result->{$j}->{LastEnd}, $job_result->{$j}->{Status}];
      push @$tally, $row;

      if ($opt->{PrintTally}) {
         printf get_autorep_J_format(), @$row;
      }
   }
}


sub count_error_in_result {
   my ($job_result, $opt) = @_;

   my @subjobs = keys %$job_result;
   my $subcount = scalar(@subjobs);

   my $sub_err = 0;

   for my $j (@subjobs) {
      $sub_err++ if $job_result->{$j}->{Status} =~ /^(TE|FA)$/;
   }

   return ($subcount, $sub_err);
}

sub resolve_jobs {
   my ($unresolved, $superset, $opt) = @_;

   # unresolved examples: test_job1, test%, test%1
   #   resolved examples: test_job1, test_job2, test_box1, should be unique
   # $superset can be an array of resolved jobs or a hash keyed by jobs
   # note:  if an unresolved job name has no wild card, it will be passed through as
   #        a resolved job by default. The downstream logic is expected to handle this.
   #        The rational is that this sub is soly to resolve jobs, not to validate jobs.
   #        To change the default behavior, use WithinSuperset flag.

   my $type = ref $superset;
   my $jobs;
   my $exist_job;

   if (!$type) {
      # this is a scalar
      $jobs = [$superset];
      $exist_job->{$superset} = 1;
   } elsif ($type eq 'HASH') {
      $jobs = [keys(%$superset)];
      $exist_job = $superset;
   } elsif ($type eq 'ARRAY') {
      $jobs = $superset;

      for my $job (@$superset) {
         $exist_job->{$job} = 1;
      }
   } else  {
      croak "unsupported type=$type in superset";
   }

   my   $MatchPattern =   $opt->{MatchPattern} ? qr/$opt->{MatchPattern}/i   : undef;
   my $ExcludePattern = $opt->{ExcludePattern} ? qr/$opt->{ExcludePattern}/i : undef;

   my @resolved;
   my %seen;

   for my $j (@$unresolved) {
      if ($j !~ /\%/) {
         if (!$seen{$j}) {
            $seen{$j} = 1;
            if (!$opt->{WithinSuperset} || $exist_job->{$j}) {
               push @resolved, $j;
            }
         }
         next;
      }

      my $pattern = $j;
      $pattern =~ s/\%/.*/g;
      my $compiled = qr/^$pattern$/;

      for my $j2 (grep {/$compiled/} @$jobs) {
         if (!$seen{$j2}) {
            $seen{$j2} = 1;

            next if defined   $MatchPattern && $j2 !~   /$MatchPattern/ && $j2 =~ /\%/;
            next if defined $ExcludePattern && $j2 =~ /$ExcludePattern/;
            
            push @resolved, $j2; 
         }
      }
   }  
   
   return \@resolved;
}


sub main {
   use Data::Dumper;

   print "\n----------------------------------------------------\n";
   print "autosys cfg=", Dumper(load_autosys_cfg()); 

   print "\n----------------------------------------------------\n";
   print "autorep_J=", Dumper(autorep_J("file=autorep_J_example.txt")); 

   print "\n----------------------------------------------------\n";
   print "autorep_q_J=", Dumper(autorep_q_J("file=autorep_q_J_example.txt")); 

   print "\n----------------------------------------------------\n";
   print "get_dependency=", Dumper(get_dependency("test_job1", 
                                     {
                                        DetailFiles => "autorep_q_J_example.txt", 
                                        StatusFiles => "autorep_J_example.txt", 
                                        #verbose => 1,
                                     })); 
   
}

main() unless caller();

1
