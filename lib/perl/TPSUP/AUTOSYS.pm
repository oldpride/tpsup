#!/usr/bin/env perl

package TPSUP::AUTOSYS;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
      autorep_J
      autorep_q_J
      get_dependency
      get_univ_patterns
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
      $in_fh = open "$cmd |" or confess "cmd='$cmd' failed: $!";
   } else {
      confess "unknown input='$input'";
   }

   return $in_fh;
}

sub autorep_J {
   my ($input, $opt) = @_;

   if (!$input) {
      my $UnivPatterns = get_setting_from_env('UNIV_PATTERNS', 'TPAUTOSYS', get_homedir_by_user() . "/.tpautosys");
      $input = "command=autorep -J $UnivPatterns";
   } elsif ($input !~ /(file|command)=/) {
      # $input is a pattern
      $input = "command=autorep -J $input";
   }

   my $in_fh = get_autosys_fh($input, $opt);

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

   my $skip = 3;
   {
      my $i = 0;
      while ( $i<$skip && <$in_fh> ) {
         $i++;
      }
   }

   my $result;

   while (<$in_fh>) {
      my $line = $_;
      chomp $line;

      if ( $line =~ /^\s*(\S+?)\s+?(\S.{18})\s+?(\S.{18})\s+?(\S+)\s+/ ) {
         @{$result->{$1}}{qw(JobName LastStart LastEnd Status)} = ($1, $2, $3, $4);
      } else {
         print STDERR "unsupported format at line: $line\n";
      }
   }
   
   close $in_fh if $in_fh != \*STDIN;

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

   sub need_refresh {
      my ($f) = @_;
      return 1 if $opt->{Refresh};

      return 1 if ! -f $f;

      my ($dev,$ino,$mode,$nlink,$uid,$gid,$rdev,$size,$atime,$mtime,$ctime,$blksize,$blocks) = lstat($f);
      my $now_sec = time();
      my $expire_sec = $opt->{CacheExpire} ? $opt->{CacheExpire} : 3600 * 12;

      return 1 if $now_sec - $mtime > $expire_sec;

      return 0;
   }

   if (!need_refresh($file)) {
      $opt->{verbose} && print STDERR "we will use cached $file\n";
      return $file;
   }

   my $cmd = "autorep $QuerySwitch $pattern > $file";
   $opt->{verbose} && print STDERR "running cmd=$cmd\n";
   system($cmd);
   confess "cmd=$cmd failed: $!" if $?;

   return $file;
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
   for my $job (keys %$all_ref) {
      my $r = $all_ref->{$job};

      for my $cond_job (condition_to_jobs($r->{condition})) {
         push @{$children_by_parent->{$cond_job}}, $job;
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
   my $depth = 0;
   my $dependency;
   my $seen;

   sub trace_dependency {
      my ($serial, $job, $updown) = @_;

      $opt->{verbose} && print "trace_dependency($serial, $job, $updown)\n";

      my $r = $all_ref->{$job};

      if ($matchExps) {
         TPSUP::Expression::export_var($r, {RESET=>1});
         for my $e (@$matchExps) {
            if (! $e->()) {
               return;
            }
         }
      }

      push @{$dependency->{$updown}}, { detail => $r,
                                        serial => $serial,
                                      };
      my $i = 1;

      # just in case we got into a dead loop
      $depth ++;
      croak "exceeded max depth $max_depth" if $depth > $max_depth;

      my $box_name = $all_ref->{$job}->{box_name};
      if ($box_name) {
         if (!$seen->{$updown}->{$box_name}) {
            my $r = $all_ref->{$box_name};
            trace_dependency($serial.".$i", $box_name, $updown);
            $i++;
            $seen->{$updown}->{$box_name} = 1;
         }
      }

      my @next_level;
      if ($updown eq 'up') {
         @next_level = condition_to_jobs($all_ref->{$job}->{condition});
      } else {
         if ($children_by_parent->{$job}) {
            @next_level = @{$children_by_parent->{$job}}
         }
      }

      for my $j (@next_level) {
         if (!$seen->{$updown}->{$j}) {
            my $r = $all_ref->{$j};

            trace_dependency($serial.".$i", $j, $updown);
            $i++;
            $seen->{$updown}->{$j} = 1;
         } 
      } 
   }

   trace_dependency("-1", $job2, "up");
   trace_dependency( "1", $job2, "down");

   push @{$dependency->{'self'}}, { detail => $all_ref->{$job2},
                                    serial => "0",
                                  };

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
