#!/usr/bin/env perl

use strict;

my $line = "echo cmd ";
for (my $i = 0; $i < 30; $i++) {
    $line .= "arg$i ";
}
print "$line\n";
