#!/usr/bin/env perl

use strict;
use warnings;
use TPSUP::SELENIUM qw();

# don't add 'my' in front of below because the variable is declared in the caller.
our $our_cfg = {
   resources => {
      selenium => {
         method => \&TPSUP::SELENIUM::get_driver,
         cfg => {},
      },
   },

   usage_example => <<'END',

   {{prog}} any

END

   extra_args => {
      headless  => 'headless',
   },

};

sub code {
   my ($all_cfg, $known, $opt) = @_;

   my $driver = $all_cfg->{resources}->{selenium}->{driver};

   my $actions = [
      [ "url=file:///$ENV{TPSUP}/scripts/tpslnm_test_alert.html"],
      ['click_xpath=//input[@id="fname"]', ["string=henry",'tab=1'], 'enter first name'],
      ["url_accept_alert=http://google.com", 'sleep=1', 'go to a different site, we should see alert'],
   ];

   TPSUP::SELENIUM::run_actions($driver, $actions, $opt);
}
   
sub post_batch {
   my ($all_cfg, $opt) = @_;

   print "running post batch\n";

   my $driver = $all_cfg->{resources}->{selenium}->{driver};

   $driver->shutdown_binary;

   system("ps -ef |grep -v grep|grep chrome");
   if ( $? != 0 ) {
      print "seeing leftover chrome\n";
   }

   # list all the log files
   system("ls -ld $driver->{seleniumEnv}->{log_base}/selenium*");
}

