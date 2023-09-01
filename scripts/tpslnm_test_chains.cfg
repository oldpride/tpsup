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
      {{prog}} any
END
};

sub code {
   my ($all_cfg, $known, $opt) = @_;

   my $driver = $all_cfg->{resources}->{selenium}->{driver};

   my $actions = [
      [ "url=chrome-search://local-ntp/local-ntp.html" ],

      [
         {
            'chains' => [
               [
                  'xpath=/html/body[1]/ntp-app[1]', 'shadow', 'css=#mostVisited', 'shadow',

                  # correct one would be 'css=#removeButton'. we purposefully typoed
                  'css=#removeButton2', 

               ],
               [
                  'xpath=/html/body[1]/ntp-app[1]', 'shadow', 'css=#mostVisited', 'shadow',
                  'css=#actionMenuButton'
               ],
            ],
         },
         {
            '0.0.0.0.0.0' => 'code=print "found remove button\n"',
            '1.0.0.0.0.0' => 'code=print "found action button\n"',
         },
         "test chains",
      ],
      [
         {
            'chains' => [
               [
                  'xpath=/html/body[1]/ntp-app[1]', 'shadow', 'css=#mostVisited', 'shadow',
                  '
                     css=#removeButton2,
                     css=#actionMenuButton

                  ',
               ],
            ]
         },
         {
            '0.0.0.0.0.0' => 'code=print "found remove button again\n"',
            '0.0.0.0.0.1' => 'code=print "found action button again\n"',
         },
         "test chains again",
      ],
   ];

   print "test actions = ", Dumper($actions);
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

