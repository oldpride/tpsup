
from pprint import pformat
import types
from typing import Union

from tpsup.cfgtools import check_syntax


swagger_syntax = {
    'top': {
        'cfg': {'type': dict, 'required': 1},
        'package': {'type': str},
        'minimal_args': {'type': str},
    },

    'base': {
        'base_urls': {'type': list, 'required': 1},
        'op': {'type': dict, 'required': 1},
        'entry': {'type': str},
        'entry_func': {'type': Union[str, types.CodeType, types.FunctionType]},
    },
    'op': {
        'sub_url': {'type': str, 'required': 1},
        'num_args': {'type': str, 'pattern': r'^\d+$'},
        'json': {'type': str, 'pattern': r'^\d+$'},
        'method': {'type': str, 'pattern': r'^(GET|POST|DELETE)$'},
        'Accept': {'type': str},
        'comment': {'type': str},
        'validator': {'type': str},
        'post_data': {'type': str},
        'test_str': {'type': list},
    },
}


def tpbatch_parse_hash_cfg(hash_cfg: dict, **opt):
    verbose = opt.get('verbose', 0)

    if verbose:
        print(f"hash_cfg = {pformat(hash_cfg)}")
        print(f"swagger_syntax = {pformat(swagger_syntax)}")

    check_syntax(hash_cfg, swagger_syntax, fatal=1)

    if not hash_cfg.get('usage_example'):
        example = "\n"

        for base in sorted(hash_cfg['cfg'].keys()):
            base_cfg = hash_cfg['cfg'][base]

            for op in sorted(base_cfg['op'].keys()):
                cfg = base_cfg['op'][op]
                example += f"   {{prog}} {base} {op}"

                num_args = cfg.get('num_args', 0)
                for i in range(num_args):
                    example += f" arg{i}"

                example += "\n"

                example += f"      {cfg['comment']}\n" if cfg.get('comment') is not None

                Accept = cfg.get('Accept', 'application/json')

                if ('json' in Accept or cfg.get('json')) and not opt.get('nojson'):
                    example += "      expect json in output\n"
                else:
                    example += "      not expect json in output\n"

                example += f"      validator: {cfg['validator']}\n" if cfg.get('validator') is not None
                if cfg.get('test_str'):
                    for test_str in cfg['test_str']:
                        example += f"      e.g. {{prog}} {base} {op} {test_str}\n"

                sub_url = cfg['sub_url']

                sub_ui = cfg.get('sub_ui')
                if sub_ui:
                    sub_ui = cfg['sub_ui']
                else:
                    sub_ui, discarded = sub_url.split('/')
                    sub_ui += "/swagger-ui"

                for base_url in base_cfg['base_urls']:
                    example += f"        curl: {base_url}/{sub_url}\n"

                for base_url in base_cfg['base_urls']:
                    example += f"      manual: {base_url}/{sub_ui}\n"

                example += "\n"

        hash_cfg['usage_example'] = example

        hash_cfg['usage_top'] = f'''
    {{prog}} base operation arg1 arg2

    -nojson        don't apply json parser on output 
    -n | -dryrun   dryrun. only print out command.
    -v                                                              
        '''
    return hash_cfg


'''
sub tpbatch_parse_input {
   my ( $input, $all_cfg, $opt ) = @_;

   # this overrides the default TPSUP::BATCH::parse_input_default_way

   my @copied = @$input;
   my $base   = shift @copied;
   my $op     = shift @copied;
   my $args   = \@copied;

   if ( !exists $all_cfg->{cfg}->{$base} ) {
      print "ERROR: base='$base' is not defined in cfg\n";
      exit 1;
   }

   if ( !exists $all_cfg->{cfg}->{$base}->{op}->{$op} ) {
      print "ERROR: op='$op' is not defined in cfg in base=$base\n";
      exit 1;
   }

   my $num_args = $all_cfg->{cfg}->{$base}->{op}->{$op}->{num_args};
   $num_args = 0 if !defined($num_args);

   my $num_input = scalar(@copied);

   if ( $num_args != $num_input ) {
      print
        "ERROR: wrong number of args, expecting $num_args but got $num_input, input=",
        Dumper( \@copied );
      exit 1;
   }

   my $known = { base => $base, op => $op, args => $args };

   return $known;
}

sub tpbatch_code {
   my ( $all_cfg, $known, $opt ) = @_;

   # this provides a default code() for TPSUP::BATCH's config. see tpswagger_test.cfg
   # can be overriden by a code() subroutine in cfg file.

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   if ($verbose) {
      print __FILE__ . " " . __LINE__ . " all_cfg = ", Dumper($all_cfg);
      print __FILE__ . " " . __LINE__ . " known   = ", Dumper($known);
      print __FILE__ . " " . __LINE__ . " opt     = ", Dumper($opt);
   }

   my $base = $known->{base};
   my $op   = $known->{op};

   my $cfg = $all_cfg->{cfg}->{$base}->{op}->{$op};

   if ( !defined($cfg) ) {
      croak "base=$base, op=$op, doesn't exist";
   }

   # push down upper level config to lower level
   my @upper_keys = qw(base_urls entry entry_func);
   @{$cfg}{@upper_keys} = @{ $all_cfg->{cfg}->{$base} }{@upper_keys};
   $cfg->{op}   = $op;
   $cfg->{meta} = $all_cfg->{meta};

   $verbose && print __FILE__ . " " . __LINE__ . " base=$base, op=$op, cfg = ", Dumper($cfg);

   TPSUP::SWAGGER::swagger( $cfg, $known->{args}, $opt );
}
'''

def tpbatch_parse_input(input, all_cfg, **opt):
    # this overrides the default tpsup.batch parse_input_default_way

    # command line like: tpswagger_test  mybase2 myop2_1 arg0 arg1
    #                                    base    op      args ...
    copied = input.copy()
    base = copied.pop(0)
    op = copied.pop(0)
    args = copied
        