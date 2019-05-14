package TPSUP::Expression;

use strict;
no strict "refs";
no strict "vars";

sub export {
   while (@_) {
      my ($k, $v) = splice(@_, 0, 2);
      next unless defined $k;
      ${k} = $v;
   }
}

my %_exist;

sub export_var {
   my ($ref, $opt) = @_;
