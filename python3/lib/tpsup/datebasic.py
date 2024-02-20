import datetime


def get_date(**opt):
    date = {}
    now = datetime.datetime.now()
    date['yyyy'] = now.strftime('%Y')
    date['mm'] = now.strftime('%m')
    date['dd'] = now.strftime('%d')
    date['HH'] = now.strftime('%H')
    date['MM'] = now.strftime('%M')
    date['SS'] = now.strftime('%S')
    date['DST'] = now.strftime('%z')
    date['WD'] = now.strftime('%w')

    return date


'''
sub get_yyyymmdd_by_yyyymmdd_offset {
   my ( $yyyymmdd1, $offset, $opt ) = @_;

   my $yyyymmdd2 = `date -d "$yyyymmdd1 $offset day" '+%Y%m%d'`;
   chomp $yyyymmdd2;
   return $yyyymmdd2;
}
'''


def get_yyyymmdd_by_yyyymmdd_offset(yyyymmdd1, offset, **opt):
    from tpsup.cmdtools import run_cmd
    # yyyymmdd2 = run_cmd(f'date -d "{yyyymmdd1} {offset} day" "+%Y%m%d"', is_bash=True)['stdout'].strip()
    yyyy, mm, dd = yyyymmdd1[:4], yyyymmdd1[4:6], yyyymmdd1[6:8]
    yyyymmdd2 = datetime.datetime(year=int(yyyy), month=int(mm), day=int(dd)) + datetime.timedelta(days=offset)
    return yyyymmdd2


def main():
    def test_codes():
        get_date()
        get_yyyymmdd_by_yyyymmdd_offset('20200901', -1)

    import tpsup.exectools
    tpsup.exectools.test_lines(test_codes, globals(), locals())


if __name__ == "__main__":
    main()
