import datetime
import datetime
import os
from pprint import pformat
import re
import csv
import datetime
import sys


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


def get_timezone_offset():
    local_sec = datetime.datetime.now().timestamp()
    t = datetime.datetime.utcfromtimestamp(local_sec)
    gmt_offset_in_seconds = (t - datetime.datetime.fromtimestamp(local_sec)).total_seconds()
    gmt_offset_in_hours = gmt_offset_in_seconds / 3600
    return gmt_offset_in_hours


exists_by_exch_holiday = {}
holidays_by_exch = {}


def parse_holiday_csv(exch, HolidayRef: dict = None, HolidaysCsv: str = None, **opt):

    if HolidayRef:
        exists_by_exch_holiday[exch] = HolidayRef
        return exists_by_exch_holiday[exch]

    if not HolidaysCsv:
        directory = os.path.dirname(os.path.abspath(__file__))
        HolidaysCsv = os.path.join(directory, '../../../lib/perl/TPSUP/holidays.csv')

    if not os.path.isfile(HolidaysCsv):
        raise FileNotFoundError(f"{HolidaysCsv} is not found")

    ref = {}

    with open(HolidaysCsv, 'r') as fh:
        row_count = 0
        while line := fh.readline():
            row_count += 1

            if line.startswith(f"{exch},"):
                # name,days
                # NYSE,20200101 20200120 20200217 ...
                row = line.strip().split(',')
                holidays = row[1].split()

                yyyymmdd_pattern = r'\d{8}'
                yyyymmdd_compiled = re.compile(yyyymmdd_pattern)

                item_count = 0
                last_holiday = None

                for yyyymmdd in holidays:
                    item_count += 1

                    if re.match(yyyymmdd_compiled, yyyymmdd):
                        if last_holiday and yyyymmdd <= last_holiday:
                            raise ValueError(
                                f"{HolidaysCsv} row {row_count} item {item_count} '{yyyymmdd}' <= last one '{last_holiday}', out of order")
                        last_holiday = yyyymmdd
                        ref[yyyymmdd] = 1
                    else:
                        raise ValueError(f"{HolidaysCsv} row {row_count} item {item_count} '{yyyymmdd}' bad format")

                break
    if not ref:
        raise ValueError(f"no holiday info found for {exch} in {HolidaysCsv}")

    holidays_by_exch[exch] = holidays
    exists_by_exch_holiday[exch] = ref

    return exists_by_exch_holiday[exch]


def is_holiday(exch, yyyymmdd, **opt):
    parse_holiday_csv(exch, **opt)
    return exists_by_exch_holiday[exch].get(yyyymmdd, None)


def yyyymmdd_to_DayOfWeek(yyyymmdd: str, **opt):
    date = get_date(yyyymmdd=yyyymmdd)
    return date['WD']


'''
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
'''


def yyyymmddHHMMSS_to_epoc(yyyymmddHHMMSS, IsUTC=False, **opt):
    # convert time to seconds from epoch

    if type(yyyymmddHHMMSS) == list:
        if len(yyyymmddHHMMSS) != 6:
            print(f"bad format of yyyymmddHHMMSS list={pformat(yyyymmddHHMMSS)}", file=sys.stderr)
            raise ValueError("List size must be 6")

        if IsUTC:
            return datetime.datetime.utcfromtimestamp(datetime.datetime(*yyyymmddHHMMSS).timestamp())
        else:
            return datetime.datetime.fromtimestamp(datetime.datetime(*yyyymmddHHMMSS).timestamp())
    else:
        yyyymmddHHMMSS_pattern = r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})'
        yyyymmddHHMMSS_compiled = re.compile(yyyymmddHHMMSS_pattern)

        if m := re.match(yyyymmddHHMMSS_compiled, yyyymmddHHMMSS):
            yyyy, mm, dd, HH, MM, SS = m.groups()
            if IsUTC:
                return datetime.datetime.utcfromtimestamp(datetime.datetime(int(yyyy), int(mm), int(dd), int(HH), int(MM), int(SS)).timestamp())
            else:
                return datetime.datetime.fromtimestamp(datetime.datetime(int(yyyy), int(mm), int(dd), int(HH), int(MM), int(SS)).timestamp())
        else:
            raise ValueError(f"yyyymmddHHMMSS='{yyyymmddHHMMSS}', bad format")


'''

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
'''


def epoc_to_yyyymmddHHMMSS(epoc, **opt):
    date = datetime.datetime.fromtimestamp(epoc)
    return date.strftime('%Y%m%d%H%M%S')


def get_yyyymmddHHMMSS(**opt):
    now_sec = datetime.datetime.now().timestamp()
    return epoc_to_yyyymmddHHMMSS(now_sec, **opt)


def main():
    def test_codes():
        get_date()
        get_yyyymmdd()
        yyyymmdd_to_DayOfWeek(yyyymmdd=get_yyyymmdd())
        get_date(yyyymmdd='20200901')
        get_yyyymmdd_by_yyyymmdd_offset('20200901', -1) == '20200831'
        get_timezone_offset() in (4.0, 5.0)
        is_holiday('NYSE', '20240101') == 1
        yyyymmddHHMMSS_to_epoc('20200901120000')
        epoc_to_yyyymmddHHMMSS(1598959200)
        yyyymmddHHMMSS_to_epoc('20200901120000', IsUTC=True)
        epoc_to_yyyymmddHHMMSS(1598959200, IsUTC=True)

        yyyymmddHHMMSS_to_epoc([2020, 9, 1, 12, 0, 59])
        yyyymmddHHMMSS_to_epoc([2020, 9, 1, 12, 0, 59], IsUTC=1)

    import tpsup.exectools
    tpsup.exectools.test_lines(test_codes, globals(), locals())


if __name__ == "__main__":
    main()
