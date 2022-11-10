import importlib
import re
import sys
from collections import ChainMap
from pprint import pprint
from typing import Dict

from tpsup.modtools import load_module

field_by_version_tag = {}
tag_by_version_field = {}
desc_by_version_tag_value = {}

module_name_by_version = {
    '4.0': 'tpsup.fix.fix_4_0',
    '4.1': 'tpsup.fix.fix_4_1',
    '4.2': 'tpsup.fix.fix_4_2',
    '4.3': 'tpsup.fix.fix_4_3',
    '4.4': 'tpsup.fix.fix_4_4',
    '5.0': 'tpsup.fix.fix_5_0_SP2',
}


def map_fix_dictionary(**opt):
    fix_version = opt.get('FixVersion', '4.4')

    if field_by_version_tag.get(fix_version) and not opt.get('RefreshCache'):
        return

    fix_module_name = module_name_by_version.get(fix_version)

    if not fix_module_name:
        raise RuntimeError(f'unsupported FIX version {fix_version}. Supported: {module_name_by_version.keys()}')

    _myfix = importlib.import_module(fix_module_name)

    if opt.get('FixDict'):
        # dict_source = None
        with open(opt.get('FixDict'), 'r') as fh:
            dict_source = fh.read()
        dict_module = load_module(dict_source)

        dict_dir = dir(dict_module)

        if 'field_by_tag' in dict_dir:
            # ChainMap first arg overwrites the second when duplicate
            field_by_version_tag[fix_version] = ChainMap(dict_module.field_by_tag, _myfix.field_by_tag)
        else:
            field_by_version_tag[fix_version] = _myfix.field_by_tag

        if 'tag_by_field' in dict_dir:
            tag_by_version_field[fix_version] = ChainMap(dict_module.tag_by_field, _myfix.tag_by_field)
        else:
            tag_by_version_field[fix_version] = _myfix.tag_by_field

        if 'desc_by_tag_value' in dict_dir:
            desc_by_version_tag_value[fix_version] = ChainMap(dict_module.desc_by_tag_value, _myfix.desc_by_tag_value)
        else:
            desc_by_version_tag_value[fix_version] = _myfix.desc_by_tag_value
    else:
        field_by_version_tag[fix_version] = _myfix.field_by_tag
        tag_by_version_field[fix_version] = _myfix.tag_by_field
        desc_by_version_tag_value[fix_version] = _myfix.desc_by_tag_value


def get_field_by_tag(tag, **opt):
    map_fix_dictionary(**opt)
    fix_version = opt.get('FixVersion', '4.4')
    return field_by_version_tag[fix_version].get(tag)


def get_tag_by_field(field, **opt):
    map_fix_dictionary(**opt)
    fix_version = opt.get('FixVersion', '4.4')
    return tag_by_version_field[fix_version].get(field)


def get_desc_by_tag_value(tag, value, **opt):
    map_fix_dictionary(**opt)
    fix_version = opt.get('FixVersion', '4.4')
    return desc_by_version_tag_value[fix_version].get(tag, {}).get(value)


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

    verbose = opt.get('verbose', 0)
    only_numeric = opt.get('OnlyNumeric', 0)
    nested_fix = opt.get('NestedFix', 0)

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

    fix_section = fix_section[:j+1].strip()

    if verbose > 0:
        print('fix_section =', fix_section, file=sys.stderr)

    if not fix_section:
        return None

    delimiter = opt.get('FixDelimiter')
    if delimiter is None:
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

        k, v = pair.decode('utf-8').split('=', 1)

        if k is None or v is None:
            continue

        if only_numeric == 1 and not k.isdigit():
            continue

        if k == '35':
            if v == 'AB':
                is_new_multileg = True
                if nested_fix == 0:
                    print(f'warnings: multileg message (35=AB), need to parse with NestedFix=1, at line: ', line,
                          file=sys.stderr)
            elif v == 'E':
                is_new_list = True
                print(f'warnings: list message (35=E666), need to parse with NestedFix=1, at line: ', line,
                      file=sys.stderr)

        if nested_fix == 1:
            if not in_block:
                if is_new_multileg and k == "555":
                    if int(v) > 0:
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
                    # => 564 LegPositionEffect
                    # => 566 LegPrice N
                    # => 587 LegSettlType N
                    # => 588 LegSettlDate N
                    if k != "654" and k != "566" and k != "587" and k != "588" and k != "564" and \
                            (last_tag is None or
                             last_tag == "654" or last_tag == "566" or last_tag == "587" or last_tag == "588"
                             or last_tag == "564"):
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
            return {'common': common_by_k, 'components': components, 'delimiter': delimiter}
    else:
        # not assuming Nested Fix, very naive
        if 'ReturnDetail' in opt and opt['ReturnDetail']:
            return {'delimiter': delimiter, 'dict': v_by_k}
        else:
            return v_by_k


def dump_nested_fix(nested_fix, **opt):
    dump_fh = opt.get('DumpFH', sys.stderr)

    dump_value_by_tag(nested_fix['common'], **opt)

    total = len(nested_fix['components'])
    i = 0
    for c in nested_fix['components']:
        i += 1
        print(f'\n-------- component {i} of {total}', file=dump_fh)
        dump_value_by_tag(c, **opt)


def dump_value_by_tag(value_by_tag: Dict[bytes, bytes], **opt):
    dump_fh = opt.get('DumpFH', sys.stderr)

    select_tag = {}
    if opt.get('tags'):
        for t in opt.get('tags').split(','):
            select_tag[t] = True
    # pprint(select_tag)

    for tag, value in value_by_tag.items():
        if select_tag and not select_tag.get(tag):
            continue

        field = get_field_by_tag(tag, **opt)

        if not field:
            field = ''

        desc = get_desc_by_tag_value(tag, value, **opt)
        if not desc:
            desc = ''

        print(f'{field:>19} {tag:>5} = {value} ({desc})', file=dump_fh)


def dump_fix_message(line, **opt):
    dump_nested_fix(parse_fix_message(line, NestedFix=1, **opt), **opt)


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

    file = 'fix_test_multileg.txt'
    with open(file, 'rb') as fh:
        for line in fh:
            dump_fix_message(line, tags='35,54,38,624', FixDict='fix_test_dict.py', RefreshCache=1, verbose=1)
            break


if __name__ == '__main__':
    main()
