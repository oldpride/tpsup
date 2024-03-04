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
use POSIX qw(:sys_wait_h :unistd_h);    # For WNOHANG and isatty
use IO::Pty;
use IO::Select;
use Symbol 'gensym';                    # vivify a separate handle for STDERR for open3()

my $current_child;

sub init_child {
   my ( $cmd, $opt ) = @_;

   my $verbose = $opt->{verbose};

   my $child;
   if ( !$opt->{method} || $opt->{method} eq 'open3' ) {
      $child = ipc_open3( $cmd, $opt );
   } elsif ( $opt->{method} eq 'pty' ) {
      $child = spawn_pty( $cmd, $opt );
   } else {
      croak "unsupported method: $opt->{method}";
   }

   $current_child = $child;
   $verbose && print STDERR "current_child = ", Dumper($current_child), "\n";

   return $child;
}

# Expect spawn() vs IPC::Open3 open3()
#     Expect spawn() can handle subprocess outputs
#     https://unix.stackexchange.com/questions/771371
#     IPC::Open3 open3() can is cleaner

# spawn() is copied from Expect.pm
# There, Expect is a subclass of IO::Pty.
sub spawn_pty {
   my ( $cmd, $opt ) = @_;

   my $verbose = $opt->{verbose};

   my $pty = IO::Pty->new;
   $pty->autoflush(1);

   my $child = {};
   $child->{pty}    = $pty;
   $child->{cmd}    = $cmd;
   $child->{method} = 'pty';

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
      # $pty->set_raw() if $pty->raw_pty() and isatty($pty);
      $pty->set_raw() if isatty($pty);
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
      $slv->set_raw();
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

   # parent again
   $child->{Tty}       = $pty->ttyname();
   $child->{fh}->{in}  = $pty;
   $child->{fh}->{out} = $pty;

   return $child;
}

sub ipc_open3 {
   my ( $cmd, $opt ) = @_;

   my $verbose = $opt->{verbose};

   my $child;
   $child->{cmd}    = $cmd;
   $child->{method} = 'open3';

   $child->{pid} = open3( $child->{fh}->{in}, $child->{fh}->{out}, $child->{fh}->{err} = gensym, $cmd )
     or croak "open3 failed: $!";

   return $child;
}

# convert control characters to '.'
sub clean_data {
   my $data = shift;
   # 's/(?!\t)[[:cntrl:]]//g';    # remove control characters except tab
   $data =~ s/[^a-zA-Z0-9.~!@#$%^&*()=\[\]{}+|\\:;'"?\/<>, `_-]/./g;
   return $data;
}

sub expect_child {
   my ( $patterns, $opt ) = @_;

   my $child = $opt->{child};

   if ( !$child ) {
      if ( !$current_child ) {
         croak "no child process is defined";
      } else {
         $child = $current_child;
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
   my $data            = {};

   # https://perldoc.perl.org/functions/select
   # my $readmask = '';
   # if ($child->{method} eq 'open3') {
   #    vec( $readmask, $child->{out}->fileno, 1 ) = 1;
   #    vec( $readmask, $child->{err}->fileno, 1 ) = 1;
   # } elsif ($child->{method} eq 'pty') {
   #    vec( $readmask, $child->{pty}->fileno, 1 ) = 1;
   # } else {
   #    croak "unsupported method: $child->{method}";
   # }

   # IO::Select is more user friendly than select
   # IO::Select is a wrapper around select, handling the bit mask for you.
   # https://perldoc.perl.org/IO::Select
   # my $select = IO::Select->new();
   # for my $fh_name (qw(out err)) {
   #    if ( defined $child->{fh}->{$fh_name} ) {
   #       $verbose && print STDERR "add $fh_name to select\n";
   #       $select->add( $child->{fh}->{$fh_name} );
   #    }
   # }

   # $verbose && print STDERR "select = ", Dumper($select), "\n";

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

      $verbose && print STDERR "expect_child input: ", Dumper($v), "\n";

      $v->{logic}           = $logic;
      $v->{timeout}         = $timeout;
      $v->{expect_interval} = $expect_interval;
      $v->{total_wait}      = $total_wait;
      if ( exists $v->{data} ) {
         my $data2 = $v->{data};
         for my $c ( keys %$data2 ) {
            $data2->{$c}->{clean} = clean_data( $data2->{$c}->{raw} );
         }
      }

      $verbose && print STDERR "expect_child return: ", Dumper($v), "\n";
      return $v;
   };

   my $pid = waitpid( $child->{pid}, WNOHANG );
   if ( $pid == -1 ) {
      print STDERR "INFO: child pid=$child->{pid} is dead";
   }

   my $start_seconds = time();
   my $loop_count    = 0;
   my $closed_fh     = {};

   while (1) {
      my $some_fh_open = 0;
      my $select       = IO::Select->new();
      for my $fh_name (qw(out err)) {
         if ( $closed_fh->{$fh_name} ) {
            next;
         }
         if ( defined $child->{fh}->{$fh_name} ) {
            $verbose && print STDERR "add $fh_name to select\n";
            $select->add( $child->{fh}->{$fh_name} );
            $some_fh_open = 1;
         }
      }
      $verbose && print STDERR "select = ", Dumper($select), "\n";

      if ( !$some_fh_open ) {
         return $enrich->( { data => $data, matches => $matches } );
      }

      $verbose && print STDERR "waiting $expect_interval seconds for child process $child->{pid} to output\n";

      # catch busy loop
      $loop_count++;
      if ( $loop_count % 10 == 0 ) {
         my $elapsed_seconds = time() - $start_seconds;
         if ( $elapsed_seconds < 20 ) {
            croak "expect_child is in a busy loop. elapsed_seconds=$elapsed_seconds, loop_count=$loop_count";
         }
      }

      for my $c (qw(out err)) {
         if ( defined $child->{fh}->{$c} ) {
            # $child->{fh}->{$c}->autoflush(0); # autoflush(0) is for write. non-blocking write.
            $child->{fh}->{$c}->blocking(0);    # blocking(0)  is for read.  non-blocking read.
         }
      }

      # select() is working, but IO::Select is more user friendly.
      # my $nfound = select(
      #    $readmask,
      #    undef,    # write mask
      #    undef,    # exception mask
      #    $expect_interval
      # );
      my @ready = $select->can_read($expect_interval);

      if ( !@ready ) {
         $total_wait += $expect_interval;
         if ( $total_wait > $timeout ) {
            my $msg = "expect timed out after timeout seconds";
            print STDERR "$msg\n";
            return $enrich->( { error => $msg, data => $data, matches => $matches } );
         }
         $verbose && print STDERR "idled for $total_wait seconds.\n";
         next;
      } else {
         $verbose && print STDERR "child process $child->{pid} pty has data to read\n";
      }

      if ( $child->{method} eq 'pty' ) {
         $verbose && print STDERR "child process $child->{pid} pty is non-blocking read\n";
         # $child->{pty}->autoflush(0);    # autoflush(0) is for write. non-blocking write.
         $child->{pty}->blocking(0);    # blocking(0) is for read. non-blocking read.
      }

      my $size_by_fh = {};

      for my $fh (@ready) {
         my $sub_data;
         # my $sub_size = read( $child->{pty}, $sub_data, 1024000 );
         my $sub_size = read( $fh, $sub_data, 1024000 );

         # reverse lookup the file handle name, kind awkward.
         my $fh_name;
         for my $c (qw(out err)) {
            if ( $child->{fh}->{$c} == $fh ) {
               $fh_name = $c;
               last;
            }
         }

         if ($fh_name) {
            $verbose && print STDERR "read from file_handle=$fh_name, sub_size=$sub_size\n";
         } else {
            croak "child pid=$child->{pid} file_handle=$fh is not recognized";
         }

         if ( !defined($sub_size) ) {
            my $msg = "child pid=$child->{pid} file_handle=$fh_name is closed";
            print STDERR "$msg\n";
            # return $enrich->( { error => $msg, data => $data, matches => $matches } );
            $closed_fh->{$fh_name} = 1;
            next;
         } elsif ( $sub_size == 0 ) {
            my $msg = "child pid=$child->{pid} file_handle=$fh_name is EOF";
            print STDERR "$msg\n";
            # return $enrich->( { error => $msg, data => $data, matches => $matches } );
            $closed_fh->{$fh_name} = 1;
            next;
         }

         $data->{$fh_name}->{raw} .= $sub_data;
         $size_by_fh->{$fh_name} += $sub_size;

         $verbose && print STDERR "sub_data=$sub_data, last read sub_size=$sub_size\n";
         $verbose && print STDERR "read from file_handle=$fh_name total_size=$size_by_fh->{$fh_name}\n";
         # $verbose && print STDERR "data=", Dumper($data), "\n";
      }

      if ( $logic eq 'or' ) {
         my $i = 0;
         for my $r (@$matches) {
            # match against the file handle name, default to 'out'
            my $fh_name = $r->{fh_name} ? $r->{fh_name} : 'out';
            my $data2   = $data->{$fh_name}->{raw};
            if ( defined($data2) && $data2 =~ /$r->{compiled}/ ) {
               $r->{matched} = 1;
               return $enrich->( { data => $data, matches => $matches } );
            }
         }
      } elsif ( $logic eq 'and' ) {
         my $all_matched = 1;
         for my $r (@$matches) {
            # match against the file handle name, default to 'out'
            my $fh_name = $r->{fh_name} ? $r->{fh_name} : 'out';
            my $data2   = $data->{$fh_name}->{raw};

            $verbose && print STDERR "matching '$r->{pattern}' against '$data2'\n";

            if ( defined($data2) && $data2 =~ /$r->{compiled}/ ) {
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
      if ( !$current_child ) {
         croak "no child process is defined";
      } else {
         $child = $current_child;
      }
   }

   # actions is an array of hash references
   # each hash reference has a key: action, and optional keys, eg, data.

   for my $r (@$actions) {
      if ( $r->{action} eq 'send' ) {
         if ( $child->{method} eq 'pty' ) {

            if ( !defined $child->{pty}->fileno() ) {
               print STDERR "cannot send because pty is closed\n";
               return;
            }
            return $child->{pty}->print( $r->{data} );
         } else {
            return print( { $child->{fh}->{in} } $r->{data} );
         }
      } elsif ( $r->{action} eq 'close' ) {
         if ( $child->{method} eq 'pty' ) {
            return $child->{pty}->close();
         } else {
            for my $fh ( values %{ $child->{fh} } ) {
               close($fh);
            }
         }
         return;
      } elsif ( $r->{action} eq 'wait' ) {
         return waitpid( $child->{pid}, 0 );
      } elsif ( $r->{action} eq 'kill' ) {
         return kill( 9, $child->{pid} );
      } else {
         croak "unsupported action: $r->{action}";
      }
   }
}

sub main {
   require TPSUP::TEST;

   my $test_code2 = <<'END';
   TPSUP::IPC::init_child( "sftp localhost", { method=>'pty', verbose => 1 } );
   TPSUP::IPC::expect_child([ { pattern => 'password:' } ], { verbose => 1 } );
   TPSUP::IPC::send_to_child([ { action => 'send', data => "password\n" } ], { verbose => 1 } );
   TPSUP::IPC::expect_child([ { pattern => 'password:' } ], { verbose => 1 } );
   TPSUP::IPC::send_to_child([ { action => 'close' } ], { verbose => 1 } );
   sleep 1;
   TPSUP::IPC::send_to_child([ { action => 'kill' } ], { verbose => 1 } );
   sleep 1;
   TPSUP::IPC::send_to_child([ { action => 'wait' } ], { verbose => 1 } );

   TPSUP::IPC::init_child( "tpnc -i 1 localhost 6789", { method => 'open3', verbose => 1 } );
   TPSUP::IPC::expect_child( [ { pattern => 'ERROR:', fh_name=>'err' } ], { verbose => 1 } );
   TPSUP::IPC::send_to_child( [ { action => 'close' } ], { verbose => 1 } );
   sleep 1;
   TPSUP::IPC::send_to_child( [ { action => 'kill' } ], { verbose => 1 } );
   sleep 1;
   TPSUP::IPC::send_to_child( [ { action => 'wait' } ], { verbose => 1 } );

END

   my $test_code = <<'END';
   TPSUP::IPC::init_child( "sftp localhost", { method=>'pty',  } );
   TPSUP::IPC::expect_child([ { pattern => 'password:' } ], {  } );
   TPSUP::IPC::send_to_child([ { action => 'send', data => "password\n" } ], {  } );
   TPSUP::IPC::expect_child([ { pattern => 'password:' } ], {  } );
   TPSUP::IPC::send_to_child([ { action => 'close' } ], {  } );
   sleep 1;
   TPSUP::IPC::send_to_child([ { action => 'kill' } ], {  } );
   sleep 1;
   TPSUP::IPC::send_to_child([ { action => 'wait' } ], {  } );

   TPSUP::IPC::init_child( "tpnc -i 1 localhost 6789", { method => 'open3',  } );
   TPSUP::IPC::expect_child( [ { pattern => 'ERROR:', fh_name=>'err' } ], {  } );
   TPSUP::IPC::send_to_child( [ { action => 'close' } ], {  } );
   sleep 1;
   TPSUP::IPC::send_to_child( [ { action => 'kill' } ], {  } );
   sleep 1;
   TPSUP::IPC::send_to_child( [ { action => 'wait' } ], {  } );

END

   TPSUP::TEST::test_lines($test_code);
}

main() unless caller;

1;
