package TPSUP::DATE;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   parse_holiday_csv
   is_holiday
   get_tradeday_by_exch_start_offset
   get_tradedays_by_exch_start_end
   get_interval_seconds
   get_Mon_by_number
   get_mm_by_Mon
   convert_from_yyyymmdd
   date2any
   yyyymmddHHMMSS_to_epoc
);

use Carp;
use Data::Dumper;
use TPSUP::CSV qw(parse_csv_file);
use Time::Local;


sub yyyymmddHHMMSS_to_epoc {
   my ($yyyymmddHHMMSS, $opt) = @_;

   if ("$yyyymmddHHMMSS" =~ /^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$/) {
      my ($yyyy, $mm, $dd, $HH, $MM, $SS) = ($1, $2, $3, $4, $5, $6); 

      return timelocal($SS, $MM, $HH, $dd, $mm-1, $yyyy);
   } else {
      die "yyyymmddHHMMSS='$yyyymmddHHMMSS', bad format";
   }
}


my $exists_by_exch_holiday;

sub parse_holiday_csv {
   my ($exch, $opt) = @_;
      
   croak "need to specify exch when calling parse_holiday_csv()" if ! $exch;
      
   return $exists_by_exch_holiday->{$exch} if exists $exists_by_exch_holiday->{$exch};
      
   die "TPSUP is not defined in shell" if !$ENV{TPSUP};
      
   my $base = $ENV{TPSUP};
      
   my $file = "$ENV{TPSUP}/lib/etc/hoilday.$exch.csv";
      
   die "cannot find $file" if ! -f $file;
      
   my $exists_holiday = parse_csv_file($file, {keyColumn=>'HOLIDAY_DATE'});
      
   #HOLIDAY_DATE,HOLIDAY_DESCPsIPTION,RIC_TRD_E\CH
   # 20090101,NewYear's Day,NYS
   # 20090119,Martin Luther King's Birthday,NYS
      
   $exists_by_exch_holiday->{$exch} = $exists_holiday;
      
   return $exists_by_exch_holiday->{$exch};
}
      
sub is_holiday {
   my ($exch, $day, $opt) = @_;
      
   parse_holiday_csv($exch, $opt);
      
   return $exists_by_exch_holiday->{$exch}->{$day};
}
      
my $pos_by_exch_tradeday;
my $tradedays_by_exch;
      
sub parse_tradeday_csv {
   my ($exch, $opt) = @_;

   croak "need to specify exch when calling parse_tradeday_csv()" if ! $exch;
      
   return if exists $pos_by_exch_tradeday->{$exch};
      
   die "TPSUP is not defined in shell" if !$ENV{TPSUP};
      
   my $base = $ENV{TPSUP};
      
   my $file = "$ENV{TPSUP}/lib/etc/tradeday.$exch.csv";
      
   die "cannot find $file" if ! -f $file;
      
   my $cmd = "sed ld $file";
      
   my @tradedays = `$cmd`;
   die "cmd=$cmd failed: $!" if $?;
      
   chomp @tradedays;
      
   $tradedays_by_exch->{$exch} = \@tradedays;
      
   my $pos_by_tradeday;
      
   my $pos = 1; # pos starts with 1 in order to make "if ($pos_by_tradeday->{$day})" work,
      
   for my $d (@tradedays) {
      $pos_by_tradeday->{$d} = $pos;
      $pos ++;
   }
      
   $pos_by_exch_tradeday->{$exch} = $pos_by_tradeday;
      
   return;
}
      
sub get_tradedays_by_exch {
   my ($exch, $opt) = @_;
      
   parse_tradeday_csv($exch, $opt);
      
   return $tradedays_by_exch->{$exch};

}
      
my $tradeday_by_exch_start_offset;
      
sub get_tradeday_by_exch_start_offset {
   my ($exch, $start, $offset, $opt) = @_;
      
   return $tradeday_by_exch_start_offset->{$exch}->{$start}->{$offset}
      if exists $tradeday_by_exch_start_offset->{$exch}->{$start}->{$offset};
      
   my $tradedays = get_tradedays_by_exch($exch, $opt);
   
   #print "tradedays = ", Dumper($tradedays);
   
   my $start_pos;
   
   if ($pos_by_exch_tradeday->{$start}) {
      $start_pos = $pos_by_exch_tradeday->{$start};
   } else {
      if ($start < $tradedays->[0] || $start > $tradedays->[-1]) {
         carp "$start is out of range: $tradedays->[0] ~ $tradedays->[-1]";
         $tradeday_by_exch_start_offset->{$exch}->{$start}->{$offset} = undef;
         return undef;
      }
      
      my $pos = 1;
      for my $d (@$tradedays) {
         if ( $d < $start ) {
            $pos ++;
            next;
         }
      
         $start_pos = $pos;
         last;
      }
      
      if (!$start_pos) {
         carp "$start is out of range: $tradedays->[0] ~ $tradedays->[-1]";
         $tradeday_by_exch_start_offset->{$exch}->{$start}->{$offset} = undef;
         return undef;
      }
   }
      
   my $target_pos = $start_pos + $offset - 1; # -1 because pos starts with 1
   #print "target_pos = $start_pos + $offset - 1 = $target_pos\n";
      
   my $total_tradedays = scalar(@$tradedays);
      
   if ($target_pos <0 || $target_pos > $total_tradedays) {
      carp "target date is out of range: $tradedays->[0] ~ $tradedays->[-1], pos 1 ~ $total_tradedays";
      $tradeday_by_exch_start_offset->{$exch}->{$start}->{$offset} = undef;
      return undef;
   }
      
   my $tradeday = $tradedays->[$target_pos]; # -1 because pos starts with 1
      
   $tradeday_by_exch_start_offset->{$exch}->{$start}->{$offset} = $tradeday;
      
   return $tradeday;

}
      
my $tradedays_by_exch_start_end;
      
sub get_tradedays_by_exch_start_end {
   my ($exch, $start, $end, $opt) = @_;
      
   return $tradedays_by_exch_start_end->{$exch}->{$start}->{$end}
      
   if exists $tradedays_by_exch_start_end->{$exch}->{$start}->{$end};
   my $tradedays = get_tradedays_by_exch($exch, $opt);
   
   if ($start < $tradedays->[0] || $start > $tradedays->[-1]) {
      carp "start day $start is out of range: $tradedays->[0] ~ $tradedays->[-1]";
      $tradedays_by_exch_start_end->{$exch}->{$start}->{$end} = undef;
      return undef;
   }
   
   if ($end < $tradedays->[0] || $end > $tradedays->[-1]) {
      carp "end day $end is out of range: $tradedays->[0] ~ $tradedays->[-1]";
      $tradedays_by_exch_start_end->{$exch}->{$start}->{$end} = undef;
      return undef;
   }
   
   my @days;
   
   for my $d (@$tradedays) {
      if ( $d < $start ) {
         next;
      }
   
      if ( $d > $end ) {
         last;
      }
      
      push @days, $d;
   }
      
   $tradedays_by_exch_start_end->{$exch}->{$start}->{$end} = \@days;
      
   return $tradedays_by_exch_start_end->{$exch}->{$start}->{$end};
}      


sub get_interval_seconds {
   my ($yyyymmdd1, $HHMMSS1, $yyyymmdd2, $HHMMSS2, $opt) = @_;
      
   my $seconds;
      
   require Date::Calc;
   # TODO:
   # in prod, use the following instead, and move it to top of this module
   #use Date::Calc qw(Delta_Days);

   if ($yyyymmdd1 && $yyyymmdd2 && $yyyymmdd1 != $yyyymmdd2) {
      my ($yyyy1,$mm1,$dd1, $yyyy2,$mm2,$dd2);
      
      if ("$yyyymmdd1" =~ /^([0-9]{4})([0-9]{2})([0-9]{2})$/) {
         ($yyyy1, $mm1, $dd1) = ($1, $2, $3);
      } else {
         croak "yyyymmdd1='$yyyymmdd1' is in bad format";
      }
      
      if ("$yyyymmdd2" =~ /^([0-9]{4})([0-9]{2})([0-9]{2})$/) {
         ($yyyy2, $mm2, $dd2) = ($1, $2, $3);
      } else {
         croak "yyyymmdd2='$yyyymmdd2' is in bad format";
      }
      
      # use the Date::Calc module
      my $days = Date::Calc::Delta_Days($yyyy1,$mm1,$dd1, $yyyy2,$mm2,$dd2);
      
      $seconds += $days*86400; # 86400 = 24*60*60;
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

1
