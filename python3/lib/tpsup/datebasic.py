import datetime


def get_date(**opt):
    if yyyymmdd := opt.get('yyyymmdd', None):
        yyyy, mm, dd = yyyymmdd[:4], yyyymmdd[4:6], yyyymmdd[6:8]
        now = datetime.datetime(year=int(yyyy), month=int(mm), day=int(dd))
    else:
        now = datetime.datetime.now()
    date = {}
    date['yyyy'] = now.strftime('%Y')
    date['mm'] = now.strftime('%m')
    date['dd'] = now.strftime('%d')
    date['HH'] = now.strftime('%H')
    date['MM'] = now.strftime('%M')
    date['SS'] = now.strftime('%S')
    date['DST'] = now.strftime('%z')
    date['WD'] = now.strftime('%w')

    return date


def get_yyyymmdd(**opt):
    date = get_date(**opt)
    return f"{date['yyyy']}{date['mm']}{date['dd']}"


def get_yyyymmdd_by_yyyymmdd_offset(yyyymmdd1, offset, **opt):
    # from tpsup.cmdtools import run_cmd
    # yyyymmdd2 = run_cmd(f'date -d "{yyyymmdd1} {offset} day" "+%Y%m%d"', is_bash=True)['stdout'].strip()
    yyyy, mm, dd = yyyymmdd1[:4], yyyymmdd1[4:6], yyyymmdd1[6:8]
    date1 = datetime.datetime(year=int(yyyy), month=int(mm), day=int(dd))
    date2 = date1 + datetime.timedelta(days=offset)
    yyyymmdd2 = date2.strftime("%Y%m%d")
    return yyyymmdd2


'''
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
'''

# convert above to python


'''
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
               $ref->{$yyyymmdd}++;
            } else {
               croak
"$HolidaysCsv row $row_count item $item_count '$yyyymmdd'  bad format";
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
   $opt->{verbose} && print STDERR Dumper( $holidays_by_exch->{$exch} );

   return $exists_by_exch_holiday->{$exch};
}

'''


def yyyymmdd_to_DayOfWeek(yyyymmdd: str, **opt):
    date = get_date(yyyymmdd=yyyymmdd)
    return date['WD']


def main():
    def test_codes():
        get_date()
        get_yyyymmdd()
        yyyymmdd_to_DayOfWeek(yyyymmdd=get_yyyymmdd())
        get_date(yyyymmdd='20200901')
        get_yyyymmdd_by_yyyymmdd_offset('20200901', -1)

    import tpsup.exectools
    tpsup.exectools.test_lines(test_codes, globals(), locals())


if __name__ == "__main__":
    main()
