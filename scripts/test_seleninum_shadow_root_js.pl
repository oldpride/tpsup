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

#print "shadow_host = ", Dumper($shadow_host);
#print "blessed = ", blessed($shadow_host), "\n";

my $js1 = <<'END';
var shadow_root = arguments[0].shadowRoot;
return shadow_root.querySelector(":host > *").outerHTML;
END

my $shadow1 = $driver->execute_script($js1, $shadow_host);
print "shadow1 = ", Dumper($shadow1);

my $js2 = <<'END';
var shadow_root = arguments[0].shadowRoot;
//var all_elements = shadow_root.querySelectorAll(":host > *");
var all_elements = shadow_root.querySelectorAll("cr-button");
var html = '';
for (var i=0; i<all_elements.length; i++) {
   html += all_elements[i].outerHTML
   html += '\n'
   html += '--------------------------------------------\n'
   html += '\n'
}

return html
END

my $shadow2 = $driver->execute_script($js2, $shadow_host);
print "shadow2 = ", Dumper($shadow2);

my $js3 = <<'END';
var shadow_root = arguments[0].shadowRoot;
var elements = shadow_root.querySelectorAll(":host > *");
return elements
END

my $shadow3 = $driver->execute_script($js3, $shadow_host);
print "shadow3 = ", Dumper($shadow3);

for my $e (@$shadow3) {
   print "found\n";
}

$driver->shutdown_binary();
