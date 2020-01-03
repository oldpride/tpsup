#!/usr/bin/env perl

package TPSUP::AUTOSYS;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
      autorep_J
      autorep_q_J
      get_dependency
);
      
use Carp;
use Data::Dumper;
use TPSUP::UTIL qw(get_in_fh get_out_fh get_homedir_by_user);

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
      while ( <$in_fh> && $i<$skip ) {
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

   my $file  = get_homedir_by_user;

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


sub get_dependency {
   my ($job2, $opt) = @_;

   my $detail_ref; 
   my $status_ref; 
   
   if ($opt->{DetailFiles}) {
      for my $file (split /,/, $opt->{DetailFiles}) {
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

      if (! $detail_ref->{$job2}) {
         print STDERR "$job2 is not part: $opt->{DetailFiles}\n";
         return undef;
      }
   } elsif ($opt->{UnivPatterns}) {
      # APP1%|APP2%
      for my $pattern (split /[|]/, $opt->{UnivPatterns}) {
         my $file = get_cache_file($pattern, {QuerySwitch=>'-q -J',
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

      if (! $detail_ref->{$job2}) {
         print STDERR "$job2 is not part: $opt->{UnivPatterns}\n";
         return undef;
      }
   } else {
      confess "don't know how to find universe: neither DetailFiles nor UnivPatterns is defined.";
   }

   if ($opt->{StatusFiles}) {
      for my $file (split /,/, $opt->{StatusFiles}) {
         $file =~ s/\s+//;
         $file =~ s/\s+$//;
         my $new = autorep_J("file=$file", $opt);

         next if ! $new;

         if ($status_ref) {
            $status_ref = {%$status_ref, %$new};
         } else {
            $status_ref = $new;
         }                          'box_name' => 'test_box1',

      }
   } elsif ($opt->{UnivPatterns}) {
      # APP1%|APP2%
      for my $pattern (split /[|]/, $opt->{UnivPatterns}) {
         my $file = get_cache_file($pattern, {QuerySwitch=>'-J',
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

   my $children_by_parent;
   for my $job (keys %$detail_ref) {
      for my $cond_job (condition_to_jobs($detail_ref->{$job}->{condition})) {
         push @{$children_by_parent->{$cond_job}}, $job;
      } 
   }
    
   $opt->{verbose} && print STDERR "detail=", Dumper($detail_ref);
   $opt->{verbose} && print STDERR "status=", Dumper($status_ref);
   $opt->{verbose} && print STDERR "children=", Dumper($children_by_parent);

   my $max_depth = 100;
   my $depth = 0;
   my $dependency;
   my $seen;

   sub trace_dependency {
      my ($serial, $job, $updown) = @_;

      $opt->{verbose} && print "trace_dependency($serial, $job, $updown)\n";

      my $i = 1;

      # just in case we got into a dead loop
      $depth ++;
      croak "exceeded max depth $max_depth" if $depth > $max_depth;

      my $box_name = $detail_ref->{$job}->{box_name};
      if ($box_name) {
         if (!$seen->{$updown}->{$box_name}) {
            my $status = $status_ref->{$box_name}->{Status};
            $status = "UNKNOWN" if !defined $status;

            push @{$dependency->{$updown}}, 
               [$serial.".$i", $status_ref->{$box_name}, $detail_ref->{$box_name}];
            trace_dependency($serial.".$i", $box_name, $updown);
            $i++;
            $seen->{$updown}->{$box_name} = 1;
         }
      }

      my @next_level;
      if ($updown eq 'up') {
         @next_level = condition_to_jobs($detail_ref->{$job}->{condition});
      } else {
         if ($children_by_parent->{$job}) {
            @next_level = @{$children_by_parent->{$job}}
         }
      }

      for my $j (@next_level) {
         if (!$seen->{$updown}->{$j}) {
            my $status = $status_ref->{$j}->{Status};
            $status = "UNKNOWN" if !defined $status;

            push @{$dependency->{$updown}},
               [$serial.".$i", $status_ref->{$j}, $detail_ref->{$j}];
            trace_dependency($serial.".$i", $j, $updown);
            $i++;
            $seen->{$updown}->{$j} = 1;
         } 
      } 
   }

   my $starting_serial = "1";

   trace_dependency($starting_serial, $job2, "up");
   trace_dependency($starting_serial, $job2, "down");

   push @{$dependency->{'self'}},
       [$starting_serial, $status_ref->{$job2}, $detail_ref->{$job2}];

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
