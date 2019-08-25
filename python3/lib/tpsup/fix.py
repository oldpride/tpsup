import re
import sys


def parse_fix_message(line: str, **opt):
    if line is None or len(line) == 0:
        return None

    verbose = 0
    if 'verbose' in opt and opt['verbose'] is not None:
        verbose = opt['verbose']

    only_numeric = 0
    if 'OnlyNumeric' in opt and opt['OnlyNumeric'] == 1:
        only_numeric = 1

    nested_fix = 0
    if 'NestedFix' in opt and opt['NestedFix'] is not None:
        nested_fix = opt['NestedFix']

    # TIME(05:39:37:015) EID(0) JMSID(ID:db_us_GTO_GEMS_S006PROD.35EB53D568E41950096:11763)
    # LEN(196) RAW_DATA(8=FIX.4.1^A9=0172^A35=D^A34=1491...^A59=0^A100=0^A10=142^A)

    # trim everything before 8=FIX ...
    start = line.find("8=FIX")
    if start != -1:
        fix_section = line[start:]
    else:
        fix_section = line

    # trim the end
    j = len(fix_section) - 1
    while True:
        ending = fix_section[j]
        if ending == "'" or ending == '"' or ending == ')' or ending == '\r':
            j -= 1
        else:
            break
    fix_section = fix_section[:j].strip()

    delimiter = None

    if 'FixDelimiter' in opt and opt['FixDelimiter'] is not None:
        delimiter = opt['FixDelimiter']
    else:
        # we take pain to figure out the delimiter, time-consuming
        # 8=FIX.4.1
        # 8=FIXT.1.1

        patterns = [r'8=FIX[.0-9T]+(.+?)\d', r'\b35=[0-9a-zA-Z]{1,2}([^.0-9B-Z]{1,2})\d']
        for p in patterns:
            compiled = re.compile(p)
            m = compiled.match(fix_section)
            if m:
                delimiter = m.group(1)
                break

        if not delimiter:
            p = r'\d=.+'
            compiled = re.compile(p)
            m = compiled.match(fix_section)
            if m:
                # only one element
                delimiter = 'not_needed'

        # if delimiter == '^A':
        #     # the delmiter is caret+A because of copy-paste, we need to
        #     # convert caret+A to control-A in order to make the later split work.
        #     # otherwise, caret+A means 'not A' in split.
        #     fix_section.replace('^A', char(0x01))

        if not delimiter:
            raise RuntimeError(f'we cannot figure out delimiter at line: {line}')

    if verbose > 0:
        print('delimiter is ', delimiter, file=sys.stderr)

    v_by_k = {}
    is_new_multileg = False
    is_new_list = False
    in_block = False
    num_components = 0
    comp_idx = 0
    components = []
    current_comp = {}
    common_by_k = {}
    last_tag = None

    for pair in fix_section.split(delimiter):
        if '=' not in pair:
            continue

        k, v = pair.split('=', 1)

        if k is None or v is None:
            continue

        if only_numeric == 1 and not k.isdigit():
            continue

        if k == '35':
            if v == 'AB':
                is_new_multileg = True
                if is_nested_fix == 0:
                    print(f'warnings: multileg message (35=AB), need to parse with NestedFix=1, at line: ', line,
                          file=sys.stderr)
            elif v == 'E':
                is_new_list = True
                print(f'warnings: list message (35=E666), need to parse with NestedFix=1, at line: ', line,
                      file=sys.stderr)

        if nested_fix == 1:
            if not in_block:
                if is_new_multileg and k == "555":
                    if v > 0:
                        in_block = True
                        # otherwise, when 555=0, no leg block
                    num_components = int(v)
                    # tag 555 belongs to common section
                    common_by_k[k] = v
                elif is_new_list and k == "11":
                    in_block = True

                    # in List, tag 11 belongs to component section
                    current_comp[k] = v
                else:
                    common_by_k[k] = v
            else:
                # in_block == True
                if is_new_multileg:
                    # leg block ending with this four tags
                    # => 654 LegRefID N
                    # => 566 LegPrice N
                    # => 587 LegSettlType N
                    # => 588 LegSettlDate N
                    if k != "654" and k != "566" and k != "587" and k != "588" and \
                            (last_tag is None or
                             last_tag == "654" or last_tag == "566" or last_tag == "587" or last_tag == "588"):
                        # we have just completed a leg. start a new one
                        components.append(current_comp)
                        current_comp = {}

                        if len(components) >= num_components:
                            # we finished the whole leg block and are back to common tags
                            in_block = False
                            common_by_k[k] = v
                        else:
                            # this is the next leg
                            current_comp[k] = v
                    else:
                        # we are still within the current leg
                        current_comp[k] = v
                elif is_new_list:
                    if k == "11":
                        # start a list
                        if current_comp:
                            # is current_comp is not empty, save it into the component list
                            components.append(current_comp)

                    current_comp = {k: v}
        else:
            # not assuming NestedFix, very naive
            v_by_k[k] = v

        if k == "10":
            common_by_k[k] = v
            break

        last_tag = k

    if nested_fix:
        if 'ReturnNestedInArray' in opt and opt['ReturnNestedInArray']:
            ret = []

            for leg in components:
                merged = leg
                merged.update(common_by_k)
                ret.append(merged)

            return ret
        else:
            ret = {'common':common_by_k, 'components':components, 'delimiter':delimiter}
            return ret
    else:
        # not assuming Nested Fix, very naive
        return v_by_k


def main():
    pass


