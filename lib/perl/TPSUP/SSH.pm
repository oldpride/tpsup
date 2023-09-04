#!/usr/bin/env perl

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
$Data::Dumper::Sortkeys = 1;  # this sorts the Dumper output!
$Data::Dumper::Terse = 1;     # print without "$VAR1="
use TPSUP::UTIL qw(get_timestamp get_tmp_file parse_rc get_abs_path);

my $timeout_rc = 254;

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


   # this is the cmd timeout, not the ssh handshake ConnectTimeout
   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;
   my $profile = $opt->{profile};
   my $timeout = defined($opt->{timeout}) ? $opt->{timeout} : -1;

   # system/exec takes both Array and String
   #     exec @Array
   #     exec $String
   #
   # Pro and Con 
   #      Array                 |  String
   #    ----------------------------------------------------
   #    exec 'ls', '/etc/hosts' |  exec 'ls /etc/hosts'
   #    better variable border  |  can handle pipe (|)
   #    handle quotes better    |  can handle wildcard, ie, glob(): *, ?
   #
   # therefore, we add $opt->{GlobArray} to glob() in Array type. but there is
   # a detrimental effect. for example, in
   #    egrep "pattern.*" myfile.txt
   # if we glob("pattern.*"), it becomes blank, try below
   #    $ perl -e 'print glob("pattern.*"), "\n";'
   #
   # therefore, try not to use wildcard (*, ?) or pipe (|) when ExecArgType = Array

   my $ExecArgType = $opt->{ExecArgType} ? $opt->{ExecArgType} : "Array";
   my $GlobArray   = $opt->{GlobArray}   ? $opt->{GlobArray}   : 0;
   
   $verbose && print "tpssh opt = ", Dumper($opt);

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
   
      my $unique_string = "dir_";
      {
          # get the calling script path
          my ($package, $filename, $line) = caller;

          # get the script name
          $filename =~ s:.*/::;

          $unique_string .= $filename;
   
          my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime(time);
          $unique_string =  substr($unique_string, 0, 10)
                          . sprintf("%02d%02d%02d", $hour, $min, $sec);
      }
        
      # use "l" and "r" to distinguish between local and remote in case we do "ssh localhost"
      my $dir0  = get_tmp_file("/var/tmp", $unique_string, {IsDir=>1});
      my $cmdfile = "cmd";

      my $ldir  = "${dir0}.L";
      my $local_cmd_file = "$ldir/$cmdfile";

      my $rdir  = "${dir0}.R";
         $rdir  =~ s:/var/tmp/tmp_${local_login}:/var/tmp/tmp_${remote_login}:;
      my $remote_cmd_file = "$rdir/$cmdfile";

      $verbose && print STDERR  "local_cmd_file = $local_cmd_file\n";
      $verbose && print STDERR "remote_cmd_file = $remote_cmd_file\n";
   
      if (!-d $ldir) {
         system("mkdir -p $ldir");
         confess "mkdir -p $ldir failed" if $? != 0;
      }

      if (defined $opt->{copy}) {
         my $src = $opt->{copy};
         my $abs_path = get_abs_path($src);
         my ($dir, $file) = ($abs_path =~ m:^(.+)/([^/]+)$:);

         my $cmd = "cd $dir; tar cf - $file | (cd $ldir; tar xf -)";
         $verbose && print STDERR "cmd = $cmd\n";
         system($cmd) && exit 1;
      }

      open my $cfh, ">$local_cmd_file" or die "cannot write to $local_cmd_file";
   
      if ($opt->{style} eq 'bash') {
         print {$cfh} "#!/bin/bash\n\n";
         print {$cfh} join(" ", @$args), "\n";
      } else {
         # default to perl style
         # use single quote  in heredoc to disable interpolation
         # use double quotes in heredoc to  enable interpolation
         print {$cfh} <<"EOF";   
#!/usr/bin/perl

use strict;
use warnings;
use Data::Dumper;
\$Data::Dumper::Sortkeys = 1;  # this sorts the Dumper output!
\$Data::Dumper::Terse = 1;     # print without "\$VAR1="

my \$verbose     = $verbose;
my \$seconds     = $timeout;
my \$ExecArgType = "$ExecArgType";
my \$GlobArray   = $GlobArray;
my \$timeout_rc  = $timeout_rc;

EOF

         print {$cfh} "my \$ARGS=", Dumper($args), ";\n";
      
         #print {$cfh} qq(\$ENV{PATH}="/usr/bin:/bin:\$ENV{PATH}";\n);
         
         # use single quote  in heredoc to disable interpolation
         # use double quotes in heredoc to  enable interpolation
         print {$cfh} <<'EOF';
$verbose && print STDERR Dumper($ARGS);

if ($seconds == -1) {
   # when system/exec run with array, the arg's wildcard will not be resolved by glob
   #    perl -e 'system "ls", "*";'
   #    perl -e 'exec   "ls", "*";'
   # you get error: ls: cannot access '*': No such file or directory
   #
   # when system/exec run with string, the arg's wildcard will be resolved by glob
   #    perl -e 'system "ls *";'
   #    perl -e 'exec   "ls *";'

   if ($ExecArgType =~ /^Array$/i) {
      if ($GlobArray) {
         my @globbed = map {glob($_)} @$ARGS;
         $verbose && print STDERR "globbed = ", Dumper(\@globbed);
         exec @globbed;
      } else {
         exec @$ARGS;
      }
   } else {
      # default to $ExecArgType = /^String$/i
      my $cmd = join(" ", @$ARGS);
      $verbose && print STDERR "cmd = $cmd\n";
      exec $cmd;
   }
}

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

      print STDERR "$HHMMSS timed out after $seconds seconds, killing pid=$child_pid. return code set to $timeout_rc\n";

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

      exit $timeout_rc;
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
      print STDERR "$HHMMSS cmd=", join(' ', @$ARGS), "\n";
   }

   if ($ExecArgType =~ /^Array$/i) {
      if ($GlobArray) {
         my @globbed = map {glob($_)} @$ARGS;
         $verbose && print STDERR "globbed = ", Dumper(\@globbed);
         exec @globbed;
      } else {
         exec @$ARGS;
      }
   } else {
      # default to $ExecArgType = /^String$/i
      my $cmd = join(" ", @$ARGS);
      $verbose && print STDERR "cmd = $cmd\n";
      exec $cmd;
   }
} else {
   die "ERROR: Could not fork new process: $!\n";
}

EOF
      }
   
      close $cfh;
   
      system("chmod 744 $local_cmd_file");
      $? && exit 1;
   
      $verbose && system("cat $local_cmd_file") ;
   
      # idea was coming from:
      # http://unix.stackexchange.com/questions/57807/copy-over-ssh-and-execute-commands-in-one-session
      # $cmd = "tar cf - -C $ldir $cmdfile | ssh -o StrictHostKeyChecking=no -o ConnectTimeout=2 -o BatchMode=yes \\
      # ${ remote_login}\@${host} 'OWD=`pwd`; mkdir -p $rdir && cd $rdir && tar xf - && cd \$OWD && $remote_cmd_file'";
      
      #$cmd =   "cat $local_cmd_file|"
      $cmd =   "cd $ldir; tar -cf - .|"
             . " ssh -o StrictHostKeyChecking=no -o ConnectTimeout=$ConnectTimeout -o BatchMode=yes"
             . " $extra_ssh $remote_login\@$remote_host"
             . " '";
             
      $cmd .= ". $profile; " if $profile;
      $cmd .= "RDIR=$rdir; export RDIR;";
      #$cmd .= " mkdir -p $rdir && cat >$remote_cmd_file && chmod u+rx $remote_cmd_file && $remote_cmd_file' $stdout $stderr";
      #$cmd .= ' mkdir -p $RDIR && cat >$RDIR/' . $cmdfile . ' && chmod u+rx $RDIR/' . $cmdfile .
      $cmd .= ' mkdir -p $RDIR && chmod u+rx $RDIR && cd $RDIR && tar -xf - && $RDIR/'
              . $cmdfile . "' $stdout $stderr";

      $dryrun_cmd = "ssh $remote_login\@$remote_host " . join(" ", @$args);
   } else {
      croak "unknown action='$action'. expecting 'ssh' or 'scp'";
   }

   $verbose && print "cmd = $cmd\n";

   if ($opt->{dryrun}) {
      print "dryrun (not exact) = $dryrun_cmd\n";
   } else {
      if (!$opt->{ExecMethod} || $opt->{ExecMethod} =~ /^system$/i) { 
         system($cmd);
         my $rc = $?;
         my $r = parse_rc($rc);
         if ($r->{rc} == 255) {
            print STDERR "ssh connection to $remote_login\@$remote_host failed\n";
         } elsif ($r->{rc} == $timeout_rc) {
            print STDERR "remote cmd timed out.\n";
         }

         $verbose && print STDERR "r=", Dumper($r);

         return $rc;
      } elsif ($opt->{ExecMethod} =~ /^exec$/ ) { 
         exec($cmd);
      } else {
         confess "unsupport exec=$opt->{ExecMethod}";
      }
   }
}

sub main {
   use Getopt::Long;

   my $prog = $0; $prog =~ s:.*/::;  
   
   sub usage {
      my ($message) = @_; 
   
      print "$message\n" if $message;  
   
      print << "END";  
   usage:  
   
      $0               host -- command
   
      $0 remote_login\@host -- command  
   
      $0 remote_login\@host -f local_file
   
   description:  
   
      An alertnative to ssh to better handle command args, in particular, ' and ".
   
      It runs in BatchMode only, no interactive shell.  
   
      -l login            remote login
      -v                  verbose mode
      -sshargs string     args to pass to generic ssh command. can set multiple times.
   
      -style bash|perl    Default to 'perl', because perl handles ' and " much better.
                          Can also be 'bash'.
   
      -timeout number     time out after this number of seconds, default to no timeout.  
   
      -copy path          copy this path from local host to remove temp folder.
                          The path can be a file or directory.

      -cpRun              copy and run the first arg on the remote host. this is a
                          shortcut for -copy path. see example below.
                          it is good way to run a standalone script.

      -ExecMethod  System|Exec
                          use system() or exec(). 
                          When using System, "ssh connection failure" can be reported;
                          therefore it is better when running standalone, eg, tpssh.
                          Exec is better when called by mssh which waitpid() on the pids. 
                          this script is default to System

      -ExecArgType Array|String
                          Array:  good at handling quotes, better arg border
                          String: good at handling  wildcard (*,?) and pipe (|)
                          default to String.

      -GlobArray          apply glob() when ExecArgType is Array.
                          may have detrimental effort, be careful.
                          default is not to apply glob() to Array.
   
   examples:  
   
      $prog         linux1 ls '/etc/hosts*'
      $prog -l tian linux1 ls '/etc/hosts*'
      $prog    tian\@linux1 ls '/etc/hosts*'
   
      - use -- to handle tricky options, eg "-l" is both an arg of ls and $prog, compare
      $prog    linux1 ls -l '/etc/hosts*' 
      $prog -- linux1 ls -l '/etc/hosts*' 
      
      - test timout
      $prog -t 3 linux1 -- 'while :;do date;hostname;id;sleep 1; done'
   
      - test -sshargs
      $prog -sshargs=-q linux1 hostname
   
      - test pipe, wildcards
      $prog linux1 'ls -l /etc/hosts*'
      $prog linux1 'ls -l /etc/hosts*|tail -1'
   
      - test mixed quotes, better to use "-ExecArgType Array". compare
      $prog                    -- linux1 perl -e 'print join(",", lstat("/bin")), "\\n";'
      $prog -ExecArgType Array -- linux1 perl -e 'print join(",", lstat("/bin")), "\\n";'
   
      - this command should return "No such file or directory", compare
      $prog                    linux1 ls '/etc /usr' |head
      $prog -ExecArgType Array linux1 ls '/etc /usr' |head

      - test -copy and -cpRun
      $prog -copy tpssh_test_local.bash linux1 '\$RDIR/tpssh_test_local.bash'
      $prog -copy tpssh_test_local.pl   linux1 '\$RDIR/tpssh_test_local.pl'

      $prog -cpRun linux1 ./tpssh_test_local.bash
      $prog -cpRun linux1 ./tpssh_test_local.pl

END
   
      exit 1;
   }
   
   my $verbose;
   my $remote_login;
   my $style = 'perl';
   my @sshargs;
   my $timeout = -1;
   my $copy;
   my $cpRun;
   my $ExecMethod  = "System";
   my $ExecArgType = "String";
   my $GlobArray   = 0;
   
   GetOptions(
      'v|verbose'    => \$verbose,
      'l=s'          => \$remote_login,
      'style=s'      => \$style,
      'sshargs=s'    => \@sshargs,
      't|timeout=s'  => \$timeout,
      'ExecMethod=s' => \$ExecMethod,
      'ExecArgType=s'=> \$ExecArgType,
      'GlobArray'    => \$GlobArray,
      'copy=s'       => \$copy,
      'cpRun'        => \$cpRun,
   ) || usage("cannot parse command line: $!");
   
   usage("wrong number of args") if @ARGV < 2;
   
   my ($host) = shift @ARGV;
   
   $verbose && print "command = ", Dumper (\@ARGV) ;
   
   my $opt = {
      style        => $style,
      timeout      => $timeout,
      remote_login => $remote_login,
      ExecMethod   => $ExecMethod,
      ExecArgType  => $ExecArgType,
      GlobArray    => $GlobArray,
      sshargs      => \@sshargs,
      verbose      => $verbose,
      copy         => $copy,
   };

   if ($cpRun) {
      $opt->{copy} = $ARGV[0];
      $ARGV[0] =~ s:.*/::;
      $ARGV[0] = "\$RDIR/$ARGV[0]";
   }
   
   my $rc = tpssh('ssh', $host, \@ARGV, $opt);
   my $r = parse_rc($rc);
   exit $r->{rc};
}

main() unless caller();

1

