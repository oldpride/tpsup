package TPSUP::LOG;

use strict;
use warnings;

use base qw( Exporter );
our @EXPORT_OK = qw(
   eval_exp_to_sub
   get_PatternCfg_by_app
   itemize_log
   parse_PatternCfg
   find_log_PatternCfg
   yyyymmddHHMMSS_to_log_time
   get_log_fh
   get_log_time
   get_log_time_by_yyyymmddHHMMSS
   get_log_latency
   get_log_section_gen
   get_log_section_headers
filter_log_section_gen
   get_log_sections
   get_logs
   get_logs_by_cfg
   get_logname_cfg
);

use Carp;
use Data::Dumper;
#use XML::Simple;
use TPSUP::CSV  qw(query_csv2);
use TPSUP::CFG  qw(parse_simple_cfg);
use TPSUP::DATE qw(
   yyyymmddHHMMSS_to_epoc
   epoc_to_yyyymmddHHMMSS
   get_seconds_between_two_days
);
use TPSUP::UTIL qw(
   get_in_fh 
   close_in_fh 
   add_line_number_to_code 
   get_user
   resolve_scalar_var_in_string
);

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

   my $ItemChars  = $opt->{ItemChars}   ? $opt->{ItemChars}   : 64000;
   my $ItemLines  = $opt->{ItemLines}   ? $opt->{ItemLines}   : 100;
   my $ItemWarn   = $opt->{ItemWarn}    ? $opt->{ItemWarn}    : 0;

   my $maxcount   = $opt->{MaxCount};

   my $ifh = get_in_fh($input, $opt);
   return undef if !$ifh;

   my $line;
   my $started;
   my $item_count = 0;

   return sub {
      my $item;
      my $line_count = 0;

      # item will be undefined before 1st item
      if (defined($line) && $started) {
         $item = $line;
      }

      while ( defined($line = <$ifh>) ) {
         last if defined($maxcount) && $item_count >= $maxcount;
         
         if ($line =~ /$start_pattern/) {
            # this is a starting line. if we already have an $item, we return the 
            # $item, unless this is the first line.

            $started = 1;
            $line_count = 1;

            if (defined $item) {
               # this is not the first line of file

               if ( (  $match_pattern && $item !~   /$match_pattern/) || 
                    ($exclude_pattern && $item =~ /$exclude_pattern/) ){
                  # throw away the current complete item.
                  $item = $line;
                  next;
               } else {
                  $item_count ++;
                  return $item; 
               }
            }
         } 
         
         next if ! $started;

         # this is not a starting line
         $item .= $line;
         $line_count ++;
         my $char_count = length($item);

         if ($char_count > $ItemChars || $line_count > $ItemLines) {
            if ($ItemWarn) {
               if ($char_count > $ItemChars) {
                  carp "item cut off here: char count ($char_count) > limit ($ItemChars).";
               } else {
                  carp "item cut off here: line count ($line_count) > limit ($ItemLines).";
               }
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
                  return undef;  # return undef to signal end of generator
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

my $PatternCfg_by_file;

sub parse_PatternCfg {
   my ($opt) = @_;
      
   my $file;
      
   if ($opt->{PatternFile}) {
      $file = $opt->{PatternFile};
   } elsif ($ENV{TPSUP}) {
      $file = "$ENV{TPSUP}/scripts/log_pattern.cfg";
   } else {
      croak "Don't know where to find Pattern File. Noramlly \$TPSUP/scripts/log_pattern.cfg. Please set \$TPSUP in env.";
   }
      
   if (!exists $PatternCfg_by_file->{$file}) {
      croak "$file is not found" if ! -f $file;

      $PatternCfg_by_file->{$file} = parse_simple_cfg($file, {CfgKey=>'name', %$opt});
   }

   return $PatternCfg_by_file->{$file};
}

      
sub get_PatternCfg_by_app {
   my ($name, $opt) = @_;

   my $cfg;

   if (!defined($name) || $name eq 'auto') {
      # 'auto' is a reserved word, meaning to auto-detect pattern
      my $LogFile = $opt->{LogFile};

      croak "missing attr=LogFile in get_PatternCfg_by_app" if ! defined $LogFile;
      $cfg = find_log_PatternCfg($LogFile, $opt);
   } else {
      my $PatternCfg_by_app = parse_PatternCfg($opt);
      $cfg = $PatternCfg_by_app->{$name};
   }

   return undef if !$cfg;

   $name = $cfg->{name};  # set the found name.

   # the following is to enrich the $cfg;

   my @requiredFields = qw(assignment sortkeys pattern);

   for my $f (@requiredFields) {
      if (!$cfg->{$f}) {
         carp "ERROR: name=$name missing field=$f in cfg\n";
         return undef;
      }
   }

   @{$cfg->{assignList}} = split /,/, $cfg->{assignment};

   if ($opt->{sortkeys}) {
      $cfg->{sortkeys} = $opt->{sortkeys};
   }

   @{$cfg->{sortkeyList}} = split /,/, $cfg->{sortkeys};

   for my $a (@{$cfg->{assignList}}) {
      $cfg->{assigned}->{$a} = 1;
   }

   for my $a (@{$cfg->{sortkeyList}}) {
      $cfg->{InSortKeyList}->{$a} = 1;
   }

   my $yyyymmdd;
   if ($opt->{yyyymmdd}) {
      $yyyymmdd = $opt->{yyyymmdd};
   } else {
      $yyyymmdd = $TPSUP::LOG::yyyymmdd;
   }

   my ($yyyy, $mm, $dd) = ($yyyymmdd =~ /^(\d{4})(\d{2})(\d{2})/);

   if ($cfg->{InSortKeyList}->{yyyy}) {
      if ($cfg->{assigned}->{yyyy}) {
         # pass through
         $cfg->{func}->{yyyy} = sub { return $_[0]->{yyyy}; };
      } elsif ($cfg->{assigned}->{yy}) {
         # convert 21 to 2021
         $cfg->{func}->{yyyy} = sub { return sprintf("20%02d", $_[0]->{yy}); };
      } else {
         # default to given yyyymmdd
         $cfg->{func}->{yyyy} = sub { return $yyyy; };
      }
   }

   if ($cfg->{InSortKeyList}->{mm}) {
      if ($cfg->{assigned}->{mm}) {
         # pass through
         $cfg->{func}->{mm} = sub { return $_[0]->{mm}; };
      } elsif ($cfg->{assigned}->{Mon}) {
         # convert Jan/JAN/January to 01
         $cfg->{func}->{mm} = sub { return  $TPSUP::LOG::mm_by_Mon{$_[0]->{Mon}}; };
      } elsif ($cfg->{assigned}->{m}) {
         # convert 1 to 01
         $cfg->{func}->{mm} = sub { return sprintf("%02d", $_[0]->{m}); };
      } else {
         # default to given yyyymmdd
         $cfg->{func}->{mm} = sub { return $mm; };
      }
   }

   if ($cfg->{InSortKeyList}->{dd}) {
      if ($cfg->{assigned}->{dd}) {
         # pass through
         $cfg->{func}->{dd} = sub { return $_[0]->{dd}; };
      } elsif ($cfg->{assigned}->{d}) {
          # convert 1 to 01
          $cfg->{func}->{dd} = sub { return sprintf("%02d", $_[0]->{d}); };
      } else {
          # default to given yyyymmdd
          $cfg->{func}->{dd} = sub { return $dd; };
      }
   }

   if (exists $cfg->{func}->{yyyy} && 
       exists $cfg->{func}->{mm}   &&
       exists $cfg->{func}->{dd}
      ) {
      $cfg->{func}->{yyyymmdd} = sub { return $cfg->{func}->{yyyy}->($_[0]) . 
                                              $cfg->{func}->{mm}->($_[0])   .
                                              $cfg->{func}->{dd}->($_[0])   ;
                                     };
   }

   $cfg->{func}->{HHMMSS}   = sub { return $_[0]->{HH} . $_[0]->{MM} . $_[0]->{SS};};

   # make sure sortkey components are all available: 
   #    either assigned or can be retrieved from a function.
   for my $k (@{$cfg->{sortkeyList}}) {
      next if $cfg->{assigned}->{$k};
      next if $cfg->{func}->{$k};
      croak "sortkey component '$k' is not assigned or defined as a function";
   }

   my $KeyDelimiter = defined($opt->{SortKeyDelimiter}) ? $opt->{SortKeyDelimiter} : "";

   $cfg->{func}->{key} = sub { 
      my ($r) = @_;      
      my @a;
      for my $k (@{$cfg->{sortkeyList}}) {
         if (exists $r->{$k}) {
            push @a, $r->{$k};
         } else {
            push @a, $cfg->{func}->{$k}->($r);
         } 
      }

      return join($KeyDelimiter, @a);
   };

   $cfg->{compiled} = qr/$cfg->{pattern}/;

   return $cfg;
}

sub find_log_PatternCfg {
   my ($log, $opt) = @_;

   my $PatternCfg_by_app = parse_PatternCfg($opt); 

   # convert hash to array for speed
   my @compiled;
   my @apps;

   for my $app (sort(keys %$PatternCfg_by_app)) {
      # 'auto' is a reserved word to avoid deadloop, should not be used in config file.
      croak "'auto' is a reserved word, should not be used in config file" if $app eq 'auto';

      # use get_PatternCfg_by_app($app, $opt) instead of $PatternCfg_by_app->{$app}
      # because the former will enrich the cfg, for example, it will pre-compile the pattern.
      #my $cfg = $PatternCfg_by_app->{$app};
      my $cfg = get_PatternCfg_by_app($app, $opt); 
      
      push @compiled, $cfg->{compiled};
      push @apps,     $app;
   }

   my $row_max = 100;
   my $row_count = 0;

   my $number_of_patterns = scalar(@compiled);

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

   $opt->{verbose} && print "count_by_idx = ", Dumper(\@count_by_idx), "\n";

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
         my $app = $apps[$max_idx];

         my $cfg = $PatternCfg_by_app->{$app};

         $cfg->{test_row_count} = $row_count;
         $cfg->{test_hit_count} = $max_hits;

         my $max_percent = $max_hits*100/$row_count;
         my $threshold = 5;
         if ($max_percent < $threshold) {
            print STDERR "Tried to auto-detect pattern, but even the best-matching pattern has very low matching ratio $max_percent\%, < threshold $threshold\%\n";
            print STDERR "cfg = ", Dumper($cfg);
            return undef;
         }
          
         return $cfg;
      } else {
         return undef;
      }
   } else {
      return undef;
   }
}


sub yyyymmddHHMMSS_to_log_time {
   my ($yyyymmddHHMMSS, $cfg, $opt) = @_;

   my $r;

   my $type = ref $yyyymmddHHMMSS;

   if ($type eq 'ARRAY') {
      if (@$yyyymmddHHMMSS == 2) {
         @{$r}{qw(yyyymmdd HHMMSS)} = @$yyyymmddHHMMSS;

         @{$r}{qw(yyyy mm dd)} = ($r->{yyyymmdd} =~ /^(\d{4})(\d{2})(\d{2})$/);
         croak "unknown format of yyyymmdd string = '$r->{yyyymmdd}'" if !defined $r->{dd};

         @{$r}{qw(HH   MM SS)} = ($r->{HHMMSSSS} =~ /^(\d{2})(\d{2})(\d{2})$/);
         croak "unknown format of HHMMSS string = '$r->{HHMMSS}'"     if !defined $r->{SS};
      } elsif (@$yyyymmddHHMMSS == 6) {
         @{$r}{qw(yyyy mm dd HH MM SS)} = @$yyyymmddHHMMSS;

         $r->{yyyymmdd} = $r->{yyyy} . $r->{mm} . $r->{dd};
         $r->{HHMMSS}   = $r->{HH}   . $r->{MM} . $r->{SS};
      } else {
         croak "unknown format of yyyymmddHHMMSS aref = " . Dumper($yyyymmddHHMMSS);
      }
   } else {
      @{$r}{qw(yyyy mm dd HH MM SS)} 
         = ($yyyymmddHHMMSS =~ /^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$/);
      croak "unknown format of yyyymmddHHMMSS string = '$yyyymmddHHMMSS'"
         if !defined $r->{SS};

      $r->{yyyymmdd} = $r->{yyyy} . $r->{mm} . $r->{dd};
      $r->{HHMMSS}   = $r->{HH}   . $r->{MM} . $r->{SS};
   }

   if ($cfg->{assigned}->{MS}) {
      $r->{MS} = 0;
   }

   $r->{key} = $cfg->{func}->{key}->($r);

   return $r;
}


sub get_log_time {
   my ($line_ref, $cfg, $opt) = @_;

   croak "missing cfg" if !$cfg;
   croak ("missing attr=compiled in cfg = " . Dumper($cfg)) if !$cfg->{compiled};

   my @matches = ($$line_ref =~ /$cfg->{compiled}/);

   my $r;

   if (@matches) {
      @{$r}{@{$cfg->{assignList}}} = @matches;

      $r->{yyyymmdd} = $cfg->{func}->{yyyymmdd}->($r) if exists $cfg->{func}->{yyyymmdd};
      $r->{HHMMSS}   = $cfg->{func}->{HHMMSS}->($r);
      $r->{key}      = $cfg->{func}->{key}->($r);

      if ($opt->{verbose}) {
         print "1ine=$$line_ref\n";
         #print "\@matches = ", Dumper(\@matches), "\n";
         print "ret = ", Dumper($r);
      }
   }
  
   return $r;
}

sub get_log_time_by_yyyymmddHHMMSS {
   my ($yyyymmddHHMMSS, $cfg, $opt) = @_;

   # this is similar to get_log_time but is given a yyyymmddHHMMSS instead of a log line

   if ($opt->{is_epoc_seconds}) {
      $yyyymmddHHMMSS = epoc_to_yyyymmddHHMMSS($yyyymmddHHMMSS);
   }

   my $type = ref $yyyymmddHHMMSS;

   my $r;
   if (!$type) {
      # scalar
      if ($yyyymmddHHMMSS =~ /^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$/) {
         @{$r}{qw(yyyy mm dd HH MM SS)} = ($1, $2, $3, $4, $5, $6);
      } else {
         croak "yyyymmddHHMMSS='$yyyymmddHHMMSS' bad format";
      }
   } else {
      croak "yyyymmddHHMMSS=" . Dumper($yyyymmddHHMMSS) . " unsupported type";
   }

   $r->{yyyymmdd} = $cfg->{func}->{yyyymmdd}->($r) if exists $cfg->{func}->{yyyymmdd};
   $r->{HHMMSS}   = $cfg->{func}->{HHMMSS}->($r);
   $r->{key}      = $cfg->{func}->{key}->($r);

   return $r;
}


sub get_log_fh {
   my ($f, $opt) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   my $backstring;
   my $criteria;

   my $backpattern;
   my $backpattern_compiled;
   my $backcount;

   my $startstring;
   my $startpattern;
   my $startpattern_compiled;
      
   return get_in_fh($f, $opt) if !$opt->{Anchor};

   my ($AnchorType, $AnchorValue) = split /=/, $opt->{Anchor}, 2;
   return get_in_fh($f, $opt) if !$AnchorType || !defined($AnchorValue);

   my $PosIfSearchFail = $opt->{PosIfSearchFail};

   my $is_backward = ($AnchorType =~ /^back/) ? 1 : 0;

   my $cfg;
   if ($AnchorType eq 'backseconds') {
      $cfg = $opt->{TimePatternCfg};
      croak "must specify TimePatternCfg to parse timestamp" if !$cfg;

      my $now_seconds;
      if ($opt->{FakeNow}) {
         $now_seconds = yyyymmddHHMMSS_to_epoc($opt->{FakeNow}); 
      } else {
         $now_seconds = time();
      }

      my $backseconds = $AnchorValue;
      my $old_seconds = $now_seconds - $backseconds;
      my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime($old_seconds);
      
      my $r;
      $r->{SS}   = sprintf("%02d", $sec);
      $r->{MM}   = sprintf("%02d", $min);
      $r->{HH}   = sprintf("%02d", $hour);
      $r->{yyyy} = sprintf("%04d", $year+1900);
      $r->{mm}   = sprintf("%02d", $mon+1);
      $r->{dd}   = sprintf("%02d", $mday);
      $r->{d}    = sprintf("%d",   $mday);
      #$r->{Mon}  = get_Mon_by_number($mon+1);

      $backstring = $cfg->{func}->{key}->($r);
      $criteria = "le $backstring";
   } elsif ($AnchorType eq 'backtime') {
      $cfg = $opt->{TimePatternCfg};
      croak "must specify TimePatternCfg to parse timestamp" if !$cfg;

      my $backtime = $AnchorValue;

      my $t = get_log_time(\$backtime, $cfg);

      croak "backtime=$backtime not matching: /$cfg->{pattern}/\n" if !$t;

      $backstring = $t->{key};
      $criteria = "le '$backstring'";
   } elsif ($AnchorType eq 'backpattern') {
      $backpattern          = $AnchorValue;
      $backpattern_compiled = qr/$backpattern/;
      $criteria = "=~ /$backpattern/";
   } elsif ($AnchorType eq 'backcount') {
      $backcount = $AnchorValue;
      $criteria = "backward $backcount lines";
   } elsif ($AnchorType eq 'starttime') {
      my $starttime = $AnchorValue;
     
      $cfg = $opt->{TimePatternCfg};
      croak "must specify -app AppName to parse timestamp" if !$cfg;

      my $t = get_log_time(\$starttime, $cfg);
      croak "starttime='$starttime' not matching: $cfg->{pattern}" if !$t;

      $startstring = $t->{key};
      $criteria = "gt '$startstring'";
   } elsif ($AnchorType eq 'startpattern') {
      $startpattern = $AnchorValue;
      $startpattern_compiled = qr/$startpattern /;
     
      $criteria = "=~ /$startpattern/";
   } else {
      croak "unsupported AnchorType=$AnchorType\n";
   }

   $verbose && print STDERR "criteria: $criteria\n";
   
   my $line_count = 0;
   my $pos;
   
   my $last_time;
   my $progress = $opt->{ShowProgress};
   if ($progress) {
      $last_time = time();
   }

   my $last_progress_time = $last_time;
   my $timestring;
   
   my $exclude_pattern = $opt->{ExcludePattern};
   my   $match_pattern = $opt->{MatchPattern};

   my $exclude_pattern_compiled;
   my   $match_pattern_compiled;

   $exclude_pattern_compiled = qr/$exclude_pattern/ if $exclude_pattern;
     $match_pattern_compiled =   qr/$match_pattern/ if   $match_pattern;

   # only backward search up to these many lines for the position
   my $SearchMax = $opt->{SearchMax}; 

   my $backward_obj;
   my $forward_fh;
   my $direction;

   if ($is_backward) {
      require File::ReadBackwards;
      $backward_obj = File::ReadBackwards->new($f) or croak $!;
      $direction = "backward";
   } else {
      $forward_fh = get_in_fh($f, $opt);
      $direction = "forward";
   }

   while (1) {
      $line_count ++;
   
      if (defined($SearchMax) && $line_count >= $SearchMax) {
         $verbose && print STDERR "Max backward $SearchMax lines. stop.\n";
         $pos = $backward_obj->tell();
         last;
      }
   
      my $line;
      if ($is_backward) {
         $line = $backward_obj->readline();
      } else {
         $line = <$forward_fh>;
      }
   
      last if ! defined($line);
   
      my $need_to_print_test_detail;

      if ($progress) {
         if ($line_count % $progress == 0 ) {
            my $now = time();
   
            my $seconds = $now - $last_progress_time;
   
            $last_progress_time = $now;
   
            print STDERR "$line_count lines are processed $direction, $progress lines in $seconds seconds\n";
            if ($verbose) {
               $need_to_print_test_detail = 1;
            }
         }
      }
      
      next if defined $exclude_pattern && $line =~ /$exclude_pattern_compiled/;
      
      next if defined   $match_pattern && $line !~   /$match_pattern_compiled/;
      
      if ($backpattern) {
         if ($line =~ /$backpattern_compiled/) {
            $pos = $backward_obj->tell();
            $verbose && print STDERR "\nbackpattern=$backpattern found: $line\n";
            last;
         } 
      } elsif ($backstring) {
         # type is time or seconds
         my $t = get_log_time(\$line, $cfg);
         next if !$t;
         my $key = $t->{key};
      
         $verbose>=2 && print STDERR "backward check: $key le $backstring ?\n";
         if ($key le $backstring) {
            $pos = $backward_obj->tell();
            $opt->{verbose} && print STDERR "\nbackward found line: $key le $backstring\n$line\n";
            last;
         } else {
            if ($need_to_print_test_detail) {
               print STDERR "last test pattern '$criteria' failed at line:\n$line";
            }
         }
      } elsif (defined $backcount) {
         if ($line_count >= $backcount) {
            $pos = $backward_obj->tell();
            last;
         }
      } elsif ($startpattern) {
         if ($line =~ /$startpattern_compiled/) {
            $pos = tell($forward_fh) - length($line);
            $verbose && print STDERR "\nstartpattern=$startpattern found: $line\n";
            last;
         }
      } elsif ($startstring) {
         my $t = get_log_time(\$line, $cfg);
         next if !$t;
         my $key = $t->{key};

         $verbose>=2 && print STDERR "check: $key gt $startstring ?\n";
         if ($key gt $startstring) {
            $pos = tell($forward_fh) - length($line);
            $opt->{verbose} && print STDERR "\nforward check passed: $key gt $startstring\n$line\n";
            last;
         } else {
            if ($need_to_print_test_detail) {
               print STDERR "last test: $key gt $startstring, failed at line:\n$line";
            }
         }
      }
   }
      
   if ($progress) {
      my $now = time();
      
      my $seconds = $now - $last_time;
      
      $last_time = $now;
   
      $opt->{verbose} && print STDERR "total $line_count lines are processed $direction in $seconds seconds\n";
   }
      
   if (!defined($pos)) {
      my $pos = $opt->{PosIfSearchFail};
      if (defined $pos) {
         print STDERR "WARN: cannot find the backward position using $criteria. setting pos=$pos\n";
      } else {
         croak "cannot find the backward position in $f";
      }
   }

   my $fh = $is_backward ? $backward_obj->get_handle() : $forward_fh;
   seek($fh, $pos, 0);
   return $fh;
}


sub get_log_latency {
   my ($old, $new, $opt) = @_;

   if ($opt->{verbose}) {
      print STDERR "old = ", Dumper($old);
      print STDERR "new = ", Dumper($new);
   }

   croak "old is not defined in get_latency(old, new)" if !$old;
   croak "new is not defined in get_latency(old, new)" if !$new;

   my $seconds = 0;

   if (   (!$old->{yyyymmdd} &&  $new->{yyyymmdd}) 
        ||( $old->{yyyymmdd} && !$new->{yyyymmdd})
      ) {
      croak ("inconsistent existence of yyyymmdd in get_latency(old, new)\n" 
             . "old = " . Dumper($old)
             . "new = " . Dumper($new)
            );
   }


   if ( $old->{yyyymmdd} && $new->{yyyymmdd} )  {
      $seconds = get_seconds_between_two_days($old->{yyyymmdd}, $new->{yyyymmdd}, $opt);
   }

   $seconds = $seconds + 
             ($new->{HH} - $old->{HH}) * 3600 +
             ($new->{MM} - $old->{MM}) *   60 +
             ($new->{SS} - $old->{SS});

   if ( defined $new->{MS} && defined $old->{MS}) {
      $seconds = sprintf("%.3f", $seconds + ($new->{MS}-$old->{MS})*0.001);
   } 

   return $seconds;
}


sub get_logs {
   my ($log, $opt) = @_;

   my @log_patterns;
   my $type = ref($log);
   if (!$type) {
      # a scalar
      @log_patterns = ($log);
   } elsif ($type eq 'ARRAY') {
      @log_patterns = @$log;
   } else {
      confess "type='$type' for log=", Dumper($log);
   }

   my @logs;
   for my $lp (@log_patterns) {
      my $cmd = "/bin/ls -1dtr $lp";
      $opt->{verbose} && print STDERR "cmd=$cmd\n";
      my @lines = `$cmd`;
      chomp @lines;
      push @logs, @lines;
   }

   #print "logs = ", Dumper(\@logs);

   my $LogLastCount = $opt->{LogLastCount};
   if ($LogLastCount) {
      if ($LogLastCount >= @logs) {
         return \@logs;
      } else {
         my @logs2 = @logs[$#logs-$LogLastCount+1..$#logs];
         return \@logs2;
      }
   } else {
      return \@logs;
   }
}


sub get_logname_cfg {
   my ($cfg_file, $opt) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 1;

   croak "$cfg_file not found"    if ! -f $cfg_file;
   croak "$cfg_file not readable" if ! -r $cfg_file;

   my $yyyymmdd = $opt->{yyyymmdd};
   if (!defined $yyyymmdd) {
      $yyyymmdd = $TPSUP::LOG::yyyymmdd;
   }
   
   my ($yy2, $yy, $mm, $dd) = ($yyyymmdd =~ /^(..)(..)(..)(..)$/);
   
   my $yyyy = "${yy2}${yy}";
   
   my $user = get_user();    

   my $cfg_string = `cat $cfg_file`;

   croak "failed to read $cfg_file: $!" if $?;

   my $string2 = resolve_scalar_var_in_string($cfg_string, {yyyymmdd=>$yyyymmdd, user=>$user});

   our $our_logname_cfg;
   eval $string2;
   if ($@) {
      croak "ERROR in parsing $cfg_file: $@\n";
      return undef;
   }

   return $our_logname_cfg;
}


sub get_logs_by_cfg {
   my ($cfg_file, $cfg_key, $opt) = @_;

   my $verbose = $opt->{verbose};

   my $yyyymmdd = $opt->{yyyymmdd} ? $opt->{yyyymmdd} : $TPSUP::LOG::yyyymmdd;
   my @days = ($yyyymmdd);

   my $BackwardDays = $opt->{BackwardDays};
   if ($BackwardDays) {
      for (my $i=1; $i<=$BackwardDays; $i++) {
         my $day = `date -d "$yyyymmdd - $i day" "+%Y%m%d"`; chomp $day;
         push @days, $day;
      }
   }

   my @logs;
   my $seen;
   for my $day (@days) {
      my $all_cfg = get_logname_cfg($cfg_file, {%$opt, yyyymmdd=>$day});
   
      $verbose && print "all_cfg = ", Dumper($all_cfg);
   
      my $cfg = $all_cfg->{$cfg_key};
   
      croak "'$cfg_key' is not defined in $cfg_file" if ! defined($cfg);
   
      my @patterns;
      my @pattern_keys;
      if ( $day eq $TPSUP::LOG::yyyymmdd) {
          @pattern_keys = qw(yyyymmdd_pattern today_pattern);
      } else {
          @pattern_keys = qw(yyyymmdd_pattern);
      }
   
      for my $k (@pattern_keys) {
          my $pattern = $cfg->{$k};
          next if ! defined $pattern;
          push @patterns, $pattern;
      }
   
      my $logs2 = get_logs(\@patterns, {%$opt, yyyymmdd=>$day});

      for my $log (@$logs2) {
         next if $seen->{$log};

         push @logs, $log;
         $seen->{$log} ++;
      }
   }

   return \@logs;
}


sub get_log_section_gen {
   my ($log, $section_cfg, $opt) = @_;

   my $verbose = $opt->{verbose};

   confess "section_cfg is not defined" if !$section_cfg;

   # - both BeginPattern/EndPattern can be undefined at the same time; in this
   #   case the whole file is one section.
   # - when only BeginPattern is undefined, we start with assuming the first
   #   section is started.
   # - when only EndPattern is undefined, we assume the end of section is the
   #   line before the next BeginPattern is matched.

   my $BeginPattern = $section_cfg->{BeginPattern};
   my   $EndPattern = $section_cfg->{EndPattern};

   my $CompiledBegin;
   my $CompiledEnd;
   if (defined $BeginPattern) { $CompiledBegin = qr/$BeginPattern/; } 
   if (defined $EndPattern)   { $CompiledEnd   =   qr/$EndPattern/; }

   # PreMatch/PreExclude are tried before BeginPattern/EndPattern are tried
   # they are for speedup, it covers every line, therefore, be careful to 
   # avoid filtering out BeginPattern/EndPattern.
   #
   # PostPattern/PostPattern are tried after BeginPattern/EndPattern are tried
   # they are for both speedup and reduce noise, 

   my $PreMatch   = $section_cfg->{PreMatch}  ;
   my $PreExclude = $section_cfg->{PreExclude};

   my $CompiledPreMatch;
   my $CompiledPreExclude;
   if (defined $PreMatch)   { $CompiledPreMatch   = qr/$PreMatch/;   }
   if (defined $PreExclude) { $CompiledPreExclude = qr/$PreExclude/; }

   my $PostMatch   = $section_cfg->{PostMatch};
   my $PostExclude = $section_cfg->{PostExclude};

   my $CompiledPostMatch;
   my $CompiledPostExclude;
   if (defined $PostMatch)   { $CompiledPostMatch   = qr/$PostMatch/; }
   if (defined $PostExclude) { $CompiledPostExclude = qr/$PostExclude/; }

   my $KeyAttr         = $section_cfg->{KeyAttr};
   my $KeyDefault      = $section_cfg->{KeyDefault};
   my $ExtractPatterns = $section_cfg->{ExtractPatterns};

   my @CompiledExtracts;
   if (defined($ExtractPatterns)) {
      @CompiledExtracts = map {qr/$_/} @$ExtractPatterns;
   }

   my $maxcount   = $opt->{MaxCount};

   #my $fh = get_in_fh($log, $opt);
   #return undef if !$fh;

   my $fh;
   my $logs = get_logs($log, $opt);
   my $item;
   my $line;
   my $item_count = 0;
   my $all_done = 0;   # to indicate whether whole file has been parsed. 
                       # this is to avoid error: read closed file handle

   # need to define the inner sub as an anonymous sub
   #    1. to avoid the error: Variable "$line" will not stay shared
   #    2. to be able to call the outer sub multiple times
   # detail see:
   #    https://stackoverflow.com/questions/25399728/perl-variable-will-not-stay-shared
   my $consume_line_update_item = sub {
      my $saved_line;
      for my $p (@CompiledExtracts) {
         if ($line =~ /$p/) {
            my %match = %+;
            next if ! %match;

            $verbose && print "matched = ", Dumper(%match);

            if (!defined $saved_line) {
               $saved_line = $line;
               push @{$item->{lines}}, $line;
            }

            for my $k (keys (%match)) {
               my $v = $match{$k};
               if (!$KeyAttr->{$k}) {
                  $item->{$k} = $v;
               } elsif ($KeyAttr->{$k} eq 'Array') {
                  push @{$item->{$k}}, $v;
               } elsif ($KeyAttr->{$k} eq 'Hash') {
                  $item->{$k}->{$v} ++;
               } else {
                  confess "unsupported KeyAttr at '$k=$KeyAttr->{$k}'";
               }
            }
         }
      }

      $line = undef; # after $line is consumed, reset it to undef to avoid double use.
   };

   return sub {
      $item_count ++;

      # returning undef to signal the end of iterator/generator
      return undef if $maxcount && $item_count >= $maxcount;
      return undef if $all_done;  # we have finished reading the file in last call

      $item = {};    # avoid return undef $item when there is no captures, 
                     # as undef $item indicates end of generator

      if ($KeyDefault) {
         for my $k (%$KeyDefault) {
            if (exists $KeyDefault->{$k}) {
               my $default = $KeyDefault->{$k};

               # make deep copy here; otherwise KeyDefault could be updated inadvertently
               my $type = ref($default);
               if (!$type) {
                  # scalar 
                  $item->{$k} = $default;
               } elsif ($type eq 'ARRAY') {
                  @{$item->{$k}} = @$default;
               } elsif ($type eq 'HASH') {
                  # first-level copy for HASH. not perfect but should be enough.
                  %{$item->{$k}} = %$default;
               } elsif ($type eq 'HASH') {
                  confess "unsupported type=$type at key=$k in KeyDefault=" .
                          Dumper($KeyDefault);
               }
            }
         }
      }

      # if we don't have begin pattern, then we assume already started
      my $started = defined($CompiledBegin) ? 0 : 1;

      if (defined($line)) {
         # if $line is defined here, it was left from last call. 
         # we must haven't matched $CompiledEnd in last call. 
         # therefore, it wasn't a clean finish.
         $consume_line_update_item->();
         $started = 1;
      }

      while (@$logs) {
         if (!$fh) {
            $verbose && print "logs = ", Dumper($logs);
            my $next_log = shift @$logs;
            $verbose && print "next_log = $next_log\n";
   
            if ($next_log) {
               $fh = get_in_fh($next_log, $opt);
            } else {
               $all_done = 1;
            }
         } 
           
         if ($fh) {
            while ( defined($line = <$fh>) ) {
               next if defined($CompiledPreMatch)    && $line !~ /$CompiledPreMatch/;
               next if defined($CompiledPreExclude)  && $line =~ /$CompiledPreExclude/;
      
               if (defined($CompiledBegin) && $line =~ /$CompiledBegin/) {
                  # this is a starting line. 
                  if ($started) {
                     # if we already started, we have an $item, we return the $item.
                     return $item; 
                     # note: we didn't consume $line and it is left for the next call.
                  } else {
                     $consume_line_update_item->();
                  }
                  $started = 1;
               } elsif (defined($CompiledEnd) && $line =~ /$CompiledEnd/) {
                  # we matched the end pattern. this will be a clean finish
                  if ($started) {
                     # consume this only if the section already started
                     $consume_line_update_item->();
                     return $item; 
                  } 
                  # unwanted line is thrown away
                  # we don't need to do any of below as they will be taken care of by loop
                  # $line = undef;
                  # next;
               } elsif ( ($CompiledPostMatch   && $line !~ /$CompiledPostMatch/) || 
                         ($CompiledPostExclude && $line =~ /$CompiledPostExclude/) ){
                  next;
               } else {
                  $consume_line_update_item->() if $started;
               } 
            }
            
            close_in_fh($fh);
            $fh = undef;
         } 
      }

      # no more logs to parse
      if (!$started) {
         return undef;    # returning undef to signal the end of iterator/generator
      } else {
         return $item;
      }
   }   
}

sub get_log_section_headers {
   my ($ExtractPatterns, $opt) = @_;

   my @headers;
   
   if ($ExtractPatterns) {
      my $seen;
      for my $line (@$ExtractPatterns) {
         my @keys = ($line =~ /[?]<([a-zA-Z0-9_]+)>/g);
         for my $k (@keys) {
            $seen->{$k} ++;
         }
      }
      @headers = sort(keys %$seen);
   }

   return \@headers;
}


sub filter_log_section_gen {
   my ($log, $section_cfg, $opt) = @_;

   my $verbose = $opt->{verbose};

   #my $section_gen = get_log_section_gen($log, $section_cfg, $opt);
   my $section_gen = get_log_section_gen($log, $section_cfg);

   my $compiledExp;
   for my $ExpName (qw(MatchExp ExcludeExp)) { 
      my $exp = $section_cfg->{$ExpName};

      next if ! defined $exp;

      $compiledExp->{$ExpName} = eval_exp_to_sub($exp, {ExpName=>$ExpName});
   }

   my $CompiledMatch   = $compiledExp->{MatchExp};
   my $CompiledExclude = $compiledExp->{ExcludeExp};

   return sub {
      while (my $r = $section_gen->()) {
         next if defined($CompiledMatch)   && ! $CompiledMatch->(  $r, {verbose=>$verbose});
         next if defined($CompiledExclude) &&   $CompiledExclude->($r, {verbose=>$verbose});

         return $r;
      } 

      return undef;
   };
}


sub eval_exp_to_sub {
   my ($exp, $opt) = @_;

   my $ExpName = $opt->{ExpName} ? $opt->{ExpName} : "";

   my $sub;

   # using variable is easier to work with data structures, eg, array
   # using hash (%r) instead of ref ($r2) makes expression cleaner:
   #     $r{name} vs $r2->{name}

   my $code = '$sub = sub {
      my ($r2, $opt)=@_; 
      my %r=%$r2; 
      my $verbose = $opt->{verbose};
      if ($verbose) {
         print STDERR "$ExpName $exp, r=", Dumper(\%r);
      }
      my $result = ' . $exp . ' ? 1 : 0;
      if ($verbose) {
         print STDERR "exp result=$result\n";
      }
      return $result;
   }';

   eval $code;
   if ($@) {
      # compile-time error happens here
      my $numbered_code = add_line_number_to_code($code);
      confess "failed to compile code='
$numbered_code
$@
      '\n" ;
   }

   return $sub;
}


sub get_log_sections {
   my ($log, $cfg, $opt) = @_;
   my $section_gen = filter_log_section_gen($log, $cfg, $opt);

   my $MaxSections = $opt->{MaxSections};

   my @sections;
   my $count = 0;

   while (my $r = $section_gen->()) {
      $count ++;
      last if defined($MaxSections) && $count>$MaxSections;
      push @sections, $r;
   }

   return \@sections;
}

sub main {
   print <<"EOF";
------------------------------
print global variables

yyyy = $TPSUP::LOG::yyyy
mm   = $TPSUP::LOG::mm
dd   = $TPSUP::LOG::dd
HH   = $TPSUP::LOG::HH
MM   = $TPSUP::LOG::MM
SS   = $TPSUP::LOG::SS

yyyymmdd = $TPSUP::LOG::yyyymmdd
HHMMSS   = $TPSUP::LOG::HHMMSS

EOF

   my $log = "$ENV{TPSUP}/scripts/log_event_test.log";
   my $cfg = find_log_PatternCfg($log);
   print <<"EOF";

------------------------------
test find_log_PatternCfg(...)

EOF
   print "matched cfg = ", Dumper($cfg);

   print <<"EOF";

------------------------------
test get_log_time(...)

EOF

   my $log2 = "$ENV{TPSUP}/scripts/log_event_test2.log";
   my $cfg2 = find_log_PatternCfg($log2);
   print "matched cfg2 = ", Dumper($cfg2);
   my $fh2 = get_in_fh($log2);
   while (<$fh2>) {
      print $_;
      print "get_log_time(...) = ", Dumper(get_log_time(\$_, $cfg2));       
   }
   close_in_fh($fh2);

   { 
      my $backtime = 'Sep 18 13:02:33';
      print <<"EOF";

------------------------------

test get_log_fh(backtime=$backtime)
print 2 lines;

EOF
      my $fh = get_log_fh($log, {
                                     TimePatternCfg => $cfg,
                                     Anchor  => "backtime=$backtime",
                                   }
                             );
      my $line = <$fh>;
      print $line;
      $line = <$fh>;
      print $line;
      close $fh;
   }
   
   {
      my $backseconds = 300;
      my $yyyy = `date +%Y`; chomp $yyyy;
      my $FakeNow = $yyyy . '0918131800';
      print <<"EOF";

------------------------------

test get_log_fh(backseconds=$backseconds, FakeNow=$FakeNow)
print 2 lines;

EOF
      my $fh = get_log_fh($log, {
                                     TimePatternCfg => $cfg,
                                     Anchor => "backseconds=$backseconds",
                                     #verbose => 1,
                                     #ShowProgress=>2,
                                     FakeNow=>$FakeNow,
                                   }
                             );
      my $line = <$fh>;
      print $line;
      $line = <$fh>;
      print $line;
      close $fh;
   }

   {
      my $backpattern = "Starting Message of the Day";
      print <<"EOF";

------------------------------

test get_log_fh(backpattern=$backpattern )
print 1 lines;

EOF
      my $fh = get_log_fh($log, {Anchor => "backpattern=$backpattern"});
      my $line = <$fh>;
      print $line;
      close $fh;
   }

   {
      my $backcount = 2;
      print <<"EOF";

------------------------------

test get_log_fh(backcount=$backcount )
print 1 lines;

EOF
      my $fh = get_log_fh($log, {Anchor => "backcount=$backcount"});
      my $line = <$fh>;
      print $line;
      close $fh;
   }

   {
      my $log = "./LOG_test_section*.log";
      # 2021/08/24 00:00:03,123 section id 2 started
      # 2021/08/25 00:00:04,123 item id 201
      # 2021/08/25 00:00:05,123 item id 202
      # 2021/08/25 00:00:06,123 section completed

      my $cfg = {
              PreMatch => '^2021',
         BeginPattern  => 'section id .*? started',
           EndPattern  => 'section completed',
            PostMatch  => 'order id|trade id',
       ExtractPatterns => [
                           '^(?<BeginTime>.{23}) section id (?<SectionId>.*?) started',
                             '^(?<EndTime>.{23}) section completed',
                           'order id (?<OrderId>\S+)',
                           'trade id (?<TradeId>\S+)',
                          ],
            KeyAttr    => { OrderId=>'Hash', TradeId=>'Array' },
            KeyDefault => { OrderId=>{},     TradeId=>[] },
            # KeyDefault is to simplify MatchExp, allowing us to use
            #     MatchExp =>'grep {/^TRD-0001$/}  @{$r{TradeId}}'
            # without worrying about whether $r{OrderId} is defined.

           # the following are only used by filter_log_section_gen()
              MatchExp =>'$r{OrderId}{"ORD-0001"}', 
            ExcludeExp =>'$r{OrderId}{"ORD-0003"}', 
      };
      print <<"EOF";

------------------------------

test get_log_section_gen

EOF
      
      {
         my $section_gen = get_log_section_gen($log, $cfg,
                                               #{verbose=>1}
                                              );
         while (my $r = $section_gen->()) {
           print "r = ", Dumper($r);
         }
      }

      print <<"EOF";

------------------------------

test get_log_section_headers

EOF
      
      {
         my $headers = get_log_section_headers($cfg->{ExtractPatterns},
                                               #{verbose=>1}
                                              );
         print "headers = ", Dumper($headers);
      }


      {
        # my $sections = get_log_sections($log, $cfg, 
        #                                #{verbose=>1}
        #                                );
        # print "sections = ", Dumper($sections);
      }
   }
}


main() unless caller();
      
1
      
