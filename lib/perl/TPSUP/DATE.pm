package TPSUP::DATE;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   get_timezone_offset
   parse_holiday_csv
   is_holiday
   get_tradeday
   get_tradeday_by_exch_begin_offset
   get_holidays_by_exch_begin_end
   get_tradedays_by_exch_begin_end
   get_interval_seconds
   get_Mon_by_number
   get_mm_by_Mon
   convert_from_yyyymmdd
   date2any
   yyyymmddHHMMSS_to_epoc
   yyyymmdd_to_DayOfWeek
);

use Carp;
use Data::Dumper;
use TPSUP::CSV qw(parse_csv_file);
use TPSUP::UTIL qw(get_in_fh binary_search_numeric);
use Time::Local;
use File::Spec;
use POSIX;

my $yyyymmdd_pattern = qr/^(\d{4})(\d{2})(\d{2})$/;
my $yyyymmddHHMMSS_pattern = qr/^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$/;
my $whole_week_seconds = 7*24*60*60;

sub get_timezone_offset {
   my ($opt) = @_;

   # use Time::Local;
   my $local_sec = time();
   my @t = localtime($local_sec);
   my $gmt_offset_in_seconds = timegm(@t) - $local_sec;
   my $gmt_offset_in_hours = $gmt_offset_in_seconds/3600;

   return $gmt_offset_in_hours;
}


sub yyyymmddHHMMSS_to_epoc {
   my ($yyyymmddHHMMSS, $opt) = @_;

   my $type = ref $yyyymmddHHMMSS;

   if ($type eq 'ARRAY') {
      return timelocal(
         $yyyymmddHHMMSS->[5],    # SS
         $yyyymmddHHMMSS->[4],    # MM
         $yyyymmddHHMMSS->[3],    # HH
         $yyyymmddHHMMSS->[2],    # dd
         $yyyymmddHHMMSS->[1]-1,  # mm-1 
         $yyyymmddHHMMSS->[0],    # yyyy
      );
   } else {
      if ("$yyyymmddHHMMSS" =~ /$yyyymmddHHMMSS_pattern/) {
          my ($yyyy, $mm, $dd, $HH, $MM, $SS) = ($1, $2, $3, $4, $5, $6); 

          return timelocal($SS, $MM, $HH, $dd, $mm-1, $yyyy);
      } else {
          die "yyyymmddHHMMSS='$yyyymmddHHMMSS', bad format";
      }
   }
}


my $holidays_by_exch;
my $exists_by_exch_holiday;

sub parse_holiday_csv {
   my ($exch, $opt) = @_;

   croak "need to specify exch when calling parse_holiday_csv()" if ! $exch;

   return $exists_by_exch_holiday->{$exch} if exists $exists_by_exch_holiday->{$exch};

   if (exists($opt->{HolidayRef}) and defined($opt->{HolidayRef})) {
      $exists_by_exch_holiday->{$exch} = $opt->{HolidayRef};
      return $exists_by_exch_holiday->{$exch};
   }

   my $HolidaysCsv;
   if (exists($opt->{HolidaysCsv}) and defined($opt->{HolidaysCsv})) {
      $HolidaysCsv = $opt->{HolidaysCsv};
   } else {
      # https://stackoverflow.com/questions/2403343/in-perl-how-do-i-get-the-directory-or-path-of-the-current-executing-code
      my ($volume, $directory, $file) = File::Spec->splitpath(__FILE__);
      $directory = File::Spec->rel2abs($directory);
      # print "$volume, $directory, $file\n";
      $HolidaysCsv = "$directory/holidays.csv";
   }

   croak "$HolidaysCsv is not found" if ! -f $HolidaysCsv;

   # name,days
   # NYSE,20200101 20200120 20200217 20200410 20200525 20200703 20200907 20201126 20201125 20210101 20210118 20210402 20210531 20210705 20210906 20211125 20211224 20220101 20220117 20220221 20220415 20220530 20220704 20220905 20221124 20221126

   my $fh = get_in_fh($HolidaysCsv);

   my $row_count = 0;
   my @holidays;
   my $ref;

   while(<$fh>) {
      $row_count ++;

      if (/^$exch,(.+)/) {
         @holidays = map {int($_)} split(/\s+/, $1);

         my $item_count = 0;
         my $last_holiday;

         for my $yyyymmdd (@holidays) {
            $item_count ++;

            if ($yyyymmdd =~ /$yyyymmdd_pattern/) {
               my ($yyyy, $mm, $dd) = ($1, $2, $3);
               if ($last_holiday && $yyyymmdd <= $last_holiday ) {
                  die "$HolidaysCsv row $row_count item $item_count '$yyyymmdd' <= last one '$last_holiday', out of order";
               }

               $last_holiday = $yyyymmdd; 
               $ref->{$yyyymmdd} ++;
            } else {
               die "$HolidaysCsv row $row_count item $item_count '$yyyymmdd'  bad format";
            }
         }

         last;
      }
   }

   close $fh;

   $holidays_by_exch->{$exch}       = \@holidays;
   $exists_by_exch_holiday->{$exch} = $ref;

   #$opt->{verbose} && print STDERR "\$exists_by_exch_holiday->{$exch} = \n";
   #$opt->{verbose} && print STDERR Dumper($exists_by_exch_holiday->{$exch});

   $opt->{verbose} && print STDERR "\$holidays_by_exch->{$exch} = \n";
   $opt->{verbose} && print STDERR Dumper($holidays_by_exch->{$exch});

   return $exists_by_exch_holiday->{$exch};
}

      
sub is_holiday {
   my ($exch, $day, $opt) = @_;
      
   parse_holiday_csv($exch, $opt);
      
   return $exists_by_exch_holiday->{$exch}->{$day};
}


sub get_tradeday {
   my ($offset, $opt) = @_;

   my $exch  = exists($opt->{Exch}) && defined($opt->{Exch})  ? $opt->{Exch}  : 'NYSE';

   my $begin;
   if ($opt->{Begin}) {
      $begin = $opt->{Begin};
   } else {
      my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime();
      $begin = sprintf("%4d%02d%02d", 1900+$year, $mon+1, $mday);
   }

   return get_tradeday_by_exch_begin_offset($exch, $begin, $offset);
}
      
my $tradeday_by_exch_begin_offset;
my $weekdays;

sub get_tradeday_by_exch_begin_offset {
   my ($exch, $begin, $offset, $opt) = @_;

   return       $tradeday_by_exch_begin_offset->{$exch}->{$begin}->{$offset}
      if exists $tradeday_by_exch_begin_offset->{$exch}->{$begin}->{$offset};

   my $holiday_href;
   my $IgnoreHoliday;

   if ($opt->{IgnoreHoliday} or $exch eq 'WeekDay') {
      $IgnoreHoliday = 1;
   } else {
      $holiday_href = parse_holiday_csv($exch, $opt);
   }

   my $new_yyyymmdd;

   if (!$opt->{RegenerateWeekday}) {
      if (!$weekdays) {
         use TPSUP::DATE_Weekdays;
         $weekdays = $TPSUP::DATE_Weekdays::weekdays;
      }

      my $begin_pos = binary_search_numeric($begin, $weekdays, 0, scalar(@$weekdays)-1);

      $opt->{verbose} && print "begin_yyyymmdd = $weekdays->[$begin_pos]\n";

      $new_yyyymmdd = $weekdays->[$begin_pos + $offset];
   } else {
      my $whole_weeks    = POSIX::floor($offset/5);
      my $rest_tradedays = $offset%5;
   
      my $begin_DayOfWeek = yyyymmdd_to_DayOfWeek($begin);
      $opt->{verbose} && print STDERR "begin=$begin, begin_DayOfWeek = $begin_DayOfWeek\n";
   
      my $add_CalendarDays = 0;
      if ($begin_DayOfWeek >5) {
         # this is weekend
         $add_CalendarDays = 7-$begin_DayOfWeek+1;
      } elsif ($rest_tradedays + $begin_DayOfWeek > 5) {
         # this is run over weekends 
         $add_CalendarDays +=2;  
      }
      
      my $total_CalendarDays = ($whole_weeks*7) + $rest_tradedays + $add_CalendarDays;
      $opt->{verbose} && print STDERR "total_CalendarDays ",
            "= (\$whole_weeks*7) + \$rest_tradedays + \$add_CalendarDays", 
            "= ($whole_weeks*7) + $rest_tradedays + $add_CalendarDays", 
            "= $total_CalendarDays\n";
   
      my $total_CalendarDays_seconds = $total_CalendarDays*24*60*60;
   
      # we use 12:00:00 instead of 00:00:00 to avoid daylight-saving-change causing +/- day
      my $begin_epoc_seconds = yyyymmddHHMMSS_to_epoc("${begin}120000");
      my   $new_epoc_seconds = $begin_epoc_seconds + $total_CalendarDays_seconds;
      my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime($new_epoc_seconds);
      $new_yyyymmdd = sprintf("%4d%02d%02d", 1900+$year, $mon+1, $mday);
   }

   if ($IgnoreHoliday) {
      # without taking holiday into account, we basically return a weekday 
      return $new_yyyymmdd;
   }

   # we haven't considered holidays yet. now we need to do that

   my $holidays;
   my $sign;

   if ($offset >0) {
      $opt->{verbose} && print STDERR "get_holidays_by_exch_begin_end($exch, $begin, $new_yyyymmdd)\n";
      $holidays = get_holidays_by_exch_begin_end($exch, $begin, $new_yyyymmdd, $opt); 
      $sign = 1;
   } elsif ($offset <0) {
      $opt->{verbose} && print STDERR "get_holidays_by_exch_begin_end($exch, $new_yyyymmdd, $begin)\n";
      $holidays = get_holidays_by_exch_begin_end($exch, $new_yyyymmdd, $begin, $opt); 
      $sign = -1;
   } else { 
      # $offset == 0
      $holidays = get_holidays_by_exch_begin_end($exch, $new_yyyymmdd, $new_yyyymmdd, $opt); 
      $sign = 1;
   }

   my $holiday_count = scalar(@$holidays);

   if ($holiday_count) {
      # to avoid the same hoilday counted twice due to edge condition, introduce
      #  IgnoreEdgeHoliday flag
      # get_holidays_by_exch_begin_end(NYSE, 20200901, 20200907)
      # recursively calling get_tradeday_by_exch_begin_offset(NYSE, 20200907, 1*1)
      # get_holidays_by_exch_begin_end(NYSE, 20200907, 20200908)
      # recursively calling get_tradeday_by_exch_begin_offset(NYSE, 20200908, 1*1)
      # get_holidays_by_exch_begin_end(NYSE, 20200908, 20200909)
      # get_tradeday_by_exch_begin_offset('NYSE', '20200901', 4) = 20200909
      # should see 20200908

      # when IgnoreEdgeHoliday = -1,  ignore the end   holiday
      # when IgnoreEdgeHoliday =  1,  ignore the begin holiday
      # when IgnoreEdgeHoliday undef, count all holidays.

      # recursively call this function
      $opt->{verbose} && print STDERR "recursively calling get_tradeday_by_exch_begin_offset($exch, $new_yyyymmdd, $sign*$holiday_count)\n";

      my $afterAdjustedHoliday_yyyymmdd = 
          get_tradeday_by_exch_begin_offset($exch, $new_yyyymmdd, $sign*$holiday_count, 
                                            {%$opt, IgnoreEdgeHoliday=>$sign});  
      $tradeday_by_exch_begin_offset->{$exch}->{$begin}->{$offset} = 
         $afterAdjustedHoliday_yyyymmdd;
      return $afterAdjustedHoliday_yyyymmdd;
   } else {
      if (!$opt->{IgnoreEdgeHoliday}) {
         # IgnoreEdgeHoliday distorted the 'absolute' offset, therefore, don't cache it.
         # cache it only when IgnoreEdgeHoliday is not set
         $tradeday_by_exch_begin_offset->{$exch}->{$begin}->{$offset} = $new_yyyymmdd;
      }
      return $new_yyyymmdd;
   }
}


sub get_holidays_by_exch_begin_end {
   my ($exch, $begin, $end, $opt) = @_;

   parse_holiday_csv($exch, $opt);

   if (!exists($holidays_by_exch->{$exch}) || !defined($holidays_by_exch->{$exch})) {
      die "no holiday information for exch=$exch";
   }

   my $all_holidays = $holidays_by_exch->{$exch};

   my @holidays;
   my $begin_covered;
   my $end_covered;

   for my $d (@$all_holidays) {
      if ($d >= $end ) {
         $end_covered ++;
         if ( $d == $end ) {
            if (!$opt->{IgnoreEdgeHoliday} || $opt->{IgnoreEdgeHoliday} != -1) {
               push @holidays, $d; 
            }
         }
         last;
      }

      if ( $d > $begin ) {
         push @holidays, $d; 
      } else {
         # $d <= $begin 
         $begin_covered ++;
         if ( $d == $begin) {
            if (!$opt->{IgnoreEdgeHoliday} || $opt->{IgnoreEdgeHoliday} != 1) {
               push @holidays, $d; 
            }
         }
      }
   }

   if (!$end_covered) {
      warn "end=$end exceeded upper range of '$exch' holidays ($all_holidays->[-1])" 
   } elsif (!$begin_covered) {
      warn "begin=$begin exceeded lower range of '$exch' holidays ($all_holidays->[0])" 
   }

   return \@holidays;
}


sub yyyymmdd_to_DayOfWeek {
   my ($yyyymmdd, $opt) = @_;

   if ("$yyyymmdd" =~ /$yyyymmdd_pattern/) {
      my ($yyyy, $mm, $dd) = ($1, $2, $3); 

      # https://perldoc.perl.org/Time::Local
      #     The value for the day of the month is the actual day (i.e. 1..31), while
      #     the month is the number of months since January (0..11). 
      #     timelocal( $sec, $min, $hour, $mday, $mon, $year );
      # i use 12pm instead of 0 am, to avoid daylight-saving-change causing +/- day
      my $seconds = timelocal(0, 0, 12, $dd, $mm-1, $yyyy);

      # https://perldoc.pl/functions/localtime
      # the month in the range 0..11, with 0 for January and 11 for December.
      my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime($seconds);

      # print "$mday,$mon,$year\n";

      return $wday;
   } else {
       die "yyyymmdd='$yyyymmdd', bad format";
   }
}


sub get_interval_seconds {
   my ($yyyymmdd1, $HHMMSS1, $yyyymmdd2, $HHMMSS2, $opt) = @_;
      
   my $seconds;
      
   if ($yyyymmdd1 && $yyyymmdd2 && $yyyymmdd1 != $yyyymmdd2) {
      # we use 12:00:00 instead of 00:00:00 to avoid daylight-saving-change causing +/- day
      my $seconds1 = yyyymmddHHMMSS_to_epoc("${yyyymmdd1}120000");
      my $seconds2 = yyyymmddHHMMSS_to_epoc("${yyyymmdd2}120000");

      $seconds = $seconds2 - $seconds1;
   }
      
   {
      my ($HH1, $MM1, $SS1, $HH2, $MM2, $SS2);
      #tian@linux1$ perl -e 'print "012" =~ /^[0-9]{3}$/ ? "true" : "false", "\n";'
      #true
      #tian@linux1$ perl -e 'print "012" =~ /^[0-9]{2}$/ ? "true" : "false", "\n";'
      #false

      if ("$HHMMSS1" =~ /^([0-9]{2})([0-9]{2})([0-9]{2})$/) {
         ($HH1, $MM1, $SS1) = ($1, $2, $3);
      } else {
         croak "HHMMSS1='$HHMMSS1' is in bad format";
      }
         
      if ("$HHMMSS2" =~ /^([0-9]{2})([0-9]{2})([0-9]{2})$/) {
         ($HH2, $MM2, $SS2) = ($1, $2, $3);
      } else {
         croak "HHMMSS2='$HHMMSS2' is in bad format";
      }
      
      $seconds += ($HH2-$HH1)*3600 + ($MM2-$MM1)*60 + ($SS2-$SS1);
   }
      
   return $seconds;
}
      

my $Mon_by_number;
      
sub get_Mon_by_number {
   my ($number) = @_;
      
   if (!$Mon_by_number) {
      $Mon_by_number = {
            1 => 'Jan',
            2 => 'Feb',
            3 => 'Mar',
            4 => 'Apr',
            5 => 'May',
            6 => 'Jun',
            7 => 'Jul',
            8 => 'Aug',
            9 => 'Sep',
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
         
   if (!$mm_by_Mon) {
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
   my ($template, $yyyymmdd, $opt) = @_;
         
   # 20161103 to 03 Nov 2016

   if ($yyyymmdd =~ /^(\d{2})(\d{2})(\d{2})(\d{2})$/) {
      my ($YY, $yy, $mm, $dd) = ($1, $2, $3, $4);
         
      my $Mon = get_Mon_by_number($mm);
         
      my $d = "$dd"; $d =~ s/^0//;

      my $m = "$mm"; $m =~ s/^0//;
         
      my $yyyy = "$YY$yy";
         
      $opt->{verbose} && print STDERR "template=$template, YY=$YY, mm=$mm, m=$m, dd=$dd, d=$d, Mon=$Mon, yyyy=$yyyy\n";
         
      eval "return qq($template)";
   } else {
      carp "yyyymmdd='$yyyymmdd' is in bad format";
      return undef;
   }
}
   
sub get_tradedays_by_exch_begin_end {
   my ($exch, $begin, $end, $opt) = @_;

   my $exists_holiday = parse_holiday_csv($exch, $opt);

   use TPSUP::DATE_Weekdays;

   my $weekdays = $TPSUP::DATE_Weekdays::weekdays;

   if ($begin < $weekdays->[0] || $begin > $weekdays->[-1]) {
      carp "begin day $begin is out of range: $weekdays->[0] ~ $weekdays->[-1]";
      return undef;
   }

   if ($end < $weekdays->[0] || $end > $weekdays->[-1]) {
      carp "end day $end is out of range: $weekdays->[0] ~ $weekdays->[-1]";
      return undef;
   }

   my @tradedays;

   for my $d (@$weekdays) {
      if ( $d < $begin ) {
         next;
      }

      if ($exists_holiday->{$d}) {
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
   my ($date, $input_pattern, $input_assignment, $output_template, $opt) = @_;

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

   my @a = ($date =~ /$input_pattern/);
         
   if (!@a) {
      $opt->{verbose} && carp "date='$date' doesn't match pattern '$input_pattern'";
      return undef;
   }
         
   my $r; # ref
   @{$r}{@assignments} = @a;
         
   if (!$r->{dd}) {
      if ($r->{d}) {
         $r->{dd} = sprintf("%02d", $r->{d});
      }
   }
         
   if (!$r->{mm}) {
      if ($r->{m}) {
         $r->{mm} =sprintf("%02d", $r->{m});
      } elsif ($r->{Mon}) {
         $r->{mm} = get_mm_by_Mon($r->{Mon});
      }
   }
         
   my $converted_r;
         
   if ($opt->{gmt21ocal}) {
      # http://stackoverflow.com/questions/411740/how-can-i-parse-dates-and-convert-time-zones-in-perl
      if (!exists $r->{mm} || !exists $r->{dd} || !exists $r->{yyyy} ||!exists $r->{HH}) {
         carp "missing yyyy/mm/dd/HH, cannot do gmt21ocal. date='$date', input_pattern='$input_pattern', input_assignment='$input_assignment'";
         return undef;
      }
         
      $r->{MM} - 0 if !exists $r->{MM};
      $r->{SS} = 0 if !exists $r->{SS};
         
      my $gmt_seconds
         =timegm($r->{SS}, $r->{MM}, $r->{HH}, $r->{dd}, $r->{mm}-1, $r->{yyyy}-1900);
         
      my ($sec, $min, $hour, $day, $mon, $year) = localtime($gmt_seconds);
         
      $converted_r->{SS} = sprintf("%02d", $sec);
      $converted_r->{MM} - sprintf("%02d", $min);
      $converted_r->{HH} = sprintf("%02d", $hour);
      $converted_r->{dd} = sprintf("%02d", $day);
      $converted_r->{mm} = sprintf("%02d", $mon+1);
      $converted_r->{yyyy} = sprintf("%d", $year+1900);
   } else {
      $converted_r = $r;
   }
         
   if (defined $converted_r->{yyyy}) {
      if (!defined $converted_r->{yy}) {
         if ( "$converted_r->{yyyy}" =~ /^\d{2}(\d{2})/) {
            $converted_r->{yy} = "$1";
         }
      }
   }
         
   if (defined $converted_r->{mm}) {
      if (!defined $converted_r->{m}) {
         my $m = $converted_r->{mm};
         $m =~ s/^0//;
         $converted_r->{m} = $m;
      }
         
      if (!defined $converted_r->{Mon}) {
         $converted_r->{Mon} = get_Mon_by_number($converted_r->{mm});
      }
   }
         
   if (defined $converted_r->{dd}) {
      if (!defined $converted_r->{d}) {
         my $d = $converted_r->{dd};
         $d =~ s/^0//;
         $converted_r->{d} = $d;
      }
   }
         
   # we could have used the current name space to evaluate the expression
   # but using TPSUP::Expression name space will allow use "no strict 'ref'"
   # and 'no warnings'
         
   TPSUP::Expression::export_var( $converted_r, {RESET=>1});
         
   my $compiled = TPSUP::Expression::compile_exp($output_template, $opt);
   return $compiled->();
}


sub main {
   print "get_timezone_offset() = ", get_timezone_offset(), "\n\n";

   print "get_interval_seconds('20200901', '120000', '20200902', '120001') = ", 
          get_interval_seconds('20200901', '120000', '20200902', '120001'),
         ", expecting 86401\n\n";

   my $verbose = 0;

   print "get_tradeday_by_exch_begin_offset('NYSE', '20200901', 3) = ", 
          get_tradeday_by_exch_begin_offset('NYSE', '20200901', 3, {verbose=>$verbose}),
         ", expecting 20200904\n\n";

   print "get_tradeday_by_exch_begin_offset('NYSE', '20200901', 4) = ",
          get_tradeday_by_exch_begin_offset('NYSE', '20200901', 4, {verbose=>$verbose}),
         ", expecting 20200908\n\n";

   print "get_tradeday_by_exch_begin_offset('WeekDay', '20200901', 4) = ",
          get_tradeday_by_exch_begin_offset('WeekDay', '20200901', 4, {verbose=>$verbose}),
         ", expecting 20200907\n\n";
          "\n";

   print "get_tradeday_by_exch_begin_offset('NYSE', '20200908', -4) = ",
          get_tradeday_by_exch_begin_offset('NYSE', '20200908', -4, {verbose=>$verbose}),
         ", expecting 20200901\n\n";
          "\n";

   print "get_tradeday_by_exch_begin_offset('NYSE', '20200904', -3) = ",
          get_tradeday_by_exch_begin_offset('NYSE', '20200904', -3, {verbose=>$verbose}),
         ", expecting 20200901\n\n";
          "\n";

   print "get_tradeday_by_exch_begin_offset('NYSE', '20200904', 0) = ",
          get_tradeday_by_exch_begin_offset('NYSE', '20200904', 0, {verbose=>$verbose}),
         ", expecting 20200904\n\n";
          "\n";

   print "get_tradeday_by_exch_begin_offset('NYSE', '20200905', 0) = ",
          get_tradeday_by_exch_begin_offset('NYSE', '20200905', 0, {verbose=>$verbose}),
         ", expecting 20200908\n\n";
          "\n";

   print "get_tradeday_by_exch_begin_offset('NYSE', '20200907', 0) = ",
          get_tradeday_by_exch_begin_offset('NYSE', '20200907', 0, {verbose=>$verbose}),
         ", expecting 20200908\n\n";
          "\n";

   $verbose && print "\$tradeday_by_exch_begin_offset->{NYSE} = \n";
   $verbose && print Dumper($tradeday_by_exch_begin_offset->{NYSE});

   print "get_tradeday_by_exch_begin_offset('NYSE', '20200907', 1) = ",
          get_tradeday_by_exch_begin_offset('NYSE', '20200907', 1, {verbose=>$verbose}),
         ", expecting 20200909\n\n";
          "\n";

   print "get_tradedays_by_exch_begin_end('NYSE', '20200901', '20200907') = ",
          join(",", 
        @{get_tradedays_by_exch_begin_end('NYSE', '20200901', '20200907', {verbose=>$verbose})}), 
         ", expecting 4 days\n\n";
          "\n";

   print "get_tradedays_by_exch_begin_end('NYSE', '20200901', '20200908') = ",
          join(",", 
        @{get_tradedays_by_exch_begin_end('NYSE', '20200901', '20200908', {verbose=>$verbose})}), 
          ", expecting 5 days\n\n";
          "\n";

   print "get_tradeday(-4, {Begin=>'20200908'}) = ",
          get_tradeday(-4, {Begin=>'20200908', verbose=>$verbose}),
         ", expecting 20200901\n\n";
          "\n";
}

main() unless caller();

1
