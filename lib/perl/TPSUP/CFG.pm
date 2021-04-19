package TPSUP::CFG;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   parse_simple_cfg
);

use warnings;
use Data::Dumper;
use Carp;
use TPSUP::UTIL qw(get_in_fh close_in_fh);

sub parse_simple_cfg {
   my ($file, $opt) = @_;
   
   my $ifh = get_in_fh($file, $opt);

   my $result;
   my $current;

   while(my $line = <$ifh>) {
      chomp $line;

      next if $line =~ /^\s*$/;
      next if $line =~ /^\s*#/;

      if ($line =~ /^([^=]+)=(.*)/) {
         my ($key, $value) = ($1, $2);

         if ($key eq 'name') {
            my $name = $value;
            if ($result->{$name}) {
               croak "duplicate name=$name";
            }

            $result->{$name}->{name} = $value;
            $current = $result->{$name};
         } else {
            if (!$current) {
               croak "name must be defined first";
            }

            $current->{$key} = $value;
         }
      }
   }

   close_in_fh($ifh);

   return $result;
}

sub main {
   my $file = "$ENV{TPSUP}/scripts/log_pattern.cfg";

   print << "EOF";
parse $file

EOF

   print Dumper(parse_simple_cfg($file));
}


main() unless caller();


1
