package TPSUP::MECHANIZE;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   get_mech
);


use Carp;
$SIG{ __DIE__ } = \&Carp::confess; # this stack-trace on all fatal error !!!

use Data::Dumper;
$Data::Dumper::Terse = 1;     # print without "$VAR1="
$Data::Dumper::Sortkeys = 1;  # this sorts the Dumper output!

#use LWP;
use WWW::Mechanize;
use HTTP::Cookies;

my $mech;

sub get_mech {
   my ($opt) = @_;

   my $verbose = $opt->{verbose};

   if ($mech) {
      $verbose && print STDERR 'reusing existing $mech', "\n";
      return $mech;
   } else {
      $verbose && print STDERR 'creatiing a new $mech', "\n";
   }

   my $cookie_file = $opt->{cookie_file} ? $opt->{cookie_file} : 
                                           "$ENV{'HOME'}/.tpsup/cookies_mechanize.txt";

   if (! -f $cookie_file) {
      $verbose && print STDERR "cmd = cat /dev/null > $cookie_file\n";
      open my $fh, ">$cookie_file" or die "cannot write to $cookie_file: $!";
      close $fh;
   }

   my $file_mode = sprintf("%04o", (stat($cookie_file))[2] & 07777);
   if ("$file_mode" ne "0600") {
      my $cmd = "chmod 600 $cookie_file";
      $verbose && print STDERR "cmd = $cmd\n";
      system($cmd);
      ( $? != 0 ) && die "cmd failed: $!";
   }

   my $cookie_jar = HTTP::Cookies->new(
     file => "$ENV{'HOME'}/.tpsup/cookies_mechanize.txt",

     autosave => 1,

     # the cookies might be expired, or requested to be discarded,
     # so,construct your $cookie_jar with ignore_discard set to 1:
     # somehow, without this setting, cookies are not saved to the file.
     ignore_discard => 1,
   );
   
   $mech = WWW::Mechanize->new(
      # agent_alias => 'Linux Mozilla',
      agent => 'Mozilla/5.0 (X11; Linux x86_64)',
   
      # Enable strict form processing to catch typos and non-existant form fields.
      strict_forms => 1,
   
      # Checks each request made to see if it was successful
      autocheck => 1,
   
      cookie_jar => $cookie_jar,
   );

   return $mech;
}


sub main {
   print "------------ test get_mech -----------------------------\n";
   my $mech = get_mech();
   print "mech = ", Dumper($mech);
}

main() unless caller();

1
