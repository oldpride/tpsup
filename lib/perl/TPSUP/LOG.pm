package TPSUP::LOG;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   parse_PatternFile
   get_PatternCfg_by_app
   get_PatternCfg
   itemize_log
);

use Carp;
use Data::Dumper;
#use XML::Simple;
use TPSUP::CSV  qw(query_csv2);
use TPSUP::UTIL qw(get_in_fh);

my $PatternCfg_by_file_app;
                  
my $current_patternFile; # a workaround to keep track of which patternFile used. need refactoring

sub parse_PatternFile {
   my ($opt) = @_;
      
   my $file;
      
   if ($opt->{PatternFile}) {
      $file = $opt->{PatternFile};
   } elsif ($ENV{TPSUP}) {
      $file = "$ENV{TPSUP}/scripts/log_pattern.csv";
   } else {
      croak "Don't know where to find Pattern File. Noramlly \$TPSUP/scripts/log_pattern.csv";
   }
      
   croak "$file is not found" if ! -f $file;
      
   $current_patternFile = $file;

   return if exists $PatternCfg_by_file_app->{$file};
      
   my $result = query_csv2($file, { ReturnType =>'StringKeyedHash=App',
                                    QuotedInput     => 1,
                                    NoPrint         => 1,
                                    # skip comments and blank lines
                                    MatchPatterns   => ['^[ ]*[^#]'],
                                    %$opt
                                  });

   $PatternCfg_by_file_app->{$file} = $result->{KeyedHash};

   return $PatternCfg_by_file_app->{$file};
}
      
sub get_PatternCfg_by_app {
   my ($app, $opt) = @_;
      
   my $PatternCfg_by_app = parse_PatternFile($opt);

   return $PatternCfg_by_app->{$app}->[0];
}
      
sub get_PatternCfg {
   my ($opt) = @_;
      
   my $cfg;
      
   if ($opt->{App}) {
      $cfg = get_PatternCfg_by_app($opt->{App}, $opt);
      croak "missing setting for App='$opt->{App}' in $current_patternFile" if ! $cfg;
   }
      
   if ($opt->{TimePattern}) {
      $cfg->{TimePattern} = $opt->{TimePattern};
   }
      
   if ($opt->{TimeKey}) {
      $cfg->{TimeKey} = $opt->{TimeKey};
   }
      
   if ($opt->{Assignment}) {
      $cfg->{Assignment} = $opt->{Assignment};
   }
      
   if ($opt->{CheckSettings} && @{$opt->{CheckSettings}}) {
      for my $k (@{$opt->{CheckSettings}}) {
         croak "missing $k setting in $current_patternFile" if ! defined($cfg->{$k});
         $opt->{verbose} && print STDERR "$k = '$cfg->{$k}'\n";
      }
   }
      
   return $cfg;
}

# a perl iterator/generator 
# https://stackoverflow.com/questions/3775413/what-is-the-perl-version-of-a-python-iterator
# use bigint;
# sub fibonacci {
#     my $limit = 10**( shift || 0 );
#     my ( $a, $b ) = ( 0, 1 );
#     return sub {
#         return if $a > $limit;
#         ( my $r, $a, $b ) = ( $a, $b, $a + $b );
#         return $r;
#     };
# }
# 
# my $fit = fibonacci( 15 );
# 
# my $n = 0;
# while ( defined( my $f = $fit->())) {
#      print "F($n): $f\n";
#      $n++;
# }

sub itemize_log {
   my ($input, $item_start_pattern, $opt) = @_;

   my $start_pattern = qr/$item_start_pattern/;

   my $match_pattern;
   if ($opt->{MatchPattern}) {
      $match_pattern = qr/$opt->{MatchPattern}/;
   }

   my $exclude_pattern;
   if ($opt->{ExcludePattern}) {
      $exclude_pattern = qr/$opt->{ExcludePattern}/;
   }

   my $maxlen     = $opt->{MaxLen}     ? $opt->{MaxLen}     : 64000;
   my $maxcount   = $opt->{MaxCount};
   my $warnMaxlen = $opt->{warnMaxlen} ? $opt->{WarnMaxlen} : 0;

   my $ifh = get_in_fh($input, $opt);
   return undef if !$ifh;

   my $line;
   my $item_count = 0;

   return sub {
      my $item;

      # item will be undefined before 1st item
      if (defined $line) {
         $item = $line;
      }

      while ( defined($line = <$ifh>) ) {
         last if $maxcount && $item_count >= $maxcount;
         
         if ($line =~ /$start_pattern/) {
            # this is a starting line. if we already have an $item, we return the 
            # $item, unless this is the first line.

            if (defined $item) {
               # this is not the first line

               if ( (  $match_pattern && $item !~   /$match_pattern/) || 
                    ($exclude_pattern && $item =~ /$exclude_pattern/) ){
                  # throw away the current complete item.
                  $item = $line;
                  next;
               }

               $item_count ++;
               return $item; 
            }
         } 
         
         # this is not a starting line
         $item .= $line;
         my $length = length($item);

         if ($length > $maxlen) {
            if ($warnMaxlen) {
               carp "item size ($length) over limit ($maxlen); returned this much.";
            }

            # undef $line before skipping or returning the item
            # this will undef $item in the next call also
            undef $line;

            if ( (  $match_pattern && $item !~   /$match_pattern/) || 
               ($exclude_pattern && $item =~ /$exclude_pattern/) ){
               # throw away the current complete item.
               next;
            }

            $item_count ++;
            return $item;
         }
      }
      
      close($ifh) if $ifh != \*STDIN;

      if (!$maxcount || $item_count < $maxcount) {
            if (defined $item) {
               # this is not the first line

               if ( (  $match_pattern && $item !~   /$match_pattern/) || 
                    ($exclude_pattern && $item =~ /$exclude_pattern/) ){
                  # throw away the current complete item.
                  $item = $line;
                  next;
               }
               return $item; 
            }
      }

      return undef;    # returning undef to signal the end of iterator/generator
   }   
}
      
1
      
