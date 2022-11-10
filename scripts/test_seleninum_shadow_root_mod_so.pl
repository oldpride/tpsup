#!/usr/bin/env perl

# for stackoverflow.com
# https://stackoverflow.com/questions/73724414/

use Selenium::Chrome;

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

package MyShadow { 
   sub new {
      my ($class, %attrs) = @_;
      my $shadow_root = $attrs{driver}->execute_script('return arguments[0].shadowRoot', $attrs{shadow_host});
      return undef if ! $shadow_root;
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

my $shadow_driver = MyShadow->new(driver=>$driver, shadow_host=>$shadow_host);
if ($shadow_driver) {
   for my $e ( @{$shadow_driver->find_elements(':host > *', 'css')} ) {
      print "found\n";
   }
}

$driver->shutdown_binary();
