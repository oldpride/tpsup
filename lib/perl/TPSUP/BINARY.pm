package TPSUP::BINARY;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   get_fixed_records
);

use warnings;
use Data::Dumper;
use Carp;
use TPSUP::UTIL qw(get_in_fh);


sub get_fixed_records {
   my ($input, $record_size, $opt) = @_;

   my $template = $opt->{Template} ? $opt->{Template} : undef;

   my $ref;

   if ($opt->{FixedRecordInputType} && $opt->{FixedRecordInputType} eq 'string') {
      # https://perldoc.perl.org/functions/pack
      $ref = \$input;
   } else {
      my $ifh = get_in_fh($input, $opt);
   
      my $chunk_size = 2*1024*1024;
      my $string;
      my $record;

      until ( eof($ifh) ) {
         my $actual_size = read($ifh, $record, $chunk_size);

         last if !$actual_size;

         $string .= $record;
      }
      $ref = \$string;
   }

   # both of the following ways work to split a string
   # https://stackoverflow.com/questions/8265653/split-a-string-into-equal-length-chunk-in-perl
   #
   # 1. use regex
       my $split_pattern = qr/.{$record_size}/;
       my @records = ($$ref =~ /$split_pattern/g);
   #
   # 2. use unpack 
   #    a  A string with arbitrary binary data, will be null padded.
   #    my @records = unpack("(a$record_size)*", $$ref);

   if (!$template) {
      return \@records;
   } else {
      my @unpacked;
      for my $record (@records) {
         my @fields = unpack($template, $record);
         push @unpacked, \@fields;
      }
      return \@unpacked;
   }
}

sub main {
   my $string = "Joan        Smith       33  135 25 Elms Street    Joe         Spinsak     46  195 6 5th Ave         Stephen     Kierbarsky  9   60  125 Main Street   ";

   my $records = get_fixed_records($string, 50, {FixedRecordInputType=>'string'});

   for my $record (@$records) {
      print $record, "\n";
   }

   $records = get_fixed_records($string, 50, {FixedRecordInputType=>'string', 
                                              Template=>"A12 A12 A4 A4 A18"
                                             });

   for my $record (@$records) {
      print join(',', @$record), "\n";
   }
}

main() unless caller();


1
