package TPSUP::PRINT;

use strict;
use warnings;
use base qw( Exporter );
our @EXPORT_OK = qw(
  render_arrays

);

use Carp;
$SIG{__DIE__} = \&Carp::confess;    # this stack-trace on all fatal error !!!

use Data::Dumper;
$Data::Dumper::Terse    = 1;        # print without "$VAR1="
$Data::Dumper::Sortkeys = 1;        # this sorts the Dumper output!

sub find_row_type {
   my ( $rows, $opt ) = @_;

   return undef if !$rows;

   my $previous_type;
   my $max_rows_to_check = $opt->{CheckMaxRows} || 100;

   my $i = 0;
   for my $r (@$rows) {
      $i++;
      my $row_type = ref $r;
      if ( !$row_type || ( $row_type ne 'HASH' && $row_type ne 'ARRAY' ) ) {
         print "ERROR: row #$i is not HASH or ARRAY: ", Dumper($r);
         return undef;
      }
      if ( !$previous_type ) {
         $previous_type = $row_type;
      } elsif ( $previous_type ne $row_type ) {
         print
"ERROR: inconsistent row type at row $i, $row_type vs $previous_type";
         return undef;
      }

      if ( $i >= $max_rows_to_check ) {
         last;
      }
   }

   return $previous_type;

}

sub find_hashes_keys {
   my ( $rows, $opt ) = @_;

   return undef if !$rows;

   my $seen_keys         = {};
   my $max_rows_to_check = $opt->{CheckMaxRows} || 100;

   my $i = 0;
   for my $r (@$rows) {
      $i++;
      for my $k ( keys %$r ) {
         $seen_keys->{$k} = 1;
      }

   }
   if ( $i >= $max_rows_to_check ) {
      last;
   }

   return sort( keys %$seen_keys );

}

sub render_one_row {
   my ( $r, $max_by_pos, $out_fh, $opt ) = @_;

   my $verbose = $opt->{verbose} || 0;

   my $MaxColumnWidth = $opt->{MaxColumnWidth};

   my $num_fields = scalar(@$r);
   my $max_fields = scalar(@$max_by_pos);

   my $truncated = [];

   for my $i ( 0 .. $max_fields - 1 ) {
      my $max_len = $max_by_pos->[$i];

      my $v;
      if ( $i < $num_fields && defined( $r->[$i] ) ) {
         $v = $r->[$i];
      } else {
         $v = "";
      }

      if ( $MaxColumnWidth && length($v) > $MaxColumnWidth ) {
         push @$truncated, $i;
         $v = substr( $v, 0, $MaxColumnWidth - 2 ) . '..';
      }

      my $buffLen = $max_len - length($v);

      if ( $i == 0 ) {
         printf $out_fh "%s%s", ' ' x $buffLen, $v;
      } else {
         printf $out_fh " | %s%s", ' ' x $buffLen, $v;
      }
   }

   print $out_fh "\n";

   if ($verbose) {
      print $out_fh "(truncated at column: ", join( ',', @$truncated ), ")\n";
   }

}

sub render_arrays {
   my ( $rows, $opt ) = @_;

   my $verbose = $opt->{verbose} || 0;

   print "rows=", Dumper($rows) if $verbose > 1;

   if ( !$rows ) {
      return;
   }

   if ( scalar(@$rows) == 0 ) {
      return;
   }

   my $out_fh;
   if ( $opt->{interactive} ) {
      my $cmd = "less -S";

      open $out_fh, "|$cmd" or croak "cmd=$cmd failed: $!";
   } elsif ( $opt->{out_fh} ) {
      $out_fh = $opt->{out_fh};
   } else {
      $out_fh = \*STDOUT;
   }

   my $RowType = $opt->{RowType} || find_row_type( $rows, $opt );

   if ( !$RowType ) {
      croak "RowType is not specified and cannot be determined from rows";
   }

   if ( $RowType ne 'ARRAY' && $RowType ne 'HASH' ) {
      croak "unsupported RowType: $RowType. can only be ARRAY or HASH";
   }

# user-specified headers make code more complicated, but we still need it
# because csv module (CSV.pm) needs to call this module to print data, and csv
# module needs to specify headers:
#    csv module often needs to print a structure of either:
#       1. headers + a array of arrays of data
#       2. headers + a array of hashes of data
#    in the first case, the headers are like the first row of data.
#    in the second case, the headers are used to filter keys of the hashes.
# Headers' role could get more complicated if want to support other features around them.
#    But we should keep this part simple.
#    if users need more feautures around headers, they can use CSV module to pre-process
#       the data, and then use this module to print the data.
#    For example, if user wanted to specify headers to filter array of arrays, it should
#       convert the array of arrays to array of hashes first, using CSV module, and then
#       filter the keys.
# outside csv module, we rarely need user-specifed headers. but we will
# keep the behavior consistent with csv module.
# summary:
#    If $rows is array of arrays,
#       if user specified headers, we prepend it to the rows, making it the first row.
#       if user didn't specify headers,
#           if user wanted to render headers, we use the first row as headers.
#           if user didn't want to render headers, we print rows without headers.
#    If $rows is array of hashes,
#       if user specified headers, we use it to filter out unwanted keys.
#       if user didn't specify headers, we use all keys as headers.

   my $headers;
   my $print_header;
   if ( $opt->{headers} ) {
      my $headers2    = $opt->{headers};
      my $header_type = ref $headers2;
      if ( !$header_type ) {
         $headers = [ split( /[ ,]+/, $headers2 ) ];
      } elsif ( $header_type eq 'ARRAY' ) {
         $headers = $headers2;
      } else {
         croak
           "unsupported header type: $header_type. can only be ARRAY or string."
           . Dumper($headers2);
      }

      for my $h (@$headers) {
         $print_header->{$h} = 1;
      }
   }

   my $MaxRows = $opt->{MaxRows} || scalar(@$rows);

   if ( $opt->{Vertical} ) {
      if ( $RowType eq 'ARRAY' ) {
         my $start_row = 0;
         if ( !$headers ) {
            if ( scalar(@$rows) < 2 ) {

     # when vertically print the arrays, we need at least 2 rows, with the first
     # as the header
     #    name: tian
     #     age: 36
     #
     #    name: john
     #     age: 30
               return;
            }
            $headers   = $rows->[0];
            $start_row = 1;
         }
         my $num_headers = scalar(@$headers);

         # print(f"headers={headers}", file=sys.stderr);

         my $i = 0;
         for my $r ( @$rows[ $start_row .. $#$rows ] ) {
            for my $j ( 0 .. scalar(@$r) - 1 ) {
               if ( $j < $num_headers ) {
                  printf $out_fh "%-25s '%s'\n", $headers->[$j], $r->[$j];
               } else {

                  # repeating chars
                  printf $out_fh "%-25s '%s'\n", ' ', $r->[$j];
               }
            }
            print $out_fh "\n";    # blank line

            $i++;
            if ( $i >= $MaxRows ) {
               last;
            }
         }
      } else {    # RowType == HASH
         my $i = 0;
         for my $r (@$rows) {
            for my $k ( sort( keys %$r ) ) {

   # for hash, if user specified headers, we use it to filter out unwanted keys.
               if ( $print_header && !$print_header->{$k} ) {
                  next;
               }
               printf $out_fh "%-25s '%s'\n", $k, $r->{$k};
            }

            print $out_fh "\n";    # blank line

            $i++;
            if ( $i >= $MaxRows ) {
               last;
            }
         }
      }

      return;
   }

   my $max_by_pos     = [];
   my $MaxColumnWidth = $opt->{MaxColumnWidth};
   my $truncated      = 0;

# fix headers of hash (dict), so that we can convert dict to list in a consistent way.
   if ( $RowType eq 'HASH' ) {
      if ( !$headers ) {

         # for hash:
         # if user specified headers, we use it to filter out unwanted keys.
         $headers = [ find_hashes_keys( $rows, $opt )];
      }

      for my $k (@$headers) {
         if ( $MaxColumnWidth && length($k) > $MaxColumnWidth ) {
            push @$max_by_pos, $MaxColumnWidth;
            $truncated = 1;
         } else {
            push @$max_by_pos, length($k);
         }
      }
   }

# at this point, $headers is defined for array of hashes, but not for array of arrays.
# only if user specified headers, then headers is defined for array of arrays.
# on the other hand, array of hashes always has headers, but array of arrays may not.
# array of arrays only need headers when user want to render headers.

   # find max width for each column
   my $i = 0;
   for my $r2 (@$rows) {
      my $r;
      if ( $RowType eq 'ARRAY' ) {
         $r = $r2;
      } else {    # RowType == HASH
         $r = [ map { defined( $r2->{$_} ) ? $r2->{$_} : '' } @$headers ];
      }

      for my $i ( 0 .. scalar(@$r) - 1 ) {
         my $i_length = length( $r->[$i] );

         # check whether an index in a list
         if ( $i >= scalar(@$max_by_pos) ) {
            if ( $MaxColumnWidth && $i_length > $MaxColumnWidth ) {
               $i_length  = $MaxColumnWidth;
               $truncated = 1;
            }
            push @$max_by_pos, $i_length;
         } elsif ( $max_by_pos->[$i] < $i_length ) {
            if ( $MaxColumnWidth && $i_length > $MaxColumnWidth ) {
               $i_length  = $MaxColumnWidth;
               $truncated = 1;
            }
            $max_by_pos->[$i] = $i_length;
         }
      }

      $i++;
      if ( $i >= $MaxRows ) {
         last;
      }
   }

   if ($verbose) {
      print $out_fh "max_by_pos=", Dumper($max_by_pos);
   }

   my $max_fields = scalar(@$max_by_pos);

   # range of rows to be printed. the following defaults works for most cases.
   my $range_start = 0;
   my $range_end   = $MaxRows - 1;    # from 0 .. $MaxRows-1, total $MaxRows rows

   if ( $opt->{RenderHeader} ) {
      if ( $RowType eq 'ARRAY' ) {
         if ( !$headers ) {
            $headers     = $rows->[0];
            $range_start = 1;

            if ( $opt->{MaxRows} ) {
               $range_end =
                 $opt->{MaxRows} > $#{$rows}-1
                 ? $#{$rows} - 1
                 : $opt->{MaxRows};    # ie $opt->{MaxRows}-1 +1
            }
         }
      }

      render_one_row( $headers, $max_by_pos, $out_fh, $opt );

      # print the bar right under the header.
      # length will be the bar length, total number of columns.
      # 3 is " | " between columns.
      my $r_length = 3 * ( $max_fields - 1 );

      for my $i ( 0 .. $max_fields - 1 ) {
         $r_length += $max_by_pos->[$i];
      }

      print $out_fh '=' x $r_length, "\n";
   }

   for my $r2 ( @$rows[ $range_start .. $range_end ] ) {
      my $r;
      if ( $RowType eq 'ARRAY' ) {
         $r = $r2;
      } else {    # RowType == HASH
         $r = [ map { defined( $r2->{$_} ) ? $r2->{$_} : '' } @$headers ];
      }

      render_one_row( $r, $max_by_pos, $out_fh, $opt );
   }

   if ( $out_fh != \*STDOUT ) {

      # if out_fh is from caller, then don't close it. let caller close it.
      if ( !$opt->{out_fh} ) {
         close $out_fh;
      }
   }

   if ($truncated) {
      print $out_fh
        "some columns were truncated to MaxColumnWidth=$MaxColumnWidth\n";
   }

   return;
}

sub main {
   use TPSUP::TEST qw(test_lines);

# to suppress "once" warning
#     once used only once: possible typo at /home/tian/perl5/lib/perl5/TPSUP/PRINT.pm line 10.
   no warnings 'once';

   $DUMMY::rows1 = [
      [ 'name',       'age' ],
      [ 'tian',       '36' ],
      [ 'olenstroff', '40', 'will discuss later' ],
      [ 'john',       '30' ], ['mary'],
   ];

   $DUMMY::rows2 = [
      { 'name' => 'tian', 'age'     => '36' },
      { 'name' => 'john', 'comment' => 'friend of tian' },
   ];

   my $test_code = <<'END';
    TPSUP::PRINT::find_row_type($rows1);
    TPSUP::PRINT::render_arrays($rows1, {MaxColumnWidth=>10});
    TPSUP::PRINT::render_arrays($rows1, {MaxColumnWidth=>10, RenderHeader=>1});
    TPSUP::PRINT::render_arrays($rows1, {MaxColumnWidth=>10, RenderHeader=>1, headers=>'name'});
    TPSUP::PRINT::render_arrays($rows1, {MaxColumnWidth=>10, Vertical=>1});
    TPSUP::PRINT::render_arrays($rows1, {MaxColumnWidth=>10, Vertical=>1, headers=>'name'});
    

    TPSUP::PRINT::find_row_type($rows2);
    TPSUP::PRINT::find_hashes_keys($rows2);
    TPSUP::PRINT::render_arrays($rows2, {MaxColumnWidth=>10});
    TPSUP::PRINT::render_arrays($rows2, {MaxColumnWidth=>10, RenderHeader=>1});
    TPSUP::PRINT::render_arrays($rows2, {MaxColumnWidth=>10, RenderHeader=>1, headers=>'name,age'});
    TPSUP::PRINT::render_arrays($rows2, {MaxColumnWidth=>10, Vertical=>1});
    TPSUP::PRINT::render_arrays($rows2, {MaxColumnWidth=>10, Vertical=>1, headers=>'name,age'});
    
END

   test_lines($test_code);
}

main() unless caller;

1;
