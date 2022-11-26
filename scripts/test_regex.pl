#!/usr/bin/perl

use strict;
use warnings;
use Data::Dumper;
$Data::Dumper::Sortkeys = 1;  # this sorts the Dumper output!
$Data::Dumper::Terse = 1;     # print without "$VAR1="

my @strings = (
    "this is a var only: {{var}}. some tail ",
    "this is a var with default: {{var=this is multiline 
default}}. some tail",
    "this has dup vars {{JUNK=junk1}}|{{JUNK=junk2}}",
    "this has long default {{JUNK=this default is longer than to be accepted}}",
);

my @patterns = (
   '\{\{([0-9a-zA-Z_.-]+)\}\}',            # regex_var_only

   '\{\{([0-9a-zA-Z_.-]+)(=.{0,25}?)?\}\}', # regex_var_with_default
   # there are 2 ?,
   #    the 1st ? is for ungreedy match
   #    the 2nd ? says the (...) is optional
);

for my $s (@strings) {
   for my $p (@patterns) {
      print "\n";
      print "string=$s\n";
      print "pattern=$p\n";

      my @captures = ($s =~ /$p/sg);
      if (@captures) {
         print "matched. captures=" . Dumper(\@captures); 
      } else {
         print "didn't match\n";
      }
   }
}


