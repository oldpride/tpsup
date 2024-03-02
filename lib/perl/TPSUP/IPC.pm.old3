package TPSUP::IPC;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(

);

use Carp;
use Data::Dumper;
$Data::Dumper::Sortkeys = 1;    # this sorts the Dumper output!
$Data::Dumper::Terse    = 1;    # print without "$VAR1="
use TPSUP::UTIL qw(get_timestamp parse_rc get_abs_path get_user);
use TPSUP::TMP  qw(get_tmp_file);
use IPC::Open3;
use POSIX ":sys_wait_h";
use IO::Select;
use IO::Pty;

my $default_child;

sub spawn {
   my ( $cmd, $opt ) = @_;
   # learned from Expect.pm

   my $verbose = $opt->{verbose};

   my $pty = IO::Pty->new;
   $pty->autoflush(1);

   my $child = {};
   $child->{pty} = $pty;
   $child->{cmd} = $cmd;

   # set up pipe to detect childs exec error
   pipe( FROM_CHILD,  TO_PARENT ) or die "Cannot open pipe: $!";
   pipe( FROM_PARENT, TO_CHILD )  or die "Cannot open pipe: $!";
   TO_PARENT->autoflush(1);
   TO_CHILD->autoflush(1);
   eval { fcntl( TO_PARENT, Fcntl::F_SETFD, Fcntl::FD_CLOEXEC ); };

   my $pid = fork;

   unless ( defined($pid) ) {
      warn "Cannot fork: $!" if $^W;
      return;
   }

   $child->{pid} = $pid;

   if ($pid) {
      # parent
      my $errno;
      close TO_PARENT;
      close FROM_PARENT;
      $pty->close_slave();
      # $pty->set_raw() if $pty->raw_pty and isatty($pty);
      close TO_CHILD;    # so child gets EOF and can go ahead

      # now wait for child exec (eof due to close-on-exit) or exec error
      print STDERR "waiting for child to exec\n" if $verbose;
      my $errstatus = sysread( FROM_CHILD, $errno, 256 );
      die "Cannot sync with child: $!" if not defined $errstatus;
      close FROM_CHILD;
      if ($errstatus) {
         $! = $errno + 0;
         warn "Cannot exec($cmd): $!\n" if $^W;
         return;
      }
   } else {
      # child
      close FROM_CHILD;
      close TO_CHILD;

      $pty->make_slave_controlling_terminal();
      my $slv = $pty->slave()
        or die "Cannot get slave: $!";

      # $slv->set_raw() if $pty->raw_pty;
      close($pty);

      # wait for parent before we detach
      my $buffer;

      print STDERR "waiting for parent to close TO_CHILD\n" if $verbose;
      my $errstatus = sysread( FROM_PARENT, $buffer, 256 );
      die "Cannot sync with parent: $!" if not defined $errstatus;
      close FROM_PARENT;

      close(STDIN);
      open( STDIN, "<&" . $slv->fileno() )
        or die "Couldn't reopen STDIN for reading, $!\n";
      close(STDOUT);
      open( STDOUT, ">&" . $slv->fileno() )
        or die "Couldn't reopen STDOUT for writing, $!\n";
      close(STDERR);
      open( STDERR, ">&" . $slv->fileno() )
        or die "Couldn't reopen STDERR for writing, $!\n";

      { exec($cmd) };
      print TO_PARENT $! + 0;
      die "Cannot exec($cmd): $!\n";

   }

   $default_child = $child;
   return $child;

}

sub init_child {
   my ( $cmd, $opt ) = @_;

   my $verbose = $opt->{verbose};

   my $child;
   my $child->{cmd} = $cmd;

   # this 1-liner is not working. the file handles are not assigned.
   # my $child->{pid} = open3( $child->{in}, $child->{out}, $child->{err}, $cmd ) or croak "open3 failed: $!";
   # so I have to do it the long way.
   my $child_stdin;
   my $child_stdout;
   my $child_stderr;
   my $child->{pid} = open3( $child_stdin, $child_stdout, $child_stderr, $cmd ) or croak "open3 failed: $!";

   $child_stdin->blocking(0);

   $child->{in}  = $child_stdin;
   $child->{out} = $child_stdout;
   $child->{err} = $child_stderr;

   $verbose && print STDERR "child = ", Dumper($child), "\n";

   $default_child = $child;

   return $child;
}

sub expect_child {
   my ( $patterns, $opt ) = @_;

   my $child = $opt->{child};

   if ( !$child ) {
      if ( !$default_child ) {
         croak "no child process is defined";
      } else {
         $child = $default_child;
      }
   }

   my $verbose = $opt->{verbose};
   my $timeout = $opt->{timeout};
   $timeout = 10 unless $timeout;
   my $logic = $opt->{logic};
   $logic = 'and' unless $logic;

   # patterns is an array of hash references
   # each hash reference has a key: pattern, and optional keys, eg, case_sensitive.

   my $expect_interval = 3;
   my $total_wait      = 0;
   my $data            = '';
   my $select          = IO::Select->new( $child->{pty}->fileno ) or die "IO::Select $!";

   my $matches = [];

   for my $r (@$patterns) {
      my $r2 = {%$r};    # matches is built on top of patterns.
      $r2->{matched} = 0;
      if ( $r2->{case_sensitive} ) {
         $r2->{compiled} = qr/$r2->{pattern}/;
      } else {
         $r2->{compiled} = qr/$r2->{pattern}/i;
      }
      push @$matches, $r2;
   }

   my $enrich = sub {
      # use this function to
      #   1. print verbose message
      #   2. enrich the return value
      my $v = shift;
      $v->{logic}           = $logic;
      $v->{timeout}         = $timeout;
      $v->{expect_interval} = $expect_interval;
      $v->{total_wait}      = $total_wait;
      $verbose && print STDERR "expect_child return: ", Dumper($v), "\n";
      return $v;
   };

   # check if the child is still alive
   if ( !$child->{pty}->fileno ) {
      return $enrich->( { error => "child process pty is closed", data => $data, matches => $matches } );
   }

   my $pid = waitpid( $child->{pid}, WNOHANG );
   if ( $pid == -1 ) {
      # croak "child process $child->{pid} is dead";
      return $enrich->( { error => "child process $child->{pid} is dead", data => $data, matches => $matches } );
   }

   while (1) {
      print STDERR "waiting $expect_interval seconds for child process $child->{pid} to output\n" if $verbose;
      if ( !$select->can_read($expect_interval) ) {
         $total_wait += $expect_interval;
         if ( $total_wait > $timeout ) {
            my $msg = "expect timed out after timeout seconds";
            print STDERR "$msg\n";
            return $enrich->( { error => $msg, data => $data, matches => $matches } );
         }
         $verbose && print STDERR "idled for $total_wait seconds.\n";
         next;
      }

      my $sub_data;
      my $size = read( $child->{pty}, $sub_data, 1024000 );
      if ( !defined($size) ) {
         print "child process $child->{pid} output is closed \n";
         return $enrich->(
            { error => "child process $child->{pid} output is closed", data => $data, matches => $matches } );
      }

      $data .= $sub_data;

      $verbose && print STDERR "read $size bytes from child process $child->{pid}\n";

      if ( $logic eq 'or' ) {
         my $i = 0;
         for my $r (@$matches) {
            if ( $data =~ /$r->{compiled}/ ) {
               $r->{matched} = 1;
               return $enrich->( { data => $data, matches => $matches } );
            }
         }
      } elsif ( $logic eq 'and' ) {
         my $all_matched = 1;
         for my $r (@$matches) {
            if ( $data =~ /$r->{compiled}/ ) {
               $r->{matched} = 1;
            } else {
               $all_matched = 0;
            }
         }

         if ($all_matched) {
            return $enrich->( { data => $data, matches => $matches } );
         }
      } else {
         croak "unsupported logic: $logic";
      }
   }
}

sub send_to_child {
   my ( $actions, $opt ) = @_;

   my $verbose = $opt->{verbose};
   my $child   = $opt->{child};

   if ( !$child ) {
      if ( !$default_child ) {
         croak "no child process is defined";
      } else {
         $child = $default_child;
      }
   }

   # actions is an array of hash references
   # each hash reference has a key: action, and optional keys, eg, data.

   for my $r (@$actions) {
      if ( $r->{action} eq 'send' ) {
         print { $child->{pty} } $r->{data};
      } elsif ( $r->{action} eq 'close' ) {
         close $child->{pty};
      } elsif ( $r->{action} eq 'wait' ) {
         waitpid( $child->{pid}, 0 );
      } elsif ( $r->{action} eq 'kill' ) {
         kill 9, $child->{pid};
      } else {
         croak "unsupported action: $r->{action}";
      }
   }
}

sub main {
   require TPSUP::TEST;

   my $test_code = <<'END';
   TPSUP::IPC::spawn( "sftp localhost", { verbose => 1 } );
   TPSUP::IPC::expect_child([ { pattern => 'password:' } ], { verbose => 1 } );
   TPSUP::IPC::send_to_child([ { action => 'send', data => 'password\n' } ], { verbose => 1 } );
   TPSUP::IPC::expect_child([ { pattern => 'password:' } ], { verbose => 1 } );
   TPSUP::IPC::send_to_child([ { action => 'close' } ], { verbose => 1 } );
   sleep 1;
   TPSUP::IPC::send_to_child([ { action => 'kill' } ], { verbose => 1 } );
   sleep 1;
   TPSUP::IPC::send_to_child([ { action => 'wait' } ], { verbose => 1 } );
END

   TPSUP::TEST::test_lines($test_code);
}

main() unless caller;

1;
