package TPSUP::SELENIUM::SHADOWROOT;

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

   if (!$shadow_root) {
      print STDERR "this is not a shadow host\n" if exists $attrs{verbose} && $attrs{verbose};
      return undef;
   }

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

1
