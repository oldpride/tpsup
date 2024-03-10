import datetime
import datetime
import os
from pprint import pformat
import re
import csv
import datetime
import sys

from tpsup.searchtools import binary_search_match

# Date and time objects may be categorized as “aware” or “naive” depending on whether or not they include timezone information.
#     Objects of the "date" type are always naive.
#     An object of type "time" or "datetime" may be aware or naive.
#
# A datetime object d is aware if both of the following hold:
#     d.tzinfo is not None
#     d.tzinfo.utcoffset(d) does not return None
# Otherwise, d is naive.
#
# A time object t is aware if both of the following hold:
#     t.tzinfo is not None
#     t.tzinfo.utcoffset(None) does not return None.
# Otherwise, t is naive.
# Subclass relationships:
# object
#     timedelta
#     tzinfo
#         timezone
#     time
#     date
#         datetime


tzinfo = None


def get_timezone():
    global tzinfo
    if tzinfo:
        return tzinfo
    else:
        tzinfo = datetime.datetime.now().astimezone().tzinfo
    return tzinfo


def get_date(yyyymmdd=None, **opt):
    if yyyymmdd:
        yyyy, mm, dd = yyyymmdd[:4], yyyymmdd[4:6], yyyymmdd[6:8]
        dt = datetime.datetime(year=int(yyyy), month=int(mm), day=int(dd), tzinfo=get_timezone())
    else:
        dt = datetime.datetime.now(tz=get_timezone())
    r = {}
    r['yyyy'] = dt.strftime('%Y')
    r['mm'] = dt.strftime('%m')
    r['dd'] = dt.strftime('%d')
    r['HH'] = dt.strftime('%H')
    r['MM'] = dt.strftime('%M')
    r['SS'] = dt.strftime('%S')
    r['offset'] = dt.strftime('%z')
    r['WD'] = dt.strftime('%w')
    r['datetime'] = dt

    return r


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

    if exists_by_exch_holiday.get(exch, None):
        return exists_by_exch_holiday[exch]

    if not HolidaysCsv:
        perllib_dir = get_perllib_dir()
        HolidaysCsv = os.path.join(perllib_dir, 'DATE_holidays.csv')

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
    global exists_by_exch_holiday
    parse_holiday_csv(exch, **opt)
    return exists_by_exch_holiday[exch].get(yyyymmdd, None)


def yyyymmdd_to_DayOfWeek(yyyymmdd: str, **opt):
    date = get_date(yyyymmdd=yyyymmdd)
    return date['WD']


yyyymmddHHMMSS_pattern = r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})'
yyyymmddHHMMSS_compiled = None


def yyyymmddHHMMSS_to_epoc(yyyymmddHHMMSS, fromUTC=False, **opt):
    # convert time to seconds from epoch

    settings = {}
    if fromUTC:
        settings['tzinfo'] = datetime.timezone.utc

    if type(yyyymmddHHMMSS) == list:
        if len(yyyymmddHHMMSS) != 6:
            print(f"bad format of yyyymmddHHMMSS list={pformat(yyyymmddHHMMSS)}", file=sys.stderr)
            raise ValueError("List size must be 6")

        dt = datetime.datetime(*yyyymmddHHMMSS, **settings)

    else:
        global yyyymmddHHMMSS_compiled
        if yyyymmddHHMMSS_compiled == None:
            yyyymmddHHMMSS_compiled = re.compile(yyyymmddHHMMSS_pattern)

        if m := re.match(yyyymmddHHMMSS_compiled, yyyymmddHHMMSS):
            yyyy, mm, dd, HH, MM, SS = m.groups()

            dt = datetime.datetime(int(yyyy), int(mm), int(dd), int(HH), int(MM), int(SS), **settings)
        else:
            raise ValueError(f"yyyymmddHHMMSS='{yyyymmddHHMMSS}', bad format")

    seconds = dt.timestamp()
    return seconds


def epoc_to_yyyymmddHHMMSS(epoc, toUTC=False, **opt):
    if toUTC:
        dt = datetime.datetime.utcfromtimestamp(epoc)
    else:
        dt = datetime.datetime.fromtimestamp(epoc)
    # print(pformat(dt))
    return dt.strftime('%Y%m%d%H%M%S')
    # dt = datetime.datetime.fromtimestamp(epoc)
    # if toUTC:
    #     return dt.astimezone(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
    # else:
    #     return dt.strftime('%Y%m%d%H%M%S')


def get_yyyymmddHHMMSS(**opt):
    now_sec = datetime.datetime.now().timestamp()
    return epoc_to_yyyymmddHHMMSS(now_sec, **opt)


perllib_dir = None


def get_perllib_dir():
    global perllib_dir
    if not perllib_dir:
        directory = os.path.dirname(os.path.abspath(__file__))
        perllib_dir = os.path.join(directory, '../../../lib/perl/TPSUP')
    return perllib_dir


weekdays = None


def get_weekdays():
    global weekdays
    if not weekdays:
        directory = get_perllib_dir()
        file = os.path.join(directory, 'DATE_weekdays.txt')
        with open(file, 'r') as fh:
            string = fh.read()
            weekdays = string.split()
            weekdays.pop()  # remove the last empty element
    return weekdays


tradeday_by_exch_begin_offset = {}


def get_tradeday_by_exch_begin_offset(exch, begin, offset,
                                      IgnoreHoliday=False,
                                      OnWeekend=None,
                                      # next, prev. 'next' means if the begin is on weekend,
                                      # then the next trade day is the first trade day
                                      **opt):
    global tradeday_by_exch_begin_offset

    verbose = opt.get('verbose', 0)

    if exch not in tradeday_by_exch_begin_offset:
        tradeday_by_exch_begin_offset[exch] = {}

    if begin not in tradeday_by_exch_begin_offset[exch]:
        tradeday_by_exch_begin_offset[exch][begin] = {}

    if offset in tradeday_by_exch_begin_offset[exch][begin]:
        return tradeday_by_exch_begin_offset[exch][begin][offset]

    is_holiday = {}

    # exch == 'WeekDay' is a special case, which means ignore holiday
    if IgnoreHoliday or exch == 'WeekDay':
        IgnoreHoliday = True
    else:
        is_holiday = parse_holiday_csv(exch, opt=opt)

    weekdays = get_weekdays()

    # if the binary search falls between two connective trade days, eg, on weekends
    InBetween = 'low'
    if OnWeekend and OnWeekend == 'next':
        InBetween = 'high'

    begin_weekday_pos = binary_search_match(weekdays, begin, 'string',
                                            InBetween=InBetween, OutBound='Error')
    verbose and print(f"begin_weekday={weekdays[begin_weekday_pos]}", file=sys.stderr)

    if IgnoreHoliday:
        # without taking holiday into account, we basically return a weekday
        return weekdays[begin_weekday_pos + offset]

    # we haven't considered holidays yet. now we need to do that

    # first make sure the begin_weekday is not a holiday
    begin_tradeday_pos = begin_weekday_pos

    while is_holiday.get(weekdays[begin_tradeday_pos]):
        if OnWeekend == 'next':
            begin_tradeday_pos += 1
        else:
            begin_tradeday_pos -= 1

    # tradeday is a non-holiday weekday
    begin_tradeday = weekdays[begin_tradeday_pos]
    verbose and print(f"begin_tradeday={begin_tradeday}", file=sys.stderr)

    if offset == 0:
        # we only cache offset from a tradeday, as offset from weekend and holiday
        # can be affected by OnWeekend flag
        tradeday_by_exch_begin_offset[exch][begin_tradeday][offset] = begin_tradeday
        return begin_tradeday
    else:
        new_pos = begin_tradeday_pos

        if offset > 0:
            for i in range(1, offset + 1):
                new_pos += 1
                while is_holiday.get(weekdays[new_pos], None):
                    new_pos += 1
        elif offset < 0:
            for i in range(-1, offset - 1, -1):
                new_pos -= 1
                while is_holiday.get(weekdays[new_pos], None):
                    new_pos -= 1

        new_tradeday = weekdays[new_pos]

        #  we only cache offset from a tradeday, as offset from weekend and holiday
        # can be affected by OnWeekend flag
        tradeday_by_exch_begin_offset[exch][begin_tradeday][offset] = new_tradeday
        return new_tradeday


def get_holidays_by_exch_begin_end(exch, begin, end, **opt):
    global holidays_by_exch

    parse_holiday_csv(exch, **opt)

    if exch not in holidays_by_exch:
        raise RuntimeError(f"no holiday information for exch={exch}")

    all_holidays = holidays_by_exch[exch]

    holidays = []
    begin_covered = False
    end_covered = False

    for d in all_holidays:
        if d >= end:
            end_covered = True

            if d == end:
                holidays.append(d)

            break

        if d >= begin:
            holidays.append(d)
            if d == begin:
                begin_covered = True
        else:
            begin_covered = True

    if not end_covered:
        print(f"end={end} exceeded upper bound of '{exch}' holidays ({all_holidays[-1]})")

    if not begin_covered:
        print(f"begin={begin} exceeded lower bound of '{exch}' holidays ({all_holidays[0]})")

    return holidays


def get_tradedays_by_exch_begin_end(exch, begin, end, **opt):
    exists_holiday = parse_holiday_csv(exch, opt=opt)
    weekdays = get_weekdays()

    if begin < weekdays[0] or begin > weekdays[-1]:
        print(f"begin day {begin} is out of range: {weekdays[0]} ~ {weekdays[-1]}")
        return None

    if end < weekdays[0] or end > weekdays[-1]:
        print(f"end day {end} is out of range: {weekdays[0]} ~ {weekdays[-1]}")
        return None

    tradedays = []

    for d in weekdays:
        if d < begin:
            continue

        if exists_holiday.get(d):
            continue

        if d > end:
            break

        tradedays.append(d)

    return tradedays


def get_tradeday(offset, Exch='NYSE', Begin=None, **opt):
    if Begin is None:
        Begin = get_yyyymmdd(**opt)
    return get_tradeday_by_exch_begin_offset(Exch, Begin, offset, opt)


def get_tradedays(count, **opt):
    tradedays = []
    if count > 0:
        for i in range(0, count):
            tradedays.append(get_tradeday(i, **opt))
    elif count < 0:
        for i in range(0, -count):
            tradedays.append(get_tradeday(count+1+i, **opt))
    return tradedays


compiled_yyyymmdd_pattern = None


def get_compiled_yyyymmdd_pattern():
    global compiled_yyyymmdd_pattern
    if compiled_yyyymmdd_pattern == None:
        yyyymmdd_pattern = r'\d{8}'
        compiled_yyyymmdd_pattern = re.compile(yyyymmdd_pattern)
    return compiled_yyyymmdd_pattern


# get_interval_seconds
# vs get_seconds_between_yyyymmddHHMMSS
# vs get_seconds_between_two_days
#    get_interval_seconds uses strict format
#    get_seconds_between_yyyymmddHHMMSS supports more formats
#    get_seconds_between_two_days is to handle DST change
seconds_between_two_days = {}


def get_seconds_between_two_days(yyyymmdd1, yyyymmdd2,
                                 IntervalDaysNoCaching=False,
                                 CheckFormat=False,  # default not to check format, save time
                                 **opt):
    if CheckFormat:
        # by default we don't check format because
        #    1. it's time consuming
        #    2. we trust the input. it is rarely called by user input

        # make sure the two days are in same type
        yyyymmdd1 = str(yyyymmdd1)
        yyyymmdd2 = str(yyyymmdd2)

        # make sure the two days are in correct format
        compiled_yyyymmdd_pattern = get_compiled_yyyymmdd_pattern()
        if not re.match(compiled_yyyymmdd_pattern, yyyymmdd1):
            raise ValueError(f"yyyymmdd1='{yyyymmdd1}' is not in correct format")
        if not re.match(compiled_yyyymmdd_pattern, yyyymmdd2):
            raise ValueError(f"yyyymmdd2='{yyyymmdd2}' is not in correct format")

    if yyyymmdd1 == yyyymmdd2:
        return 0

    if IntervalDaysNoCaching:
        seconds1 = yyyymmddHHMMSS_to_epoc(f"{yyyymmdd1}120000")
        seconds2 = yyyymmddHHMMSS_to_epoc(f"{yyyymmdd2}120000")
        return seconds2 - seconds1
    else:
        caching_key = f"{yyyymmdd1},{yyyymmdd2}"
        if caching_key not in seconds_between_two_days:
            seconds1 = yyyymmddHHMMSS_to_epoc(f"{yyyymmdd1}120000")
            seconds2 = yyyymmddHHMMSS_to_epoc(f"{yyyymmdd2}120000")
            seconds_between_two_days[caching_key] = seconds2 - seconds1

        return seconds_between_two_days[caching_key]


compiled_HHMMSS_pattern = None


def get_compiled_HHMMSS_pattern():
    global compiled_HHMMSS_pattern
    if compiled_HHMMSS_pattern == None:
        HHMMSS_pattern = r'^[0-9]{2}[0-9]{2}[0-9]{2}$'
        compiled_HHMMSS_pattern = re.compile(HHMMSS_pattern)
    return compiled_HHMMSS_pattern


def get_interval_seconds(yyyymmdd1, HHMMSS1, yyyymmdd2, HHMMSS2,
                         CheckFormat=False,
                         **opt):
    seconds = 0

    if yyyymmdd1 and yyyymmdd2 and yyyymmdd1 != yyyymmdd2:
        seconds = get_seconds_between_two_days(yyyymmdd1, yyyymmdd2, opt)

    if CheckFormat:
        compiled_HHMMSS_pattern = get_compiled_HHMMSS_pattern()
        if not compiled_HHMMSS_pattern.match(HHMMSS1):
            raise ValueError(f"HHMMSS1='{HHMMSS1}' is in bad format")
        if not compiled_HHMMSS_pattern.match(HHMMSS2):
            raise ValueError(f"HHMMSS2='{HHMMSS2}' is in bad format")

    HH1, MM1, SS1 = HHMMSS1[:2], HHMMSS1[2:4], HHMMSS1[4:6]
    HH2, MM2, SS2 = HHMMSS2[:2], HHMMSS2[2:4], HHMMSS2[4:6]

    seconds += (int(HH2) - int(HH1)) * 3600 + (int(MM2) - int(MM1)) * 60 + (int(SS2) - int(SS1))

    return seconds


'''
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
'''

compiled_yyyymmddHHMMSS_pattern = None


def get_compiled_yyyymmddHHMMSS_pattern():
    global compiled_yyyymmddHHMMSS_pattern
    if compiled_yyyymmddHHMMSS_pattern == None:
        yyyymmddHHMMSS_pattern = r'^([12][09]\d{12})(.*)'
        compiled_yyyymmddHHMMSS_pattern = re.compile(yyyymmddHHMMSS_pattern)
    return compiled_yyyymmddHHMMSS_pattern


compiled_yyyymmddHHMMSS_sep_pattern = None


def get_compiled_yyyymmddHHMMSS_sep_pattern():
    global compiled_yyyymmddHHMMSS_sep_pattern
    if compiled_yyyymmddHHMMSS_sep_pattern == None:
        yyyymmddHHMMSS_sep_pattern = r'^([12][09]\d{2})([^\d])(\d{2})(.)(\d{2})(.)(\d{2})(.)(\d{2})(.)(\d{2})(.*)'
        compiled_yyyymmddHHMMSS_sep_pattern = re.compile(yyyymmddHHMMSS_sep_pattern)
    return compiled_yyyymmddHHMMSS_sep_pattern


def get_seconds_between_yyyymmddHHMMSS(yyyymmddHHMMSS1, yyyymmddHHMMSS2, **opt):
    # this supports a wider format
    s = []
    for t1 in (yyyymmddHHMMSS1, yyyymmddHHMMSS2):
        if m := re.match(get_compiled_yyyymmddHHMMSS_pattern(), t1):
            t2 = m.group(1)
        elif m := re.match(get_compiled_yyyymmddHHMMSS_sep_pattern(), t1):
            t2 = f"{m.group(1)}{m.group(3)}{m.group(5)}{m.group(7)}{m.group(9)}{m.group(11)}"
        else:
            raise ValueError(f"unsupported format at '{t1}'")

        sec = yyyymmddHHMMSS_to_epoc(t2)
        s.append(sec)
    return s[1] - s[0]


def main():
    def test_codes():
        get_timezone()
        get_date()
        get_yyyymmdd()
        yyyymmdd_to_DayOfWeek(yyyymmdd=get_yyyymmdd())
        get_date(yyyymmdd='20200901')
        get_yyyymmdd_by_yyyymmdd_offset('20200901', -1) == '20200831'
        get_timezone_offset() in (4.0, 5.0)
        is_holiday('NYSE', '20240101') == 1
        yyyymmddHHMMSS_to_epoc('20200901120000')
        epoc_to_yyyymmddHHMMSS(1598976000)
        yyyymmddHHMMSS_to_epoc('20200901120000', fromUTC=True)
        epoc_to_yyyymmddHHMMSS(1598961600, toUTC=True)

        yyyymmddHHMMSS_to_epoc([2020, 9, 1, 12, 0, 59])
        yyyymmddHHMMSS_to_epoc([2020, 9, 1, 12, 0, 59], fromUTC=1)
        yyyymmddHHMMSS_to_epoc([2020, 9, 1, 12, 0, 59], fromUTC=1) - yyyymmddHHMMSS_to_epoc([2020, 9, 1, 12, 0, 59])

        get_yyyymmddHHMMSS()
        get_yyyymmddHHMMSS(toUTC=True)

        get_holidays_by_exch_begin_end('NYSE', '20240101', '20240201') == ['20240101', '20240115']

        # 20200907, Monday, is a holiday, labor day
        get_tradeday_by_exch_begin_offset('NYSE', '20200901', 3, ) == '20200904'  # within the same week
        get_tradeday_by_exch_begin_offset('NYSE', '20200904', -3, ) == '20200901'
        get_tradeday_by_exch_begin_offset('NYSE', '20200901', 4, ) == '20200908'  # across the weekend and holiday
        get_tradeday_by_exch_begin_offset('NYSE', '20200908', -4, ) == '20200901'

        get_tradeday_by_exch_begin_offset('NYSE', '20200904', 0, ) == '20200904'  # 0 offset on a trade day
        get_tradeday_by_exch_begin_offset('NYSE', '20200905', 0, ) == '20200904'  # 0 offset on a weekend
        get_tradeday_by_exch_begin_offset('NYSE', '20200907', 0, ) == '20200904'  # 0 offset on a holiday

        get_tradeday_by_exch_begin_offset('NYSE', '20200905', 0, OnWeekend='next') == '20200908'
        get_tradeday_by_exch_begin_offset('NYSE', '20200907', 0, OnWeekend='next') == '20200908'

        get_tradeday_by_exch_begin_offset('NYSE', '20200907', 1) == '20200908'
        get_tradeday_by_exch_begin_offset('NYSE', '20200907', 1, OnWeekend='next') == '20200908'

        get_tradedays_by_exch_begin_end('NYSE', '20200903', '20200907') == ['20200903', '20200904']
        get_tradedays_by_exch_begin_end('NYSE', '20200903', '20200908') == ['20200903', '20200904', '20200908']

        get_tradeday(-4, Begin='20200908') == '20200901'
        get_tradeday(4, Begin='20200901') == '20200908'

        get_tradedays(3, Begin='20200903') == ['20200903', '20200904', '20200908']
        get_tradedays(-3, Begin='20200908') == ['20200903', '20200904', '20200908']

        # 20240310 is DST change day. we use 12:00 PM of each day
        get_seconds_between_two_days('20240309', '20240310') == 82800
        get_seconds_between_two_days('20240311', '20240312') == 86400

        get_interval_seconds('20240309', '120000', '20240310', '120001') == 82801
        get_interval_seconds('20240310', '120000', '20240311', '120001') == 86401

        get_seconds_between_yyyymmddHHMMSS('2024-03-10 00:00:01.513447', '2024-03-10 03:00:01.000000') == 7200
        get_seconds_between_yyyymmddHHMMSS('2024-03-11 00:00:01.513447', '2024-03-11 03:00:01.000000') == 10800

    import tpsup.exectools
    tpsup.exectools.test_lines(test_codes, globals(), locals())


if __name__ == "__main__":
    main()
