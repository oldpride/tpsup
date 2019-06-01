package TPSUP::LOG;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   parse_PatternFile
   get_PatternCfg_by_app
   get_PatternCfg
);

use Carp;
use Data::Dumper;
#use XML::Simple;
use TPSUP::CSV qw(query_csv2);

my $PatternCfg_by_file_app;
                  
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
      
   return if exists $PatternCfg_by_file_app->{$file};
      
   $PatternCfg_by_file_app->{$file} = query_csv2($file, { ReturnKeyedHash => ['App'],
                                                         QuotedInput     => 1,
                                                         NoPrint         => 1,
                                                         # skip comments and blank lines
                                                         MatchPatterns   => ['^[ ]*[^#]'],
                                                         %$opt
                                               });

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
         croak "missing $k setting" if ! defined($cfg->{$k});
         $opt->{verbose} && print STDERR "$k = '$cfg->{$k}'\n";
      }
   }
      
   return $cfg;
}
      
1
      
