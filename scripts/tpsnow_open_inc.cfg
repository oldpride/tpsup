#!/usr/bin/env perl

use strict;
use warnings;
use TPSUP::SELENIUM qw(run_actions);

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

   - start Chrome (c1) on remote PC with debug port 9222.

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

   # prepare test
   cygwin$ win_chrome_netpipe -allow linux1
   
   linux1$ {{prog}} -dryrun              192.168.1.179:9333 n="John Smith" s=user
   linux1$ {{prog}} -dryrun -interactive 192.168.1.179:9333 n="John Smith" s=user

END

   # all keys in keys, suits and aliases (keys and values) will be converted to uppercase.
   # this way so that user can use case-insensitive keys on command line
   keys => {
         MYNAME   => 'John Smith',
         CATEGORY => 'Technology Processing', 
      SUBCATEGORY => 'User Complaint', 
          SERVICE => 'Trade Plant',
               CI => undef,
         EXTERNAL => 'N',
           IMPACT => 3,
          URGENCY => 3,
      ASSIGNGROUP => 'TradePlantSupport',
         ASSIGNTO => undef,
            SHORT => 'User reported Trade Plant issue',
           DETAIL => undef,
   },

   suits => {
      USER => {
            CATEGORY => 'Technology Processing', 
         SUBCATEGORY => 'User Complaint', 
               SHORT => 'User reported Trade Plant issue',
      },

      DATA => {
            CATEGORY => 'Data Integrity', 
         SUBCATEGORY => 'Incorrect Data', 
               SHORT => 'Incorrect Data in TradePlant',
      },
       
      PROC => {
            CATEGORY => 'Technology Faults', 
         SUBCATEGORY => 'Unexpected Behavior', 
               SHORT => 'Trade Plant Process failed',
      },
   },

   aliases => {
     SH => 'SHORT',
      D => 'DETAIL',
      I => 'IMPACT',
      U => 'URGENCY',
      E => 'EXTERNAL',
      N => 'MYNAME',
   },

   keychains => {
      # default one key's value to another key's value
        DETAIL => 'SHORT',
      ASSIGNTO => 'MYNAME', # default to self-assigned
            CI => 'SERVICE',
   }
};

sub code {
   my ($all_cfg, $known, $opt) = @_;

   print "final known = ", Dumper($known);

   my $driver = $all_cfg->{resources}->{selenium}->{driver};

   my $actions = [
      # locator,        input,           comment,           extra
      ['url=copy the new-incident url here; make sure it loads the iframes too'],
      ['xpath=//iframe[@id="gsfta_main"]', 'iframe', 'switch iframe', {post=>'sleep 1'}],

      ['click_xpath=//div[@id="AC.incident.caller_id"]', 
        [ 'clear_attr=value',
          "string=$known->{MYNAME}",
        ],
        'enter caller name'
      ],

      ['tab=1', 
        [ 
          # it took a while for snow validate, until done, it will display "Invalid reference"
          'gone_xpath=//div[text()="Invalid reference"]',   

          # we can input string but string changes often. so stay with index is safer
          # "string=$known->{CATEGORY}",
          "select=index,1",
        ],
        'enter category'
      ],

      [
         # somehow, tab to next element doesn't work from a select element. so we use xpath
         #'tab=1',
         'click_xpath=//select[@id="sys_display.subcategory"]',

         # again, selet index is more stable than input string
         #"string=$known->{SUBCATEGORY}", 
         "select=index,1",
         'enter subcategory'
      ],

      [
         # again, tab to next element doesn't work from a select element. so we use xpath
         # 'tab=1',
         'click_xpath=//input[@id="sys_display.incident.business_service"]',
         "string=$known->{SERVICE}", 
         'enter Service'
      ],

      [ 'tab=1', 
        [
          'gone_xpath=//div[text()="Invalid reference"]',   
          "string=$known->{CI}", 
        ],
        'configuration item'
      ],

      [ 'tab=1', 
        "string=$known->{EXTERNAL}", 
        'external client affected'
      ],

      ['tab=5', "select=value,$known->{IMPACT}", 'enter impact'],

      [
         # again, tab to next element doesn't work from a select element. so we use xpath
         'click_xpath=//select[@id="incident.urgency"]', 
         "select=value,$known->{URGENCY}", 
         'enter urgency'
      ],

      [
         # again, tab to next element doesn't work from a select element. so we use xpath
         'click_xpath=//input[@id="sys_display.incident.assignment_group"]', 
         "string=$known->{ASSIGNGROUP}", 
         'assignment group'
      ],

      [
        'tab=1', 
        [
          # it took a long time for snow validate, until done, it will display "Invalid reference"
          'gone_xpath=//div[text()="Invalid reference"]',   
          "string=$known->{ASSIGNTO}",
        ],
        'enter assigned to'
      ],

      # put (self-closable) at front because short description field can be truncated.
      ['tab=1', "string=(self-closable) $known->{DETAIL}",            'short desc'],

      ['tab=1', "string=$known->{DETAIL}",                            'detail desc'],
      ['xpath=//button[@id="sysverb_insert_bottom"]', 'click',        'click to submit'],
      ['xpath=//a[starts-with(@aria-label, "Open record: INC")]', '', 'verify'],
   ];

   run_actions($driver, $actions, $opt);
}
