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
);

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

   my $type = ref($a);
   if ( !$type || $type ne 'ARRAY' ) {
      croak "parameter is not a ref to ARRAY: " . Dumper($a);
   }

   for my $e2 (@$a) {
      if ( $e2 == $e ) {
         return 1;
      }
   }

   return 0;
}

sub main {

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

        $TPSUP::DATE::tradeday_by_exch_begin_offset;
END

   test_lines( $test_code, { pre_code => $pre_code } );
}

main() unless caller;

1
