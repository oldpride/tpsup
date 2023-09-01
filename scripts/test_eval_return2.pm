package test_eval_return2;

use strict;
use warnings;

use base qw( Exporter );
our @EXPORT_OK = qw($we_return);

our $we_return;

sub eval_sub2 {
   my ($string) = @_;

   print "in test_eval_return2 module we_return=$we_return\n";

   eval($string);
}

1
