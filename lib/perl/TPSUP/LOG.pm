package TPSUP::LOG;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   parse_PatternFile
   get_PatternCfg_by_app
   get_PatternCfg
   itemize_log
   find_log_pattern_info
   parse_log_line
);

use Carp;
use Data::Dumper;
#use XML::Simple;
use TPSUP::CSV  qw(query_csv2);
use TPSUP::UTIL qw(get_in_fh close_in_fh);

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
      $match_pattern = qr/$opt->{MatchPattern}/s;  # 's' for multiline regex
   }

   my $exclude_pattern;
   if ($opt->{ExcludePattern}) {
      $exclude_pattern = qr/$opt->{ExcludePattern}/s;  # 's' for multiline regex
   }

   my $maxlen     = $opt->{MaxLen}     ? $opt->{MaxLen}     : 64000;
   my $maxcount   = $opt->{MaxCount};
   my $warnMaxlen = $opt->{warnMaxlen} ? $opt->{WarnMaxlen} : 0;

   my $ifh = get_in_fh($input, $opt);
   return undef if !$ifh;

   my $line;
   my $started;
   my $item_count = 0;

   return sub {
      my $item;

      # item will be undefined before 1st item
      if (defined($line) && $started) {
         $item = $line;
      }

      while ( defined($line = <$ifh>) ) {
         last if $maxcount && $item_count >= $maxcount;
         
         if ($line =~ /$start_pattern/) {
            # this is a starting line. if we already have an $item, we return the 
            # $item, unless this is the first line.

            $started = 1;

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
         
         next if ! $started;

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
            $started = undef;

            if ( (  $match_pattern && $item !~   /$match_pattern/) || 
               ($exclude_pattern && $item =~ /$exclude_pattern/) ){
               # throw away the current complete item.
               $item = undef;
               next;
            } else {
               $item_count ++;
               return $item;
            }
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



my ($sec, $min, $hour, $day, $mon, $year) = localtime();

############################ BEGIN no strict ########################################
# http://www.softpanorama.org/Scripting/Perlorama/perl_namespaces.shtml

# "eval '...' statements, as well as regular expressions with deferred evaluation
# (like s///e operators or $(${ }) expressions), re-establish the namespace environment
# for the duration of the expression compilation."

#don't use 'my' for the following variables, 'my' will make them not accessible as
#$TPSUP::LOG::yyyy for example.
#my $yyyy = '2021';

# without 'my', $TPSUP::LOG::yyyy is a global variable, accessible anywhere
# with 'my',    $TPSUP::LOG::yyyy will not exist in the main (calling) script
# with the 'my' above commented out, we need the following 'no strict ..' to
# disable the compiler's complain.

# for example, to set a variable from another program
#    use TPSUP::LOG;
#    no warnings 'once';   # this prevents: Name ... used only once: possible typo.
#    $TPSUP::LOG::myvar = 1;
#    @TPSUP::LOG::myarray = (1,2);
#    $TPSUP::LOG::myhash = {};
#    $TPSUP::LOG::myhash{firstname} = 'jack';

no strict;

$SS   = sprintf("%02d", $sec);
$MM   = sprintf("%02d", $min);
$HH   = sprintf("%02d", $hour);
$dd   = sprintf("%02d", $day);
$mm   = sprintf("%02d", $mon+1);
$yyyy = sprintf("%d", $year+1900);

$yyyymmdd = "$yyyy$mm$dd";
$HHMMSS   = "$HH$MM$SS";

%mm_by_Mon = ( 
         'Jan' => '01',
         'Feb' => '02',
         'Mar' => '03',
         'Apr' => '04',
         'May' => '05',
         'Jun' => '06',
         'Jul' => '07',
         'Aug' => '08',
         'Sep' => '09',
         'Oct' => '10',
         'Nov' => '11',
         'Dec' => '12',

         'JAN' => '01',
         'FEB' => '02',
         'MAR' => '03',
         'APR' => '04',
         'MAY' => '05',
         'JUN' => '06',
         'JUL' => '07',
         'AUG' => '08',
         'SEP' => '09',
         'OCT' => '10',
         'NOV' => '11',
         'DEC' => '12',

         'January'   => '01',
         'February'  => '02',
         'March'     => '03',
         'April'     => '04',
         'May'       => '05',
         'June'      => '06',
         'July'      => '07',
         'August'    => '08',
         'September' => '09',
         'October'   => '10',
         'November'  => '11',
         'December'  => '12',
);

use strict;

############################ END no strict ########################################

sub find_log_pattern_info {
   my ($log, $opt) = @_;

   my @configured_patterns = (
      # regex non-capturing group: (?:)?

      { 
          example => 'Tue Mar 23 00:30:04 EDT 2021: process started',
          pattern_src => "^(Mon|Tue|Wed|Thu|Fri|Sat|Sun) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) ([ 0-3][0-9]) ([0-5][0-9]):([0-5][0-9]):([0-5][0-9]) ([A-Z][A-Z][A-Z]) ([12][0-9][0-9][0-9])",
          yyyymmdd_src => '$6$mm_by_Mmm{$2}$3',
          HHMMSS   => '$4',
          yyyymmdd_src => 'sub { return sprintf("%s%s%s", $8, $TPSUP::LOG::mm_by_Mon{$2}, $3); }',
          HHMMSS_src   => 'sub { return sprintf("%s%s%s", $4, $5, $6); }',
      },

      { 
          example => 'Sep 18 09:26:35 testapp [9571]: testapp entered state=DONE',
          pattern_src => "^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) ([ 0-3][0-9]) ([0-5][0-9]):([0-5][0-9]):([0-5][0-9])",
          yyyymmdd_src => 'sub { return sprintf("%s%s%s", $TPSUP::LOG::yyyy, $TPSUP::LOG::mm_by_Mon{$1}, $2); }',
          HHMMSS_src   => 'sub { return sprintf("%s%s%s", $3, $4, $5); }',
      },

   );

   my @compiled;

   for my $cp (@configured_patterns) {
      my $compiled_pattern = qr/$cp->{pattern_src}/;
      $cp->{pattern} = $compiled_pattern;
      push @compiled, $compiled_pattern;
      
      $cp->{yyyymmdd} = eval "use TPSUP::LOG; $cp->{yyyymmdd_src}";
      $cp->{HHMMSS}   = eval $cp->{HHMMSS_src};
   }

   my $row_max = 100;
   my $row_count = 0;

   my $number_of_patterns = scalar(@configured_patterns);

   my @count_by_idx;

   my $ifh = get_in_fh($log);

   while (my $line = <$ifh>) {
      $row_count ++;

      for (my $idx=0; $idx<$number_of_patterns; $idx++ ) {
         if ( $line =~ /$compiled[$idx]/ ) {
            $count_by_idx[$idx] ++;
         }
      }

      last if $row_count >= $row_max;
   }

   close_in_fh($ifh);

   $opt->{verbose} && print "count_by_idx = ", Dumper(@count_by_idx), "\n";

   if ($row_count > 0)  {
      my $max_hits = 0;
      my $max_idx;

      for (my $idx=0; $idx<$number_of_patterns; $idx++ ) {
         if ($count_by_idx[$idx] && $count_by_idx[$idx] >$max_hits) {
            $max_hits = $count_by_idx[$idx];
            $max_idx  = $idx;
         }
      }
 
      if (defined $max_idx) {
         my $ref = $configured_patterns[$max_idx];
         $ref->{test_row_count} = $row_count;
         $ref->{test_hit_count} = $max_hits;
         return $ref;
      } else {
         return undef;
      }
   } else {
      return undef;
   }
}

sub parse_log_line {
   my ($line_ref, $cfg, $opt) = @_;

   my $ret;

   croak "missing cfg" if !$cfg || !$cfg->{pattern};

   my @matches = ($$line_ref =~ /$cfg->{pattern}/);
   if (@matches) {
      $ret->{yyyymmdd} = $cfg->{yyyymmdd}->();
      $ret->{HHMMSS}   = $cfg->{HHMMSS}->();

      if ($opt->{verbose}) {
         print "1ine=$$line_ref\n";
         print "\@matches = ", Dumper(\@matches), "\n";
         print "ret = ", Dumper($ret);
      }
   }
  
   return $ret;
}


sub main {
   print <<"EOF";
yyyy = $TPSUP::LOG::yyyy
mm   = $TPSUP::LOG::mm
dd   = $TPSUP::LOG::dd
HH   = $TPSUP::LOG::HH
MM   = $TPSUP::LOG::MM
SS   = $TPSUP::LOG::SS

yyyymmdd = $TPSUP::LOG::yyyymmdd
HHMMSS   = $TPSUP::LOG::HHMMSS

EOF
}

main() unless caller();
      
1
      
