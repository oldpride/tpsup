#!/usr/bin/perl

use Data::Dumper;

my $string ="
select 1 from a;
go;
select 2 from b;
go;
select 3 from cc;
";

# split separator can be a multi-line string

my @a = split /;\s*GO\s*;/i, $string, "\n";

print Dumper(\@a);
