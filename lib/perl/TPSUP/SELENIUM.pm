package TPSUP::SELENIUM;

use warnings;
use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
  get_driver
  run_actions
  wdkeys
  get_detail
  print_detail
  js_get
  js_print
  locator_chain_to_js_list
  js_list_to_locator_chain
  print_js_console_log
  wrap_js_in_trap
  dump
  tp_get_outerHTML
);

use Carp;
use Data::Dumper;
$Data::Dumper::Sortkeys = 1;    # this sorts the Dumper output!
$Data::Dumper::Terse    = 1;    # print without "$VAR1="
use TPSUP::UTIL qw(
  get_user
  get_homedir
  hit_enter_to_continue
);
use TPSUP::FILE qw(
  get_out_fh
  close_out_fh
);

use TPSUP::DATE qw(get_yyyymmdd);
use TPSUP::SELENIUM::SHADOWROOT;
use Selenium::Chrome;

# main usage info is in https://metacpan.org/pod/Selenium::Remote::Driver

use Selenium::Remote::WDKeys qw(KEYS);    # special keys: enter, backspace, ...
use Selenium::Waiter;                     # wait_until {} is from here

# https://metacpan.org/pod/Selenium::ActionChains
# need ths for things like SHIFT+TAB
use Selenium::ActionChains;

use TPSUP::GLOBAL qw($we_return);     # global vars
use TPSUP::NET    qw(is_tcp_alive);

sub wdkeys {
   my ( $key, $count, $opt ) = @_;

# example application: use this function to generate plenty backspaces to clear a field

   # Selenium::Remote::WDKeys
   my @array = ( KEYS->{$key} ) x $count;
   return @array;
}

sub get_driver {
   my ($opt) = @_;

   my $driver_cfg = $opt->{driver_cfg};

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   my $host_port = $opt->{host_port} ? $opt->{host_port} : 'auto';

   my $drivername =
     $driver_cfg->{drivername} ? $driver_cfg->{drivername} : "chromedriver";
   my $BrowserArgs =
     $driver_cfg->{BrowserArgs} ? $driver_cfg->{BrowserArgs} : [];

# startup_timeout is in seconds. basically is how long to wait for the browser ready
   my $startup_timeout =
     $driver_cfg->{startup_timeout} ? $driver_cfg->{startup_timeout} : 60;

   my $user     = get_user();
   my $home_dir = get_homedir();
   my $log_base = defined( $opt->{log_base} ) ? $opt->{log_base} : $home_dir;

   my $driver_log  = "$log_base/selenium_driver.log";
   my $driver_log2 = "$log_base/selenium_driver2.log";
   my $browser_dir = "$log_base/selenium_browser";

   my $driver_args = "--verbose --log-path=$driver_log"; # chromedriver cmd line

   my $browser_options;

   if ( $host_port eq 'auto' ) {

  # these args are chrome browser (including chromium-browser) command line args
      $browser_options->{args} = [
         '--no-sandbox',               # to run without root
         '--disable-dev-shm-usage',    # to run without root
         '--window-size=1260,720',     # make it > 1000 to avoid mobile mode

         # use a separate browser dir to avoid corruption
         "--user-data-dir=$browser_dir",
      ];

      if ( $opt->{headless} ) {
         push @{ $browser_options->{args} }, "--headless";
      }

      for my $ba (@$BrowserArgs) {
         #'--proxy-pac-url=http://pac.abc.net',
         push @{ $browser_options->{args} }, "--$ba";
      }

      push @{ $browser_options->{args} }, "--remote-debugging-pipe";

# without $browser_options->{debuggerAddress} set, chromedriver will start
# a chrome. In this case, connection between chromedriver and chrome is likely
# not using tcp/ip because --remote-debugging-port=0
#
# tian      8660 26.8  1.9 17542768 159492 pts/2 Sl+  22:23   0:01 /opt/google/chrome/chrome --allow-pre-commit-input --disable-background-networking --disable-client-side-phishing-detection --disable-default-apps --disable-dev-shm-usage --disable-hang-monitor --disable-popup-blocking --disable-prompt-on-repost --disable-sync --enable-automation --enable-blink-features=ShadowDOMV0 --enable-logging --ignore-certificate-errors --log-level=0 --no-first-run --no-sandbox --no-service-autorun --password-store=basic --remote-debugging-port=0 --test-type=webdriver --use-mock-keychain --user-data-dir=/tmp/selenium_browser_tian --window-size=960,540 --enable-crashpad
      print "we will start a chromedriver which will auto start a browser\n";
   } elsif ( $host_port =~ /^(.+?):([^:]+)$/ ) {
      my ( $host, $port ) = ( $1, $2 );

      print
"we will start a chrome driver which will connect to an existing browser at host:port=$host_port\n";

      # this is the browser's debugger listener port.
      # once we set this, chromedriver will not start up a browser
      $browser_options->{debuggerAddress} = $host_port;

      if ( $host_port =~ /^(localhost|127.0.0.1):(.+)/ ) {

         # we are expecting a local chrome browser
         if ( !is_tcp_alive( $host, $port ) ) {
            print "local brower at port $port is not up. we will start one\n";

            # this command is derived from above, when we run in 'auto' mode
            my $cmd =
"chrome --allow-pre-commit-input --disable-background-networking --disable-client-side-phishing-detection --disable-default-apps --disable-dev-shm-usage --disable-hang-monitor --disable-popup-blocking --disable-prompt-on-repost --disable-sync --enable-automation --enable-blink-features=ShadowDOMV0 --enable-logging --ignore-certificate-errors --log-level=0 --no-first-run --no-sandbox --no-service-autorun --password-store=basic --remote-debugging-port=$port --test-type=webdriver --use-mock-keychain --user-data-dir=$browser_dir --window-size=960,540 --enable-crashpad";
            print "run chrome browser in background, cmd=$cmd\n";
            unless (fork) {
               $ENV{PATH} = "/opt/google/chrome:$ENV{PATH}";
               print "current PATH=$ENV{PATH}\n";
               exec($cmd);
            }
         }
      } else {

         # we are connecting to a remote browser

         if ( !$opt->{X11} && exists( $ENV{DISPLAY} ) ) {

         # $driver->send_keys_to_active_element() will try to open an X
         # connection if it detects $DISPLAY. This will trigger a firewall alert
         # on PC in an corporate env. So we unset $DISPLAY by default. But if
         # we run the browser locally, we leave $DISPLAY alone, because broswer
         # needs $DISPLAY to launch.
            delete $ENV{DISPLAY};
         }
      }
   } else {
      croak "host_port='$host_port' is not in host:port format";
   }

# to check any lingering chromedriver. they should have been killed before we start
   my $cmd = "ps -f -u $user |grep $drivername|grep -v grep";
   print "$cmd\n";
   my @lines = `$cmd`;
   if (@lines) {
      print @lines;
      print "ERROR: seen $drivername already running\n";
      exit 1;
   }

   $cmd = "cat /dev/null > $driver_log";
   print "$cmd\n";
   system($cmd);

   if ( $verbose > 1 ) {

      # --pid PID  exits when PID is gone
      # -F         retry file if it doesn't exist
      $cmd = "tail --pid $$ -F -f $driver_log &";
      print "$cmd\n";
      system($cmd);
   }

   my $path = $ENV{PATH} ? $ENV{PATH} : "";
   if ( $path !~ m:/usr/sbin: ) {
      $ENV{PATH} .= ":/usr/sbin";
      $verbose
        && print
        "added /usr/sbin to PATH for lsof(1s) in Selenium::CanStartBinary\n";
   }

   my $driver = Selenium::Chrome->new(

      # the following seting are in Selenium::Chrome
      startup_timeout => $startup_timeout,
      custom_args     => $driver_args,

      # the following setting are in Selenium/CanStartBinary.pm
      logfile => "${driver_log2}",   # another chromedriver log, shorter version

      # Selenium::Chrome is an extension of Selenium::Remote::Driver
      # the following setting are in Selenium::Remote::Driver
      debug_on           => 1,
      extra_capabilities => {
         'goog:chromeOptions' => $browser_options,
      },
   );

   $driver->{seleniumEnv}->{log_base} =
     $log_base;    # monkey patchig for convenience

   return $driver;

}

sub run_actions {
   my ( $driver, $actions, $opt ) = @_;

   my $dryrun      = $opt->{dryrun};
   my $interactive = $opt->{interactive};
   my $debug       = $opt->{debug} ? $opt->{debug} : 0;
   my $print_console_log =
     $opt->{print_console_log} ? $opt->{pring_console_log} : 0;

   my $result = {};

   for my $row (@$actions) {

# locator                             input         comment     extra
# [ 'tab=1', ['stirng='.wdkeys('backtick',30).'hello', 'code=sleep 1'], 'greeting' ]
# [ {locator=>'xpath=//botton[@id="Submit"], NotFound=>'$we_return=1'},
#   ['click', 'sleep=2'],           'Submit ]

      my ( $locator, $input, $comment, $extra ) = @$row;

      my $element;

      if ( defined $comment ) {
         print "$comment\n";
      }

      # 'return' in eval will only return to eval, not to the caller sub.
      # in order to return the caller sub, we use the following var, which
      # can be modified by eval.
      # $TPSUP::GLOBAL::we_return;

      $element = locate( $driver, $locator, $opt );

      print_js_console_log($driver) if $print_console_log;

      if ($debug) {
         js_print_debug( $driver, $element );
      }

      return if $we_return;

      send_input( $driver, $element, $input, $opt );

      print_js_console_log($driver) if $print_console_log;

      return if $we_return;

      print "\n";
   }

   return $result;
}

sub js_print_debug {
   my ( $driver, $element ) = @_;

   print "this element is\n";
   js_print( $driver, $element, 'xpath' );
   js_print( $driver, $element, 'attrs' );

   print "current active element is\n";
   my $active_element = $driver->get_active_element();
   js_print( $driver, $active_element, 'xpath' );
   js_print( $driver, $active_element, 'attrs' );
}

my $locator_driver;
my $driver_url;

sub locate {
   my ( $driver, $locator2, $opt ) = @_;

   print "\n";

   my $dryrun      = $opt->{dryrun};
   my $interactive = $opt->{interactive};

   my $element;

   # https://metacpan.org/pod/Selenium::Remote::WebElement
   # https://metacpan.org/pod/Selenium::Remote::Driver

   my $current_url = $driver->get_current_url();

   if ( !$locator_driver || !$driver_url || $current_url ne $driver_url ) {

# - when in a shadow root, $locator_driver and $driver are diffrent.
# - when we click and go to a different page, which can be told by a url change,
#   we need to sync up $locator_driver with $driver.
# - when in an iframe, even if the iframe is in a shadow root, $locator_driver
#   and $driver are the same.

      $locator_driver = $driver;
      $driver_url     = $current_url;
   }

# example of actions:
#
#     $actions = [
#         [ 'xpath=/a/b,xpath=/a/c', 'click', 'string locator' ],
#         [ ['xpath=/a/b', 'shadow', 'css=d'], 'click', 'chain locator'],
#         [
#             {
#                 locator => 'xpath=/a/b,xpath=/a/c',
#                 NotFound => 'print "not found\n";',
#             },
#             'click',
#             'use hash for the most flexibility'
#         ],
#         [
#             '
#                 xpath=//dhi-wc-apply-button[@applystatus="true"],
#                 xpath=//dhi-wc-apply-button[@applystatus="false"],
#             ',
#             {
#                 0 => 'code=
#                       $action_data->{error} = "applied previously";
#                       $we_return=1;
#                      ',
#                 1 => undef,
#             },
#             'find applied or not. If applied, return'
#         ],
#         [
#            {
#              chains => [
#                  # branch in the beginning
#                  [
#                      'xpath=/html/body[1]/ntp-app[1]', 'shadow',
#                      'css=#mostVisited', 'shadow',
#                      'css=#removeButton2', # correct on ewould be 'css=#removeButton'. we purposefully typoed
#                  ],
#                  [
#                      'xpath=/html/body[1]/ntp-app[1]', 'shadow',
#                      'css=#mostVisited', 'shadow',
#                      'css=#actionMenuButton'
#                  ],
#              ],
#            },
#            {
#              # first number is the chain number, followed by locator number
#              '0.0.0.0.0.0' => 'code=print "found remove button\n";',
#              '1.0.0.0.0.0' => 'code=print "found action button\n";',
#            },
#            "test chains",
#        ],
#     ];

   my $type = ref $locator2;
   if ( $type && $type eq 'HASH' && exists $locator2->{chains} ) {
      my $h = $locator2;
      print "locate(): search for chains = ", Dumper( $h->{chains} );

      hit_enter_to_continue() if $interactive;

      if ( !$dryrun ) {
         my $finder = new tp_find_element_by_chains( $h->{chains}, $opt );
         $element = wait_until { $finder->find($driver) };

         if ( !$element ) {
            print "locate failed. matched_paths =\n",
              Dumper( $finder->{matched_paths} );

            my $code = $h->{NotFound};
            if ( defined $code ) {
               print "NotFound-handling code = $code\n";
               hit_enter_to_continue() if $interactive;
               eval $code;
               if ($@) {
                  croak "code='$code' failed: $@";
               }
            } else {
               croak "none of paths found\n";
            }
         }

         if ( !$element ) {
            $element = $driver->get_active_element();
         }

         if ( exists $element->{tpdata} ) {
            print "tpdata = ", Dumper( $element->{tpdata} );
         }
      }

      return $element;
   }

   my $h;

   if ( !$type ) {
      $h->{locator} = [$locator2];
   } elsif ( $type eq 'ARRAY' ) {
      $h->{locator} = $locator2;
   } elsif ( $type eq 'HASH' ) {
      $h = $locator2;
      my $type2 = $h->{locator};
      if ( !$type2 ) {

         # scalar
         $h->{locator} = [ $h->{locator} ];
      } elsif ( $type2 != 'ARRAY' ) {
         croak "unexpected locator type='$type2' at h=" . Dumper($h);
      }
   } else {
      croak "unsupported locator type=$type, ", Dumper($locator2);
   }

   my $locator_chain = $h->{locator};    # this should be a ref to array

   for my $locator (@$locator_chain) {
      if ( !$locator ) {
         print "locate(): INFO: no locator\n";
         $element = $driver->get_active_element() if !$dryrun;
         return;
      } elsif ( $locator =~ /^code=(.+)/s ) {
         my $code = $1;
         print "locate(): locator code = $code\n";
         hit_enter_to_continue() if $interactive;
         if ( !$dryrun ) {
            eval $code;
            if ($@) {
               croak "code='$code' failed: $@";
            }
            return if $we_return;
            $element = $driver->get_active_element();
         }
      } elsif ( $locator =~ /^js=(.+)/s ) {
         my $js = $1;
         print "locate(): run js code = $js\n";
         hit_enter_to_continue() if $interactive;
         if ( !$dryrun ) {
            $element = $driver->execute_script($js);
         }
      } elsif ( $locator =~ /^(url|url_accept_alert)=(.+)/ ) {
         my ( $tag, $url ) = ( $1, $2 );
         my $opt2 = { interactive => $interactive };
         if ( $tag eq 'url_accept_alert' ) {
            $opt2->{accept_alert} = 1;
         }
         print "locate(): go to $url\n";
         hit_enter_to_continue() if $interactive;
         if ( !$dryrun ) {
            tp_get_url( $driver, $url, $opt2 );
            $element        = $driver->get_active_element();
            $locator_driver = $driver;
         }
      } elsif ( $locator =~ /^tab=(\d+)/ ) {
         my $count = $1;
         print "locate(): forward $count tabs\n";
         hit_enter_to_continue() if $interactive;
         if ( !$dryrun ) {
            $driver->send_keys_to_active_element( wdkeys( 'tab', $count ) );
            $element = $driver->get_active_element();

            #$element->click();
         }
      } elsif ( $locator eq 'shadow' ) {
         print "locate(): go into shadow root\n";
         hit_enter_to_continue() if $interactive;
         if ( !$dryrun ) {

            # $locator_driver = $element->shadow_root;
            # as of 2022/09/09 Perl Selenium cannot handle shadow root
            # therefore, we have to use javascript to implement our own
            # https://stackoverflow.com/questions/36141681

            my $shadow_root = TPSUP::SELENIUM::SHADOWROOT->new(
               driver      => $driver,
               shadow_host => $element
            );

            #print "shadow_root = ", Dumper($shadow_root);

            croak "cannot find shadow root here" if !$shadow_root;

            $locator_driver = $shadow_root;

    #for my $e ( @{$locator_driver->find_elements(':host > *', 'css')} ) {
    #   # crashed with: Can't call method "find_elements" on unblessed reference
    #   print tp_get_outerHTML($driver, $e), "\n";
    #}
         }
      } elsif ( $locator eq 'iframe' ) {
         print "locate(): switch to iframe\n";
         hit_enter_to_continue() if $interactive;
         if ( !$dryrun ) {
            $driver->switch_to_frame($element);
            $locator_driver = $driver;
         }
      } elsif ( $locator =~ /^shifttab=(\d+)/ ) {
         my $count = $1;
         print "locate(): backward $count tabs (ie, shift tabs)\n";
         hit_enter_to_continue() if $interactive;
         if ( !$dryrun ) {
            my $ac = Selenium::ActionChains->new( driver => $driver );
            for ( my $i = 0 ; $i < $count ; $i++ ) {

               # we have to do key_down() for every tab
               # https://github.com/teodesian/Selenium-Remote-Driver/issues/480
               $ac->key_down( [ KEYS->{'shift'} ] );
               $ac->send_keys( KEYS->{'tab'} );
            }
            $ac->key_up( [ KEYS->{'shift'} ] );

    # print "ac = ", Dumper($ac->actions); # this only print DUMMY(...), useless

            $ac->perform;

            $element = $driver->get_active_element();

            #$element->click();
         }
      } elsif ( $locator =~ /^\s*(xpath|click_xpath|css|click_css)=(.+)/s ) {

# xpath=//a[contains(@aria-label, "Open record: ")],xpath=//tr[contains(text(), "No records to display")]
         my $type   = $1;
         my $string = $2;

         my $path = $string;

         # allowing space chars and ending comma to make the coding easier
         $string =~ s/[\s,]+$//;    # trim ending space and comma

         my @paths;

         while (
            $string =~ /\G(.+?)\s*,\s*(xpath|click_xpath|css|click_css)=/gcs )
         {
            # 'c' - keep the current position during repeated matching
            # 'g' - globally match the pattern repeatedly in the string
            # 's' - treat string as single line

          # auto-click or not ?!
          #    an element located by xpath is NOT the active (focused) element.
          #    we have to click it to make it active (foucsed)
          #
          #    on the other side, element located by tab is the active (focused)
          #    element
          #
          #    sounds like we should click on the element found by xpath.
          #    but then if it is submit button, clicking will trigger the action
          #    likely prematurally
          #
          # therefore, we introduced the click_xxxx switch

            $path = $1;
            my $type2 = $2;

            print "$1, $2\n";

            push @paths, [ $type, $path ];

            $type = $type2;    # $type is used for the next round
         }

         my ($leftover) = ( $string =~ /\G(.*)/s );

         push @paths, [ $type, $leftover ];

         print "locate(): find_element with paths = ", Dumper( \@paths );
         hit_enter_to_continue() if $interactive;
         if ( !$dryrun ) {
            if ( $locator_driver != $driver ) {
               print "we are in shadow root\n";
            }

            $element = wait_until {
               tp_find_element_by_paths( $locator_driver, \@paths, $opt );
            };

            if ( !$element ) {
               my $code = $h->{NotFound};
               if ( defined $code ) {
                  print "NotFound-handling code = $code\n";
                  hit_enter_to_continue() if $interactive;
                  eval $code;
                  if ($@) {
                     croak "code='$code' failed: $@";
                  }
               } else {
                  croak "none of paths found\n";
               }
               last;
            }
         }
      } else {
         croak "unsupported locator='$locator'";
      }
   }

   if ( !$element && !$dryrun ) {
      $element = $driver->get_active_element();
   }

   return $element;
}

sub tp_find_element_by_paths {
   my ( $driver, $paths, $opt ) = @_;
   my $e;
   for my $row (@$paths) {
      my ( $type, $path ) = @$row;
      my $click = $type =~ /^click_/ ? 1 : 0;

      # silence error from eval
      # https://stackoverflow.com/questions/27243616/
      if ( $type =~ /xpath/ ) {
         eval {
            local $SIG{__WARN__} = sub { };
            $e = $driver->find_element( $path, 'xpath' );
         };
      } else {
         eval {
            local $SIG{__WARN__} = sub { };
            $e = $driver->find_element( $path, 'css' );
         };
      }
      if ($e) {
         $e->click() if $click;
         last;
      }
   }
   $e;
}

package tp_find_element_by_chains {
   use strict;
   use warnings;
   use Data::Dumper;
   use Carp;

   sub new {
      my ( $class, $chains, $opt ) = @_;
      my $attr;
      $attr->{chains}               = [];
      $attr->{opt}                  = $opt;
      $attr->{verbose}              = $opt->{verbose} ? $opt->{verbose} : 0;
      $attr->{matched_paths}        = undef;
      $attr->{matched_numbers}      = undef;
      $attr->{current_matched_path} = undef;

# parse chains
#
#  example: convert ONE chain from
#
# [
#     'xpath=/html/body[1]/ntp-app[1]', 'shadow', 'css=#mostVisited', 'shadow',
#     '
#     css=#removeButton2,
#     css=#actionMenuButton
#     ',
# ],
#
# into
#
# [
#     [['xpath', '/html/body[1]/ntp-app[1]']], [['shadow']] , [['css', '#mostVisited']], [['shadow']] ,
#     [['css', '#removeButton2'], ['css', '#actionMenuButton']],
# ]
#
      for ( my $i = 0 ; $i < scalar(@$chains) ; $i++ ) {
         for my $locator ( @{ $chains->[$i] } ) {
            if ( ( $locator eq 'shadow' || $locator eq 'iframe' ) ) {
               push @{ $attr->{chains}->[$i] }, [ [$locator] ];
            } elsif ( $locator =~ /^\s*(xpath|css)=(.+)/s ) {

# xpath=//a[contains(@aria-label, "Open record: ")],xpath=//tr[contains(text(), "No records to display")]
               my $type   = $1;
               my $string = $2;

               my $path = $string;

               # allowing space chars and ending comma to make the coding easier
               $string =~ s/[\s,]+$//;    # trim ending space and comma

               my @paths;

               while ( $string =~ /\G(.+?)\s*,\s*(xpath|css)=/gcs ) {

                  # 'c' - keep the current position during repeated matching
                  # 'g' - globally match the pattern repeatedly in the string
                  # 's' - treat string as single line

          # auto-click or not ?!
          #    an element located by xpath is NOT the active (focused) element.
          #    we have to click it to make it active (foucsed)
          #
          #    on the other side, element located by tab is the active (focused)
          #    element
          #
          #    sounds like we should click on the element found by xpath.
          #    but then if it is submit button, clicking will trigger the action
          #    likely prematurally
          #
          # therefore, we introduced the click_xxxx switch

                  $path = $1;
                  my $type2 = $2;

                  print "$1, $2\n";

                  push @paths, [ $type, $path ];

                  $type = $type2;    # $type is used for the next round
               }

               my ($leftover) = ( $string =~ /\G(.*)/s );

               push @paths, [ $type, $leftover ];

               push @{ $attr->{chains}->[$i] }, \@paths;
            } else {
               croak "unsupported locator='$locator'";
            }
         }
      }

      print "parsed chains = ", Dumper( $attr->{chains} ) if $attr->{verbose};

      bless $attr, $class;
   }

   sub find {
      my ( $self, $driver ) = @_;
      my $verbose = $self->{verbose};

      $self->{matched_paths}        = [];
      $self->{matched_numbers}      = [];
      $self->{current_matched_path} = [];

      my $e;

      for ( my $i = 0 ; $i < scalar( @{ $self->{chains} } ) ; $i++ ) {
         my $chain = $self->{chains}->[$i];
         print "testing chain #$i = ", Dumper($chain) if $verbose;

         # reset vars
         my $locator_driver = $driver;
         $self->{matched_paths}->[$i]   = [];
         $self->{matched_numbers}->[$i] = [];

         my $found_chain = 1;

         for my $locator (@$chain) {
            print "testing locator = ", Dumper($locator) if $verbose;
            if ( $locator->[0]->[0] eq 'shadow' ) {
               print "testing locator->[0]->[0] = $locator->[0]->[0]\n"
                 if $verbose;
               croak "element is not defined before going into shadow root"
                 if !$e;

               my $shadow_root = TPSUP::SELENIUM::SHADOWROOT->new(
                  driver      => $driver,
                  shadow_host => $e
               );

               if ( !$shadow_root ) {
                  print "not found $locator->[0]->[0]\n" if $verbose;
                  $found_chain = 0;
                  last;
               }

               print "found $locator->[0]->[0]\n" if $verbose;
               $locator_driver = $shadow_root;
               push @{ $self->{matched_paths}->[$i] },   $locator->[0]->[0];
               push @{ $self->{matched_numbers}->[$i] }, 0;
            } elsif ( $locator->[0]->[0] eq 'iframe' ) {
               print "testing locator->[0]->[0] = $locator->[0]->[0]\n"
                 if $verbose;
               croak "element is not defined before going into iframe" if !$e;
               eval { $driver->switch_to_frame($e); };
               if ($@) {
                  print "not found $locator->[0]->[0]. $@\n" if $verbose;
                  $found_chain = 0;
                  last;
               }
               print "found $locator->[0]->[0]\n" if $verbose;
               $locator_driver = $driver;
               push @{ $self->{matched_paths}->[$i] },   $locator->[0]->[0];
               push @{ $self->{matched_numbers}->[$i] }, 0;
            } else {
               my $one_parallel_path_matched = 0;
               my $j                         = 0;
               for my $parallel_path (@$locator) {

           # if one of the rows found, we move to next locator. otherwise, fail.
                  my ( $type, $path ) = @$parallel_path;
                  print "testing $type=$path\n" if $verbose;
                  if ( $type =~ /xpath/ ) {
                     eval {
                        local $SIG{__WARN__} = sub { };
                        $e = $locator_driver->find_element( $path, 'xpath' );
                     };
                     if ($@) {
                        $j++;
                        next;
                     }
                  } else {
                     eval {
                        local $SIG{__WARN__} = sub { };
                        $e = $locator_driver->find_element( $path, 'css' );
                     };
                     if ($@) {
                        $j++;
                        next;
                     }
                  }

                  print "found $type=$path\n" if $verbose;
                  $one_parallel_path_matched = 1;
                  push @{ $self->{matched_paths}->[$i] },   "$type=$path";
                  push @{ $self->{matched_numbers}->[$i] }, $j;
                  last;
               }

               print "one_parallel_path_matched=$one_parallel_path_matched\n"
                 if $verbose;
               if ( !$one_parallel_path_matched ) {
                  $found_chain = 0;
                  last;
               }
            }

            if ( !$e ) {

               # some locators don't explicitly return an element,
               # therefore, we set it here.
               $e = $driver->get_active_element();
            }

            print "matched_paths->[$i] = ",
              Dumper( $self->{matched_paths}->[$i] )
              if $verbose;
            $self->{current_matched_path} =
              [ @{ $self->{matched_paths}->[$i] } ];    #copy array
         }

         if ($found_chain) {
            $e->{tpdata} = {
               matched_chain => [ @{ $self->{matched_paths}->[$i] } ]
               ,                                        # copy array
               position => "$i."
                 . join( ".", @{ $self->{matched_numbers}->[$i] } ),
            };    # monkey patch

            return $e;
         }
      }

      return undef;
   }
};

sub print_js_console_log {
   my ( $driver, $opt ) = @_;

   # https://stackoverflow.com/questions/57494687
   my $log = $driver->get_log('browser');

   my $printed_header = 0;
   for my $entry (@$log) {
      if ( !$printed_header ) {
         print "------ begin console log -------\n";
         $printed_header = 1;
      }

      print( Dumper($entry) );
   }

   if ($printed_header) {
      print "------ end console log -------\n";
   }
}

sub send_input {
   my ( $driver, $element, $input, $opt ) = @_;

   my $dryrun      = $opt->{dryrun};
   my $interactive = $opt->{interactive};
   my $humanlike   = $opt->{humanlike};

   if ( !$input ) {
      print "INFO: no input\n";
      return;
   }

   my @steps;

   my $input_type = ref $input;
   if ( !$input_type ) {
      push @steps, $input;
   } elsif ( $input_type eq 'ARRAY' ) {
      @steps = @$input;
   } elsif ( $input_type eq 'HASH' ) {

      # {
      #    '0' => 'click',
      #    '1' => ['click', 'sleep=1'],
      #    '2' => 'code=pass',
      # }

      if ( exists( $element->{tpdata} ) && defined( $element->{tpdata} ) ) {
         my $tpdata = $element->{tpdata};

         my $position = $tpdata->{position};

         if ( exists $input->{$position} ) {
            my $input2 = $input->{$position};

            if ( !$input2 ) {
               print "action: no input\n";
               return;
            }

            my $input2_type = ref($input2);
            if ( !$input2_type ) {
               push @steps, $input2;
            } elsif ( $input2_type eq "ARRAY" ) {
               push @steps, @$input2;
            } else {
               croak "input->{$position} type=$input2_type is not supported."
                 . Dumper($input2);
            }
         } else {
            croak "position='$position' is not defined in input="
              . Dumper($input);
         }
      } else {
         croak "tpdata is not available from element";
      }
   } else {
      croak "unsupported input_type='$input_type', input=", Dumper($input);
   }

   if ( !$interactive && $humanlike ) {
      human_delay($opt);
   }

   for my $step (@steps) {
      if ( $step eq 'debug' ) {
         print "action: print debug info\n";
         js_print_debug( $driver, $element );
      } elsif ( $step =~ /^code=(.+)/s ) {
         my $code = $1;
         print "action: step code = $code\n";
         hit_enter_to_continue() if $interactive;
         eval($code)             if !$dryrun;
         if ($@) {
            croak "code='$code' failed: $@";
         }
         return if $we_return;
      } elsif ( $step =~ /^sleep=(.+)/s ) {
         my $seconds = $1;
         print "action: sleep $seconds seconds\n";
         hit_enter_to_continue() if $interactive;
         sleep $seconds          if !$dryrun;
      } elsif ( $step =~ /string=(.*)/ ) {
         my $string = $1;
         print "action: typing $string\n";
         hit_enter_to_continue() if $interactive;
         if ( !$dryrun ) {
            $driver->send_keys_to_active_element($string);
         }
      } elsif ( $step =~ /is_attr_empty=(.*)/ ) {
         my $attr = $1;
         print "action: assert attr=$attr is empty\n";
         hit_enter_to_continue() if $interactive;
         if ( !$dryrun ) {
            my $value = $element->get_attribute($attr);
            if ($value) {
               print "attr='$value' is already set.\n";
               return;
            }
         }
      } elsif ( $step =~ /clear_attr=(.*)/ ) {
         my $attr = $1;
         print "action: check whether need to clear '$attr'\n";
         hit_enter_to_continue() if $interactive;
         if ( !$dryrun ) {
            my $value = $element->get_attribute($attr);
            if ($value) {
               print "attr='$value'. removing it with backspaces now\n";
               my $length = length($value);
               $driver->send_keys_to_active_element(
                  wdkeys( 'backspace', $length ) );
            }
         }
      } elsif ( $step =~ /^tab=(\d+)/ ) {
         my $count = $1;
         print "action: forward $count tabs\n";
         hit_enter_to_continue() if $interactive;
         if ( !$dryrun ) {
            $driver->send_keys_to_active_element( wdkeys( 'tab', $count ) );
         }
      } elsif ( $step =~ /key=(.+?),(\d+)/ ) {
         my $key   = $1;
         my $count = $2;
         print "action: typing $key $count times\n";
         hit_enter_to_continue() if $interactive;
         $driver->send_keys_to_active_element( wdkeys( $key, $count ) )
           if !$dryrun;
      } elsif ( $step eq 'click' ) {
         print "action: click\n";
         hit_enter_to_continue() if $interactive;
         $element->click()       if !$dryrun;
      } elsif ( $step eq 'iframe' ) {
         print "action: switch to iframe\n";
         hit_enter_to_continue()            if $interactive;
         $driver->switch_to_frame($element) if !$dryrun;
      } elsif ( $step =~ /select=(text|value|index),(.*)/ ) {
         my $attr  = $1;
         my $value = $2;
         print "action: select $attr='$value'\n";
         hit_enter_to_continue()                           if $interactive;
         select_option( $driver, $element, $attr, $value ) if !$dryrun;
      } elsif ( $step =~ /dump_(all|element)=(.+)/ ) {
         my $scope      = $1;
         my $output_dir = $2;
         print "action: dump $scope to $output_dir\n";
         if ( $scope eq 'all' ) {
            TPSUP::SELENIUM::dump( $driver, $output_dir, undef, $opt );
         } else {
            if ( !$element ) {
               print
"dump_element is called but element is undef. dump all instead\n";
            }
            TPSUP::SELENIUM::dump( $driver, $output_dir, $element, $opt );
         }
      } elsif ( $step =~ /^\s*gone_(xpath|css)=(.+)/s ) {

         # gone_xpath=//div[text()="Invalid reference"]
         my $type   = $1;
         my $string = $2;

         my $path = $string;

         # allowing space chars and ending comma to make the coding easier
         $string =~ s/[\s,]+$//;    # trim ending space and comma

         my @paths;
         my $element_exist;

         while ( $string =~ /\G(.+?)\s*,\s*gone_(xpath|css)=/gcs ) {
            $path = $1;
            my $type2 = $2;

            print "$1, $2\n";

            push @paths, [ $type, $path ];

            $type = $type2;    # $type is used for the next round
         }

         my ($leftover) = ( $string =~ /\G(.*)/s );

         push @paths, [ $type, $leftover ];

         my $interval =
           defined $opt->{gone_interval} ? $opt->{gone_interval} : 60;

         print "action: wait max $interval seconds for elements gone, paths = ",
           Dumper( \@paths );

         hit_enter_to_continue() if $interactive;

         if ( !$dryrun ) {
            my $e;

            my $i = 0;
          GONE_LOOP:
            while ( $i < $interval ) {
               $i++;
               sleep 1;

               $e = undef;

               for my $row (@paths) {
                  my ( $type, $path ) = @$row;
                  my $key = "$type=$path";

                  if ( $type =~ /xpath/ ) {
                     eval {
                        local $SIG{__WARN__} = sub { };
                        $e = $driver->find_element_by_xpath($path);
                     };
                  } else {
                     eval {
                        local $SIG{__WARN__} = sub { };
                        $e = $driver->find_element_by_css($path);
                     };
                  }

                  if ($e) {
                     next GONE_LOOP;
                  }
               }

               if ( !$e ) {
                  if ( $i > 1 ) {
                     print "total wait time is $i seconds\n";
                  }
                  last GONE_LOOP;
               }
            }

            if ($e) {
               js_print_debug( $driver, $e );
               croak
"at least one of the element still exists after $interval seconds";
            }
         }
      } else {
         croak "unsupported step=" . Dumper($step);
      }
   }
}

sub locator_chain_to_js_list {
   my ( $locator_chain, $opt ) = @_;
   my $js_list = [];

   my $trap = $opt->{trap};

   my $js = 'var e = document';
   for my $locator (@$locator_chain) {
      if ( $locator =~ /^(xpath|css)=(.+)/ ) {
         my ( $ptype, $path ) = ( $1, $2 );
         if ( $ptype eq 'xpath' ) {
            $js .=
".evaluate(\"$path\", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue";
         } else {    # ($ptype eq 'css') {
            $js .= ".querySelector(\"$path\")";
         }
      } elsif ( $locator eq 'shadow' ) {
         $js .= ".shadowRoot";
      } elsif ( $locator eq 'iframe' ) {
         $js .= <<'END';

try {

    let iframe_inner = e.contentDocument || e.contentWindow.document;

    document = iframe_inner

    const current_origin = window.location.origin;

    console.log(`iframe stays in the same origin ${current_origin}`); // note to use backticks

} catch(err) {

    let iframe_src = e.getAttribute('src');

    //iframe_url = new URL(iframe_src);

    iframe_url = iframe_src;

    console.log(`iframe needs new url ${iframe_url}`);  // note to use backticks

    window.location.replace(iframe_url);

}
END

         # save one js after every iframe
         if ($trap) {
            $js = wrap_js_in_trap($js);
         }
         push @{$js_list}, $js;

         # start a new js
         #    var vs let vs const
         #    var is global, can be re-defined
         #    let and const are better, block-scopeed, cannot be re-defined
         $js = 'var e = document';
      } else {
         croak "unsupported locator=$locator";
      }
   }

   # save the last js.
   #  - only the last js 'return e'
   #   - the intermediate js were all ending with iframes
   $js .= ";\nreturn e";

   if ($trap) {
      $js .= wrap_js_in_trap($js);
   }
   push @$js_list, $js;

   return $js_list;
}

sub wrap_js_in_trap {
   my ( $js, $opt ) = @_;
   my $js2 = <<"END";
try {
//don't indent $js which could change change js.
$js
} catch(err) {
   console.log(err.stack);
   return;
}
END
   return $js2;
}

sub js_list_to_locator_chain {
   my ( $js_list, $opt ) = @_;

   my $locator_chain = [];
   for my $js (@$js_list) {
      push @$locator_chain, "js=$js";
   }

   return $locator_chain;
}

sub dump {
   my ( $driver, $output_dir, $element, $opt ) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   my $source_file = "$output_dir/source.html";
   my $ofh         = get_out_fh($source_file);
   print {$ofh} tp_get_outerHTML( $driver, $element, $opt );
   close_out_fh($ofh);

   my $iframe_list;
   if ( !$element ) {

      # this is dump_all()
      $iframe_list = $driver->find_elements( '//iframe', 'xpath' );
   } else {
      $iframe_list =
        tp_find_elements_from_element( $driver, $element, '//iframe', 'xpath' );

      #tp_find_elements_from_element($driver, $element, 'iframe', 'css');
   }

   my $dump_state = {
      output_dir    => $output_dir,
      type_chain    => [],            # iframe, shadow
      typekey_chain => [],            # iframe001, shadow001
      locator_chain => [],            # 'xpath=/a/b', 'shadow', 'css=div'
      xpath_chain   => [],            # /a/b, shadow, //div'
      scan_count    => {
         iframe => 0,
         shadow => 0,
      },
      exist_count => {
         iframe => 0,
         shadow => 0,
      },
      max_depth_so_far => 0,
   };

   for my $format (qw(list map)) {
      for my $scheme (qw(locator_chain xpath_chain xpath)) {
         my $f = "$output_dir/${scheme}_${format}.txt";
         $dump_state->{$format}->{$scheme} = get_out_fh($f);
      }
   }

   for my $iframe (@$iframe_list) {
      dump_deeper( $driver, $iframe, $dump_state, 'iframe', $opt );
   }

# get all shadow doms
#
# https://developer.mozilla.org/en-US/docs/Web/Web_Components/Using_shadow_DOM
#   There are some bits of shadow DOM terminology to be aware of:
#     Shadow host: The regular DOM node that the shadow DOM is attached to.
#     Shadow tree: The DOM tree inside the shadow DOM.
#     Shadow boundary: the place where the shadow DOM ends, and the regular DOM begins.
#     Shadow root: The root node of the shadow tree.

   my $start_node;
   my $find_path;

   if ( !$element ) {
      $start_node = $driver;
      $find_path  = '//*';
   } else {
      $start_node = $element;
      $find_path  = './/*';

      # this element can also be a shadow host
      dump_deeper( $driver, $element, $dump_state, 'shadow', $opt );
   }

   my $elements =
     tp_find_elements_from_element( $driver, $start_node, $find_path, 'xpath' );

   for my $e (@$elements) {
      dump_deeper( $driver, $e, $dump_state, 'shadow', $opt );
   }

   for my $format (qw(list map)) {
      for my $scheme (qw(xpath xpath_chain locator_chain)) {
         close_out_fh( $dump_state->{$format}->{$scheme} );
      }
   }

   # summary and final stats
   print "final dump_state = ", Dumper($dump_state);
   my $iframe_scan_count = $dump_state->{scan_count}->{iframe};
   my $shadow_scan_count = $dump_state->{scan_count}->{shadow};
   my $total_scan_count  = $iframe_scan_count + $shadow_scan_count;
   my $scan_depth        = scalar( @{ $dump_state->{type_chain} } );
   my $max_depth_so_far  = $dump_state->{max_depth_so_far};
   print "total scanned $total_scan_count, for iframe $iframe_scan_count, ",
     "for shadow $shadow_scan_count, iframe can be scanned by locator, ",
     "therefore, less count\n";
   print
"current depth=$scan_depth, max_depth_so_far so far=$max_depth_so_far, max_exist_depth is 1 less\n";

   # we put the chain check at last so that we won't miss the summary
   croak "dump_state type_chain is not empty" if $scan_depth;
}

sub dump_deeper {
   my ( $driver, $element, $dump_state, $type, $opt ) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   $dump_state->{scan_count}->{$type} += 1;
   my $iframe_scan_count = $dump_state->{scan_count}->{iframe};
   my $shadow_scan_count = $dump_state->{scan_count}->{shadow};
   my $total_scan_count  = $iframe_scan_count + $shadow_scan_count;
   my $scan_depth        = scalar( @{ $dump_state->{type_chain} } );
   if ( $scan_depth > $dump_state->{max_depth_so_far} ) {
      $dump_state->{max_depth_so_far} = $scan_depth;
   }
   my $max_depth_so_far = $dump_state->{max_depth_so_far};

   my $limit_depth = defined( $opt->{limit_depth} ) ? $opt->{limit_depth} : 5;

   if (  ( ( $total_scan_count % 100 ) == 0 )
      || ( $scan_depth >= $limit_depth ) )
   {
      print
"total scanned $total_scan_count, for iframe $iframe_scan_count, for shadow $shadow_scan_count\n";
      print
"current depth=$scan_depth, max depth so far=$max_depth_so_far, max_exist_depth is 1 less\n";

      if ( $scan_depth >= $limit_depth ) {
         print
"current depth=$scan_depth >= limit_depth=$limit_depth, stop going deepper\n";
         return;
      }
   }

   my $shadow_driver;
   if ( $type eq 'shadow' ) {
      $shadow_driver = TPSUP::SELENIUM::SHADOWROOT->new(
         driver      => $driver,
         shadow_host => $element
      );
      if ( !$shadow_driver ) {
         if ($verbose) {
            my $xpath = js_get( $driver, $element, 'xpath' );
            print "no shadow root under xpath=$xpath\n";
         }
         return;
      }
   }

   print "dump_state = ", Dumper($dump_state);
   print "type = $type\n";

# selenium.common.exceptions.StaleElementReferenceException: Message: stale element reference:
#   element is not attached to the page document
   my $xpath;

   # https://perlmaven.com/fatal-errors-in-external-modules
   eval {    # perl try{...} except {...}
      $xpath = js_get( $driver, $element, 'xpath' );
   } or do {
      my $error = $@ || 'unknown error';
      print "error=$error\n";
      print "we skipped this $type\n";
      return;
   };        # don't forget this ';'

   my $shadowed = 0;
   if ( grep { $_ eq 'shadow' } @{ $dump_state->{type_chain} } ) {
      $shadowed = 1;
   }

   my $css;
   if ($shadowed) {
      eval {    # perl try{...} except {...}
         $css = js_get( $driver, $element, 'css' );
      } or do {
         my $error = $@ || 'unknown error';
         print "error=$error\n";
         print "we skipped this $type\n";
         return;
      };        # don't forget this ';'
   }

   my $output_dir = $dump_state->{output_dir};

   $dump_state->{exist_count}->{$type} += 1;
   my $i = $dump_state->{exist_count}->{$type};

   my $typekey = sprintf( '%s%03d', $type, $i );    # padding
   push @{ $dump_state->{type_chain} },    $type;
   push @{ $dump_state->{typekey_chain} }, $typekey;
   push @{ $dump_state->{xpath_chain} }, ( $xpath, $type );
   if ($shadowed) {
      push @{ $dump_state->{locator_chain} }, ( "css=$css", $type );
   } else {
      push @{ $dump_state->{locator_chain} }, ( "xpath=$xpath", $type );
   }

   my $output_file = "$output_dir/$typekey.html";

   my $typekey_chain = join( ".", @{ $dump_state->{typekey_chain} } );
   my $line          = "${typekey_chain}: $xpath\n";
   print $line;
   print { $dump_state->{map}->{xpath} } $line;
   print { $dump_state->{list}->{xpath} } "$xpath\n";

   my $xpath_chain = join( " ", @{ $dump_state->{xpath_chain} } );
   $line = "${typekey_chain}: $xpath_chain\n";
   print { $dump_state->{map}->{xpath_chain} } $line;
   print { $dump_state->{list}->{xpath_chain} } "$xpath_chain\n";

   my $locator_chain =
     "'" . join( "', '", @{ $dump_state->{locator_chain} } ) . "'";
   $line = "${typekey_chain}: $locator_chain\n";
   print { $dump_state->{map}->{locator_chain} } $line;
   print { $dump_state->{list}->{locator_chain} } "$locator_chain\n";

   if ( $type eq 'iframe' ) {
      $driver->switch_to_frame($element);
      my $ofh = get_out_fh($output_file);
      print {$ofh} tp_get_outerHTML($driver);
      close_out_fh($ofh);

      # find sub iframes in this frame
      my $iframe_list = $driver->find_elements( '//iframe', 'xpath' );
      for my $sub_frame (@$iframe_list) {
         dump_deeper( $driver, $sub_frame, $dump_state, 'iframe', $opt );
      }

      # find shadows in this frame
      for my $e ( @{ $driver->find_elements( "//*", 'xpath' ) } ) {
         dump_deeper( $driver, $e, $dump_state, 'shadow', $opt );
      }

      $driver->switch_to_frame();    # don't forget to switch back
   } else {

      # $type eq 'shadow'
      my $ofh = get_out_fh($output_file);

      for my $e ( @{ $shadow_driver->find_elements( ':host > *', 'css' ) } ) {
         print {$ofh} tp_get_outerHTML( $driver, $e );
         print {$ofh} "\n";
      }
      close_out_fh($ofh);

      # find sub iframes in this shadow
      my $iframe_list = $shadow_driver->find_elements( 'iframe', 'css' );

      for my $iframe (@$iframe_list) {
         dump_deeper( $driver, $iframe, $dump_state, 'iframe', $opt );
      }

      # find child shadows in this shadow, can only use CSS SELECTOR
      # https://stackoverflow.com/questions/42627939
      for my $e ( @{ $shadow_driver->find_elements( '*', 'css' ) } ) {
         dump_deeper( $driver, $e, $dump_state, 'shadow', $opt );
      }
   }

   my $poptype = pop @{ $dump_state->{type_chain} };
   my $popkey  = pop @{ $dump_state->{typekey_chain} };
   if ( $popkey ne $typekey ) {
      croak "popkey=$popkey is not the same expected typekey=$typekey";
   }

   my $pop_xpath_chain1   = pop @{ $dump_state->{xpath_chain} };
   my $pop_xpath_chain2   = pop @{ $dump_state->{xpath_chain} };
   my $pop_locator_chain1 = pop @{ $dump_state->{locator_chain} };
   my $pop_locator_chain2 = pop @{ $dump_state->{locator_chain} };
}

sub tp_get_url {
   my ( $driver, $url, $opt ) = @_;
   $driver->get($url);

   if ( $opt->{accept_alert} ) {
      sleep 1;

# https://stackoverflow.com/questions/14843724/selenium-perl-check-if-alert-exists
      eval { $driver->accept_alert; };
      if ($@) {
         warn "Maybe no alert?";
         warn $@;
      } else {
         print "accepted alert\n";
      }
   }
}

sub tp_get_outerHTML {
   my ( $driver, $element, $opt ) = @_;

   my $html;

   # https://stackoverflow.com/questions/35905517
   if ( !$element ) {
      print "getting whole html\n";
      $html =
        $driver->execute_script("return document.documentElement.outerHTML;");
   } else {
      $html =
        $driver->execute_script( "return arguments[0].outerHTML;", $element );
   }

   if ( !defined($html) ) {
      print "not outerHTML found\n";
   }

   return $html;
}

sub human_delay {
   my ($opt) = @_;
   my $max   = defined( $opt->{max_delay} ) ? $opt->{max_delay} : 3;
   my $min   = defined( $opt->{min_delay} ) ? $opt->{min_delay} : 1;

   # default to sleep, 1, 2, or 3 seconds
   croak "min=$min is less than 0, not acceptable. min must >= 0" if $min < 0;
   croak "max=$max is less than 0, not acceptable. max must >= 0" if $max < 0;
   croak "max ($max) < min ($min)" if $max < $min;
   if ( $max == $min ) {

      # not random any more
      print "like human: sleep seconds = $max\n";
      if ( $max > 0 ) {
         sleep $max;
      }
   } else {
      my $seconds = int( time . time() );

      # random_seconds = (seconds % max) + 1
      my $random_seconds = ( $seconds % ( $max + 1 - $min ) ) + $min;
      print "like human: sleep random_seconds = $random_seconds\n";
      if ( $random_seconds > 0 ) {
         sleep $random_seconds;
      }
   }
}

# moved this part to a separate file
#package TPSUP::SELENIUM::SHADOWROOT {   # perl oop
#   # we make the shadow_root look like a driver - this is what Python did.
#   # the main goal is to allow us to search in the shadow DOM.
#   #     find_element( $target, $scheme)
#   #     find_elements($target, $scheme)
#   # eg
#   #     find_element( "input",     "css")
#   #     find_elements(":host > *", "css")
#
#   use Data::Dumper;
#   use Carp;
#
#   sub new {
#      my ($class, %attrs) = @_;
#      my $shadow_root = $attrs{driver}->execute_script('return arguments[0].shadowRoot', $attrs{shadow_host});
#
#      return undef if ! $shadow_root;
#
#      # croak "this is not a shadow host" if ! $shadow_root;
#      #print "shadow_root = ", Dumper($shadow_root);
#
#      $attrs{shadow_root} = $shadow_root;
#
#      bless \%attrs, $class;
#   }
#   sub find_element {
#      my ($self, $target, $scheme) = @_;
#      die "scheme=$scheme is not supported. Only css is supported" if $scheme ne 'css';
#      return $self->{driver}->execute_script(
#                 "return arguments[0].querySelector(arguments[1])",
#                 $self->{shadow_root},
#                 $target
#             );
#   }
#   sub find_elements {
#      my ($self, $target, $scheme) = @_;
#      die "scheme=$scheme is not supported. Only css is supported" if $scheme ne 'css';
#      return $self->{driver}->execute_script(
#                "return arguments[0].querySelectorAll(arguments[1])",
#                $self->{shadow_root},
#                $target
#             );
#   }
#}

sub tp_find_from_element {
   my ( $driver, $element_number, $element, $target, $scheme, $opt ) = @_;

   croak "unsupported unsupport='$element_number'"
     if $element_number ne 'element' && $element_number ne 'elements';

   my $js;

   if ( $scheme eq 'css' ) {
      if ( $element_number eq 'elements' ) {
         $js = "return arguments[0].querySelectorAll(arguments[1])";
      } else {
         $js = "return arguments[0].querySelector(arguments[1])";
      }
   } elsif ( $scheme eq 'xpath' ) {
      if ( $element_number eq 'elements' ) {
         $js = <<'END';
            let results = [];
            let query = document.evaluate(arguments[1], arguments[0] || document,
               null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
      
            for (let i = 0, length = query.snapshotLength; i < length; ++i) {
               results.push(query.snapshotItem(i));
            }
      
            return results;
END
      } else {

         # how-to-use-document-evaluate-and-xpath-to-get-a-list-of-elements
         # https://stackoverflow.com/questions/36303869

         $js =
"return document.evaluate(arguments[1], document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue";
      }
   } else {
      croak "unsupported scheme='$scheme'";
   }

   my $result;
   eval { $result = $driver->execute_script( $js, $element, $target ); } or do {
      print "js=$js\n";
      croak "$@";
   };    # don't forget about this ;

   return $result;
}

sub tp_find_elements_from_element {
   my ( $driver, $element, $target, $scheme, $opt ) = @_;
   return tp_find_from_element( $driver, 'elements', $element, $target,
      $scheme, $opt );
}

sub tp_find_element_from_element {
   my ( $driver, $element, $target, $scheme, $opt ) = @_;
   return tp_find_from_element( $driver, 'element', $element, $target, $scheme,
      $opt );
}

my $js_by_key = {

   # java script. duplicate attributes will be overwritten
   attrs => <<'END',
      var items = {};
      for (index = 0; index < arguments[0].attributes.length; ++index) {
         items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value
      };
      return items;
END

   # https://stackoverflow.com/questions/2661818/javascript-get-xpath-of-a-node
   xpath => <<'END',
      if (typeof(createXPathFromElement) !== 'function') {
         window.createXPathFromElement = function (elm, xpath_style) { 
            var segs = [];
            let allNodes = document.getElementsByTagName('*'); 

            if (!xpath_style || xpath_style != 'full') {
               //if id is unique on document level, we return with id
               if (elm.hasAttribute('id')) {               
                  let documentUnique = 0; 
                  for (var n=0;n < allNodes.length;n++) { 
                     if (allNodes[n].hasAttribute('id') && allNodes[n].id == elm.id) {
                        documentUnique++;
                     }
                     if (documentUnique > 1) break; 
                  }; 
                  if ( documentUnique == 1) { 
                     segs.unshift(`id("${elm.id}")`);  // backtick for interpolation
                     return segs.join('/'); 
                  } 
               }
   
               // do the same with class
               // note the attribute name is inconsitent
               //   element.hasAttribute('class')
               //   element.className
               if (elm.hasAttribute('class')) {               
                  let documentUnique = 0; 
                  for (var n=0;n < allNodes.length;n++) { 
                     if (allNodes[n].hasAttribute('class') && allNodes[n].className == elm.className) {
                        documentUnique++;
                     }
                     if (documentUnique > 1) break; 
                  }; 
   
                  if ( documentUnique == 1) { 
                     segs.unshift(`class("${elm.className}")`); 
                     return segs.join('/'); 
                  } 
               }
            }

            // now that neither id nor class is unique on document level
            for (; elm && elm.nodeType == 1; elm = elm.parentNode) 
            {    
               // if id/class is unique among siblings, we use it to identify on sibling level
               if (elm.parentNode) {                 
                  // childNodes vs children
                  //    childNodes include both elements and non-elements, eg, text
                  //    children include only elements.
                  // let siblings= elm.parentNode.childNodes;
                  let siblings= elm.parentNode.children;

                  var siblingUnique = 0
                  for (var i= 0; i<siblings.length; i++) {
                     if (siblings[i].hasAttribute('id') && siblings[i].id == elm.id) {
                        siblingUnique++;

                     }

                     if (siblingUnique > 1) break; 
                  }; 
                  if (siblingUnique == 1) { 
                     // https://developer.mozilla.org/en-US/docs/Web/API/Element/localNam
                     //   <ecomm:partners> ....
                     // in the qualified name ecomm:partners, 
                     //   partners is the local name 
                     //   ecomm is the prefix
                     segs.unshift(`${elm.localName.toLowerCase()}[@id="${elm.id}"]`);  
                     continue;
                  } 

                  // check class
                  var siblingUnique = 0
                  for (var i= 0; i<siblings.length; i++) {
                     if (siblings[i].hasAttribute('class') && siblings[i].className == elm.className) {
                        siblingUnique++;
                     }
                     if (siblingUnique > 1) break; 
                  }; 

                  if (siblingUnique == 1) { 
                     segs.unshift(`${elm.localName.toLowerCase()}[@class="${elm.className}"]`);  
                     continue;
                  } 
               }

               // As neither id/class is unique on sibling level, we have to use position
               let j = 1;
               for (sib = elm.previousSibling; sib; sib = sib.previousSibling) { 
                  if (sib.localName == elm.localName)  j++; 
               }
               segs.unshift(`${elm.localName.toLowerCase()}[${j}]`);               
            }            

            return segs.length ? '/' + segs.join('/') : null; 
         };
      }     

      return createXPathFromElement(arguments[0], arguments[1]);   
END

# https://stackoverflow.com/questions/4588119/get-elements-css-selector-when-it-doesnt-have-an-id
   css => <<'END',
      if (typeof(getCssFullPath) !== 'function') {
         window.getCssFullPath = function (el) { 
            var names = [];
            while (el.parentNode){
              if (el.id){
                names.unshift('#'+el.id);
                break;
              }else{
                if (el==el.ownerDocument.documentElement) names.unshift(el.tagName);
                else{
                  for (var c=1,e=el;e.previousElementSibling;e=e.previousElementSibling,c++);
                  names.unshift(el.tagName+":nth-child("+c+")");
                }
                el=el.parentNode;
              }
            }
            return names.join(" > ");
         };
      }
      return getCssFullPath(arguments[0]);
END
};

sub js_get {
   my ( $driver, $element, $key, $opt ) = @_;

   if ( !$driver ) {
      print "driver is not defined\n";
      return undef;
   }

   if ( !$element ) {
      print "element is not defined\n";
      return undef;
   }

   my $js = $js_by_key->{$key};

   croak "key='$key' is not supported" if !defined $js;

   my @extra_args = ();

   if ( $key eq 'xpath' ) {
      if ( $opt->{full} ) {

         # print full xpath
         push @extra_args, 'full';
      }
   }

   return $driver->execute_script( $js, $element, @extra_args );
}

sub js_print {
   my ( $driver, $element, $key, $opt ) = @_;

   print "$key = ", Dumper( js_get( $driver, $element, $key, $opt ) );
}

# https://stackoverflow.com/questions/10911526/how-do-i-programatically-select-an-html-option-using-javascript

sub select_option {
   my ( $driver, $element, $attr, $value, $opt ) = @_;

   my $js;
   if ( $attr eq 'text' ) {
      $js = << 'END';
         if (typeof(setSelectBoxByText) !== 'function') {
             window.setSelectBoxByText = function (el, etxt) {
                for (var i = 0; i < el.options.length; ++i) {
                    if (el.options[i].text === etxt) {
                        // backticks in javascript is for string interpolation
                        console.log(`found '${etxt}' at index ${i}`);
                        el.options[i].selected = true;
                    }
                }
             };
         }      
         return setSelectBoxByText(arguments[0], arguments[1]);
END
   } elsif ( $attr eq 'value' ) {
      $js = << 'END';
         if (typeof(setSelectBoxByValue) !== 'function') {
             window.setSelectBoxByValue = function (el, evalue) {
                 el.value = evalue;
             };
         }
      
         return setSelectBoxByValue(arguments[0], arguments[1]);
END
   } elsif ( $attr eq 'index' ) {
      $js = << 'END';
         if (typeof(setSelectBoxByIndex) !== 'function') {
             window.setSelectBoxByIndex = function (el, eindx) {
                 el.getElementsByTagName('option')[eindx].selected = 'selected';
                 //or el.options[eindx].selected = 'selected';
             }; 
         }
         return setSelectBoxByIndex(arguments[0], arguments[1]);
END
   } else {
      croak "unsupport select attr='$attr'";
   }

   return $driver->execute_script( $js, $element, $value );
}

sub get_detail {
   my ( $element, $opt ) = @_;

   # innerHTML vs outerHTML
   # <p id="pid">welcome</p>
   # innerHTML of element "pid" == welcome
   # outerHTML of element "pid" == <p id="pid">welcome</p>

# perl selenimu doesn't support $element->get_attribute('innerHTML' or 'outerHTML');
# therefore, we use this sub to get the basic idea of the the element.

   my @attributes = qw( id name class href value );

   my $ret;

   for my $attr (@attributes) {
      my $v = $element->get_attribute($attr);

      next if !defined $v;

      $ret->{$attr} = $v;
   }

   my $text = $element->get_text();
   $ret->{text} = $text if defined $text;

   return $ret;
}

sub print_detail {
   my ( $element, $opt ) = @_;

   print "detail = ", Dumper( get_detail( $element, $opt ) );
}

sub main {
   print "------------ test get_driver() ----------------------------\n";
   my $driver_cfg = { startup_timeout => 10 };

   my $opt = {
      host_port => "auto",

      #host_port=>"localhost:9333",
      #host_port=>"192.168.1.179:9333",

      driver_cfg => $driver_cfg,

      #interactive=>1,
   };

   my $driver = get_driver($opt);

   #print "driver = ", Dumper($driver);

   my $actions = [
      ['url=https://www.google.com/'],

      [
         'xpath=//input[@name="q"]',
         [
            'clear_attr=value',
            'string=perl selenium',
            'code=js_print($driver, $element, "attrs")',
            'code=js_print($driver, $element, "xpath")',
            'code=js_print($driver, $element, "css")',
         ],
         'type query',
      ],

      # note: the xpath between www.google.com and google.com are different

      [ '', [ 'key=enter,1', 'code=sleep 3' ], 'click enter' ],
   ];

   run_actions( $driver, $actions, $opt );

   $driver->shutdown_binary;
}

main() unless caller();

1
