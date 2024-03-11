package TPSUP::NAMESPACE;

use strict;
use warnings;
use Carp;
use Data::Dumper;
$Data::Dumper::Sortkeys = 1;    # this sorts the Dumper output!
$Data::Dumper::Terse    = 1;    # print without "$VAR1="

use base qw( Exporter );
our @EXPORT_OK = qw(
  get_EXPORT_OK
  import_EXPECT_OK
);

# "EXPORT" vs "EXPORT_OK":
#   "EXPORT" is for default export.
#   "EXPORT_OK" is on demand export.
# we are using "EXPORT_OK" in our modules for better control.
# TPSUP::TEST needs to get all the "EXPORT_OK" from a module.
# the following tricks only works for "EXPORT", not "EXPORT_OK"
#    use MY::PACKAGE qw(/./);
#    use MY::PACKAGE qw(:DEFAULT);
# Therefore, we have to
#    1. get the list of all "EXPORT_OK" from a module
#    2. use "use MY::PACKAGE qw(...)" for each of them.
# the following function does #1.
# learned from # https://stackoverflow.com/questions/65349217
sub get_EXPORT_OK {
   my ($module) = @_;

   my $class = $module;
   no warnings;

   # check if the package is already loaded
   my $already_loaded = 0;

   # When Perl sees that's not a reference, it instead uses
   # the package variable it works out from the string value.
   # 'strict' disallows this, so you have to turn off that
   # portion of its checks:

   {
      no strict 'refs';
      if ( %{ $class . '::' } ) {
         $already_loaded = 1;
      }
   }

   if ( !$already_loaded ) {
      eval "require $class";
   }

   my @exports = do {
      no strict 'refs';
      @{ $class . '::' . 'EXPORT_OK' };
   };

   return \@exports;
}

sub import_EXPECT_OK {
   my ( $module, $namespace, $opt ) = @_;
   my $verbose = $opt->{verbose};

   my $exports = get_EXPORT_OK($module);
   if ( !$exports ) {
      $verbose && print STDERR "no EXPORT_OK from $module\n";
      return 1;
   }
   my $exports_string = join( " ", @$exports );

   my $code = "package $namespace; use $module qw($exports_string);";
   print STDERR "eval code=$code\n" if $verbose;
   eval $code;
   if ($@) {
      croak "failed to import $exports_string from $module: $@";
   } else {
      return 1;
   }

}

1
