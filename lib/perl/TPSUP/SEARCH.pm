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
   my ( $arr, $target, $compare_func, $opt ) = @_;

   my $verbose = $opt->{verbose};

   my $compare_type  = ref($compare_func);
   my $compare_usage = "compare_func must be either a string ('<=>', 'numeric', 'cmp', 'string'), or a code reference.";
   if ( !$compare_type ) {
      if ( $compare_func eq '<=>' || $compare_func eq 'numeric' ) {
         $compare_func = sub { $_[0] <=> $_[1] };
      } elsif ( $compare_func eq 'cmp' || $compare_func eq 'string' ) {
         $compare_func = sub { $_[0] cmp $_[1] };
      } else {
         croak $compare_usage . "yours is a string '$compare_func'";
      }
   } elsif ( $compare_type ne 'CODE' ) {
      croak $compare_usage . "your type is '$compare_type'";
   }

   my $low0  = 0;
   my $high0 = scalar(@$arr) - 1;

   if ( defined( $opt->{low} ) ) {
      if ( $opt->{low} < 0 ) {
         croak "low cannot be negative";
      }
      $low0 = $opt->{low};
   }

   if ( defined( $opt->{high} ) ) {
      if ( $opt->{high} > $high0 ) {
         croak "high cannot be larger than the size of the array";
      }
      $high0 = $opt->{high};
   }

   my $low  = $low0;
   my $high = $high0;

   while ( $low <= $high ) {
      my $mid = int( ( $low + $high ) / 2 );

      my $cmp = $compare_func->( $arr->[$mid], $target );

      if ( $cmp == 0 ) {
         return $mid;
      } elsif ( $cmp < 0 ) {
         $low = $mid + 1;
      } else {
         $high = $mid - 1;
      }
   }

   # at this point, $low > $high
   if ( $low > $high0 ) {
      if ($verbose) {
         print STDERR "target $target is after the last element in the array\n";
      }
      if ( $opt->{OutBound} ) {
         if ( $opt->{OutBound} eq 'UseClosest' ) {
            return $high0;
         } elsif ( $opt->{OutBound} eq 'Error' ) {
            croak "target $target is after the last element in the array";
         } else {
            croak "'OutBound' must be either 'UseClosest' or 'Error'. Yours is '$opt->{OutBound}'";
         }
      } else {
         return -1;
      }
   } elsif ( $high < $low0 ) {
        if ($verbose) {
             print STDERR "target $target is before the first element in the array\n";
        }
        if ( $opt->{OutBound} ) {
             if ( $opt->{OutBound} eq 'UseClosest' ) {
                return $low0;
             } elsif ( $opt->{OutBound} eq 'Error' ) {
                croak "target $target is before the first element in the array";
             } else {
                croak "'OutBound' must be either 'UseClosest' or 'Error'. Yours is '$opt->{OutBound}'";
             }
        } else {
             return -1;
        }
   } else {
      # target is in between 2 elements;
      if ($verbose) {
         print STDERR "target $target is in between 2 elements\n";
      }
      if ( $opt->{InBetween} ) {
         if ( $opt->{InBetween} eq 'low' ) {
            return $high;    # remember at this point, $low > $high
         } elsif ( $opt->{InBetween} eq 'high' ) {
            return $low;
         } elsif ( $opt->{InBetween} eq 'Error' ) {
            croak "target $target is in between 2 elements";
         } else {
            croak "'InBetween' must be either 'low', 'high', or 'Error'. Yours is '$opt->{InBetween}'";
         }
      } else {
         return -1;
      }
   }

   if ($verbose) {
      print STDERR "target $target is not in the array. consider set flag 'UseClosest'\n";
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
      } else {
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
        TPSUP::SEARCH::binary_search_match(\@arr, 9, sub { $_[0] <=> $_[1] }, {verbose=>1, InBetween=>'low'});
        TPSUP::SEARCH::binary_search_match(\@arr, 9, sub { $_[0] <=> $_[1] }, {verbose=>1, InBetween=>'high'});
        TPSUP::SEARCH::binary_search_match(\@arr, 15, sub { $_[0] <=> $_[1] }, {verbose=>1, OutBound=>'UseClosest'});
        TPSUP::SEARCH::binary_search_match(\@arr, 0, sub { $_[0] <=> $_[1] }, {verbose=>1, OutBound=>'UseClosest'});
        
        TPSUP::SEARCH::binary_search_match(\@arr, 10, 'numeric');
        TPSUP::SEARCH::binary_search_match(['a', 'b', 'c', 'd', 'e'], 'd', 'string');

        TPSUP::SEARCH::binary_search_match(\@arr, 10, 'string'); # not sorted, not working
        TPSUP::SEARCH::binary_search_match(['1', '2', '4', '10', '12'], '10', 'string'); # not sorted, not working
        TPSUP::SEARCH::binary_search_match([ sort {$a cmp $b} @arr], 10, 'string'); # sorted, working

        TPSUP::SEARCH::binary_search_first(\@arr, sub { $_[0] >= 4 });
END

   test_lines($test_code);

}

main() unless caller();

1
