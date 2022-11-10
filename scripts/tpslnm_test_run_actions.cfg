#!/usr/bin/env perl

use strict;
use warnings;
use TPSUP::SELENIUM qw();

# don't add 'my' in front of below because the variable is declared in the caller.
our $our_cfg = {
   resources => {
      selenium => {
         method => \&TPSUP::SELENIUM::get_driver,
         cfg => {
            # drivername  => "chromedriver",        # default
            # BrowserArgs => [],                    # default
         },
         # enabled => 1,   # default is enabled.
      },
   },

   # position_args will be inserted into $opt hash to pass forward
   position_args => ['host_port'],

   show_progress => 1, 

   usage_example => <<'END',

   Use chrome in three ways:

   1. let chromedriver to start a chrome locally. 
      linux1$ {{prog}} auto suit=perl

   2. let chromedriver to connect to an existing local chrome
      linux1$ {{prog}} localhost:9222  suit=perl

      2.1.1 if the chrome is indeed running at that port
         the chromedriver will connect to the chrome
      2.1.2 if no chrome is running at that port
         SELENIUM.pm will start a chrome, and then chromedriver will connect to it.

  3. let chromedriver to connect to a remote chrome
     3.1  start Chrome (c1) on remote PC with debug port 9222.

    +------------------+       +---------------------+
    | +---------+      |       |  +---------------+  |
    | |selenium |      |       |  |chrome browser +------->internet
    | +---+-----+      |       |  +----+----------+  |
    |     |            |       |       ^             |
    |     |            |       |       |             |
    |     v            |       |       |             |
    | +---+---------+  |       |  +----+---+         |
    | |chromedriver +------------>+netpipe |         |
    | +-------------+  |       |  +--------+         |
    |                  |       |                     |
    |                  |       |                     |
    |  Linux           |       |   PC                |
    |                  |       |                     |
    +------------------+       +---------------------+

    3.2 PC only allows local process to connect to local chrome.
        use netpipe to overcome PC restriction on chrome 
        cygwin$ win_chrome_netpipe -allow linux1

    3.3 run the test
       linux1$ {{prog}} 192.168.1.179:9333 suit=perl
       linux1$ {{prog}} 192.168.1.179:9333 q='selenium python'
       linux1$ {{prog}} 192.168.1.179:9333 -batch tpslnm_test_batch.txt

END

   # all keys in keys, suits and aliases (keys and values) will be converted to uppercase.
   # this way so that user can use case-insensitive keys on command line
   keys => {
      URL   => 'https://www.google.com',
      # URL => 'https://google.com',   # www.google and google's input xpath are different

      QUERY =>  undef, 
      LINES => 'this can be one line or lines',
   },

   suits => {
      PERL => {
         QUERY => 'perl selenium',
      },
       
      PYTHON => {
         QUERY => 'python selenium',
         LINES => 'overwritten lines',
      },
   },

   aliases => {
      Q => 'QUERY',
      L => 'LINES',
   },
};

# this should be site-spec functions
use TPSUP::UTIL qw(get_user);


sub code {
   my ($all_cfg, $known, $opt) = @_;

   my $driver = $all_cfg->{resources}->{selenium}->{driver};

   my $actions = [
      [ 'url=https://www.google.com/'],

      [ 'xpath=//input[@name="q"]', 'string=perl selenium', 'type query' ],
      # note: the xpath between www.google.com and google.com are different

      [  '',  ['key=enter,1','code=sleep 3'],  'click enter'],
   ];

   TPSUP::SELENIUM::run_actions($driver, $actions, $opt);
}
   
sub post_batch {
   my ($all_cfg, $opt) = @_;

   print "running post batch\n";

   my $driver = $all_cfg->{resources}->{selenium}->{driver};

   $driver->shutdown_binary;

   # list all the log files
   system("ls -ld $driver->{seleniumEnv}->{log_base}/selenium*");
}
