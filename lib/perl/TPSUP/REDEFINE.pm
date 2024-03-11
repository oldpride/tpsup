package TPSUP::REDEFINE;

# find a solution to fix the "redefined" warning

use strict;
use warnings;

use base qw( Exporter );
our @EXPORT_OK = qw(
  dummy_sub
  add
);

use Carp;
use Data::Dumper;

sub dummy_sub {
   print STDERR "this is dummy_sub\n";
}

sub add {
   my ( $a, $b ) = @_;

   return $a + $b;
}

sub main {
   no warnings;

   require TPSUP::NAMESPACE;
   TPSUP::NAMESPACE::import_EXPECT_OK( "TPSUP::TEST", __PACKAGE__ );

   my $test_code = <<'END';
   dummy_sub();
   equal(add(1, 2), 1);
END

   test_lines( $test_code, { verbose => 1 } );
}

main() unless caller();

1;
