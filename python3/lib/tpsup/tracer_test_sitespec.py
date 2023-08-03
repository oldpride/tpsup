import re
import sys

from tpsup.sqltools import run_sql


sids_by_security = {}


def get_sids_by_security(security: str, **opt):
    verbose = opt.get('verbose', 0)

    if security in sids_by_security:
        return sids_by_security[security]

    Sid_clause = ""
    if re.match(r'^\d+$', security):
        # if this is a number, then it could also be a SID
        Sid_clause = f"or Sid = '{security}'"

    type_clause = f"""
                ( Symbol = '{security}' or Cusip = '{security}'
                 or Isin = '{security}' or Sedol = '{security}'
                 {Sid_clause}
                )"""
    if 'SecType' in opt and not re.match(r'SECURITY', opt['SecType'], re.IGNORECASE):
        type_clause = f"{opt['SecType']} = '{security}'"

    db = 'tptest@tpdbmssql'
    sql = f"""
        select sid from securities (nolock)
        where IsActive = 'Y'
                and {type_clause}
    """

    opt2 = {}
    if verbose:
        opt2 = {
            'out_fh': sys.stderr,
            'RenderOutput': 1,
            'verbose': verbose,
            # MaxColumnWidth => $entity_cfg->{MaxColumnWidth},
        }

        print(f'sql {db} "{sql}"')

    result = run_sql(sql, nickname=db, ReturnType="ListList")

    if not result:
        raise RuntimeError(f'failed to run sql={sql}')

    sids_by_security[security] = []

    for row in result[1:]:
        sids_by_security[security].append(row[0])

    return sids_by_security[security]


def main():
    def test_codes():
        print(get_sids_by_security('IBM'))

    from tpsup.exectools import test_lines
    test_lines(test_codes, source_globals=globals())


if __name__ == '__main__':
    main()
