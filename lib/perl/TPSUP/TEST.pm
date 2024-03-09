package TPSUP::TEST;

use strict;
use warnings;
use Carp;
use Data::Dumper;
$Data::Dumper::Sortkeys = 1;    # this sorts the Dumper output!
$Data::Dumper::Terse    = 1;    # print without "$VAR1="

use base qw( Exporter );
our @EXPORT_OK = qw(
  test_lines
  in
  equal
);

# my $prepared_DUMMY = 0;  # this will not work, because it is not a global variable
$DUMMY::prepared = 0;

sub prepare_DUMMY {
   my ($opt) = @_;
   my $verbose = $opt->{verbose};

   # if ($prepared_DUMMY) {
   #    $verbose && print STDERR "by prepared_DUMMY, DUMMY is already prepared\n";
   #    return;
   # }

   if ($DUMMY::prepared) {
      $verbose && print STDERR "by \$DUMMY::prepared, DUMMY is already prepared\n";
      return;
   }

   # $prepared_DUMMY  = 1;
   $DUMMY::prepared = 1;

   my $code = <<'END';
package DUMMY;
no strict;
use warnings;

# no warnings 'redfined';  
# this made the 'redefined" warning go away
# but it also made below 'use ...' not working.
# so I commented it out.

use TPSUP::TEST qw(in equal);
$DUMMY::prepared = 1;

END
   if ( $opt->{extra_code} ) {
      $code .= $opt->{extra_code};
      $code .= "\n";
   }

   $verbose && print STDERR "eval: $code\n";
   eval $code;

}

sub process_block {
   my ( $block, $opt ) = @_;
   my $verbose = $opt->{verbose};

   my @lines = split /\n/, $block;
   for my $line (@lines) {
      next if $line =~ /^\s*$/;
      next if $line =~ /^\s*#/;

      if ( $line =~ /^\s*my\s+/ ) {
         print "WARN: 'my' doesn't work in test codes. Use 'our' instead.\n";
      }

      $line =~ s/^\s+//;    # remove leading spaces
      print "----------------------------------------\n";
      print "eval: $line\n";
      # my $code = "package DUMMY; no strict; use TPSUP::TEST qw(in equal); $line";
      # my $code = "package DUMMY; no strict; $line";
      my $code = "package DUMMY; no strict; $line";
      print "eval $code\n" if $verbose;

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
}

sub test_lines {
   my ( $block, $opt ) = @_;

   $opt = {} unless $opt;

   # get the caller's package name
   my $caller_package = caller;
   print "caller_package=$caller_package\n" if $opt->{verbose};

   # get current package's name
   my $current_package = __PACKAGE__;

   my $import_code = '';
   if ( $caller_package ne $current_package ) {
      # get caller's package's EXPORT_OK
      my $exports = get_EXPORT_OK($caller_package);
      if ( $exports && scalar(@$exports) > 0 ) {
         $import_code = <<END;
use $caller_package qw(@$exports);
END
         print "import_code=$import_code\n" if $opt->{verbose};
      }
   }

   prepare_DUMMY( { extra_code => $import_code, verbose => $opt->{verbose} } );

   my $pre_code = $opt->{pre_code};
   if ($pre_code) {
      process_block( $pre_code, { %$opt, not_show_result => 1 } );
   }

   process_block( $block, $opt );
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

# "EXPORT" vs "EXPORT_OK":
#   "EXPORT" is for default export.
#   "EXPORT_OK" is on demand export.
# we are using "EXPORT_OK" in our modules for better control.
# TPSUP::TEST needs to get all the "EXPORT_OK" from a module.
# the following tricks only works for "EXPORT", not "EXPORT_OK"
#    use MY::PACKAGE qw(/./);
#    use MY::PACKAGE qw(:DEFAULT);
# Therefore, we have to
#    1. get the list of all "EXPORT_OK" from a module
#    2. use "use MY::PACKAGE qw(...)" for each of them.
# the following function does #1.
# learned from # https://stackoverflow.com/questions/65349217
sub get_EXPORT_OK {
   my ($module) = @_;

   my $class = $module;
   eval "require $class";
   my @exports = do {
      no strict 'refs';
      @{ $class . '::' . 'EXPORT_OK' };
   };

   return \@exports;
}

sub main {
   print <<"END";
   We will see 'redfined' warnings like this
      Subroutine process_block redefined at ...
   This is annoying but seems to be harmless. 
   This only happens for test in this module, TPSUP::TEST.
   It doesn't happen for test in other modules.

END

   # suppress "once" warning
   #   Name "DUMMY::array1" used only once: possible typo at TEST.pm line 63.
   no warnings 'once';

   # multiple-line variable declaration, use DUMMY namespace
   $DUMMY::array1 = [ [ 1, 2, 3 ], [ 4, 5, 6 ], ];

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




END

   test_lines( $test_code, { pre_code => $pre_code } );
}

main() unless caller;

1
