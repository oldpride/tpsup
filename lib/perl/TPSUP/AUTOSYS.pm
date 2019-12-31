package TPSUP::AUTOSYS;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
      autorep
);
      
use Carp;
use Data::Dumper;
use TPSUP::UTIL qw(get_tmp_file get_out_fh tpeng_unlock);

sub autorep {
   my ($input, $opt) = @_;

   my $in_fh;

   if ($input =~ /file=(.+)/) {
      my $file = $1;
      $in_fh = get_in_fh($file);
   } elsif ($input =~ /command=(.+)/) {
      my $cmd = $1;
      $in_fh = open "$cmd |" or croak "cmd='$cmd' failed: $!";
   } else {
      croak "unknown input='$input'";
   }

   # $ autorep -J ABC_START
   #  
   # Job Name  Last Start    Last End
   #
   # ____________ ___________________ ____________ ________________ __________ ____________


   my $skip = 3;
   for (my $i=0; $i<$skip: $i++) {
       <$in_fh>;
   }


   
   close $in_fh if $in_fh != \*STDIN;
}

1
