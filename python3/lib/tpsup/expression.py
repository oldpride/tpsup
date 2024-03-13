
from pprint import pformat


_exist = {}  # keep track of the existence of variables
# keep track of fix-protocol variables
# fix protocal uses number as key; therefore, we need to add a prefix to the key.
# 35 can be a variable name, but fix['35'] can.
fix = {}


def export_var(ref: dict,
               ExpPrefix=None,  # prefix the exported variables
               RESET=False,  # whether to clear the existing variables
               FIX=False,  # fix protocol
               verbose=False):

    # we use this function to populate the global variables

    global _exist
    global fix
    prefix = ExpPrefix
    if RESET:
        if prefix:
            if prefix in globals():
                var = globals()[prefix]
                if isinstance(var, dict):
                    # how to clear a dict ?
                    # https://stackoverflow.com/questions/369898
                    # var = {}
                    var.clear()
        elif FIX:
            fix.clear()
        else:
            _exist.clear()

    if prefix:
        if prefix not in globals():
            globals()[prefix] = {}
        for k in ref:
            if isinstance(ref[k], dict):
                # only support 2 levels of nesting
                for k2 in ref[k]:
                    globals()[prefix][k][k2] = ref[k][k2]
            else:
                globals()[prefix][k] = ref[k]
    elif FIX:
        for k in ref:
            if isinstance(ref[k], dict):
                for k2 in ref[k]:
                    fix[k][k2] = ref[k][k2]
            else:
                fix[k] = ref[k]
    else:
        for k in ref:
            if isinstance(ref[k], dict):
                if k not in globals():
                    globals()[k] = {}
                for k2 in ref[k]:
                    globals()[k][k2] = ref[k][k2]
                    _exist[k] = 1
            else:
                globals()[k] = ref[k]
                _exist[k] = 1


def dump_var(DumpFH=None, ExpPrefix=None, FIX=False):
    prefix = ExpPrefix
    if prefix:
        if prefix in globals():
            print(f"\n{prefix} =\n", file=DumpFH)
            print(f"{pformat(globals()[prefix])}", file=DumpFH)
        else:
            print(f"\n{prefix} is not defined", file=DumpFH)
    elif FIX:
        print("\n%fix =\n", file=DumpFH)
        print(f"{pformat(fix)}", file=DumpFH)
    else:
        print("\nvars =\n", file=DumpFH)
        for k in sorted(_exist):
            print(f"{k} => {pformat(globals()[k])}", file=DumpFH)


'''
sub compile_exp {
   my ($exp, $opt) = @_;
   #print STDERR "compile_exp opt =", Data::Dumper::Dumper($opt);
   
   if (exists $compiled_by_exp->{$exp}) {
      return $compiled_by_exp->{$exp};
   }

   print STDERR "compile exp='$exp'\n" if $opt->{verbose} || $verbose;

   my $workaround_exp;

   if ($opt->{FIX} || $FIX) {
      # This is a workaround to modify $1, $2, ..., eg, ${35} = D
      # The following don't work
      # $ perl -e '${"35"} = "D"'
      # $ perl -e '${35} = "D"'
      # Modification of a read-only value attempted at -e line 1.
      #
      # The following work
      # $ perl -e '$fix{35} = "D"'
      # $ perl -e '$fix{"35"} = "D"'
   
      $workaround_exp = convert_to_fix_expression($exp);
   
      ($opt->{verbose} || $verbose) && print STDERR "converted '$exp' to '$workaround_exp'\n";
   } else {
      $workaround_exp = $exp;
   }
   
   my $warn = ($opt->{verbose}||$verbose) ? 'use' : 'no';
   
   my $compiled = eval "$warn warnings; no strict; package TPSUP::Expression; sub { $workaround_exp } ";

   if ($@) {
      if ($opt->{FIX} || $FIX) {
         die "Bad match expression '$workaround_exp', converted from '$exp': $@";
      } else {
         die "Bad match expression '$workaround_exp': $@";
      }
   }
   
   $compiled_by_exp->{$exp} = $compiled;
   
   return $compiled;
   
}
'''

compiled_by_source = {}


def compile_code(source: str,
                 is_exp=False,  # whether the source is an expression, exp needs return statement
                 **opt):

    verbose = opt.get('verbose', False)

    if source in compiled_by_source:
        return compiled_by_source[source]

    source2 = 'def f():\n'

    if is_exp:
        # this is an expression
        # we need to add a return statement
        source2 += f"    return {source}\n"
    else:
        source2 += f"    {source}\n"

    if verbose:
        print(f"compile source=\n'\n{source2}'")

    try:
        compiled = compile(source2, '<string>', 'exec')
    except Exception as e:
        raise Exception(f"failed to compile source='{source2}': {e}")

    try:
        exec(compiled, globals())
    except Exception as e:
        raise Exception(f"failed to execute compiled source='{source2}': {e}")

    compiled_by_source[source] = f

    if verbose:
        print(f'globals={pformat(globals())}')

    return compiled_by_source[source]


def main():
    def test_codes():
        export_var({'a': 1, 'b': 2, 'c': 3})
        dump_var()
        a+b
        export_var({'a': 4, 'd': 5}, RESET=True)
        dump_var()
        a+d
        export_var({'a': 7, 'b': 8, 'c': 9}, ExpPrefix='tian', RESET=True)
        dump_var(ExpPrefix='tian')

        compile_code('a+d', is_exp=True)()

    from tpsup.exectools import test_lines
    test_lines(test_codes, source_globals=globals(), source_locals=locals())
    # test_codes()


if __name__ == '__main__':
    main()
