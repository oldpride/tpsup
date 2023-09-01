#!/usr/bin/perl

use strict;
use warnings;

# close() will return false for any error, $! will be set only if a syscall had an error, 
# and $? will be set to the exit status.

for my $script (("test_open_cmd_fail.bash", "test_open_cmd_success.bash")) {
   print "reading from $script output\n";

   open my $fh, "$script|";
   
   my $rc = $?;
   
   print "open() rc = $rc. open_rc is actually a previously close() rc.\n";
   
   while (my $line = <$fh>) {
      print "read: $line";
   }
   
   if (!close($fh)) {
      print "close() fail\n";
   } else {
      print "close() success\n";
   }

   $rc = $?;
   print "close() rc = $rc\n";
   
}   
   
   
   
   
