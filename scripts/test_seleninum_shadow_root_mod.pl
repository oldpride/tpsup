#!/usr/bin/env perl

use Selenium::Chrome;
use Data::Dumper;
use Scalar::Util qw(blessed);

my $driver = Selenium::Chrome->new (
   startup_timeout => 60,
   custom_args => "--log-path=/tmp/selenium_chromedriver",
   logfile => "/tmp/selenium_chromedriver2", 
   debug_on => 1,
   extra_capabilities => {
      'goog:chromeOptions' => {
         args => [
            '--no-sandbox',
            '--disable-dev-shm-usage', 
            '--window-size=1260,720',
            '--user-data-dir=/tmp/selenium_chrome',
         ],
      },
   },
);

$driver->get("chrome-search://local-ntp/local-ntp.html"); # chrome new tab
my $shadow_host = $driver->find_element("html/body/ntp-app", "xpath");
#my $shadow_root = $driver->execute_script('return arguments[0].shadowRoot', $shadow_host);
#for my $e ( @{$shadow_root->find_elements(':host > *', 'css')} ) {
#   # i get error: unblessed
#   print "found\n";
#}

package TPSUP::SELENIUM::SHADOWROOT {   # perl oop
   # we make the shadow_root look like a driver - this is what Python did.
   # the main goal is to allow us to search in the shadow DOM.
   #     find_element( $target, $scheme)
   #     find_elements($target, $scheme)
   # eg
   #     find_element( "input",     "css")
   #     find_elements(":host > *", "css")

   use Data::Dumper;
   use Carp;

   sub new {
      my ($class, %attrs) = @_;
      my $shadow_root = $attrs{driver}->execute_script('return arguments[0].shadowRoot', $attrs{shadow_host});

      return undef if ! $shadow_root;

      # croak "this is not a shadow host" if ! $shadow_root;
      #print "shadow_root = ", Dumper($shadow_root);

      $attrs{shadow_root} = $shadow_root;

      bless \%attrs, $class;
   }
   sub find_element {
      my ($self, $target, $scheme) = @_;
      die "scheme=$scheme is not supported. Only css is supported" if $scheme ne 'css';
      return $self->{driver}->execute_script(
                 "return arguments[0].querySelector(arguments[1])",
                 $self->{shadow_root},
                 $target
             );
   }
   sub find_elements {
      my ($self, $target, $scheme) = @_;
      die "scheme=$scheme is not supported. Only css is supported" if $scheme ne 'css';
      return $self->{driver}->execute_script(
                "return arguments[0].querySelectorAll(arguments[1])",
                $self->{shadow_root},
                $target
      );
   }
};

my $shadow_driver = TPSUP::SELENIUM::SHADOWROOT->new(driver=>$driver, shadow_host=>$shadow_host);
for my $e ( @{$shadow_driver->find_elements(':host > *', 'css')} ) {
   print "found\n";
}


$driver->shutdown_binary();
