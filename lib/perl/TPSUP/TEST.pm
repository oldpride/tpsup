package TPSUP::TEST;

use strict;
use warnings;
use Data::Dumper;
$Data::Dumper::Sortkeys = 1;    # this sorts the Dumper output!
$Data::Dumper::Terse    = 1;    # print without "$VAR1="

use Carp;

use base qw( Exporter );

# "EXPORT" vs "EXPORT_OK":
#   "EXPORT" is for default export.
#   "EXPORT_OK" is on demand export.
#
#  we use "EXPORT" in our modules for simiplicity. The caller only
#  needs to do
#     use TPSUP::TEST qw(:DEFAULT);
#
#  if we used "EXPORT_OK", the caller needs to do
#     use TPSUP::TEST qw(test_lines in equal);
#  or dynamically get the list of "EXPORT_OK" from TPSUP::TEST
#     require TPSUP::NAMESPACE;
#     TPSUP::NAMESPACE::import_EXPECT_OK( "TPSUP::TEST", __PACKAGE__ );
#  neither is convenient.
#
# our @EXPORT_OK = qw(
#   test_lines
#   in
#   equal
# );
our @EXPORT = qw(
  test_lines
  in
  equal
);

sub process_block {
   my ( $block, $namespace, $opt ) = @_;
   # namespace is the package name where the test code is running

   my $verbose = $opt->{verbose};

   my @lines     = split /\n/, $block;
   my $in_test   = 0;
   my $test_code = '';
   for my $line (@lines) {
      if ( !$in_test ) {
         if ( $line =~ /^[\s#]*TEST_BEGIN/ ) {
            $in_test = 1;
         } else {
            next if $line =~ /^\s*$/;
            next if $line =~ /^\s*#/;

            $line =~ s/^\s+//;    # remove leading spaces

            if ( $line =~ /^my\s+/ ) {
               print "WARN: single-line 'my' doesn't work in test codes. Use 'our' instead.\n";
            }

            run_1_test( $line, $namespace, $opt );
         }
      } else {
         # $in_test == 1
         if ( $line =~ /^[\s#]*TEST_END/ ) {
            $in_test = 0;
            run_1_test( $test_code, $namespace, $opt );
            $test_code = '';
         } else {
            $test_code .= "$line\n";
         }
      }
   }
}

sub run_1_test {
   my ( $test, $namespace, $opt ) = @_;

   print "----------------------------------------\n";
   print "eval: $test\n";
   my $code = "package $namespace; no strict; $test";

   # the following could convert result type.
   #   my $result = eval $code;
   # for example, if result is an array (0, 1, 2). the $result will be 3.
   # therefore, use [] to preserve original type.

   my $result = [ eval $code ];
   if ($@) {
      print "eval error: $@\n";
   }

   if ( !$opt->{not_show_result} ) {
      print "result=", Dumper(@$result), "\n";
   }

   print "\n";

}

sub test_lines {
   my ( $block, $opt ) = @_;

   $opt = {} unless $opt;

   # get the caller's package name
   my $caller_package = caller;
   print "caller_package=$caller_package\n" if $opt->{verbose};

   # run test in caller's package (namespace), so that we have access to all subs
   # and variables in the caller's package.
   my $pre_code = $opt->{pre_code};
   if ($pre_code) {
      process_block( $pre_code, $caller_package, { %$opt, not_show_result => 1 } );
   }

   process_block( $block, $caller_package, $opt );
}

# perl doesn't have a 'in list' operator
# we create our own
sub in {
   my ( $e, $a, $opt ) = @_;

   my $verbose = $opt->{verbose};
   my $method  = $opt->{method};
   $method = "equal" if !defined $method;

   my $type = ref($a);
   if ( !$type || $type ne 'ARRAY' ) {
      croak "parameter is not a ref to ARRAY: " . Dumper($a);
   }

   my $method_type = ref $method;
   if ( !$method_type ) {
      if ( $method eq 'numeric' ) {
         for my $e2 (@$a) {
            if ( $e2 == $e ) {
               return 1;
            }
         }

         return 0;
      } elsif ( $method eq 'string' ) {
         for my $e2 (@$a) {
            if ( "$e2" eq "$e" ) {
               return 1;
            }
         }

         return 0;
      } elsif ( $method eq 'equal' ) {
         for my $e2 (@$a) {
            if ( equal( $e2, $e ) ) {
               return 1;
            }
         }

         return 0;
      } else {
         croak "method=$method is not supported. must be either 'numeric' or 'string'";
      }
   } elsif ( $method_type eq 'CODE' ) {
      for my $e2 (@$a) {
         if ( $method->( $e2, $e ) ) {
            return 1;
         }
      }

      return 0;
   } else {
      croak "method=$method is not supported. must be either 'numeric' or 'string', or a sub";
   }

}

# compare two data structures
sub equal {
   my ( $a, $b, $opt ) = @_;

   my $verbose = $opt->{verbose};

   my $type_a = ref($a);
   my $type_b = ref($b);

   if ( !$type_a ) {
      if ( !$type_b ) {
         return equal_scalar( $a, $b, $opt );
      } else {
         $verbose && print STDERR "type_a=$type_a, type_b=$type_b, type_a is not a ref\n";
         return 0;
      }
   }

   # safeguard from infinite loop
   if ( !exists $opt->{level} ) {
      $opt->{level} = 0;
   } elsif ( $opt->{level} > 20 ) {
      print STDERR "level=$opt->{level} is too deep\n";
      return 0;
   }

   $opt->{level}++;

   if ( $type_a eq 'ARRAY' ) {
      if ( $type_b ne 'ARRAY' ) {
         $verbose && print STDERR "type_a=$type_a, type_b=$type_b, type_b is not an array\n";
         return 0;
      }

      if ( scalar(@$a) != scalar(@$b) ) {
         $verbose && print STDERR "array size not equal: " . scalar(@$a) . "!=" . scalar(@$b) . "\n";
         return 0;
      }

      for my $i ( 0 .. scalar(@$a) - 1 ) {
         if ( !equal( $a->[$i], $b->[$i], $opt ) ) {
            $verbose && print STDERR "element $i not equal: $a->[$i] vs $b->[$i]\n";
            return 0;
         }
      }

      return 1;
   } else {
      # ( $type_a eq 'HASH' ) {
      if ( $type_b ne 'HASH' ) {
         $verbose && print STDERR "type_a=$type_a, type_b=$type_b, type_b is not a hash\n";
         return 0;
      }
      my @keys_a = sort keys %$a;
      my @keys_b = sort keys %$b;

      if ( scalar(@keys_a) != scalar(@keys_b) ) {
         $verbose && print STDERR "hash size not equal: " . scalar(@keys_a) . "!=" . scalar(@keys_b) . "\n";
         return 0;
      }

      for my $i ( 0 .. scalar(@keys_a) - 1 ) {
         if ( $keys_a[$i] ne $keys_b[$i] ) {
            $verbose && print STDERR "key $i not equal: '$keys_a[$i]' ne '$keys_b[$i]'\n";
            return 0;
         }

         if ( !equal( $a->{ $keys_a[$i] }, $b->{ $keys_b[$i] }, $opt ) ) {
            $verbose && print STDERR "value for key $keys_a[$i] not equal: $a->{$keys_a[$i]} vs $b->{$keys_b[$i]}\n";
            return 0;
         }
      }

      return 1;
   }

   return 1;
}

# compare two scalars
# this may be rarely called directly.
# usually called by equal()
sub equal_scalar {
   my ( $a, $b, $opt ) = @_;

   my $verbose = $opt->{verbose};
   my $method  = $opt->{method};    # numeric or string

   if ( !defined $method ) {
      # if no method is specified, we try to find out the best method
      my $numeric = 1;
      for my $e ( $a, $b ) {
         if ( $e !~ /^[+-]?\d+([.]\d*)?$/ ) {
            $verbose && print "e='$e' is not numeric\n";
            $numeric = 0;
            last;
         }
      }
      if ($numeric) {
         $method = 'numeric';
      } else {
         $method = 'string';
      }
   }

   if ( $method eq 'numeric' ) {
      $verbose && print "a=$a, b=$b, numeric comparison\n";
      if ( $a == $b ) {
         return 1;
      } else {
         return 0;
      }
   } else {
      $verbose && print "a=$a, b=$b, string comparison\n";
      if ( "$a" eq "$b" ) {
         return 1;
      } else {

         return 0;
      }
   }
}

sub main {
   # suppress "once" warning
   #   Name "DUMMY::array1" used only once: possible typo at TEST.pm line 63.
   no warnings 'once';

   # multiple-line variable declaration, use DUMMY namespace
   $TPSUP::TESTDUMMY::array1 = [ [ 1, 2, 3 ], [ 4, 5, 6 ], ];

   my $pre_code = <<END;
        # var declared using "our" which is global to the package. "my" will not work.
        our \$a = 1;
        our \$b = "hello";
END

   my $test_code = <<'END';
      $a+1;
      $b;

      # caller is in DUMMY package (namespace), therefore, we just use $array1;
      # don't need to use $DUMMY::array1
      $array1;

      {key1=>1, key2=>[3,4]};

      1+1 == 2;

      in(1, [1.0, 2]) == 1;
      in("a", ["a", "b"]) == 1;
      in("a", ["c", "b"]) == 0;

      equal(1, 1.0);
      equal(1, "1");
      equal("a", "a");
      equal( 1, "one");

      equal([1,2], [1.0, "2"]) == 1;
      equal({a=>-1, b=>2}, {b=>"2", a=>-1.0} ) == 1;

      #TEST_BEGIN
      my $a = 1;
      my $b = 2;
      $a + $b == 3;
      #TEST_END

      #TEST_BEGIN
      1+1 == 2;
      #TEST_END

END

   test_lines( $test_code, { pre_code => $pre_code } );
}

main() unless caller;

1
