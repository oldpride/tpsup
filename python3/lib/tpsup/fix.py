import re
import sys
from pprint import pprint, pformat
from fix_4_4 import field_by_tag, desc_by_tag_value
from typing import Dict, List

delimiter_patterns = {
    'standard': rb'8=FIX[.0-9T]+(.+?)\d',
    'repeating': rb'.*?(?P<delimiter>[^0-9a-zB-Z]{1,2})\d+=[^=]+?(?P=delimiter)',
    'two_items': rb'.*?([\^]?[^0-9])\d+=',
    'one_item': rb'^\d+=[^=]+$',
}

# dict comprehension syntax. https://www.python.org/dev/peps/pep-0274/
compiled_delimiter_patterns = {key: re.compile(value) for key, value in delimiter_patterns.items()}


def parse_fix_message(line: bytes, **opt):
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
    start = line.find(b'8=FIX')
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

    if verbose > 0:
        print('fix_section =', fix_section, file=sys.stderr)

    if not fix_section or fix_section == '':
        return None

    delimiter = None

    if 'FixDelimiter' in opt and opt['FixDelimiter'] is not None:
        delimiter = opt['FixDelimiter']
    else:
        # we take pain to figure out the delimiter, time-consuming
        # 8=FIX.4.1
        # 8=FIXT.1.1

        # re.match() vs re.search(): match() is from beginning, search() is anywhere
        global compiled_delimiter_patterns
        global delimiter_patterns
        match_order = ['standard', 'repeating', 'two_items']
        for way in match_order:
            compiled = compiled_delimiter_patterns[way]
            m = compiled.match(fix_section)
            if m:
                if verbose:
                    print(f"matched '{way}': {delimiter_patterns[way]}")
                delimiter = m.group(1)
                break

        if not delimiter:
            way = 'one_item'
            compiled = compiled_delimiter_patterns[way]
            m = compiled.match(fix_section)
            if m:
                # only one element
                if verbose:
                    print(f"matched '{way}': {delimiter_patterns[way]}")
                delimiter = b'_no_need_'

        if not delimiter:
            raise RuntimeError(f'we cannot figure out delimiter at line: {line}')

    if verbose > 0:
        print('delimiter is ', delimiter, '\n', file=sys.stderr)

    v_by_k = {}
    is_new_multileg = False
    is_new_list = False
    in_block = False
    num_components = 0
    components = []
    current_comp = {}
    common_by_k = {}
    last_tag = None

    for pair in fix_section.split(delimiter):
        if b'=' not in pair:
            continue

        k, v = pair.split(b'=', 1)

        if k is None or v is None:
            continue

        if only_numeric == 1 and not k.isdigit():
            continue

        if k == b'35':
            if v == b'AB':
                is_new_multileg = True
                if nested_fix == 0:
                    print(f'warnings: multileg message (35=AB), need to parse with NestedFix=1, at line: ', line,
                          file=sys.stderr)
            elif v == b'E':
                is_new_list = True
                print(f'warnings: list message (35=E666), need to parse with NestedFix=1, at line: ', line,
                      file=sys.stderr)

        if nested_fix == 1:
            if not in_block:
                if is_new_multileg and k == b"555":
                    if int(v) > 0:
                        in_block = True
                        # otherwise, when 555=0, no leg block
                    num_components = int(v)
                    # tag 555 belongs to common section
                    common_by_k[k] = v
                elif is_new_list and k == b"11":
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
                    # => 564 LegPositionEffect
                    # => 566 LegPrice N
                    # => 587 LegSettlType N
                    # => 588 LegSettlDate N
                    if k != b"654" and k != b"566" and k != b"587" and k != b"588" and k != b"564" and \
                            (last_tag is None or
                             last_tag == b"654" or last_tag == b"566" or last_tag == b"587" or last_tag == b"588"
                             or last_tag == b"564"):
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
                    if k == b"11":
                        # start a list
                        if current_comp:
                            # is current_comp is not empty, save it into the component list
                            components.append(current_comp)

                    current_comp = {k: v}
        else:
            # not assuming NestedFix, very naive
            v_by_k[k] = v

        if k == b"10":
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
            return {'common': common_by_k, 'components': components, 'delimiter': delimiter}
    else:
        # not assuming Nested Fix, very naive
        if 'ReturnDetail' in opt and opt['ReturnDetail']:
            return {'delimiter': delimiter, 'dict': v_by_k}
        else:
            return v_by_k


def dump_nested_fix(nested_fix, **opt):
    if 'DumpFH' in opt and opt['DumpFH']:
        dump_fh = opt['DumpFH']
    else:
        dump_fh = sys.stderr

    dump_value_by_tag(nested_fix['common'], **opt)

    total = len(nested_fix['components'])
    i = 0
    for c in nested_fix['components']:
        i += 1
        print(f'\n-------- component {i} of {total}')
        dump_value_by_tag(c)


def dump_value_by_tag(value_by_tag: Dict[bytes, bytes], **opt):
    if 'DumpFH' in opt and opt['DumpFH']:
        dump_fh = opt['DumpFH']
    else:
        dump_fh = sys.stderr

    for tag, value in value_by_tag.items():
        tag_str = tag.decode('utf-8')
        value_str = value.decode('utf-8')
        if tag_str in field_by_tag:
            field = field_by_tag[tag_str]
        else:
            field = ''

        if tag_str in desc_by_tag_value and value_str in desc_by_tag_value[tag_str]:
            desc = desc_by_tag_value[tag_str][value_str]
        else:
            desc = ''

        print(f'{field:>19} {tag_str:>5} = {value_str} ({desc})', file=sys.stderr)


def dump_fix_message(line, **opt):
    dump_nested_fix(parse_fix_message(line, NestedFix=1, **opt))


def main():
    file = 'fix_test_delimiter.txt'
    with open(file, 'rb') as fh:
        for line in fh:
            pprint(parse_fix_message(line, ReturnDetail=1, verbose=1))

    print('')

    file = 'fix_test_multileg.txt'
    with open(file, 'rb') as fh:
        for line in fh:
            pprint(parse_fix_message(line, ReturnDetail=1, verbose=1))
            pprint(parse_fix_message(line, ReturnDetail=1, verbose=1, NestedFix=1))
            break

    print('')

    file = 'fix_test_delimiter.txt'
    with open(file, 'rb') as fh:
        for line in fh:
            dump_value_by_tag(parse_fix_message(line, verbose=1))
            break

    print('')

    file = 'fix_test_multileg.txt'
    with open(file, 'rb') as fh:
        for line in fh:
            dump_fix_message(line, verbose=1)
            break


if __name__ == '__main__':
    main()
