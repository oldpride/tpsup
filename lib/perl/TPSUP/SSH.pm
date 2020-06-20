package TPSUP::SSH;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   tpssh
   get_local_login
   get_remote_login_host
);

use Carp;
use Data::Dumper;
use TPSUP::UTIL qw(get_timestamp get_tmp_file);

my $local_login;
sub get_local_login {
   if (!$local_login) {
      $local_login = `id | cut -d\\\( -f2 | cut -d\\\) -f1`;
      chomp $local_login;
   }

   return $local_login;
}

sub get_remote_login_host {
   my ($remote, $opt) = @_;

   my $login;
   my $host;

   if ( $remote =~ /(\S+)\@(\S+)/ ) {
      $login = $1;
      $host  = $2;
   } elsif ($opt->{remote_login}) {
      $login = $opt->{remote_login};
      $host  = $remote;
   } else {
      $login = get_local_login();
      $host = $remote
   }

   return ($login, $host);
}

sub tpssh {
   my ($action, $host, $args, $opt) = @_;
   # $host could be host, or login@host. login could also come from $opt
   my ($remote_login, $remote_host) = get_remote_login_host($host, $opt);
   
   my $verbose = $opt->{verbose};

   my $extra_ssh = "";

   $extra_ssh .= "-q" if !$verbose;

   if ($opt->{sshargs}) {
      $extra_ssh .= " " . join(" ", @{$opt->{sshargs}}) ;
   }

   my $ConnectTimeout = $opt->{ConnectTimeout} ? $opt->{ConnectTimeout} : 3;

   my $stdout = !$opt->{stdout}             ? ""                 :
                 $opt->{stdout} eq 'stderr' ? '>&2'              :
                                              ">$opt->{stdout}"  ;

   my $stderr = !$opt->{stderr}             ? ""                 :
                 $opt->{stderr} eq 'stdout' ? '2>&1'             :
                                              "2>$opt->{stderr}" ;

   my $cmd;
   my $dryrun_cmd;

   if ($action eq 'scp') {
      my $command = join(' ', @$args);

      $cmd =   "scp -o StrictHostKeyChecking=no -o ConnectTimeout=$ConnectTimeout"
             . " -o BatchMode=yes $extra_ssh $command $stdout $stderr";
      $dryrun_cmd = "scp $command";
   } elsif ($action eq 'ssh') {
      my $local_login = get_local_login();
   
      my $unique_string;
      {
          # get the calling script path
          my ($package, $filename, $line) = caller;
          my $unique_string = $filename;
   
          # get the script name
          $unique_string =~ s:.*/::;
   
          my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime(time);
          $unique_string =  substr($unique_string, 0, 10)
                          . sprintf("%02d%02d%02d", $hour, $min, $sec);
      }
        
      # use "l" and "r" to distinguish between local and remote in case we do "ssh localhost"
      my  $local_cmd_file = get_tmp_file("/var/tmp", $unique_string . "l");
      my $remote_cmd_file = get_tmp_file("/var/tmp", $unique_string . "r");
   
      $remote_cmd_file =~ s:/var/tmp/tmp_${local_login}:/var/tmp/tmp_${remote_login}:;
   
      my $verbose = $opt->{verbose} ? 1 : 0;
   
      $verbose && print STDERR  "local_cmd_file = $local_cmd_file\n";
      $verbose && print STDERR "remote_cmd_file = $remote_cmd_file\n";
   
      my ($ldir, $lfile) =  ($local_cmd_file =~ m:^(.*)/(.*):);
      my ($rdir, $rfile) = ($remote_cmd_file =~ m:^(.*)/(.*):);
   
      open my $cfh, ">$local_cmd_file" or die "cannot write to $local_cmd_file";
   
      if ($opt->{style} eq 'bash') {
         print {$cfh} "#!/bin/bash\n\n";
         print {$cfh} join(" ", @$args), "\n";
      } else {
         # default to perl style
         print {$cfh} <<"EOF";
#!/usr/bin/perl

use strict;
use warnings;

my \$verbose = $verbose;

EOF

         print {$cfh} "my ", Dumper(\@ARGV), "\n";
      
         #print {$cfh} qq(\$ENV{PATH}="/usr/bin:/bin:\$ENV{PATH}";\n);
         
         if (!$opt->{timeout}) {
            print {$cfh} "exec \@\$VAR1;\n";
         } else {
            print {$cfh} "my \$seconds = $opt->{timeout};\n\n";
         
            while (<DATA>) {
               print {$cfh} $_;
            }
         }
      }
   
      close $cfh;
   
      system("chmod 744 $local_cmd_file");
      $? && exit 1;
   
      $verbose && system("cat $local_cmd_file") ;
   
      # idea was coming from:
      # http://unix.stackexchange.com/questions/57807/copy-over-ssh-and-execute-commands-in-one-session
      # $cmd = "tar cf - -C $ldir $lfile | ssh -o StrictHostKeyChecking=no -o ConnectTimeout=2 -o BatchMode=yes \\
      # ${ remote_login}\@${host} 'OWD=`pwd`; mkdir -p $rdir && cd $rdir && tar xf - && cd \$OWD && $remote_cmd_file'";
      
      $cmd =   "cat $local_cmd_file|"
             . " ssh -o StrictHostKeyChecking=no -o ConnectTimeout=$ConnectTimeout -o BatchMode=yes"
             . " $extra_ssh $remote_login\@$remote_host"
             . " 'mkdir -p $rdir && cat >$remote_cmd_file && chmod u+rx $remote_cmd_file && $remote_cmd_file' $stdout $stderr";
      $dryrun_cmd = "ssh $remote_login\@$remote_host " . join(" ", @$args);
   } else {
      croak "unknown action='$action'. expecting 'ssh' or 'scp'";
   }

   $verbose && print "cmd = $cmd\n";

   if ($opt->{dryrun}) {
      print "dryrun (not exact) = $dryrun_cmd\n";
   } else {
      exec("$cmd");
   }
}

1

__DATA__
my $child_pid = fork();

if ($child_pid) {
   # this is parent
   $SIG{ALRM} = sub {
      my $os = `/bin/uname`; chomp $os;
      my $cmd;

      if ($os eq "SunOS") {
         $cmd = "/usr/bin/ptree $child_pid";
      } elsif ($os eq "Linux") {
         $cmd = "/usr/bin/pstree -pal $child_pid";
      } else {
         print STDERR "os=$os is not supported. cannot time out.";
         return;
      }

      my @lines = `$cmd 2>/dev/null`;
      if ($?) {
         print STDERR "cannot time out because '$cmd' failed: $!\n";
         return;
      }

      my $HHMMSS = `date +%H:%M:%S`; chomp $HHMMSS;
      print STDERR "$HHMMSS timed out after $seconds seconds, killing pid=$child_pid. return code set to 1\n";

      if ($verbose) {
         print STDERR "\n";
         print STDERR "cmd=$cmd\n";
         print STDERR @lines; 
      }

      my @to_be_killed;

      if ($os eq "SunOS") {
         # Solaris
         # $ /usr/bin/ptree 713
         # 7994 zsched
         # 9307 /usr/lib/ssh/sshd
         # 12609 /usr/lib/ssh/sshd
         # 12610 /usr/lib/ssh/sshd
         # 12649 -ksh
         # 713 /usr/bin/perl /home/gpt/tpsup/scripts/localstart sleep_l sleep
         # 745 sleep 1000
      
         for my $l (@lines) {
            
            if ($l =~ /^\s*(\d+)/) {
               my $p = $1;
      
               $verbose && print "kill $p\n";
      
               kill('TERM', $p);
               push @to_be_killed, $p;
            }
         }
      } elsif ($os eq "Linux") {
         # /usr/bin/pstree -pal 72199--
         # localstart,72199 /home/tian/scripts/localstart sleep_l sleep 10000
         # "-sleep,72216 10000
      
         for my $l (@lines) {
            if ($l =~ /^.*?,(\d+)/) {
               my $p = $1;
      
               $verbose && print "kill $p\n";
      
               kill('TERM', $p);
               push @to_be_killed, $p;
            }
         }
      }
      
      my $wait_time = 1;
      my $has_waited = 0;
      for my $p (@to_be_killed) {
         # wait the process to handle the signal
      
         while($has_waited < $wait_time) {
            if (-d "/proc/$p") {
               sleep 1;
               $has_waited ++;
            } else {
               last;
            }
      
            # if the child process does not exit, kill -9
            if (-d "/proc/$p") {
               $verbose && print "kill -9 $p\n";
               kill (9, $p);
            }
         }
      }

      waitpid(-1, 0) ;

      exit 1;
   };

   alarm $seconds;

   if (waitpid(-1, 0) ) {
      my $rc = $?;

      alarm 0; # clear the alarm

      my $HHMMSS = `date +%H:%M:%S`; chomp $HHMMSS;
      if ($? & 127) {
         $verbose && printf STDERR "$HHMMSS child died with signal %d, %s coredump\n",
                                   ($? & 127), ($? & 128) ? 'with' : 'without';
         exit 1;
      } else {
         my $return_code = $? >> 8;
         $verbose && printf STDERR "$HHMMSS child exited with value %d\n", $return_code;
         exit $return_code;
      }
   }
} elsif ($child_pid == 0) {
   if ($verbose) {
      # this is child
      my $HHMMSS = `date +%H:%M:%S`; chomp $HHMMSS;
      print STDERR "$HHMMSS cmd=", join(' ', @$VAR1), "\n";
   }

   exec @$VAR1;
} else {
   die "ERROR: Could not fork new process: $!\n";
}
      
      
      
