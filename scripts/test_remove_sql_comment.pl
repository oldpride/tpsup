#!/usr/bin/perl

my $sql = `cat tptrace_test_db.sql`;

# first remove multi-line comments /* ... */
$sql =~ s:/[*].*?[*]/::gs;

# then remove singlem-line comments -- ...
$sql =~ s:--.*::g;

print $sql;

