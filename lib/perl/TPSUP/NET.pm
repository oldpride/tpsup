package TPSUP::NET;

use strict;
use warnings;
use base qw( Exporter );
our @EXPORT_OK = qw(
  is_tcp_alive
  expect_socket
);

use Carp;
$SIG{__DIE__} = \&Carp::confess;    # this stack-trace on all fatal error !!!

use Data::Dumper;
$Data::Dumper::Terse    = 1;        # print without "$VAR1="
$Data::Dumper::Sortkeys = 1;        # this sorts the Dumper output!

use IO::Socket::INET;

sub is_tcp_alive {
   my ( $host, $port, $opt ) = @_;

   my $socket = new IO::Socket::INET(
      PeerHost => $host,
      PeerPort => $port,
      Proto    => 'tcp'
   );

   my $answer = $socket ? 1 : 0;

   close($socket) if $socket;

   return $answer;
}

sub wait_tcps_open {
   my ( $host_port_list, $opt ) = @_;

   my @wait_list;

   for my $host_port (@$host_port_list) {
      my $hp_type = ref($host_port);
      my ( $host, $port );

      if ( !$hp_type ) {
         ( $host, $port ) = split /:/, $host_port;
      } elsif ( $hp_type eq 'ARRAY' ) {
         ( $host, $port ) = @$host_port;
      } else {
         print "unsupported type of host_port=", Dumper($host_port);
      }

      my $item = {
         host => $host,
         port => $port,
         open => 0,
      };

      push @wait_list, $item;
   }

   my $total_time = 0;
   my $timeout    = $opt->{timeout} ? $opt->{timeout} : 60;
   while ( $total_time < $timeout ) {
      my $need_next_round = 0;
      for my $item (@wait_list) {
         if ( $item->{open} ) {
            next;
         }
         my $host   = $item->{host};
         my $port   = $item->{port};
         my $socket = new IO::Socket::INET(
            PeerHost => $host,
            PeerPort => $port,
            Proto    => 'tcp'
         );
         if ($socket) {
            print "$host:$port is open within $total_time seconds\n";
            $item->{open} = 1;
         } else {
            $need_next_round = 1;
         }
      }
      if ( !$need_next_round ) {
         print "all open\n";
         return 1;
      }
      sleep 2;
      $total_time += 2;
   }
   for my $item (@wait_list) {
      if ( !$item->{open} ) {
         my $host = $item->{host};
         my $port = $item->{port};
         print "$host:$port is NOT open after $timeout seconds\n";
      }
   }
   return 0;
}

sub expect_socket {
   my ( $socket, $patterns, $opt ) = @_;

   my $type = ref $patterns;
   croak "\$patterns must be ref to ARRAY, yours is $type" if $type ne 'ARRAY';

   my $interval = $opt->{ExpectInterval} ? $opt->{ExpectInterval} : 30;

   my $total_data;
   my @matched;
   my @captures;

   my $select = IO::Select->new($socket) or die "IO::Select $!";

   my $num_patterns = scalar(@$patterns);
   my $total_wait   = 0;

   while (1) {
      if ( !$select->can_read($interval) ) {
         if ( $opt->{ExpectTimeout} ) {
            $total_wait += $interval;

            if ( $total_wait >= $opt->{ExpectTimeout} ) {
               print STDERR
"expect_socket timed out after $opt->{ExpectTimeout} seconds\n";
               return ( \@matched, \@captures, { status => 'timed out' } );
            }
         }

         next;
      }

      my $data;

      my $size = read( $socket, $data, 1024000 );

      if ( !$size ) {
         my $total_size = length($total_data);
         my $print_size = $total_size - 100 < 0 ? $total_size : 100;

         my $last_words = substr $total_data, $total_size - $print_size,
           $print_size;

         $opt->{verbose}
           && print STDERR
           "Socket closed. Last words from peer: ... $last_words\n";
         return ( \@matched, \@captures, { status => 'closed' } );
      } else {
         $opt->{verbose} && print STDERR "received data: $data\n";

         $total_data .= $data;

         my $all_matched = 1;

         for ( my $i = 0 ; $i < $num_patterns ; $i++ ) {
            next if $matched[$i];

            if ( $total_data =~ /$patterns->[$i]/s ) {
               $opt->{verbose} && print STDERR "matched $patterns->[$i]\n";

               $matched[$i]  = 1;
               $captures[$i] = [ $1, $2, $3 ];
            } else {
               $all_matched = 0;
            }
         }

         return ( \@matched, \@captures, { status => "done" } )
           if $all_matched;
      }
   }
}

sub main {
   my $host = "localhost";
   my $port = '5555';

   my $code = "is_tcp_alive('$host', $port)";

   print "$code = ", eval($code), "\n";

   my $tcps = [
      'localhost:135',     # normally open on Windows
      'localhost:445',     # normally open on Windows
      'localhost:4723',    # appium server
      'localhost:22',      # normally open on Linux
   ];

   my $answer = wait_tcps_open( $tcps, { timeout => 2 } );
   print "wait_tcps_open() answer = $answer\n";
}

main() unless caller();

1
