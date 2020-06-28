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
      query_jobs
);
      
use Carp;
use Carp::Always;
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
   
   for my $line (@$autorep_array) {
      if ( $line =~ /^\s*(\S+?)\s+?(\S.{18})\s+?(\S.{18})\s+?(\S+)\s+/ ) {
         @{$result->{$1}}{qw(JobName LastStart LastEnd Status)} = ($1, $2, $3, $4);
      } else {
         print STDERR "unsupported format at line: $line\n";
      }
   }

   return $result;
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
            }
         } else {
            if (!$current_JobName) {
               confess "unexpected line before insert_job: $line\n";
            }

            $result->{$current_JobName}->{$attr} = $rest;
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


sub query_jobs {
   my ($opt) = @_;

   my $DetailFiles  = $opt->{DetailFiles};
   my $StatusFiles  = $opt->{StatusFiles};
   my $UnivPatterns = $opt->{UnivPatterns};

   if (!$DetailFiles || !$StatusFiles) {
      if (!$UnivPatterns) {
          $UnivPatterns = get_univ_patterns($opt);
      }
   }
   
   my $detail_ref; 
   my $status_ref; 

   if ($DetailFiles) {
      for my $file (split /,/, $DetailFiles) {
         $file =~ s/\s+//;
         $file =~ s/\s+$//;
         my $new = autorep_q_J("file=$file", $opt);

         next if ! $new;

         if ($detail_ref) {
            $detail_ref = {%$detail_ref, %$new};
         } else {
            $detail_ref = $new;
         }
      }
   } elsif ($UnivPatterns) {
      # APP1%|APP2%
      for my $pattern (split /,/, $UnivPatterns) {
         my $file = get_cache_file($pattern, {QuerySwitch=>'-q -J',
                                              CacheExpire=>$opt->{DetailExpire},
                                              %$opt,
                                   });  

         my $new = autorep_q_J("file=$file", $opt);

         next if ! $new;

         if ($detail_ref) {
            $detail_ref = {%$detail_ref, %$new};
         } else {
            $detail_ref = $new;
         }
      }
   } else {
      confess "don't know how to find universe: neither DetailFiles nor UnivPatterns is defined.";
   }

   if ($StatusFiles) {
      for my $file (split /,/, $StatusFiles) {
         $file =~ s/\s+//;
         $file =~ s/\s+$//;
         my $new = autorep_J("file=$file", $opt);

         next if ! $new;

         if ($status_ref) {
            $status_ref = {%$status_ref, %$new};
         } else {
            $status_ref = $new;
         }
      }
   } elsif ($UnivPatterns) {
      # APP1%|APP2%
      for my $pattern (split /,/, $UnivPatterns) {
         my $file = get_cache_file($pattern, {QuerySwitch=>'-J',
                                              CacheExpire=>$opt->{StatusExpire},
                                              %$opt,
                                   });  

          my $new = autorep_J("file=$file", $opt);

          next if ! $new;

          if ($status_ref) {
             $status_ref = {%$status_ref, %$new};
          } else {
             $status_ref = $new;
          }
      }
   } else {
      confess "don't know how to find universe: neither StatusFiles nor UnivPatterns is defined.";
   }

   my $warn = $opt->{verbose} ? 'use' : 'no';

   my $matchExps;
   if ($opt->{JobExps} && @{$opt->{JobExps}}) {
      @$matchExps = map {
         my $compiled = eval "$warn warnings; no strict; package TPSUP::Expression; sub { $_ } ";
         $@ ? (die "Bad match expression '$_' : $@") : $compiled;
      } @{$opt->{JobExps}};
   }

   my $return_ref;

   for my $job (keys %$status_ref) {
      my $r; 

      if (exists $detail_ref->{$job}) {
         $r = { %{$status_ref->{$job}}, %{$detail_ref->{$job}} };
      } else {
         $r = $status_ref->{$job};
      }

      $r->{JobName} = $job;

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

   return $return_ref;
}


sub get_dependency {
   my ($job2, $opt) = @_;

   my $all_ref = query_jobs($opt);

   $opt->{verbose} && print STDERR "all=", Dumper($all_ref);

   if (! $all_ref->{$job2}) {
      print STDERR "$job2 is not part of universe\n";
      return undef;
   }

   my $children_by_parent;
   my $children_by_box;
   for my $job (keys %$all_ref) {
      my $r = $all_ref->{$job};

      for my $cond_job (condition_to_jobs($r->{condition})) {
         push @{$children_by_parent->{$cond_job}}, $job;
      } 

      if ($r->{box_name}) {
         push @{$children_by_box->{$r->{box_name}}}, $job;
      } 
   }

   $opt->{verbose} && print STDERR "children=", Dumper($children_by_parent);

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
            push @next_level, ['box_child', $children_by_box->{$job}];
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

sub main {
   use Data::Dumper;
   print "autorep_J=", Dumper(autorep_J("file=autorep_J_example.txt")); 
   print "autorep_q_J=", Dumper(autorep_q_J("file=autorep_J_q_example.txt")); 
   print "get_dependency=", Dumper(get_dependency("test_job1", 
                                     {
                                        DetailFiles => "autorep_J_q_example.txt", 
                                        StatusFiles => "autorep_J_example.txt", 
                                        #verbose => 1,
                                     })); 
   
}

main() unless caller();

1
