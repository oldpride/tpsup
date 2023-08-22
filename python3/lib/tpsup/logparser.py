import re
import sys

from tpsup.tpfile import TpInput, sorted_files_by_mtime, tpglob


'''
sub get_logs {
   my ($log, $opt) = @_;

   my @log_patterns;
   my $type = ref($log);
   if (!$type) {
      # a scalar
      @log_patterns = ($log);
   } elsif ($type eq 'ARRAY') {
      @log_patterns = @$log;
   } else {
      confess "type='$type' for log=", Dumper($log);
   }

   my @logs;
   for my $lp (@log_patterns) {
      my $cmd = "/bin/ls -1dtr $lp";
      $opt->{verbose} && print STDERR "cmd=$cmd\n";
      my @lines = `$cmd`;
      chomp @lines;
      push @logs, @lines;
   }

   #print "logs = ", Dumper(\@logs);

   my $LogLastCount = $opt->{LogLastCount};
   if ($LogLastCount) {
      if ($LogLastCount >= @logs) {
         return \@logs;
      } else {
         my @logs2 = @logs[$#logs-$LogLastCount+1..$#logs];
         return \@logs2;
      }
   } else {
      return \@logs;
   }
}
'''
# convert above to python


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

    KeyAttr = section_cfg.get('KeyAttr', {})
    # key value default to scalar.
    # if need to be array or hash, specify in KeyAttr.

    CompiledExtracts = None
    if ExtractPatterns := section_cfg.get('ExtractPatterns', None):
        CompiledExtracts = [re.compile(p) for p in ExtractPatterns]

    maxcount = opt['MaxCount'] if opt and 'MaxCount' in opt else None

    item = {}
    item_count = 0
    line = None

    def consume_line_update_item():
        # nonlocal line, item, CompiledExtracts

        for p in CompiledExtracts:
            m = p.search(line)
            if m:
                match = m.groupdict()
                if not match:
                    continue

                if verbose:
                    print("matched = ", match)

                if line is None:
                    line = line
                    item['lines'].append(line)

                for k in match:
                    v = match[k]
                    if k not in KeyAttr:
                        item[k] = v
                    elif KeyAttr[k] == 'Array':
                        item[k].append(v)
                    elif KeyAttr[k] == 'Hash':
                        item[k][v] += 1
                    else:
                        raise Exception(
                            "unsupported KeyAttr at '$k=$KeyAttr->{$k}'")
        line = None

    logs = get_logs(log, opt)

    for lg in logs:
        with TpInput(filename=log, **opt) as tf:
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
                            # if we already started, we have an $item, we return the $item.
                            yield item
                            # note: we didn't consume $line and it is left for the next call.
                            item_count += 1
                            if maxcount and item_count >= maxcount:
                                return
                        else:
                            consume_line_update_item()
                        started = 1
                    elif CompiledEnd and CompiledEnd.search(line):
                        # we matched the end pattern. this will be a clean finish
                        if started:
                            # consume this only if the section already started
                            consume_line_update_item()
                            yield item
                            item_count += 1
                            if maxcount and item_count >= maxcount:
                                return
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


'''
sub get_log_section_headers {
   my ($ExtractPatterns, $opt) = @_;

   my @headers;
   
   if ($ExtractPatterns) {
      my $seen;
      for my $line (@$ExtractPatterns) {
         my @keys = ($line =~ /[?]<([a-zA-Z0-9_]+)>/g);
         for my $k (@keys) {
            $seen->{$k} ++;
         }
      }
      @headers = sort(keys %$seen);
   }

   return \@headers;
}
'''
# convert above to python


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


def main():
    import os
    TPSUP = os.environ.get('TPSUP')
    log = f'"{TPSUP}/python3/scripts/tptrace_test_section*.log"',

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
        'KeyAttr': {'OrderId': 'Array', 'TradeId': 'Hash'},
        'KeyDefault': {'OrderId': [], 'TradeId': {}},
        # KeyDefault is to simplify MatchExp, allowing us to use
        #     MatchExp =>'grep {/^ORD-0001$/}  @{$r{OrderId}}'
        # without worrying about whether $r{OrderId} is defined.

        # use csv_filter below for consistency
        # MatchExp can use {{...}} vars. this is applied after a whole section is
        # completed.
        # MatchExp =>'grep(/^{{pattern::ORDERID}}$/, @{$r{OrderId}})',
        # ExcludeExp =>'...',
    },

    def test_codes():
        get_logs(f'{TPSUP}/python3/lib/tpsup/*py', LogLastCount=5)
        get_log_section_headers(section_cfg['ExtractPatterns'])

    from tpsup.exectools import test_lines
    test_lines(test_codes, source_globals=globals(),
               source_locals=locals(), verbose=2)

    sect_gen = get_log_section_gen(log, section_cfg, verbose=2)


if __name__ == '__main__':
    main()
