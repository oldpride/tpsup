#!/usr/bin/env perl

use strict;
use warnings;
use TPSUP::SELENIUM qw(
   locator_chain_to_js_list
   js_list_to_locator_chain
);

# don't add 'my' in front of below because the variable is declared in the caller.
our $our_cfg = {
   resources => {
      selenium => {
         method => \&TPSUP::SELENIUM::get_driver,
         cfg => {
            # drivername  => "chromedriver",        # default
            # BrowserArgs => [],                    # default
         },
         init_resource => 0,  # delay init till we really need it
      },
   },

   extra_args => {
      headless  => 'headless',
      js        => {
                      spec => 'js',
                      help => 'run using java script',
                   },
      full      => {
                      spec => 'full',
                      help => 'full xpath in levels, not shortcut, eg, id("myinput")',
                   },
      trap      => {
                      spec => 'trap',
                      help => 'wrap js with try{...}except{...}',
                   },
      limit_depth  => {
                      spec => 'limit_depth=s',
                      default => 5,
                      help => 'limit scan depth. default to 5',
                   },
   },


   # position_args will be inserted into $opt hash to pass forward
   position_args => ['host_port', 'url', 'output_dir'],

   show_progress => 1, 

   usage_example => <<"END",

   locate a web element

   - test a static page with nested iframes, same origin

    {{prog}} auto file:///$ENV{TPSUP}/python3/scripts/iframe_test1.html ~/dumpdir2 xpath=//iframe[1] iframe xpath=//iframe[1] iframe xpath=//h1[1]  -js

    {{prog}} auto file:////$ENV{TPSUP}/python3/scripts/iframe_test1.html ~/dumpdir2 xpath=//iframe[1] iframe xpath=//iframe[1] iframe xpath=//h1[1]


    - test a static page with nested iframes, cross origin

    {{prog}} auto file:///$ENV{TPSUP}/python3/scripts/iframe_test1.html ~/dumpdir2 xpath=//iframe[1] iframe xpath=//iframe[2] iframe xpath=//div[1]  -js

    {{prog}} auto file:///$ENV{TPSUP}/python3/scripts/iframe_test1.html ~/dumpdir2 xpath=//iframe[1] iframe xpath=//iframe[2] iframe xpath=//div[1]


   - test with google search, dump a node
   {{prog}} auto chrome-search://local-ntp/local-ntp.html ~/dumpdir2 xpath=/html/body/ntp-app shadow css=ntp-iframe shadow "css=#iframe" iframe 'xpath=//div[\@class="gb_Id"]'

   - dump whole page, allow using xpath shortcut, eg id("mycontainer")
   {{prog}} auto       chrome-search://local-ntp/local-ntp.html ~/dumpdir2 xpath=/html

   - dump whole page, force use full xpath to show all levels, eg, /html/body/...
   {{prog}} auto -full chrome-search://local-ntp/local-ntp.html ~/dumpdir2 xpath=/html

END
};

sub code {
   my ($all_cfg, $known, $opt) = @_;

   my $driver;

   if (exists $all_cfg->{resources}->{selenium}->{driver}) {
      $driver = $all_cfg->{resources}->{selenium}->{driver};
   } else {
      print("init_driver was delayed. we start now\n");
      my $method = $all_cfg->{resources}->{selenium}->{driver_call}->{method};
      my $kwargs = $all_cfg->{resources}->{selenium}->{driver_call}->{kwargs};
      $driver = $method->($kwargs);
      $all_cfg->{resources}->{selenium}->{driver} = $driver; # post_code will need this
   }

   my $url        = $opt->{url};
   my $output_dir = $opt->{output_dir};
   my $trap       = $opt->{trap};
   my $run_js     = $opt->{js};

   my $actions = [
      [ "url=$url", 'sleep=2', 'go to url'],
   ];

   my $locator_chain = $known->{REMAININGARGS};

   if ($run_js) {
      my $js_list 
          = TPSUP::SELENIUM::locator_chain_to_js_list($locator_chain,{trap => $trap});
      my $locator_chain2 = TPSUP::SELENIUM::js_list_to_locator_chain($js_list);
      push @$actions, [$locator_chain2, "dump_element=$output_dir", 'js lcoate and dump'];
   } else {
      push @$actions, [$locator_chain,  "dump_element=$output_dir",    'locate and dump'];
   }

   my $result = TPSUP::SELENIUM::run_actions($driver, $actions, $opt);
}
   
sub parse_input_sub {
   my ($input, $all_cfg, $opt) = @_; 

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   my $type = ref $input;

   my $input_array;
   if (!$type) {
      $input_array = parse_string_like_shell($input, $opt);
   } elsif ($type eq 'ARRAY') {
      $input_array = $input;
   } else {
      die "unknown type=$type of input";
   }

   return { REMAININGARGS =>  $input_array };  # this will be $known in caller
}

sub post_batch {
   my ($all_cfg, $opt) = @_;

   print "running post batch\n";

   my $driver = $all_cfg->{resources}->{selenium}->{driver};

   $driver->shutdown_binary;

   my $user = get_user();

   # list all the log files
   system("ls -ld /tmp/selenium_*${user}*");
}

