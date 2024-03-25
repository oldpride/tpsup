
import types
from typing import Union


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

'''
sub tpbatch_parse_hash_cfg {
   my ( $hash_cfg, $opt ) = @_;

   # overwrite the default TPSUP::BATCH::parse_hash_cfg

   # verify syntax
   for my $k ( keys %{ $hash_cfg->{cfg} } ) {
      my $base_cfg = $hash_cfg->{cfg}->{$k};
      my $result   = check_hash_cfg_syntax( $base_cfg, $swagger_syntax->{base} );
      if ( $result->{error} ) {
         print STDERR "syntax error at base=$k, $result->{message}", Dumper($base_cfg);
         exit 1;
      }

      for my $k2 ( keys %{ $base_cfg->{op} } ) {
         my $op_cfg  = $base_cfg->{op}->{$k2};
         my $result2 = check_hash_cfg_syntax( $op_cfg, $swagger_syntax->{op} );
         if ( $result2->{error} ) {
            print STDERR "syntax error at op=$k, $result2->{message}", Dumper($op_cfg);
            exit 1;
         }
      }
   }

   if ( !$hash_cfg->{usage_example} ) {
      my $example = "\n";

      for my $base ( sort ( keys %{ $hash_cfg->{cfg} } ) ) {
         my $base_cfg = $hash_cfg->{cfg}->{$base};

         for my $op ( sort ( keys %{ $base_cfg->{op} } ) ) {
            my $cfg = $base_cfg->{op}->{$op};
            $example .= "   {{prog}} $base $op";

            my $num_args = $cfg->{num_args} ? $cfg->{num_args} : 0;
            for ( my $i = 0 ; $i < $num_args ; $i++ ) {
               $example .= " arg$i";
            }

            $example .= "\n";

            $example .= "      $cfg->{comment}\n" if defined $cfg->{comment};

            my $Accept = $cfg->{Accept} ? $cfg->{Accept} : 'application/json';

            if ( ( $Accept =~ /json/ || $cfg->{json} ) && !$opt->{nojson} ) {
               $example .= "      expect json in output\n";
            } else {
               $example .= "      not expect json in output\n";
            }

            $example .= "      validator: $cfg->{validator}\n"
              if defined $cfg->{validator};
            if ( defined $cfg->{test_str} ) {
               for my $test_str ( @{ $cfg->{test_str} } ) {
                  $example .= "      e.g. {{prog}} $base $op $test_str\n";
               }
            }

            # sub_url vs sub_ui
            #    sub_url is to be used by curl command
            #    sub_ui  is user interface for manually click on swagger menu.
            # sub_ui is default to share the first part of sub_url, example
            #    sub_url: app1/api/run_myop1_1
            #    sub_ui : app1/swagger-ui

            my $sub_url = $cfg->{sub_url};

            my $sub_ui;    # web user interface for manual operation
            if ( $cfg->{sub_ui} ) {
               $sub_ui = $cfg->{sub_ui};
            } else {
               # derive sub_ui from sub_url
               my $discarded;
               ( $sub_ui, $discarded ) = split( /\//, $sub_url );
               $sub_ui .= "/swagger-ui";
            }

            for my $base_url ( @{ $base_cfg->{base_urls} } ) {
               $example .= "        curl: $base_url/$sub_url\n";
            }

            for my $base_url ( @{ $base_cfg->{base_urls} } ) {
               $example .= "      manual: $base_url/$sub_ui\n";
            }

            $example .= "\n";
         }
      }

      $hash_cfg->{usage_example} = $example;

      $hash_cfg->{usage_top} = <<'END';

    {{prog}} base operation arg1 arg2

    -nojson        don't apply json parser on output 
    -n | -dryrun   dryrun. only print out command.
    -v             verbose mode. this will print http status code in the header, eg
                       < HTTP/1.1 200 OK
END
   }

   return $hash_cfg;
}
'''
