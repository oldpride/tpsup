package TPSUP::DATE;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
  get_yyyymmdd
  get_yyyymmdd_by_yyyymmdd_offset
  get_date
  get_timezone_offset
  parse_holiday_csv
  is_holiday
  get_tradeday
  get_tradedays
  get_tradeday_by_exch_begin_offset
  get_holidays_by_exch_begin_end
  get_tradedays_by_exch_begin_end
  get_interval_seconds
  get_seconds_between_yyyymmddHHMMSS
  get_seconds_between_two_days
  get_Mon_by_number
  get_mm_by_Mon
  convert_from_yyyymmdd
  date2any
  yyyymmddHHMMSS_to_epoc
  epoc_to_yyyymmddHHMMSS
  get_yyyymmddHHMMSS
  get_new_yyyymmddHHMMSS
  local_vs_utc
  yyyymmdd_to_DayOfWeek
  get_weekday_generator
);

# get_interval_seconds
# vs get_seconds_between_yyyymmddHHMMSS
# vs get_seconds_between_two_days
#    get_interval_seconds uses strict format
#    get_seconds_between_yyyymmddHHMMSS supports more formats
#    get_seconds_between_two_days is to handle DST change

use Carp;
use Data::Dumper;
use TPSUP::CSV    qw(parse_csv_file);
use TPSUP::SEARCH qw(binary_search_match);
use TPSUP::FILE   qw(get_in_fh);
use Time::Local;
use File::Spec;
use POSIX;

sub get_yyyymmdd {
   my ($opt) = @_;

   my $date = get_date($opt);

   return $date->{yyyy} . $date->{mm} . $date->{dd};
}

sub get_date {
   my ($opt) = @_;

   my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst );
   my $yyyymmdd = $opt->{yyyymmdd};
   if ($yyyymmdd) {
      if ( $yyyymmdd =~ /^(\d{4})(\d{2})(\d{2})/ ) {
         ( $year, $mon, $mday ) = ( $1, $2, $3 );
         $year -= 1900;
         $mon  -= 1;

         # we need the following to get the correct wday (weekday)
         ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) =
           localtime( timelocal( 0, 0, 0, $mday, $mon, $year ) );
      } else {
         croak "yyyymmdd='$yyyymmdd', bad format";
      }
   } else {
      ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) = localtime();
   }

   my $date;

   $date->{yyyy} = sprintf( "%4d",  $year + 1900 );
   $date->{mm}   = sprintf( "%02d", $mon + 1 );
   $date->{dd}   = sprintf( "%02d", $mday );

   $date->{HH} = sprintf( "%02d", $hour );
   $date->{MM} = sprintf( "%02d", $min );
   $date->{SS} = sprintf( "%02d", $sec );

   $date->{DST} = $isdst;
   $date->{WD}  = $wday;

   return $date;
}

sub get_yyyymmdd_by_yyyymmdd_offset {
   my ( $yyyymmdd1, $offset, $opt ) = @_;

   my $yyyymmdd2 = `date -d "$yyyymmdd1 $offset day" '+%Y%m%d'`;
   chomp $yyyymmdd2;
   return $yyyymmdd2;
}

my $yyyymmdd_pattern       = qr/^(\d{4})(\d{2})(\d{2})$/;
my $yyyymmddHHMMSS_pattern = qr/^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$/;
my $whole_week_seconds     = 7 * 24 * 60 * 60;

sub get_weekday_generator {
   my ( $begin, $opt ) = @_;

   my $DayOfWeek = yyyymmdd_to_DayOfWeek($begin);
   $opt->{verbose} && print STDERR "begin=$begin, DayOfWeek = $DayOfWeek\n";

   my $add_CalendarDays = 0;
   if ( $DayOfWeek > 5 ) {

      # this is weekend
      $add_CalendarDays = 7 - $DayOfWeek + 1;
      $DayOfWeek        = 1;
   }

   my $day_seconds = 24 * 60 * 60;

   my $add_CalendarDays_seconds = $add_CalendarDays * $day_seconds;

   # we use 12:00:00 instead of 00:00:00 to avoid daylight-saving-change causing +/- day
   my $epoc_seconds = yyyymmddHHMMSS_to_epoc("${begin}120000") + $add_CalendarDays_seconds;

   return sub {
      my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) = localtime($epoc_seconds);
      my $to_be_returned = sprintf( "%4d%02d%02d", 1900 + $year, $mon + 1, $mday );

      # this block is for the next loop
      if ( ( $DayOfWeek % 5 ) == 0 ) {

         # this is Friday. Add two days to pass weekend, for the next loop
         $epoc_seconds += 3 * $day_seconds;
         $DayOfWeek = 1;
      } else {
         $epoc_seconds += $day_seconds;
         $DayOfWeek    += 1;
      }

      return $to_be_returned;
   }
}

sub get_timezone_offset {
   my ($opt) = @_;

   # $ perl -e 'use TPSUP::DATE; print TPSUP::DATE::get_timezone_offset(), "\n";'
   # -5

   # use Time::Local;
   my $local_sec             = time();
   my @t                     = localtime($local_sec);
   my $gmt_offset_in_seconds = timegm(@t) - $local_sec;
   my $gmt_offset_in_hours   = $gmt_offset_in_seconds / 3600;

   return $gmt_offset_in_hours;
}

sub yyyymmddHHMMSS_to_epoc {
   my ( $yyyymmddHHMMSS, $opt ) = @_;

   my $type = ref $yyyymmddHHMMSS;

   if ( $type eq 'ARRAY' ) {
      if ( $opt->{fromUTC} ) {
         return timegm(
            $yyyymmddHHMMSS->[5],        # SS
            $yyyymmddHHMMSS->[4],        # MM
            $yyyymmddHHMMSS->[3],        # HH
            $yyyymmddHHMMSS->[2],        # dd
            $yyyymmddHHMMSS->[1] - 1,    # mm-1
            $yyyymmddHHMMSS->[0],        # yyyy
         );
      } else {
         return timelocal(
            $yyyymmddHHMMSS->[5],        # SS
            $yyyymmddHHMMSS->[4],        # MM
            $yyyymmddHHMMSS->[3],        # HH
            $yyyymmddHHMMSS->[2],        # dd
            $yyyymmddHHMMSS->[1] - 1,    # mm-1
            $yyyymmddHHMMSS->[0],        # yyyy
         );
      }
   } else {
      if ( "$yyyymmddHHMMSS" =~ /$yyyymmddHHMMSS_pattern/ ) {
         my ( $yyyy, $mm, $dd, $HH, $MM, $SS ) = ( $1, $2, $3, $4, $5, $6 );

         if ( $opt->{fromUTC} ) {
            return timegm( $SS, $MM, $HH, $dd, $mm - 1, $yyyy );
         } else {
            return timelocal( $SS, $MM, $HH, $dd, $mm - 1, $yyyy );
         }
      } else {
         croak "yyyymmddHHMMSS='$yyyymmddHHMMSS', bad format";
      }
   }
}

sub epoc_to_yyyymmddHHMMSS {
   my ( $epoc, $opt ) = @_;

   my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst );
   if ( $opt->{toUTC} ) {
      ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) = gmtime($epoc);
   } else {
      ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) = localtime($epoc);
   }
   my $yyyymmddHHMMSS = sprintf( '%4d%02d%02d%02d%02d%02d', 1900 + $year, $mon + 1, $mday, $hour, $min, $sec, );

   return $yyyymmddHHMMSS;
}

sub get_yyyymmddHHMMSS {
   my ($opt)          = @_;
   my $now_sec        = time();
   my $yyyymmddHHMMSS = epoc_to_yyyymmddHHMMSS( $now_sec, $opt );
   return $yyyymmddHHMMSS;
}

# get next yyyymmddHHMMSS by offset seconds.
# it supports a few formats
sub get_new_yyyymmddHHMMSS {
   my ( $old_yyyymmddHHMMSS, $offset, $opt ) = @_;

   my $out_format;
   my $old_t;
   if ( $old_yyyymmddHHMMSS =~ /^([12][09]\d{12})(.*)/ ) {
      $old_t = $1;
      my $tail = defined($2) ? $2 : '';
      $out_format = '%4d%02d%02d%02d%02d%02d' . $tail;
   } elsif ( my @c =
      ( $old_yyyymmddHHMMSS =~ /^([12][09]\d{2})([^\d])(\d{2})(.)(\d{2})(.)(\d{2})(.)(\d{2})(.)(\d{2})(.*)/ ) )
   {
      $old_t = "$c[0]$c[2]$c[4]$c[6]$c[8]$c[10]";
      my $tail = defined( $c[13] ) ? $c[13] : '';
      $out_format =
        '%4d' . $c[1] . '%02d' . $c[3] . '%02d' . $c[5] . '%02d' . $c[7] . '%02d' . $c[9] . '%02d' . $c[11] . $tail;
   } else {
      confess "unsupported format at old_yyyymmddHHMMSS='$old_yyyymmddHHMMSS'";
   }

   my $old_sec = yyyymmddHHMMSS_to_epoc($old_t);
   my $new_sec = $old_sec + $offset;

   my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) = localtime($new_sec);
   my $new_yyyymmddHHMMSS = sprintf( $out_format, 1900 + $year, $mon + 1, $mday, $hour, $min, $sec, );

   return $new_yyyymmddHHMMSS;
}

# switch between local and UTC
sub local_vs_utc {
   my ( $direction, $old_yyyymmddHHMMSS, $opt ) = @_;

   my $out_format;
   my $old_t;

   confess "old_yyyymmddHHMMSS is undef" if !defined($old_yyyymmddHHMMSS);

   if ( $old_yyyymmddHHMMSS =~ /^([12][09]\d{12})(.*)/ ) {
      $old_t = $1;
      my $tail = defined($2) ? $2 : '';
      $out_format = '%4d%02d%02d%02d%02d%02d' . $tail;
   } elsif ( my @c =
      ( $old_yyyymmddHHMMSS =~ /^([12][09]\d{2})([^\d])(\d{2})(.)(\d{2})(.)(\d{2})(.)(\d{2})(.)(\d{2})(.*)/ ) )
   {
      $old_t = "$c[0]$c[2]$c[4]$c[6]$c[8]$c[10]";
      my $tail = defined( $c[13] ) ? $c[13] : '';
      $out_format =
        '%4d' . $c[1] . '%02d' . $c[3] . '%02d' . $c[5] . '%02d' . $c[7] . '%02d' . $c[9] . '%02d' . $c[11] . $tail;
   } else {
      confess "unsupported format at old_yyyymmddHHMMSS='$old_yyyymmddHHMMSS'";
   }

   my $fromUTC;
   my $toUTC;
   if ( $direction eq 'UTC2LOCAL' ) {
      $fromUTC = 1;
      $toUTC   = 0;
   } elsif ( $direction eq 'LOCAL2UTC' ) {
      $fromUTC = 0;
      $toUTC   = 1;
   } else {
      confess "direction='$direction' is not supported";
   }

   my $old_sec = yyyymmddHHMMSS_to_epoc( $old_t, { fromUTC => $fromUTC } );

   if ( !$toUTC ) {
      my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) = localtime($old_sec);
      return sprintf( $out_format, 1900 + $year, $mon + 1, $mday, $hour, $min, $sec );
   } else {
      my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) = gmtime($old_sec);
      return sprintf( $out_format, 1900 + $year, $mon + 1, $mday, $hour, $min, $sec );
   }
}

my $perllib_dir;

sub get_perllib_dir {
   if ( !$perllib_dir ) {
      # https://stackoverflow.com/questions/2403343/in-perl-how-do-i-get-the-directory-or-path-of-the-current-executing-code
      my ( $volume, $directory, $file ) = File::Spec->splitpath(__FILE__);
      $perllib_dir = File::Spec->rel2abs($directory);
   }
   return $perllib_dir;
}

my $holidays_by_exch;
my $exists_by_exch_holiday;

sub parse_holiday_csv {
   my ( $exch, $opt ) = @_;

   croak "need to specify exch when calling parse_holiday_csv()" if !$exch;

   return $exists_by_exch_holiday->{$exch}
     if exists $exists_by_exch_holiday->{$exch};

   if ( exists( $opt->{HolidayRef} ) and defined( $opt->{HolidayRef} ) ) {
      $exists_by_exch_holiday->{$exch} = $opt->{HolidayRef};
      return $exists_by_exch_holiday->{$exch};
   }

   my $HolidaysCsv;
   if ( exists( $opt->{HolidaysCsv} ) and defined( $opt->{HolidaysCsv} ) ) {
      $HolidaysCsv = $opt->{HolidaysCsv};
   } else {
      my $directory = get_perllib_dir();
      $HolidaysCsv = "$directory/DATE_holidays.csv";
   }

   croak "$HolidaysCsv is not found" if !-f $HolidaysCsv;

   # name,days
   # NYSE,20200101 20200120 20200217 20200410 20200525 20200703 20200907 20201126 20201125 20210101 20210118 20210402 20210531 20210705 20210906 20211125 20211224 20220101 20220117 20220221 20220415 20220530 20220704 20220905 20221124 20221126

   my $fh = get_in_fh($HolidaysCsv);

   my $row_count = 0;
   my @holidays;
   my $ref;

   while (<$fh>) {
      $row_count++;

      if (/^$exch,(.+)/) {
         @holidays = map { int($_) } split( /\s+/, $1 );

         my $item_count = 0;
         my $last_holiday;

         for my $yyyymmdd (@holidays) {
            $item_count++;

            if ( $yyyymmdd =~ /$yyyymmdd_pattern/ ) {
               my ( $yyyy, $mm, $dd ) = ( $1, $2, $3 );
               if ( $last_holiday && $yyyymmdd <= $last_holiday ) {
                  croak
"$HolidaysCsv row $row_count item $item_count '$yyyymmdd' <= last one '$last_holiday', out of order";
               }

               $last_holiday = $yyyymmdd;
               $ref->{$yyyymmdd} = 1;
            } else {
               croak "$HolidaysCsv row $row_count item $item_count '$yyyymmdd'  bad format";
            }
         }

         last;
      }
   }

   close $fh;

   if ( !$ref ) {
      croak "no holiday information for exch=$exch in $HolidaysCsv";
   }

   $holidays_by_exch->{$exch}       = \@holidays;
   $exists_by_exch_holiday->{$exch} = $ref;

   #$opt->{verbose} && print STDERR "\$exists_by_exch_holiday->{$exch} = \n";
   #$opt->{verbose} && print STDERR Dumper($exists_by_exch_holiday->{$exch});

   $opt->{verbose} && print STDERR "\$holidays_by_exch->{$exch} = \n";
   $opt->{verbose} && print STDERR Dumper( $holidays_by_exch->{$exch} );

   return $exists_by_exch_holiday->{$exch};
}

sub is_holiday {
   my ( $exch, $day, $opt ) = @_;

   parse_holiday_csv( $exch, $opt );

   return $exists_by_exch_holiday->{$exch}->{$day};
}

sub get_tradeday {
   my ( $offset, $opt ) = @_;

   my $exch =
     exists( $opt->{Exch} ) && defined( $opt->{Exch} ) ? $opt->{Exch} : 'NYSE';

   my $begin;
   if ( $opt->{Begin} ) {
      $begin = $opt->{Begin};
   } else {
      my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) = localtime();
      $begin = sprintf( "%4d%02d%02d", 1900 + $year, $mon + 1, $mday );
   }

   return get_tradeday_by_exch_begin_offset( $exch, $begin, $offset, $opt );
}

sub get_tradedays {
   my ( $count, $opt ) = @_;

   my @tradedays;

   if ( $count > 0 ) {
      for ( my $i = 0 ; $i < $count ; $i++ ) {
         push @tradedays, get_tradeday( $i, $opt );
      }
   } elsif ( $count < 0 ) {
      for ( my $i = $count + 1 ; $i <= 0 ; $i++ ) {
         push @tradedays, get_tradeday( $i, $opt );
      }
   }
   return \@tradedays;
}

my $weekdays;

sub get_weekdays {
   if ( !$weekdays ) {
      # use TPSUP::DATE_Weekdays;
      # $weekdays = $TPSUP::DATE_Weekdays::weekdays;
      my $directory = get_perllib_dir();
      my $file      = "$directory/DATE_weekdays.txt";
      open my $fh, '<', $file or croak "can't open $file: $!";
      local $/ = undef;      # slurp mode. $/ is the input record separator
      my $string = <$fh>;    # read entire file
      close $fh;
      $weekdays = [ split /\s+/, $string ];
      # remove the last empty element
      pop @$weekdays;
   }

   return $weekdays;
}

my $tradeday_by_exch_begin_offset = {};

sub get_tradeday_by_exch_begin_offset {
   my ( $exch, $begin, $offset, $opt ) = @_;

   my $verbose = $opt->{verbose} || 0;

   return $tradeday_by_exch_begin_offset->{$exch}->{$begin}->{$offset}
     if exists $tradeday_by_exch_begin_offset->{$exch}->{$begin}->{$offset};

   # holidays are non-weekdays

   my $is_holiday;
   my $IgnoreHoliday;

   if ( $opt->{IgnoreHoliday} or $exch eq 'WeekDay' ) {
      $IgnoreHoliday = 1;
   } else {
      $is_holiday = parse_holiday_csv( $exch, $opt );
   }

   my $weekdays = get_weekdays();

   # if the binary search falls between two connective trade days, eg, on weekends
   my $InBetween = 'low';
   if ( $opt->{OnWeekend} && $opt->{OnWeekend} eq 'next' ) {
      $InBetween = 'high';
   }

   my $begin_weekday_pos = binary_search_match( $weekdays, $begin, sub { $_[0] <=> $_[1] },
      { InBetween => $InBetween, OutBound => 'Error' } );

   $verbose && print STDERR "begin_weekday=$weekdays->[$begin_weekday_pos]\n";

   if ($IgnoreHoliday) {
      # without taking holiday into account, we basically return a weekday
      return $weekdays->[ $begin_weekday_pos + $offset ];
   }

   # we haven't considered holidays yet. now we need to do that

   # first make sure the begin_weekday is not a holiday
   my $begin_tradeday_pos = $begin_weekday_pos;

   while ( $is_holiday->{ $weekdays->[$begin_tradeday_pos] } ) {
      if ( $opt->{OnWeekend} && $opt->{OnWeekend} eq 'next' ) {

         # OnWeekend flag affects both weekend and hoilday
         $begin_tradeday_pos++;
      } else {
         $begin_tradeday_pos--;
      }
   }

   # tradeday is a non-holiday weekday
   my $begin_tradeday = $weekdays->[$begin_tradeday_pos];
   $opt->{verbose} && print STDERR "begin_tradeday=$begin_tradeday\n";

   if ( $offset == 0 ) {

      # we only cache offset from a tradeday, as offset from weekend and holiday
      # can be affected by OnWeekend flag
      $tradeday_by_exch_begin_offset->{$exch}->{$begin_tradeday}->{$offset} =
        $begin_tradeday;
      return $begin_tradeday;
   } else {
      my $new_pos = $begin_tradeday_pos;

      if ( $offset > 0 ) {
         for ( my $i = 1 ; $i <= $offset ; $i++ ) {
            $new_pos++;
            while ( $is_holiday->{ $weekdays->[$new_pos] } ) {
               $new_pos++;
            }
         }
      } elsif ( $offset < 0 ) {
         for ( my $i = -1 ; $i >= $offset ; $i-- ) {
            $new_pos--;
            while ( $is_holiday->{ $weekdays->[$new_pos] } ) {
               $new_pos--;
            }
         }
      }

      my $new_tradeday = $weekdays->[$new_pos];

      # we only cache offset from a tradeday, as offset from weekend and holiday
      # can be affected by OnWeekend flag
      $tradeday_by_exch_begin_offset->{$exch}->{$begin_tradeday}->{$offset} =
        $new_tradeday;

      return $new_tradeday;
   }
}

sub get_holidays_by_exch_begin_end {
   my ( $exch, $begin, $end, $opt ) = @_;

   parse_holiday_csv( $exch, $opt );

   if (  !exists( $holidays_by_exch->{$exch} )
      || !defined( $holidays_by_exch->{$exch} ) )
   {
      croak "no holiday information for exch=$exch";
   }

   my $all_holidays = $holidays_by_exch->{$exch};

   my @holidays;
   my $begin_covered;
   my $end_covered;

   for my $d (@$all_holidays) {
      if ( $d >= $end ) {
         $end_covered++;

         if ( $d == $end ) {
            push @holidays, $d;
         }

         last;
      }

      if ( $d >= $begin ) {
         push @holidays, $d;
         if ( $d == $begin ) {
            $begin_covered++;
         }
      } else {
         $begin_covered++;
      }
   }

   if ( !$end_covered ) {
      warn "end=$end exceeded upper bound of '$exch' holidays ($all_holidays->[-1])";
   } elsif ( !$begin_covered ) {
      warn "begin=$begin exceeded lower bound of '$exch' holidays ($all_holidays->[0])";
   }

   return \@holidays;
}

sub yyyymmdd_to_DayOfWeek {
   my ( $yyyymmdd, $opt ) = @_;

   if ( "$yyyymmdd" =~ /$yyyymmdd_pattern/ ) {
      my ( $yyyy, $mm, $dd ) = ( $1, $2, $3 );

      # https://perldoc.perl.org/Time::Local
      #     The value for the day of the month is the actual day (i.e. 1..31), while
      #     the month is the number of months since January (0..11).
      #     timelocal( $sec, $min, $hour, $mday, $mon, $year );
      # i use 12pm instead of 0 am, to avoid daylight-saving-change causing +/- day
      my $seconds = timelocal( 0, 0, 12, $dd, $mm - 1, $yyyy );

      # https://perldoc.pl/functions/localtime
      # the month in the range 0..11, with 0 for January and 11 for December.
      my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) = localtime($seconds);

      # print "$mday,$mon,$year\n";

      return $wday;
   } else {
      croak "yyyymmdd='$yyyymmdd', bad format";
   }
}

my $seconds_between_two_days;

sub get_seconds_between_two_days {
   my ( $yyyymmdd1, $yyyymmdd2, $opt ) = @_;

   return 0 if $yyyymmdd1 == $yyyymmdd2;    # optimize

   # we use 12:00:00 instead of 00:00:00 to avoid daylight-saving-change causing +/- day

   if ( $opt->{IntervalDaysNoCaching} ) {
      $opt->{verbose} && print "no caching\n";
      my $seconds1 = yyyymmddHHMMSS_to_epoc("${yyyymmdd1}120000");
      my $seconds2 = yyyymmddHHMMSS_to_epoc("${yyyymmdd2}120000");
      return $seconds2 - $seconds1;
   } else {
      $opt->{verbose} && print "check caching key=yyyymmdd1,$yyyymmdd2\n";
      if ( !exists $seconds_between_two_days->{"$yyyymmdd1,$yyyymmdd2"} ) {
         my $seconds1 = yyyymmddHHMMSS_to_epoc("${yyyymmdd1}120000");
         my $seconds2 = yyyymmddHHMMSS_to_epoc("${yyyymmdd2}120000");
         $opt->{verbose} && print "seconds1=$seconds1, seconds2=$seconds2\n";
         $seconds_between_two_days->{"$yyyymmdd1,$yyyymmdd2"} = $seconds2 - $seconds1;
      }

      return $seconds_between_two_days->{"$yyyymmdd1,$yyyymmdd2"};
   }
}

sub get_interval_seconds {
   my ( $yyyymmdd1, $HHMMSS1, $yyyymmdd2, $HHMMSS2, $opt ) = @_;

   my $seconds;

   if ( $yyyymmdd1 && $yyyymmdd2 && $yyyymmdd1 != $yyyymmdd2 ) {

      # we use 12:00:00 instead of 00:00:00 to avoid daylight-saving-change causing +/- day
      #my $seconds1 = yyyymmddHHMMSS_to_epoc("${yyyymmdd1}120000");
      #my $seconds2 = yyyymmddHHMMSS_to_epoc("${yyyymmdd2}120000");
      #$seconds = $seconds2 - $seconds1;

      $seconds = get_seconds_between_two_days( $yyyymmdd1, $yyyymmdd2, $opt );
   }

   {
      my ( $HH1, $MM1, $SS1, $HH2, $MM2, $SS2 );

      #tian@linux1$ perl -e 'print "012" =~ /^[0-9]{3}$/ ? "true" : "false", "\n";'
      #true
      #tian@linux1$ perl -e 'print "012" =~ /^[0-9]{2}$/ ? "true" : "false", "\n";'
      #false

      if ( "$HHMMSS1" =~ /^([0-9]{2})([0-9]{2})([0-9]{2})$/ ) {
         ( $HH1, $MM1, $SS1 ) = ( $1, $2, $3 );
      } else {
         croak "HHMMSS1='$HHMMSS1' is in bad format";
      }

      if ( "$HHMMSS2" =~ /^([0-9]{2})([0-9]{2})([0-9]{2})$/ ) {
         ( $HH2, $MM2, $SS2 ) = ( $1, $2, $3 );
      } else {
         croak "HHMMSS2='$HHMMSS2' is in bad format";
      }

      $seconds +=
        ( $HH2 - $HH1 ) * 3600 + ( $MM2 - $MM1 ) * 60 + ( $SS2 - $SS1 );
   }

   return $seconds;
}

sub get_seconds_between_yyyymmddHHMMSS {
   my ( $yyyymmddHHMMSS1, $yyyymmddHHMMSS2, $opt ) = @_;

   # this supports a wider format

   my @s;
   for my $t1 ( ( $yyyymmddHHMMSS1, $yyyymmddHHMMSS2 ) ) {
      my $t2;
      if ( $t1 =~ /^([12][09]\d{12})(.*)/ ) {
         $t2 = $1;
      } elsif ( my @c = ( $t1 =~ /^([12][09]\d{2})([^\d])(\d{2})(.)(\d{2})(.)(\d{2})(.)(\d{2})(.)(\d{2})(.*)/ ) ) {
         $t2 = "$c[0]$c[2]$c[4]$c[6]$c[8]$c[10]";
      } else {
         confess "unsupported format at '$t1'";
      }

      my $sec = yyyymmddHHMMSS_to_epoc($t2);
      push @s, $sec;
   }

   return $s[1] - $s[0];
}

my $Mon_by_number = {
   1  => 'Jan',
   2  => 'Feb',
   3  => 'Mar',
   4  => 'Apr',
   5  => 'May',
   6  => 'Jun',
   7  => 'Jul',
   8  => 'Aug',
   9  => 'Sep',
   10 => 'Oct',
   11 => 'Nov',
   12 => 'Dec',

   '01' => 'Jan',
   '02' => 'Feb',
   '03' => 'Mar',
   '04' => 'Apr',
   '05' => 'May',
   '06' => 'Jun',
   '07' => 'Jul',
   '08' => 'Aug',
   '09' => 'Sep',
   '10' => 'Oct',
   '11' => 'Nov',
   '12' => 'Dec',
};

sub get_Mon_by_number {
   my ($number) = @_;
   return $Mon_by_number->{$number};
}

my $mm_by_Mon = {
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
};

sub get_mm_by_Mon {
   my ($Mon) = @_;

   return $mm_by_Mon->{$Mon};
}

sub convert_from_yyyymmdd {
   my ( $template, $yyyymmdd, $opt ) = @_;
   # template is like "$dd $Mon $yyyy"
   # 20161103 to 03 Nov 2016

   if ( $yyyymmdd =~ /^(\d{2})(\d{2})(\d{2})(\d{2})$/ ) {
      my ( $YY, $yy, $mm, $dd ) = ( $1, $2, $3, $4 );

      my $Mon = get_Mon_by_number($mm);

      my $d = "$dd";
      $d =~ s/^0//;

      my $m = "$mm";
      $m =~ s/^0//;

      my $yyyy = "$YY$yy";

      $opt->{verbose}
        && print STDERR "template=$template, YY=$YY, mm=$mm, m=$m, dd=$dd, d=$d, Mon=$Mon, yyyy=$yyyy\n";

      my $r = {
         YY   => $YY,
         mm   => $mm,
         m    => $m,
         dd   => $dd,
         d    => $d,
         Mon  => $Mon,
         yyyy => $yyyy,
      };

      # we could have used the current name space to evaluate the expression
      # but using TPSUP::Expression name space will allow use "no strict 'ref'"
      # and 'no warnings'

      TPSUP::Expression::export_var( $r, { RESET => 1 } );

      # 1. need to double-quote around $output_template to ake it an expression
      # 2. compile_exp has built-in cache to save from compiling twice
      my $compiled = TPSUP::Expression::compile_exp( qq("$template"), $opt );

      my $string = $compiled->($r);
      return $string;
   } else {
      carp "yyyymmdd='$yyyymmdd' is in bad format";
      return undef;
   }
}

sub get_tradedays_by_exch_begin_end {
   my ( $exch, $begin, $end, $opt ) = @_;

   my $exists_holiday = parse_holiday_csv( $exch, $opt );

   my $weekdays = get_weekdays();

   if ( $begin < $weekdays->[0] || $begin > $weekdays->[-1] ) {
      carp "begin day $begin is out of range: $weekdays->[0] ~ $weekdays->[-1]";
      return undef;
   }

   if ( $end < $weekdays->[0] || $end > $weekdays->[-1] ) {
      carp "end day $end is out of range: $weekdays->[0] ~ $weekdays->[-1]";
      return undef;
   }

   my @tradedays;

   for my $d (@$weekdays) {
      if ( $d < $begin ) {
         next;
      }

      if ( $exists_holiday->{$d} ) {
         next;
      }

      if ( $d > $end ) {
         last;
      }

      push @tradedays, $d;
   }

   return \@tradedays;
}

sub enrich_year {
   my ( $r, $opt ) = @_;

   my $r2 = {%$r};
   if ( $r->{yyyy} ) {
      $r2->{yy} = substr( $r->{yyyy}, 2, 2 );
      $r2->{YY} = substr( $r->{yyyy}, 0, 2 );
   } elsif ( $r->{YY} && $r->{yy} ) {
      $r2->{yyyy} = sprintf( "%d%d", $r->{YY}, $r->{yy} );
   } elsif ( $r->{yy} ) {
      if ( $r->{yy} >= 70 ) {
         $r2->{yyyy} = sprintf( "19%d", $r->{yy} );
         $r2->{YY}   = '19';
      } else {
         $r2->{yyyy} = sprintf( "20%d", $r->{yy} );
         $r2->{YY}   = '20';
      }
   } else {
      croak "no yyyy or yy in r=", Dumper;
   }

   return $r2;
}

sub enrich_month {
   my ( $r, $opt ) = @_;

   my $r2 = {%$r};
   if ( $r->{mm} ) {
      $r2->{m}   = $r->{mm};
      $r2->{Mon} = get_Mon_by_number( $r->{mm} );
   } elsif ( $r->{m} ) {
      $r2->{mm}  = sprintf( "%02d", $r->{m} );
      $r2->{Mon} = get_Mon_by_number( $r->{m} );
   } elsif ( $r->{Mon} ) {
      $r2->{mm} = get_mm_by_Mon( $r->{Mon} );
      $r2->{m}  = $r2->{mm};
   } else {
      croak "no mm or Mon in r=", Dumper;
   }

   return $r2;
}

sub enrich_day {
   my ( $r, $opt ) = @_;

   my $r2 = {%$r};
   if ( $r->{dd} ) {
      $r2->{d} = $r->{dd};
   } elsif ( $r->{d} ) {
      $r2->{dd} = sprintf( "%02d", $r->{d} );
   } else {
      croak "no dd or d in r=", Dumper;
   }

   return $r2;
}

sub enrich_yyyymmdd {
   my ( $r, $opt ) = @_;

   my $r2 = enrich_year( $r, $opt );
   $r2 = { %$r2, %{ enrich_month( $r, $opt ) } };
   $r2 = { %$r2, %{ enrich_day( $r, $opt ) } };

   return $r2;
}

sub date2any {
   my ( $date, $input_pattern, $input_assignment, $output_template, $opt ) = @_;

   my $verbose = $opt->{verbose} || 0;

   # test winter time, GMT-5=local
   # $ date -u; date; perl -e 'use TPSUP::DATE qw(/./);print date_template('date -u +%Y%m%d%S', "^(\\d{4})(\\d{2})(\\d{2})-(\\d{2}):(\\d{2}):(\\d{2})", "yyyy,mm,dd,HH,MM,SS", "sprintf(\"\$Mon-\$dd-\$yyyy,\$HH:\$MM:\$SS\")", {gmt21ocal=>1}), "\n";'
   # Thursday, January 19, 2017 11:32:10 PM GMT
   # Thursday, January 19, 2017 06:32:10 PM EST
   # Jan-19-2017,18:32:13

   # test summer time, GMT-4=local
   # $ perl -e 'use TPSUP::DATE qw(/./);print date_template("20160704-02:00:09", "^(\\d{4})(\\d{2})(\\d{2})-(\\d{2}):(\\d{2}):(\\d{2})", "yyyy,mm,dd,HH,MM,SS", "sprintf(\"\$Mon-\$dd-\$yyyy,\$HH:\$MM:\$SS\")", {gmt21ocal=>1, verbose=>l}), "\n";
   # compile exp='sprintf("$Mon-$dd-$yyyy,$HH:$MM:$SS")'
   # Jul-03-2016,22:00:09

   my @assignments = split /,/, $input_assignment;

   my @a = ( $date =~ /$input_pattern/ );

   if ( !@a ) {
      $opt->{verbose}
        && carp "date='$date' doesn't match pattern '$input_pattern'";
      return undef;
   }

   my $r;    # ref
   @{$r}{@assignments} = @a;

   # we need to ensure that we have mm, dd, yyyy, HH, MM
   # it is OK if we don't have SS, because timezone doesn't change it.
   $r = enrich_yyyymmdd( $r, $opt );

   $verbose && print STDERR "r=", Dumper($r);

   if ( $opt->{UTC2LOCAL} || $opt->{LOCAL2UTC} ) {
      # if there is a time zone conversion, we need to convert the date to epoc seconds

      # how to convert time zone
      # http://stackoverflow.com/questions/411740/
      if (  !exists $r->{mm}
         || !exists $r->{dd}
         || !exists $r->{yyyy}
         || !exists $r->{HH}
         || !exists $r->{MM} )
      {
         carp
"missing yyyy/mm/dd/HH/MM, date='$date', input_pattern='$input_pattern', input_assignment='$input_assignment'";
         return undef;
      }

      $r->{SS} = 0 if !exists $r->{SS};

      my $seconds;    # epoc seconds, not affected by time zone.
      my ( $sec, $min, $hour, $day, $mon, $year );
      if ( $opt->{UTC2LOCAL} ) {
         # UTC2LOCAL means from UTC. therefore, use timegm().
         $seconds = timegm( $r->{SS}, $r->{MM}, $r->{HH}, $r->{dd}, $r->{mm} - 1, $r->{yyyy} - 1900 );
         ( $sec, $min, $hour, $day, $mon, $year ) = localtime($seconds);
      } else {
         # LOCAL2UTC means from LOCAL. therefore, use timelocal().
         $seconds = timelocal( $r->{SS}, $r->{MM}, $r->{HH}, $r->{dd}, $r->{mm} - 1, $r->{yyyy} - 1900 );
         ( $sec, $min, $hour, $day, $mon, $year ) = gmtime($seconds);
      }

      $r->{SS}   = sprintf( "%02d", $sec );
      $r->{MM}   = sprintf( "%02d", $min );
      $r->{HH}   = sprintf( "%02d", $hour );
      $r->{dd}   = sprintf( "%02d", $day );
      $r->{mm}   = sprintf( "%02d", $mon + 1 );
      $r->{yyyy} = sprintf( "%d",   $year + 1900 );

      # enrich again, as we have changed mm, dd, yyyy, HH, MM, SS
      $r = enrich_yyyymmdd( $r, $opt );
   }

   # we could have used the current name space to evaluate the expression
   # but using TPSUP::Expression name space will allow use "no strict 'ref'"
   # and 'no warnings'

   TPSUP::Expression::export_var( $r, { RESET => 1 } );

   # 1. need to double-quote around $output_template to make it an expression
   # 2. compile_exp has built-in cache to save from compiling twice
   my $compiled = TPSUP::Expression::compile_exp( qq("$output_template"), $opt );

   return $compiled->();
}

sub main {
   use TPSUP::TEST qw(:DEFAULT);

   # use 'our' in test code, not 'my'
   my $test_code = <<'END';
      # get_date();
      # get_yyyymmdd();
      # yyyymmdd_to_DayOfWeek(get_yyyymmdd());
      # get_date( {yyyymmdd => '20200901'} )
      # get_yyyymmdd_by_yyyymmdd_offset('20200901', -1) == '20200831';
      # in(get_timezone_offset(), [-4, -5]);
      # is_holiday('NYSE', '20240101') == 1;
      # yyyymmddHHMMSS_to_epoc('20200901120000');
      # epoc_to_yyyymmddHHMMSS(1598976000);
      # yyyymmddHHMMSS_to_epoc('20200901120000', {fromUTC=>1});
      # epoc_to_yyyymmddHHMMSS(1598961600, {toUTC=>1});

      # yyyymmddHHMMSS_to_epoc([2020, 9, 1, 12, 0, 59]);
      # yyyymmddHHMMSS_to_epoc([2020, 9, 1, 12, 0, 59], {fromUTC=>1});
      # yyyymmddHHMMSS_to_epoc([2020, 9, 1, 12, 0, 59], {fromUTC=>1}) - yyyymmddHHMMSS_to_epoc([2020, 9, 1, 12, 0, 59]);

      # get_yyyymmddHHMMSS();
      # get_yyyymmddHHMMSS({toUTC=>1});

      # equal(get_holidays_by_exch_begin_end('NYSE', '20240101', '20240201'), ['20240101', '20240115']);
      #    # 2 holidays

      # # 20200907, Monday, is a holiday, labor day
      # get_tradeday_by_exch_begin_offset( 'NYSE', '20200901', 3 ) == '20200904';  # within the same week
      # get_tradeday_by_exch_begin_offset( 'NYSE', '20200904', -3 ) == '20200901';

      # get_tradeday_by_exch_begin_offset( 'NYSE', '20200901', 4 ) == '20200908';  # across the weekend and holiday
      # get_tradeday_by_exch_begin_offset( 'NYSE', '20200908', -4 ) == '20200901';

      # get_tradeday_by_exch_begin_offset( 'NYSE', '20200904', 0 ) == '20200904'; # 0 offset on a tradeday
      # get_tradeday_by_exch_begin_offset( 'NYSE', '20200905', 0 ) == '20200904'; # 0 offset on a weekend
      # get_tradeday_by_exch_begin_offset( 'NYSE', '20200907', 0,) == '20200904'; # 0 offset on a holiday

      # get_tradeday_by_exch_begin_offset( 'NYSE', '20200905', 0, {OnWeekend=>'next'}) == '20200908';
      # get_tradeday_by_exch_begin_offset( 'NYSE', '20200907', 0, {OnWeekend=>'next'}) == '20200908';

      # get_tradeday_by_exch_begin_offset( 'NYSE', '20200907', 1 ) == '20200908';
      # get_tradeday_by_exch_begin_offset( 'NYSE', '20200907', 1, {OnWeekend=>'next'}) == '20200909';

      # equal(get_tradedays_by_exch_begin_end( 'NYSE', '20200903', '20200907'), ['20200903', '20200904']);
      # equal(get_tradedays_by_exch_begin_end( 'NYSE', '20200903', '20200908'), ['20200903', '20200904', '20200908']);

      # get_tradeday( -4, { Begin => '20200908' } ) == '20200901';
      # get_tradeday(  4, { Begin => '20200901' } ) == '20200908';

      # equal(get_tradedays(  3, {Begin => '20200903'}),['20200903', '20200904', '20200908']);
      # equal(get_tradedays( -3, {Begin => '20200908'}),['20200903', '20200904', '20200908']);

      # # 20240310 is DST change day. we use 12:00 PM of each day
      # get_seconds_between_two_days('20240309', '20240310') == 82800;
      # get_seconds_between_two_days('20240311', '20240312') == 86400;

      # get_interval_seconds('20240309','120000','20240310','120001') == 82801;
      # get_interval_seconds('20240310','120000','20240311','120001') == 86401;

      # get_seconds_between_yyyymmddHHMMSS('2024-03-10 00:00:01.513447', '2024-03-10 03:00:01.000000') == 7200;
      # get_seconds_between_yyyymmddHHMMSS('2024-03-11 00:00:01.513447', '2024-03-11 03:00:01.000000') == 10800;

      # get_new_yyyymmddHHMMSS( '20211021070102', 300 ) eq '20211021070602';
      # get_new_yyyymmddHHMMSS( '2021-10-21 07:01:02.513447', 300 ) eq '2021-10-21 07:06:02.513447';

      # local_vs_utc( 'LOCAL2UTC', '2021-10-21 07:01:02.513447' ) eq '2021-10-21 11:01:02.513447';
      # local_vs_utc( 'UTC2LOCAL', '2021-10-21 07:01:02.513447' ) eq '2021-10-21 03:01:02.513447';
      convert_from_yyyymmdd( '$Mon-$dd-$yyyy', '20230901') eq 'Sep-01-2023';

      # TEST_BEGIN
      date2any('Sep 1 2023 12:34:56.789',
                '^(...)\s+(\\d{1,2}) (\\d{4}) (\\d{2}):(\\d{2}):(\\d{2})',
               'Mon,d,yyyy,HH,MM,SS', 
               '$yyyy-$mm-$dd,$HH $MM $SS'
      ) eq '2023-09-01,12 34 56';
      # TEST_END

END

   test_lines($test_code);

}

main() unless caller();

1
