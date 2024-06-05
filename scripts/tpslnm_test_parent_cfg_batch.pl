#!/usr/bin/env perl

use strict;
use warnings;
use TPSUP::SELENIUM qw();

our $our_cfg = {
   resources => {
      selenium => {
         method => \&TPSUP::SELENIUM::get_driver,
         cfg => {
         },
      },
   },

   usage_example => <<'END',

   https://stackoverflow.com/questions/71849162/how-to-find-the-neighbour-element-of-an-active-element-using-selenium-with-pytho

   {{prog}} any

END
};

use Selenium::Waiter; # this is a must, otherwise wait_until{} waits 0 seconds.

sub code {
   my ($all_cfg, $known, $opt) = @_;

   my $driver = $all_cfg->{resources}->{selenium}->{driver};

   my $url = 'file:///home/tian/sitebase/github/tpsup/scripts/tpslnm_test_parent.html';
   print "going to url=$url\n";
   $driver->get($url);

   # Selenium::Waiter
   # doc:     https://metacpan.org/pod/Selenium::Waiter
   # example: https://groups.google.com/g/selenium-remote-driver/c/-obQDdEhyWA?pli=1

   my $xpath = '//span[text()="unique text"]/../../../div[2]/textarea';
   print "find neighbour, xpath=$xpath\n";
   my $element = wait_until{$driver->find_element_by_xpath($xpath)};
   my $text = $element->get_text();
   print "text=$text\n";

   print "sleep 2 seconds so you can see\n";
   sleep 2;
}

sub post_batch {
   my ($all_cfg, $opt) = @_;

   print "running post batch\n";

   my $driver = $all_cfg->{resources}->{selenium}->{driver};

   $driver->shutdown_binary;

   # list all the log files
   system("ls -ld $driver->{seleniumEnv}->{log_base}/selenium*");
}

