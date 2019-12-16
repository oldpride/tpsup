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
      
1
      
