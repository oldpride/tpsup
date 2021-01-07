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
      query_jobs
);
      
use Carp;
use Data::Dumper;
use TPSUP::UTIL qw(get_in_fh get_out_fh get_homedir_by_user get_setting_from_env);
use TPSUP::Expression;

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
      
      close $in_fh if $in_fh != \*STDIN;
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

   my $status_has;
   for my $attr ({qw(JobName LastStart LastEnd Status)}) {
      $status_has->{$attr} = 1;
   } 

   my @a = split /\$/, $expression;
   my $need;

   for my $str (@a) {
      # has to start with at least 3 alphabets 
      if ($str =~ /^([a-zA-Z]{3,})/) {
         my $attr = $1;
         if ($status_has->{$attr}) {
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
               confess "unexpected insert_job line: $line\n";
            } else {
               $result->{$current_JobName}->{job_type} = $a[1];
               $result->{$current_JobName}->{defination} = "$line\n";
            }
         } else {
            if (!$current_JobName) {
               confess "unexpected line before insert_job: $line\n";
            }

            $result->{$current_JobName}->{$attr} = $rest;
            $result->{$current_JobName}->{defination} .= "$line\n";
         }
      }
   }
   
   close $in_fh if $in_fh != \*STDIN;

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
};    
my $last_result = {};   # after applied JobExps on $cumulative 
my $last_exp = '';      # JobExps converted into a string

sub query_jobs {
   my ($opt) = @_;

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
   my $UnivPatterns = $opt->{UnivPatterns};

   if ( (!$DetailFiles && $need_job_detail) || (!$StatusFiles && $need_job_status) ) {
      if (!$UnivPatterns) {
         if ($opt->{Jobs}) {
            # first try to figure out Prefix from the Jobs if given.
            my @jobs;

            my $type = ref $opt->{Jobs};
            if ($type eq 'ARRAY') {
               @jobs = @{$opt->{Jobs}};
            } elsif ($type eq 'HASH') {
               @jobs = keys %{$opt->{Jobs}};
            } else {
               # default to string of jobs, separated by coma ','
               @jobs = split /[ ,]+/, $opt->{Jobs};
            }

            my $seen_pattern;
            for my $j (@jobs) {
               my ($prefix, $junk) = split /_/, $j, 2;
               my $pattern = $prefix =~ /\%$/ ? $prefix : "$prefix\%";
               $seen_pattern->{$pattern} ++;
            }

            $UnivPatterns = join(",", sort(keys %$seen_pattern));
         } else {
            $UnivPatterns = get_univ_patterns($opt);
         }
      } 
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
            $new_detail_ref = $new;
         }
      } elsif ($UnivPatterns) {
         # APP1%,APP2%
         my @patterns = split /,/, $UnivPatterns;

         for my $pattern (@patterns) {
            if ($cumulative->{seen_detail_pattern}->{$pattern}) {
               next;
            }
            $cumulative->{seen_detail_pattern}->{$pattern} ++;

            my $file = get_cache_file($pattern, {QuerySwitch=>'-q -J',
                                                 CacheExpire=>$opt->{DetailExpire},
                                                 %$opt,
                                      });  
   
            my $new = autorep_q_J("file=$file", $opt);
   
            next if ! $new;
   
            $meta->{updated} ++;
            $new_detail_ref = $new;
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
            $new_status_ref = $new;
         }
      } elsif ($UnivPatterns) {
         # APP1%,APP2%
         my @patterns = split /,/, $UnivPatterns;

         for my $pattern (@patterns) {
            if ($cumulative->{seen_status_pattern}->{$pattern}) {
               next;
            }
            $cumulative->{seen_status_pattern}->{$pattern} ++;

            my $file = get_cache_file($pattern, {QuerySwitch=>'-J',
                                                 CacheExpire=>$opt->{StatusExpire},
                                                 %$opt,
                                      });  
   
            my $new = autorep_J("file=$file", $opt);
   
            next if ! $new;
   
            $meta->{updated} ++;
            $new_status_ref = $new;
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
         my $warn = $opt->{verbose} ? 'use' : 'no';
      
         my $matchExps = map {
            my $compiled = eval "$warn warnings; no strict; package TPSUP::Expression; sub { $_ } ";
            $@ ? (die "Bad match expression '$_' : $@") : $compiled;
         } @{$opt->{JobExps}};
      
         for my $job (keys %{$cumulative->{job_hash}}) {
            my $r = $cumulative->{job_hash}->{$job};
      
            if ($matchExps) {
               TPSUP::Expression::export_var(%$r, {RESET=>1});
               for my $e (@$matchExps) {
                  if (! $e->()) {
                     next;
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

   for my $job (keys %$update_ref) {
      my $r = $update_ref->{$job};
   
      for my $cond_job (condition_to_jobs($r->{condition})) {
         push @{$children_by_parent->{$cond_job}}, $job;
      } 
   
      if ($r->{box_name}) {
         push @{$children_by_box->{$r->{box_name}}}, $job;
      } 
   }
   $opt->{verbose} && print STDERR "children_by_parent=", Dumper($children_by_parent);
   $opt->{verbose} && print STDERR "children_by_box=",    Dumper($children_by_box);
}


sub get_dependency {
   my ($job2, $opt) = @_;

   my $all_ref = query_jobs({%$opt, Jobs=>[$job2]});

   $opt->{verbose} && print STDERR "all=", Dumper($all_ref);

   if (! $all_ref->{$job2}) {
      print STDERR "$job2 is not part of universe\n";
      return undef;
   }

   my $children_by_parent;
   my $children_by_box;

   update_parent_child_mapping($children_by_parent, $children_by_box, $all_ref);

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
         ($all_ref, $meta)  = query_jobs({%$opt, Jobs=>[$job]});
         if ($meta->{updated}) {
            update_parent_child_mapping($children_by_parent,
                                        $children_by_box, 
                                        $meta->{new});
         }

         my $r = $all_ref->{$job};

         if ($reason ne 'self') {
            if ($r) {
               if ($matchExps) {
                  TPSUP::Expression::export_var($r, {RESET=>1});
                  for my $e (@$matchExps) {
                     if (! $e->()) {
                        next TODO;
                     }
                  }
               }
         
               push @{$dependency->{$updown}}, { detail => $r,
                                                 serial => $serial,
                                                 reason => $reason,
                                               };
            } else {
               # this job is outside the UNIV_PATTERNS
               $r->{JobName} = $job;
      
               push @{$dependency->{$updown}}, { detail => $r,
                                                 serial => $serial,
                                                 reason => $reason,
                                               };
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
            push @next_level, ['condition', 
                               [condition_to_jobs($all_ref->{$job}->{condition})]
                              ];
         } else {
            # now $updown eq 'down'
            if ($children_by_parent->{$job}) {
               push @next_level, ['condition', $children_by_parent->{$job}];
            }
         }
   
         # this job is a box
         if ($children_by_box->{$job}) {
            # for this example, one box has two children
            #    test_box1
            #     test_job1
            #     test_job2
            # when we find the downstream dependency of test_job1, we should get
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

   printf get_autorep_J_format(),
      $indent.$job, $info->{$job}->{LastStart}, $info->{$job}->{LastEnd}, $info->{$job}->{Status};

   if (exists $info->{$job}->{status_box_children}) {
      for my $child (@{$info->{$job}->{status_box_children}}) {
         print_autorep_J_job($info, $child, $indent . " ", $opt);
      }
   }
}

sub main {
   use Data::Dumper;
   print "autorep_J=", Dumper(autorep_J("file=autorep_J_example.txt")); 
   print "autorep_q_J=", Dumper(autorep_q_J("file=autorep_q_J_example.txt")); 
   print "get_dependency=", Dumper(get_dependency("test_job1", 
                                     {
                                        DetailFiles => "autorep_q_J_example.txt", 
                                        StatusFiles => "autorep_J_example.txt", 
                                        #verbose => 1,
                                     })); 
   
}

main() unless caller();

1
