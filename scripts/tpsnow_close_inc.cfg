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
   
   linux1$ {{prog}} -dryrun              192.168.1.179:9333 s=data
   linux1$ {{prog}} -dryrun -interactive 192.168.1.179:9333 s=data

END

   # all keys in keys, suits and aliases (keys and values) will be converted to uppercase.
   # this way so that user can use case-insensitive keys on command line
   keys => {
       RESOLUTIONCODE => 'Solved (Permanently)',
      RESOLUTIONNOTES => 'done',
                CAUSE => 'Process Execution',
             SUBCAUSE => 'Execution Error',
   },

   suits => {
      PROC => {
            CAUSE => 'Process Execution',
         SUBCAUSE => 'Execution Error',
      },

      DATA => {
            CAUSE => 'Data Error',
         SUBCAUSE => 'Data Input',
      },
   },

   aliases => {
      RC => 'RESOLUTIONCODE',
      RN => 'RESOLUTIONNOTES',
       C => 'CAUSE',
      SC => 'SUBCAUSE',
   },
};

sub code {
   my ($all_cfg, $known, $opt) = @_;

   print "final known = ", Dumper($known);

   my $driver = $all_cfg->{resources}->{selenium}->{driver};

   # in ServiceNow->Incidents, create a filter
   #       Active,         is,                         true
   #
   #       Assigned to,    is (dynamic),               Me
   #
   #       State,          is not one of,              Resolved
   #                                                   Cancelled
   #                                                   Closed
   # 
   #    Short description, contains,                  (self-closable)
   # Save the filter as 'my self-closable'
   # run it
   # copy the url for below

   my $actions = [
      # locator,        input,           comment,           extra
      ['url=my self-closable url'],
      ['xpath=//iframe[@id="gsfta_main"]', 'iframe', 'switch iframe', {post=>'sleep 1'}],
      ['xpath=//div[@id="AC.incident.caller_id"]', 'key=backspace,30', 'clear caller name', {post=>'sleep 1'}],
   ]; 

   run_actions($driver, $actions, $opt);

   my $i = 0;

   while(1) {
      print "\n";

      my $actions2 = [
         # we may see a list of open records, or no record
         #    if     no record,  we return
         #    if seeing records, we click the first one
         ['xpath=//a[contains(@aria-label, "Open record: ")],
           xpath=//tr[@class="list2_no_records"],
          ',
          'code=' . <<'END',
              use strict;
              use warnings;
              my $text = $element->get_text();
              print "seeing text='$text'\n";
              if ($text eq 'No records to display') {
                 # 'return' will only return from run_actions, cannot return to upper
                 # caller. $we_return is a global var, can be picked up by upper caller.
                 print "we return\n";
                 $we_return = 1;
              } else {
                 $element->click();
              }
END
          'list open records',
          #{NotFound=>'return'}  # 'return' won't work; that's why we use $we_return=1
         ],

         [
           'xpath=//span[contains(text(), "Resolution Information")]',
           'click',
           'click resolution tab'
         ],
         ['tab=3', "string=$known->{RESOLUTIONCODE}",  'resolution code'],
         ['tab=1', "string=$known->{RESOLUTIONNOTES}", 'resolution notes'],
         ['tab=1', "string=$known->{CAUSE}",           'enter cause'],
         ['tab=1', "string=$known->{SUBCAUSE}",        'enter subcause'],
         ['tab=3', ["click","sleep=3"],                'click Resolve button'],

         # close popup if found. 
         # without closing it, we won't be able to click 'go back' button
         [
           { locator  => 'xpath=//div[@id="ui_notification"]/div[@class="panel-body"]/div/span[@class="icon-cross close"]', 
             NotFound =>'next',
           },
           'click', 'close popup if found'
         ],
         
         ['xpath=//button[@onclick="gsftSubtmitBack()"]]', 'click', 'Go Back'],
         ['code=sleep 2'],
      ];

      run_actions($driver, $actions2, $opt);
      
      last if $opt->{dryrun};   # to avoid dryrun deadloop

      #use TPSUP::GLOBAL   qw($we_return); # this import makes the cfg compilable by itself
      #last if $we_return;

      last if eval '$we_return==1'; # wrapping $we_return with eval makes cfg compliable
   }
}
