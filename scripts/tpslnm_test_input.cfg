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

   Use chrome in two ways:

   1. let chromedriver to start a chrome locally. 
      linux1$ {{prog}} auto any

   2. let chromedriver to connect to an existing local chrome
      linux1$ {{prog}} localhost:9222  any

      2.1.1 if the chrome is indeed running at that port
         the chromedriver will connect to the chrome
      2.1.2 if no chrome is running at that port
         SELENIUM.pm will start a chrome, and then chromedriver will connect to it.

END

   # all keys in keys, suits and aliases (keys and values) will be converted to uppercase.
   # this way so that user can use case-insensitive keys on command line
   keys => {
   },

   suits => {
      henry => {
         userid   => "henry",
         username => "Henry King",
         password => "dummy",
         dob      => "11222001",
      },
   },

   aliases => {
      i => "userid",
      n => "username", 
      p => "password",
   },

   opt => {
      #humanlike => 1, # add random delay 
   },
};

sub code {
   my ($all_cfg, $known, $opt) = @_;

   my $driver = $all_cfg->{resources}->{selenium}->{driver};

   my $actions = [
      [ "url=file:///$ENV{TPSUP}/scripts/tpslnm_test_input.html" ],

      [ 
        '
         css=#user\ id,
         xpath=//input[@id="user id"],
         xpath=//tr[class="non exist"]
        ', 
        [ 'click',
          'code=print_detail($element)',
        ],
        'go to user id',
      ],
      [ 'tab=4',     
        [
         #'click',
         'code=' . <<'END',
           print "element id = '", $element->get_attribute('id'), 
                 "', expecting 'DateOfBirth'\n";  
           sleep 2;
END
        ],
        'go to Date of Birth', 
      ],
      [ 'shifttab=3',
        [
          #'click', 
         'code=' . <<'END',
           print "element id = '", $element->get_attribute('id'), 
                 "', expecting 'password'\n";  
END
        ],
        'go back to password'
      ],
      [ 'click_xpath=//select[@id="Expertise"]', 'select=text,JavaScript', 'select JavaScript' ],
      # NOTE: !!!
      # alfter selection, somehow I have to use xpath to get to the next element, tab
      # won't move to next element.
      #[ 'tab=2', 'select=value,2', 'select 2-Medium' ],
      [ 'click_xpath=//select[@id="Urgency"]', 'select=value,2', 'select 2-Medium' ],

      [ 'xpath=//fieldset/legend[text()="Profile2"]/../input[@class="submit-btn"]', 
        ['click', 'gone_xpath=//select[@id="Expertise"]', 'sleep=2'], 
        'submit'
      ],
   ];

   TPSUP::SELENIUM::run_actions($driver, $actions, $opt);
}
   
sub post_batch {
   my ($all_cfg, $opt) = @_;

   my $driver = $all_cfg->{resources}->{selenium}->{driver};

   $driver->shutdown_binary;

   system("ps -ef |grep -v grep|grep chrome");
   if ( $? != 0 ) {
      print "seeing leftover chrome\n";
   }

   # list all the log files
   system("ls -ld $driver->{seleniumEnv}->{log_base}/selenium*");
}

