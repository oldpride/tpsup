#!/usr/bin/env perl

use strict;

my $line = "this is a long line: ";
for (my $i = 0; $i < 100; $i++) {
    $line .= "$i ";
}
print "$line\n";
