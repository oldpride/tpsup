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
use TPSUP::Expression;


sub get_fixed_records {
   my ($input, $record_size, $opt) = @_;

   my $template = $opt->{Template} ? $opt->{Template} : undef;

   my $ref;

   if ($opt->{FixedRecordInputType} && $opt->{FixedRecordInputType} eq 'string') {
      # https://perldoc.perl.org/functions/pack
      $ref = \$input;
   } else {
      my $ifh = get_in_fh($input, $opt);
   
      my $chunk_size = 1024*$record_size;
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

   my $records2;

   if ($opt->{FixedRecordExcludePatterns} || $opt->{FixedRecordMatchPatterns}) {
      my @exclude_qrs;
      if ($opt->{FixedRecordExcludePatterns} && @{$opt->{FixedRecordExcludePatterns}}) {
         for my $p (@{$opt->{FixedRecordExcludePatterns}}) {
            push @exclude_qrs, qr/$p/;
         }
      }
   
      my @match_qrs;
      if ($opt->{FixedRecordMatchPatterns} && @{$opt->{FixedRecordMatchPatterns}}) {
         for my $p (@{$opt->{FixedRecordMatchPatterns}}) {
            push @match_qrs, qr/$p/;
         }
      }
   
      RECORD:
      for my $r (@records) {
         my $should_exclude = 0;

         for my $qr (@exclude_qrs) {
            # this is for empty @exclude_qrs, which means no exclude.
            $should_exclude = 1;

            # remember this is AND logic; therefore, one fails means all fail
            if ($r !~ /$qr/) {
               $should_exclude = 0;
               last;
            }
         }

         next if $should_exclude;

         for my $qr (@match_qrs) {
            if ($r !~ /$qr/) {
               # remember this is AND logic; therefore, one fails means all fail.
               next RECORD;
            }
         }

         push @$records2, $r;
      }
   } else {
     $records2 = \@records;
   }

   if (!$template) {
      return $records2;
   } else {
      # fields are in array @f
      # expression example: 
      #   $f[1] eq 'Smith'

      my $matchExps;
      if ($opt->{FixedRecordMatchExps} && @{$opt->{FixedRecordMatchExps}}) {
         @$matchExps = map { TPSUP::Expression::compile_exp($_, $opt) } @{$opt->{FixedRecordMatchExps}};
      }

      my $excludeExps;
      if ($opt->{FixedRecordExcludeExps} && @{$opt->{FixedRecordExcludeExps}}) {
         @$excludeExps = map { TPSUP::Expression::compile_exp($_, $opt) } @{$opt->{FixedRecordExcludeExps}};
      }

      my @unpacked;
      for my $record (@$records2) {
         my @fields = unpack($template, $record);

         if ($matchExps || $excludeExps) {
            # this disables the warning:
            #    Name "TPSUP::Expression::f" used only once: possible typo.
            no warnings 'once';

            @TPSUP::Expression::f = @fields;

            my $exclude_from_doing;
   
            if ($excludeExps) {
               for my $e (@$excludeExps) {
                  if ($e->()) {
                     $exclude_from_doing ++;
                     last;
                  }
               }
            }
   
            if ($exclude_from_doing) {
               next;
            }
   
            {
               for my $e (@$matchExps) {
                  if (! $e->()) {
                     $exclude_from_doing ++;
                     last;
                  }
               }
            }
   
            if ($exclude_from_doing) {
               next;
            }
         }

         push @unpacked, \@fields;
      }
      return \@unpacked;
   }
}


sub main {
   my $string = "Joan        Smith       33  135 25 Elms Street    Joe         Spinsak     46  195 6 5th Ave         Stephen     Kierbarsky  9   60  125 Main Street   ";

   print "\n---------- test split -----------------\n";
   my $records = get_fixed_records($string, 50, {FixedRecordInputType=>'string'});

   for my $record (@$records) {
      print $record, "\n";
   }

   print "\n---------- test unpack -----------------\n";
   $records = get_fixed_records($string, 50, {FixedRecordInputType=>'string', 
                                              Template=>"A12 A12 A4 A4 A18"
                                             });

   for my $record (@$records) {
      print join(',', @$record), "\n";
   }

   print "\n---------- test MatchPatterns -----------------\n";
   $records = get_fixed_records($string, 50, {FixedRecordInputType=>'string', 
                                              Template=>"A12 A12 A4 A4 A18",
                                              FixedRecordMatchPatterns=>['5th',],
                                             });

   for my $record (@$records) {
      print join(',', @$record), "\n";
   }

   print "\n---------- test MatchExps -----------------\n";
   $records = get_fixed_records($string, 50, {FixedRecordInputType=>'string', 
                                              Template=>"A12 A12 A4 A4 A18",
                                              FixedRecordMatchExps=>['$f[1] eq "Spinsak"',],
                                             });

   for my $record (@$records) {
      print join(',', @$record), "\n";
   }
}

main() unless caller();


1
