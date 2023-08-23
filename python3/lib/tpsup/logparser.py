import re
import sys

from tpsup.tpfile import TpInput, sorted_files_by_mtime, tpglob
from tpsup.modtools import load_module


def get_logs(log, LogLastCount: int = 0, **opt):
    verbose = opt.get('verbose', 0)

    logs = sorted_files_by_mtime(log, **opt)

    return logs[-LogLastCount:]


def get_log_section_gen(log, section_cfg, **opt):
    # perl generator vs python generator
    #    perl generator depends on global variables and returns a sub.
    #    python generator depends on yield command.

    verbose = opt.get('verbose', 0)

    # - both BeginPattern/EndPattern can be undefined at the same time; in this
    #   case the whole file is one section.
    # - when only BeginPattern is undefined, we start with assuming the first
    #   section is started.
    # - when only EndPattern is undefined, we assume the end of section is the
    #   line before the next BeginPattern is matched.

    CompiledBegin = None
    CompiledEnd = None
    if BeginPattern := section_cfg.get('BeginPattern', None):
        CompiledBegin = re.compile(BeginPattern)
    if EndPattern := section_cfg.get('EndPattern', None):
        CompiledEnd = re.compile(EndPattern)

    # PreMatch/PreExclude are tried before BeginPattern/EndPattern are tried
    # they are for speedup, it covers every line, therefore, be careful to
    # avoid filtering out BeginPattern/EndPattern.
    #
    # PostPattern/PostPattern are tried after BeginPattern/EndPattern are tried
    # they are for both speedup and reduce noise,

    CompiledPreMatch = None
    CompiledPreExclude = None
    if PreMatch := section_cfg.get('PreMatch', None):
        CompiledPreMatch = re.compile(PreMatch)
    if PreExclude := section_cfg.get('PreExclude', None):
        CompiledPreExclude = re.compile(PreExclude)

    CompiledPostMatch = None
    CompiledPostExclude = None
    if PostMatch := section_cfg.get('PostMatch', None):
        CompiledPostMatch = re.compile(PostMatch)
    if PostExclude := section_cfg.get('PostExclude', None):
        CompiledPostExclude = re.compile(PostExclude)

    mod_source = ''
    for exp in ['ItemMatchExp', 'ItemExcludeExp']:
        # item level match, using Exp,
        if exp in section_cfg:
            mod_source += f'def {exp}(r):\n'
            mod_source += f'    return {section_cfg[exp]}\n'
            mod_source += f''

    if mod_source != '':
        exp_module = load_module(mod_source)
    else:
        exp_module = None

    KeyType = section_cfg.get('KeyType', {})
    # key value default to scalar.
    # if need to be array or hash, specify in KeyAttr.

    CompiledExtracts = None
    if ExtractPatterns := section_cfg.get('ExtractPatterns', None):
        CompiledExtracts = [re.compile(p) for p in ExtractPatterns]

    maxcount = opt['MaxCount'] if opt and 'MaxCount' in opt else None

    item = None
    item_count = 0
    line = None
    started = 0

    def reset_item():
        nonlocal item, KeyType
        item = {}
        item['lines'] = []
        for k, kt in KeyType.items():
            if kt == "Array":
                item[k] = []
            elif kt == "Hash":
                item[k] = {}

    def consume_line_update_item(file=None):
        nonlocal line, CompiledExtracts, item, verbose

        for p in CompiledExtracts:
            m = p.search(line)
            if m:
                match = m.groupdict()
                if not match:
                    continue

                if verbose:
                    print("matched = ", match)

                item['lines'].append(line)
                item['file'] = file

                for k in match:
                    v = match[k]
                    if k not in KeyType:
                        item[k] = v
                    elif KeyType[k] == 'Array':
                        item[k].append(v)
                    elif KeyType[k] == 'Hash':
                        item[k].setdefault(v, 0)
                        item[k][v] += 1
                    else:
                        raise Exception(
                            "unsupported KeyAttr at '$k=$KeyAttr->{$k}'")
        line = None

    logs = get_logs(log, **opt)
    reset_item()

    for lg in logs:
        with TpInput(filename=lg, **opt) as tf:
            try:
                for line in tf:  # this line may raise exception for binary file. so use try/except
                    if verbose > 2:
                        print(f'line={line}', file=sys.stderr)

                    if CompiledPreMatch and not CompiledPreMatch.search(line):
                        continue
                    if CompiledPreExclude and CompiledPreExclude.search(line):
                        continue

                    if CompiledBegin and CompiledBegin.search(line):
                        # this is a starting line.
                        if started:
                            # if we already started, we have an $item, we can return the $item.
                            # we check the item level match exp
                            yield_this_item = True
                            if 'ItemMatchExp' in section_cfg:
                                if not exp_module.ItemMatchExp(item):
                                    yield_this_item = False
                            if 'ItemExcludeExp' in section_cfg:
                                if exp_module.ItemExcludeExp(item):
                                    yield_this_item = False
                            if yield_this_item:
                                yield item
                                # note: we didn't consume $line and it is left for the next call.
                                item_count += 1
                                if maxcount and item_count >= maxcount:
                                    return
                            reset_item()
                            consume_line_update_item(file=lg)
                        else:
                            # if we haven't started, we need to consume this line
                            consume_line_update_item(file=lg)
                            started = 1
                    elif CompiledEnd and CompiledEnd.search(line):
                        # we matched the end pattern. this will be a clean finish
                        if started:
                            # consume this only if the section already started
                            consume_line_update_item(file=lg)

                            # we check the item level match exp
                            yield_this_item = True
                            if 'ItemMatchExp' in section_cfg:
                                if not exp_module.ItemMatchExp(item):
                                    yield_this_item = False
                            if 'ItemExcludeExp' in section_cfg:
                                if exp_module.ItemExcludeExp(item):
                                    yield_this_item = False
                            if yield_this_item:
                                yield item
                                # note: we didn't consume $line and it is left for the next call.
                                item_count += 1
                                if maxcount and item_count >= maxcount:
                                    return
                            reset_item()
                            started = 0
                        # unwanted line is thrown away
                        # we don't need to do any of below as they will be taken care of by loop
                        # line = None
                        # continue
                    elif (CompiledPostMatch and not CompiledPostMatch.search(line)) or \
                         (CompiledPostExclude and CompiledPostExclude.search(line)):
                        continue
                    else:
                        if started:
                            consume_line_update_item()
            except UnicodeDecodeError as e:
                # UnicodeDecodeError: 'utf-8' codec can't decode byte 0x9b in position 147:
                #     invalid start byte
                print(
                    f'read {lg} failed with decode error. skipped.', file=sys.stderr)
                if verbose:
                    print(e, file=sys.stderr)
                continue


def get_log_section_headers(ExtractPatterns, **opt):
    headers = []

    if ExtractPatterns:
        seen = {}
        for line in ExtractPatterns:
            keys = re.findall(r'\(\?P<([a-zA-Z0-9_]+)>', line)
            for k in keys:
                seen[k] = 1

        headers = sorted(seen.keys())

    return headers


def get_log_sections(log, cfg, **opt):
    section_gen = get_log_section_gen(log, cfg, **opt)

    sections = []

    for r in section_gen:
        sections.append(r)

    return sections


def main():
    import os
    TPSUP = os.environ.get('TPSUP')
    log = f'{TPSUP}/python3/scripts/tptrace_test_section*.log'

    section_cfg = {
        # PreMatch/PreExclude are tried before BeginPattern/EndPattern are tried
        # they are for speedup, it covers every line, therefore, be careful to
        # avoid filtering out BeginPattern/EndPattern.
        'PreMatch': '^2021',
        # PreExclude => '^2022',

        # this cfg will transferred to TPSUP::LOG::get_log_sections() sub
        'BeginPattern': 'section id .*? started',
        'EndPattern': 'section completed',

        # PostPattern/PostPattern are tried after BeginPattern/EndPattern are tried
        # they are also for speed-up
        'PostMatch': 'order id|trade id',
        # PostExclude => 'no content',

        'ExtractPatterns': [
            # named groups
            '^(?P<BeginTime>.{23}) section id (?P<SectionId>.*?) started',
            '^(?P<EndTime>.{23}) section completed',
            'order id (?P<OrderId>\S+)',
            'trade id (?P<TradeId>\S+)',
        ],
        'KeyType': {'OrderId': 'Array', 'TradeId': 'Hash'},

        # use csv_filter below for consistency
        # MatchExp can use {{...}} vars. this is applied after a whole section is
        # completed.
        # MatchExp =>'grep(/^{{pattern::ORDERID}}$/, @{$r{OrderId}})',
        # ExcludeExp =>'...',
    }

    def test_codes():
        get_logs(f'{TPSUP}/python3/lib/tpsup/*py', LogLastCount=5)
        get_log_section_headers(section_cfg['ExtractPatterns'])
        get_log_sections(log, section_cfg, MaxCount=7)
        section_cfg.update({'ItemMatchExp': '"TRD-0002" in r["TradeId"]'})
        get_log_sections(log, section_cfg)

    from tpsup.exectools import test_lines
    test_lines(test_codes, source_globals=globals(),
               source_locals=locals())

    # get_log_sections(log, section_cfg, verbose=2)


if __name__ == '__main__':
    main()
