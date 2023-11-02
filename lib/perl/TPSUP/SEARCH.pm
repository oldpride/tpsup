package TPSUP::SEARCH;

use strict;
use warnings;

use base qw( Exporter );
our @EXPORT_OK = qw(
  binary_search_match
  binary_search_first
);

use Carp;
use Data::Dumper;

sub binary_search_match {
    my ( $arr, $target, $compare_func ) = @_;

    my $low  = 0;
    my $high = scalar(@$arr) - 1;

    while ( $low <= $high ) {
        my $mid = int( ( $low + $high ) / 2 );

        my $cmp = $compare_func->( $arr->[$mid], $target );

        if ( $cmp == 0 ) {
            return $mid;
        }
        elsif ( $cmp < 0 ) {
            $low = $mid + 1;
        }
        else {
            $high = $mid - 1;
        }
    }

    return -1;
}

sub binary_search_first {
    my ( $arr, $test_func ) = @_;

    my $low  = 0;
    my $high = scalar(@$arr) - 1;
    my $first_match;

    while ( $low <= $high ) {
        my $mid = int( ( $low + $high ) / 2 );

        if ( $test_func->( $arr->[$mid] ) ) {
            $first_match = $mid;
            $high        = $mid - 1;
        }
        else {
            $low = $mid + 1;
        }
    }

    return $first_match;
}

sub main {
    use TPSUP::TEST qw(test_lines);

    my $test_code = <<'END';
        our @arr = (1, 2,  4,  10, 12); # use "our" to make it global. "my" will not work.
        TPSUP::SEARCH::binary_search_match(\@arr, 10, sub { $_[0] <=> $_[1] });
        TPSUP::SEARCH::binary_search_first(\@arr, sub { $_[0] >= 4 });
END

    test_lines($test_code);

}

main() unless caller();

1
