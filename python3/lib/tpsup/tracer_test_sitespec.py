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


security_by_sid_type = {}


def get_security_by_sid(sid: str, **opt):
    verbose = opt.get('verbose', 0)

    if f'{sid}' in security_by_sid_type:
        return security_by_sid_type[f'{sid}']

    db = 'tptest@tpdbmssql'
    sql = f"""
        select * from securities (nolock)
        where sid = '{sid}'
              and IsActive = 'Y'
    """

    opt2 = {
        # 'out_fh': sys.stderr,
        'RenderOutput': verbose,
        'verbose': verbose,
        # MaxColumnWidth => $entity_cfg->{MaxColumnWidth},
    }

    if verbose:
        print(f'sql {db} "{sql}"')

    result = run_sql(sql, nickname=db, ReturnType='DictList', **opt2)

    if result is None:
        raise RuntimeError(f'failed to run sql={sql}')

    if len(result) > 1:
        raise RuntimeError(
            f'Sid is not unique, matched multiple {result}')
    elif len(result) == 0:
        security_by_sid_type[f'{sid}'] = {}
    else:
        security_by_sid_type[f'{sid}'] = result[0]

    return security_by_sid_type[f'{sid}']


has_updated_security_knowledge = False


def update_security_knowledge(known: dict, key: str, **opt):
    verbose = opt.get('verbose', 0)

    global has_updated_security_knowledge

    if has_updated_security_knowledge:
        # because we only concern 1 security, therefore, we only need to update once.
        return

    has_updated_security_knowledge = True

    print(f'extending knowledge about security from {key}={known[key]}')

    sids: list = get_sids_by_security(known[key], SecType=key,
                                      output='-', RenderOutput=1, verbose=verbose)

    if not sids:
        raise RuntimeError(
            f'cannot match {key}={known[key]} to a Sid')
    elif len(sids) > 1:
        raise RuntimeError(
            f'{key}={known[key]} matched to multiple Sids')

    sid = sids[0]

    sec_by_type = get_security_by_sid(sid, verbose=verbose)

    for type in sorted(sec_by_type.keys()):
        value = sec_by_type[type]
        if value is None:
            continue

        known[type.upper()] = value

    return known


def main():
    def test_codes():
        get_sids_by_security('IBM')
        get_security_by_sid('40000', verbose=1)
        update_security_knowledge(
            {'BOOKID': '3000001', 'SID': '40000'}, 'SID', verbose=1)

    from tpsup.exectools import test_lines
    test_lines(test_codes, source_globals=globals())


if __name__ == '__main__':
    main()
