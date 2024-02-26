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
  get_interval_seconds                    # this only supports strict yyyymmddHHMMSS
  get_seconds_between_yyyymmddHHMMSS

  # this supports wider format
  get_seconds_between_two_days
  get_Mon_by_number
  get_mm_by_
  Mon
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
      if ( $opt->{IsUTC} ) {
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

         if ( $opt->{IsUTC} ) {
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

   my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) = localtime($epoc);
   my $yyyymmddHHMMSS = sprintf( '%4d%02d%02d%02d%02d%02d', 1900 + $year, $mon + 1, $mday, $hour, $min, $sec, );

   return $yyyymmddHHMMSS;
}

sub get_yyyymmddHHMMSS {
   my ($opt)          = @_;
   my $now_sec        = time();
   my $yyyymmddHHMMSS = epoc_to_yyyymmddHHMMSS($now_sec);
   return $yyyymmddHHMMSS;
}

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

   my $OldIsUTC;
   $OldIsUTC++ if $direction eq 'UTC2LOCAL';

   my $old_sec = yyyymmddHHMMSS_to_epoc( $old_t, { IsUTC => $OldIsUTC } );

   if ($OldIsUTC) {
      my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) = localtime($old_sec);
      return sprintf( $out_format, 1900 + $year, $mon + 1, $mday, $hour, $min, $sec );
   } else {
      my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) = gmtime($old_sec);
      return sprintf( $out_format, 1900 + $year, $mon + 1, $mday, $hour, $min, $sec );
   }
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

      # https://stackoverflow.com/questions/2403343/in-perl-how-do-i-get-the-directory-or-path-of-the-current-executing-code
      my ( $volume, $directory, $file ) = File::Spec->splitpath(__FILE__);
      $directory = File::Spec->rel2abs($directory);

      # print "$volume, $directory, $file\n";
      $HolidaysCsv = "$directory/holidays.csv";
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
      for ( my $i = 1 ; $i <= $count ; $i++ ) {
         push @tradedays, get_tradeday( $i, $opt );
      }
   } elsif ( $count < 0 ) {
      for ( my $i = $count ; $i <= -1 ; $i++ ) {
         push @tradedays, get_tradeday( $i, $opt );
      }
   }
   return \@tradedays;
}

my $tradeday_by_exch_begin_offset;
my $weekdays;

sub get_tradeday_by_exch_begin_offset {
   my ( $exch, $begin, $offset, $opt ) = @_;

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

   if ( !$weekdays ) {
      use TPSUP::DATE_Weekdays;
      $weekdays = $TPSUP::DATE_Weekdays::weekdays;
   }

   # if the binary search falls between two connective trade days, eg, on weekends
   # my $ChooseBigger = undef;
   my $InBetween = 'low';
   if ( $opt->{OnWeekend} && $opt->{OnWeekend} eq 'next' ) {
      # $ChooseBigger = 'ChooseBigger';
      $InBetween = 'high';
   }

   my $begin_weekday_pos = binary_search_match( $weekdays, $begin, sub { $_[0] <=> $_[1] },
      { InBetween => $InBetween, OutBound => 'Error' } );
   my $begin_weekday = $weekdays->[$begin_weekday_pos];
   $opt->{verbose} && print "begin_weekday=$begin_weekday\n";

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
   $opt->{verbose} && print "begin_tradeday=$begin_tradeday\n";

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
      warn "end=$end exceeded upper range of '$exch' holidays ($all_holidays->[-1])";
   } elsif ( !$begin_covered ) {
      warn "begin=$begin exceeded lower range of '$exch' holidays ($all_holidays->[0])";
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

my $Mon_by_number;

sub get_Mon_by_number {
   my ($number) = @_;

   if ( !$Mon_by_number ) {
      $Mon_by_number = {
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
      };
   }

   return $Mon_by_number->{$number};
}

my $mm_by_Mon;

sub get_mm_by_Mon {
   my ($Mon) = @_;

   if ( !$mm_by_Mon ) {
      $mm_by_Mon = {
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
   }

   return $mm_by_Mon->{$Mon};
}

sub convert_from_yyyymmdd {
   my ( $template, $yyyymmdd, $opt ) = @_;

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

      eval "return qq($template)";
   } else {
      carp "yyyymmdd='$yyyymmdd' is in bad format";
      return undef;
   }
}

sub get_tradedays_by_exch_begin_end {
   my ( $exch, $begin, $end, $opt ) = @_;

   my $exists_holiday = parse_holiday_csv( $exch, $opt );

   use TPSUP::DATE_Weekdays;

   my $weekdays = $TPSUP::DATE_Weekdays::weekdays;

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

sub date2any {
   my ( $date, $input_pattern, $input_assignment, $output_template, $opt ) = @_;

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

   if ( !$r->{dd} ) {
      if ( $r->{d} ) {
         $r->{dd} = sprintf( "%02d", $r->{d} );
      }
   }

   if ( !$r->{mm} ) {
      if ( $r->{m} ) {
         $r->{mm} = sprintf( "%02d", $r->{m} );
      } elsif ( $r->{Mon} ) {
         $r->{mm} = get_mm_by_Mon( $r->{Mon} );
      }
   }

   my $converted_r;

   if ( $opt->{gmt21ocal} ) {

      # http://stackoverflow.com/questions/411740/how-can-i-parse-dates-and-convert-time-zones-in-perl
      if (  !exists $r->{mm}
         || !exists $r->{dd}
         || !exists $r->{yyyy}
         || !exists $r->{HH} )
      {
         carp
"missing yyyy/mm/dd/HH, cannot do gmt21ocal. date='$date', input_pattern='$input_pattern', input_assignment='$input_assignment'";
         return undef;
      }

      $r->{MM} - 0 if !exists $r->{MM};
      $r->{SS} = 0 if !exists $r->{SS};

      my $gmt_seconds = timegm( $r->{SS}, $r->{MM}, $r->{HH}, $r->{dd}, $r->{mm} - 1, $r->{yyyy} - 1900 );

      my ( $sec, $min, $hour, $day, $mon, $year ) = localtime($gmt_seconds);

      $converted_r->{SS}   = sprintf( "%02d", $sec );
      $converted_r->{MM}   = sprintf( "%02d", $min );
      $converted_r->{HH}   = sprintf( "%02d", $hour );
      $converted_r->{dd}   = sprintf( "%02d", $day );
      $converted_r->{mm}   = sprintf( "%02d", $mon + 1 );
      $converted_r->{yyyy} = sprintf( "%d",   $year + 1900 );
   } else {
      $converted_r = $r;
   }

   if ( defined $converted_r->{yyyy} ) {
      if ( !defined $converted_r->{yy} ) {
         if ( "$converted_r->{yyyy}" =~ /^\d{2}(\d{2})/ ) {
            $converted_r->{yy} = "$1";
         }
      }
   }

   if ( defined $converted_r->{mm} ) {
      if ( !defined $converted_r->{m} ) {
         my $m = $converted_r->{mm};
         $m =~ s/^0//;
         $converted_r->{m} = $m;
      }

      if ( !defined $converted_r->{Mon} ) {
         $converted_r->{Mon} = get_Mon_by_number( $converted_r->{mm} );
      }
   }

   if ( defined $converted_r->{dd} ) {
      if ( !defined $converted_r->{d} ) {
         my $d = $converted_r->{dd};
         $d =~ s/^0//;
         $converted_r->{d} = $d;
      }
   }

   # we could have used the current name space to evaluate the expression
   # but using TPSUP::Expression name space will allow use "no strict 'ref'"
   # and 'no warnings'

   TPSUP::Expression::export_var( $converted_r, { RESET => 1 } );

   my $compiled = TPSUP::Expression::compile_exp( $output_template, $opt );
   return $compiled->();
}

sub main {
   require TPSUP::TEST;

   # use 'our' in test code, not 'my'
   my $test_code = <<'END';
         TPSUP::DATE::get_date();
         TPSUP::DATE::get_yyyymmdd();
         TPSUP::DATE::yyyymmdd_to_DayOfWeek(TPSUP::DATE::get_yyyymmdd());
         TPSUP::DATE::get_date( {yyyymmdd => '20200901'} )
         TPSUP::DATE::get_yyyymmdd_by_yyyymmdd_offset('20200901', -1) == '20200831';
         TPSUP::DATE::get_timezone_offset();
         TPSUP::DATE::is_holiday('NYSE', '20240101') == 1;
END

   TPSUP::TEST::test_lines($test_code);

   exit(0);

   print "get_interval_seconds('20200901', '120000', '20200902', '120001') = ",
     get_interval_seconds( '20200901', '120000', '20200902', '120001' ),
     ", expecting 86401\n\n";

   my $verbose = 0;

   print "get_tradeday_by_exch_begin_offset('NYSE', '20200901', 3) = ",
     get_tradeday_by_exch_begin_offset( 'NYSE', '20200901', 3, { verbose => $verbose } ),
     ", expecting 20200904\n\n";

   print "get_tradeday_by_exch_begin_offset('NYSE', '20200901', 4) = ",
     get_tradeday_by_exch_begin_offset( 'NYSE', '20200901', 4, { verbose => $verbose } ),
     ", expecting 20200908\n\n";

   print "get_tradeday_by_exch_begin_offset('WeekDay', '20200901', 4) = ",
     get_tradeday_by_exch_begin_offset( 'WeekDay', '20200901', 4, { verbose => $verbose } ),
     ", expecting 20200907\n\n";
   "\n";

   print "get_tradeday_by_exch_begin_offset('NYSE', '20200908', -4) = ",
     get_tradeday_by_exch_begin_offset( 'NYSE', '20200908', -4, { verbose => $verbose } ),
     ", expecting 20200901\n\n";
   "\n";

   print "get_tradeday_by_exch_begin_offset('NYSE', '20200904', -3) = ",
     get_tradeday_by_exch_begin_offset( 'NYSE', '20200904', -3, { verbose => $verbose } ),
     ", expecting 20200901\n\n";
   "\n";

   print "get_tradeday_by_exch_begin_offset('NYSE', '20200904', 0) = ",
     get_tradeday_by_exch_begin_offset( 'NYSE', '20200904', 0, { verbose => $verbose } ),
     ", expecting 20200904\n\n";
   "\n";

   print "get_tradeday_by_exch_begin_offset('NYSE', '20200905', 0) = ",
     get_tradeday_by_exch_begin_offset( 'NYSE', '20200905', 0, { verbose => $verbose } ),
     ", expecting 20200904\n\n";
   "\n";

   print
     "get_tradeday_by_exch_begin_offset('NYSE', '20200905', 0, {OnWeekend=>'next'}) = ",
     get_tradeday_by_exch_begin_offset( 'NYSE', '20200905', 0, { OnWeekend => 'next', verbose => $verbose } ),
     ", expecting 20200908\n\n";
   "\n";

   print "get_tradeday_by_exch_begin_offset('NYSE', '20200907', 0) = ",
     get_tradeday_by_exch_begin_offset( 'NYSE', '20200907', 0, { verbose => $verbose } ),
     ", expecting 20200904\n\n";
   "\n";

   print
     "get_tradeday_by_exch_begin_offset('NYSE', '20200907', 0, {OnWeekend=>'next'}) = ",
     get_tradeday_by_exch_begin_offset( 'NYSE', '20200907', 0, { OnWeekend => 'next', verbose => $verbose } ),
     ", expecting 20200908\n\n";
   "\n";

   $verbose && print "\$tradeday_by_exch_begin_offset->{NYSE} = \n";
   $verbose && print Dumper( $tradeday_by_exch_begin_offset->{NYSE} );

   print "get_tradeday_by_exch_begin_offset('NYSE', '20200907', 1) = ",
     get_tradeday_by_exch_begin_offset( 'NYSE', '20200907', 1, { verbose => $verbose } ),
     ", expecting 20200908\n\n";
   "\n";

   print
     "get_tradeday_by_exch_begin_offset('NYSE', '20200907', 1, {OnWeekend=>'next'}) = ",
     get_tradeday_by_exch_begin_offset( 'NYSE', '20200907', 1, { OnWeekend => 'next', verbose => $verbose } ),
     ", expecting 20200909\n\n";
   "\n";

   print "get_tradedays_by_exch_begin_end('NYSE', '20200901', '20200907') = ",
     join( ",", @{ get_tradedays_by_exch_begin_end( 'NYSE', '20200901', '20200907', { verbose => $verbose } ) } ),
     ", expecting 4 days\n\n";
   "\n";

   print "get_tradedays_by_exch_begin_end('NYSE', '20200901', '20200908') = ",
     join( ",", @{ get_tradedays_by_exch_begin_end( 'NYSE', '20200901', '20200908', { verbose => $verbose } ) } ),
     ", expecting 5 days\n\n";
   "\n";

   print "get_tradeday(-4, {Begin=>'20200908'}) = ",
     get_tradeday( -4, { Begin => '20200908', verbose => $verbose } ),
     ", expecting 20200901\n\n";
   "\n";

   print "get_seconds_between_two_days('20210917', '20210918') = ",
     get_seconds_between_two_days( '20210917', '20210918', { verbose => $verbose } ),
     ", expecting 86400\n\n";
   "\n";

   print "get_new_yyyymmddHHMMSS('20211021070102', 300) = ",
     get_new_yyyymmddHHMMSS( '20211021070102', 300 ),
     ", expecting 20211021070602\n\n";
   "\n";

   print "get_new_yyyymmddHHMMSS('2021-10-21 07:01:02.513447', 300) = ",
     get_new_yyyymmddHHMMSS( '2021-10-21 07:01:02.513447', 300 ),
     ", expecting 2021-10-21 07:06:02.513447\n\n";
   "\n";

   print "local_vs_utc('LOCAL2UTC', '2021-10-21 07:01:02.513447') = ",
     local_vs_utc( 'LOCAL2UTC', '2021-10-21 07:01:02.513447' ),
     ", expecting 2021-10-21 11:01:02.513447\n\n";
   "\n";

   print "local_vs_utc('UTC2LOCAL', '2021-10-21 07:01:02.513447') = ",
     local_vs_utc( 'UTC2LOCAL', '2021-10-21 07:01:02.513447' ),
     ", expecting 2021-10-21 03:01:02.513447\n\n";
   "\n";

   print
     "get_seconds_between_yyyymmddHHMMSS('2021-10-21 07:01:02.513447', '2021-10-21 03:01:02.000000') = ",
     get_seconds_between_yyyymmddHHMMSS( '2021-10-21 07:01:02.513447', '2021-10-21 03:01:02.000000' ),
     ", expecting 600\n\n";
   "\n";
}

main() unless caller();

1
