package TPSUP::SWAGGER;

# swagger is web interface for RESTful API (web service)
# swagger calls curl to connect to the RESTful API
# therefore, without swagger, you can still use curl to connect to the RESTful API.
# swagger is just a wrapper around curl.
# in this module, only "sub_ui" part is for swagger.
# the rest is for curl. therefore, this module is mainly for curl.
#
# test

use strict;
use base qw( Exporter );

# we don't export anything because this module is called by TPSUP::BATCH.
our @EXPORT_OK = qw(
);

use Carp;
$SIG{__DIE__} = \&Carp::confess;    # this stack-trace on all fatal error !!!

use Data::Dumper;
$Data::Dumper::Terse    = 1;        # print without "$VAR1="
$Data::Dumper::Sortkeys = 1;        # this sorts the Dumper output!

use TPSUP::UTIL qw(
  resolve_scalar_var_in_string
  parse_rc
  add_line_number_to_code
);

use TPSUP::CFG qw(check_syntax);

sub swagger_eval_code {
   my ( $code, $opt ) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   my $dict = $opt->{dict} ? $opt->{dict} : {};

   if ($verbose) {
      print "------ begin preparing code ------\n";
      print "original code: $code\n";
   }

   $code = resolve_scalar_var_in_string( $code, $dict, $opt );

   if ($verbose) {
      print "afer substituted scalar vars in '{{...}}': $code\n";
      eval "no warnings;
            print qq(after eval'ed code: $code\n);
            use warnings;
           ";
   }

   # use a sub{} to separate compile-time error and run-time error
   #    compile-time error should be handled right here
   #        run-time error should be handled by caller

   my $func;
   eval "\$func = sub { $code }";
   if ($@) {
      # compile-time error happens here
      my $numbered_code = add_line_number_to_code($code);
      croak "failed to compile code='
$numbered_code
$@
      '\n";
   }
   $func->();    # run-time error happens here
}

sub get_entry_by_cfg {
   my ( $cfg, $base_url, $dict, $opt ) = @_;

   # print "cfg=", Dumper($cfg);

   # entry => 'swagger-tian',
   # entry => \&TPSUP::SWAGGER::get_swagger_entry,

   my $entry      = $cfg->{entry};
   my $entry_type = ref($entry);
   my $method     = $cfg->{method} ? $cfg->{method} : 'GET';

   my $entry_name;
   if ( !$entry_type ) {
      $entry_name = $entry;
   } elsif ( $entry_type eq 'CODE' ) {
      $entry_name = $entry->( $cfg, $dict, $opt );
   } else {
      croak "unsupported entry type: $entry_type";
   }

   return $entry_name;
}

sub swagger {
   my ( $cfg, $args, $opt ) = @_;

   # $args are the the command line args after base and op.

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   my $dict = {};

   if ($args) {
      $verbose && print __FILE__ . " " . __LINE__ . " args = ", Dumper($args);

      my $n = scalar(@$args);

      for ( my $i = 0 ; $i < $n ; $i++ ) {
         $dict->{"A$i"} = $args->[$i];
      }
   }

   my $validator = $cfg->{validator};
   if ( defined $validator ) {
      $verbose && print STDERR "test validator: $validator\n";
      if ( !ref($validator) ) {
         # if it is not a reference, it is a scalar
         if ( swagger_eval_code( $validator, { %$opt, dict => $dict } ) ) {
            $verbose && print STDERR "validator test passed\n";
         } else {
            print STDERR "validator test failed: $validator\n";
            exit 1;
         }
      } elsif ( ref($validator) eq 'CODE' ) {
         if ( $validator->( $args, $opt ) ) {
            $verbose && print STDERR "validator test passed\n";
         } else {
            print STDERR "validator test failed: $validator\n";
            exit 1;
         }
      } else {
         croak "unsupported validator type: ", ref($validator);
      }
   }

   my $sub_url = resolve_scalar_var_in_string( $cfg->{sub_url}, $dict, $opt );

   delete $ENV{'LD_LIBRARY_PATH'};
   delete $ENV{'http_proxy'};
   delete $ENV{'https_proxy'};

   my @base_urls = @{ $cfg->{base_urls} };

   for my $base_url (@base_urls) {
      my @flags = ();
      if ($verbose) {
         print STDERR "resolved url = $base_url/$sub_url\n";
         push @flags, '-v';
      } else {
         push @flags, '--silent';
      }

      my $flag_string = join( " ", @flags );

      $cfg->{base_url} = $base_url;    # add base_url to cfg, so that the entry function can use it

      my $entry_name = get_entry_by_cfg( $cfg, $dict, $opt );

      my $method = $cfg->{method} ? $cfg->{method} : 'GET';
      my $accept = $cfg->{accept} ? $cfg->{accept} : 'application/json';

      # there are two places mentioning json
      #    --header 'Content-Type: application/json'
      #    --header 'Accept: application/json'
      # the 1st is for input when POST data. the 2nd is for output

      #  -w, --write-out <format>
      #   Make curl display information on stdout after a completed transfer.
      # we use -w to get http status code.

      # windows cmd.exe command line has the following challenges:
      #    1. single quote grouping is not supported - we have to use double quote.
      #    2. line continuation is tricky, uses ^; we avoid line continuation.

      # my $command = qq($flag_string -w '\nhttp_code: \%{http_code}\n' -X $method --header "Accept: $Accept");
      # ideally we should use -w '\n' to print http code into a separate line - the last line,
      # but windows cmd.exe cannot handle line continuation.
      my $command = qq($flag_string -w "http_code: \%{http_code}" -X $method --header "Accept: $accept");

      if ($entry_name) {
         $command = "tpentry -- /usr/bin/curl -u tpentry{$entry_name}{user}:tpentry{$entry_name}{decoded} $command";
      } else {
         $command = "/usr/bin/curl $command";
      }

      if ( $method eq 'POST' ) {
         my $post_data = $cfg->{post_data};

         if ( defined $post_data ) {
            # sometimes curl's POST method doesn't want -d at all.
            # therefore don't use -d '' when it is not defined.

            if ( $post_data eq 'json_array_number' ) {
               # argv list are numbers, we want to convert them to json array
               $post_data = join( ',', @$args );
               $post_data = "[$post_data]";
            } elsif ( $post_data eq 'json_array_string' ) {
               # argv list are strings, we want to convert them to json array
               $post_data = join( ',', map { qq("$_") } @$args );
               $post_data = "[$post_data]";
            } else {
               $post_data = resolve_scalar_var_in_string( $post_data, $dict, $opt );
            }
            $post_data =~ s/"/\\"/g;    # escape double quote for windows cmd.exe
            $command .= qq( --header "Content-Type: application/json" -d "$post_data");
         }
      }

      $command .= qq( "$base_url/$sub_url");

      # if ( $accept =~ /json/ && $cfg->{json} && !$opt->{nojson} ) {
      #    # 'accept' is from caller of cfg
      #    # 'json' is from cfg
      #    # 'nojson' is from caller - likely from command line
      #    $command .= " |python -m json.tool";
      # }

      if ( $opt->{dryrun} ) {
         print "DRYRUN: $command\n";
      } else {
         print STDERR "command = $command\n";
         # system($command);
         my @lines = `$command`;
         my $rc    = parse_rc($?)->{rc};
         # if ( $verbose || $rc ) {
         #    print STDERR "rc=$rc\n";
         #    print STDERR "lines = ", Dumper(@lines);
         # }

         if ($rc) {
            print @lines;
            print STDERR "ERROR: command failed: rc=$rc\n";
            print "\n";
            exit 1;
         } else {
            # my $status_line = pop @lines;
            my $status_line = "unknown status line";
            if ( $lines[-1] =~ /^(.*)(http_code: \d+)$/ ) {
               $status_line = $2;
               $lines[-1] = $1;
            }

            if ( $accept =~ /json/ && $cfg->{json} && !$opt->{nojson} ) {
               # 'accept' is from caller of cfg
               # 'json' is from cfg
               # 'nojson' is from caller - likely from command line

               # python on linux could be python or python3. we use the first one found in PATH.
               my $python_cmd;
               for my $cmd ( 'python3', 'python' ) {
                  my $which_cmd = "which $cmd 2>/dev/null";
                  my $which_out = `$which_cmd`;
                  if ( $which_out =~ /(\S+)/ ) {
                     $python_cmd = $1;
                     last;
                  }
               }
               if ( !$python_cmd ) {
                  croak "cannot find python or python3 in PATH, needed for json parsing";
               }
               my $json_cmd = "$python_cmd -m json.tool";
               open my $ofh, "|$json_cmd" or die "cmd=$json_cmd failed: $!";
               print $ofh @lines;
               close $ofh;
               print STDERR $status_line, "\n";
            } else {
               print @lines;
               STDOUT->autoflush(1);    # flush STDOUT so that we can see the status line on bottom
               print STDERR $status_line, "\n";
            }
         }
      }
   }
}

my $swagger_syntax = {
   '^/$' => {
      cfg             => { type => 'HASH', required => 1 },
      package         => { type => 'SCALAR' },
      minimal_args    => { type => 'SCALAR' },
      'extra_getopts' => { type => 'ARRAY' },
      'extra_options' => { type => 'HASH' },
      'extra_args'    => { type => 'HASH' },
      'meta'          => { type => 'HASH' },                  # this comes from TPSUP::BATCH
      'pre_checks'    => { type => 'ARRAY' },
   },

   # non-greedy match
   # note: don't use ^/cfg/(.+?)/$, because it will match /cfg/abc/def/ghi/, not only /cfg/abc/
   '^/cfg/([^/]+?)/$' => {
      base_urls => { type => 'ARRAY', required => 1 },
      op        => { type => 'HASH',  required => 1 },
      entry     => { type => [ 'SCALAR', 'CODE' ] },
   },
   '^/cfg/([^/]+?)/op/([^/]+?)/$' => {
      sub_url   => { type => 'SCALAR', required => 1 },
      num_args  => { type => 'SCALAR', pattern  => qr/^(\d+|[+*])$/ },
      json      => { type => 'SCALAR', pattern  => qr/^\d+$/ },
      method    => { type => 'SCALAR', pattern  => qr/^(GET|POST|DELETE)$/ },
      accept    => { type => 'SCALAR' },
      comment   => { type => 'SCALAR' },
      validator => { type => [ 'SCALAR', 'CODE' ] },
      post_data => { type => 'SCALAR' },
      test_str  => { type => 'ARRAY' },
   },
};

sub tpbatch_parse_hash_cfg {
   my ( $hash_cfg, $opt ) = @_;

   # overwrite the default TPSUP::BATCH::parse_hash_cfg

   my $verbose = $opt->{verbose} || 0;

   if ($verbose) {
      print __FILE__ . " " . __LINE__ . " hash_cfg = ",       Dumper($hash_cfg);
      print __FILE__ . " " . __LINE__ . " swagger_syntax = ", Dumper($swagger_syntax);
   }
   check_syntax( $hash_cfg, $swagger_syntax, { fatal => 1 } );

   if ( !$hash_cfg->{usage_example} ) {
      my $example = "\n";

      for my $base ( sort ( keys %{ $hash_cfg->{cfg} } ) ) {
         my $base_cfg = $hash_cfg->{cfg}->{$base};

         for my $op ( sort ( keys %{ $base_cfg->{op} } ) ) {
            my $cfg = $base_cfg->{op}->{$op};
            # push down meta to lower level
            my @upper_keys = qw(base_urls entry entry_func);
            @{$cfg}{@upper_keys} = @{ $hash_cfg->{cfg}->{$base} }{@upper_keys};
            $cfg->{op}   = $op;
            $cfg->{meta} = $hash_cfg->{meta};
            $example .= "   {{prog}} $base $op";

            my $num_args = $cfg->{num_args} ? $cfg->{num_args} : 0;
            if ( "$num_args" eq '+' ) {
               $example .= " arg0 [arg1 arg2 ...]";
            } elsif ( "$num_args" eq '*' ) {
               $example .= " [arg0 arg1 arg2 ...]";
            } else {
               for ( my $i = 0 ; $i < $num_args ; $i++ ) {
                  $example .= " arg$i";
               }
            }

            $example .= "\n";

            $example .= "      $cfg->{comment}\n" if defined $cfg->{comment};

            my $accept = $cfg->{accept} ? $cfg->{accept} : 'application/json';

            if ( ( $accept =~ /json/ || $cfg->{json} ) && !$opt->{nojson} ) {
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

            my $method = $cfg->{method} || 'GET';
            $example .= "      method: $method\n";

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
               # add base_url to cfg, so that the entry function can use it
               $cfg->{base_url} = $base_url;
               my $login = get_entry_by_cfg( $cfg, {}, $opt );
               if ($login) {
                  $example .= "         entry: $login\n";
               } else {
                  $example .= "         entry: none\n";
               }
               $example .= "           curl: $base_url/$sub_url\n";

               $example .= "         manual: $base_url/$sub_ui\n\n";
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

our %known;    # global var for TPSUP::BATCH

sub tpbatch_parse_input {
   my ( $input, $all_cfg, $opt ) = @_;

   # this overrides the default TPSUP::BATCH::parse_input_default_way

   # command line like: tpswagger_test  mybase2 myop2_1 arg0 arg1
   #                                    base    op      args ...
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

   if ( $num_args eq '+' ) {
      # at least num_args
      if ( $num_input < 1 ) {
         print
           "ERROR: wrong number of args, expecting at least $num_args but got $num_input, input=",
           Dumper( \@copied );
         exit 1;
      }
   } elsif ( $num_args eq '*' ) {
      # 0 or more args
      1;
   } else {
      if ( $num_args != $num_input ) {
         print
           "ERROR: wrong number of args, expecting $num_args but got $num_input, input=",
           Dumper( \@copied );
         exit 1;
      }
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

my $parsed_entry_decide_file = {};

sub parse_login_by_method_pattern_file {
   my ( $pattern_file, $opt ) = @_;

   if ( !exists( $parsed_entry_decide_file->{$pattern_file} ) ) {
      my $ref = {};

      # pattern file format:
      #   login1:pattern1
      #   login2:pattern2
      open my $fh, "<", $pattern_file or croak "cannot open $pattern_file: $!";
      while ( my $line = <$fh> ) {
         next if $line =~ /^\s*#/;    # skip comment
         next if $line =~ /^\s*$/;    # skip empty line
         chomp $line;

         # remove dos ^M
         $line =~ s/\r//g;

         my ( $login, $method, $pattern ) = split /,/, $line, 3;
         $ref->{$method}->{$login} = $pattern;
      }

      close $fh;

      $parsed_entry_decide_file->{$pattern_file} = $ref;
      # print "parsed_pattern_file=", Data::Dumper::Dumper($TPSUP::SWAGGER::parsed_pattern_file), "\n";
   }

   return $parsed_entry_decide_file->{$pattern_file};
}

sub get_entry_by_method_suburl {
   my ( $cfg, $dict, $opt ) = @_;

   # print "cfg=", Data::Dumper->Dump([$cfg], ['cfg']), "\n";
   # print "dict=", Data::Dumper->Dump([$dict], ['dict']), "\n";

   my $entry_decide_file;    # this is not the password file. this is the file to decide which entry to use
   if ( $cfg->{entry_decide_file} ) {
      $entry_decide_file = $cfg->{entry_decide_file};
      croak "\$entry_decide_file is blank of not defined" if !$entry_decide_file;
   } else {
      $entry_decide_file = $cfg->{meta}->{cfg_abs_path};
      $entry_decide_file =~ s/_cfg_batch.pl/_pattern.cfg/;
      croak "\$entry_decide_file is blank or not defined" if !$entry_decide_file;
   }
   my $pattern_file = $entry_decide_file;
   my $pattern_cfg  = parse_login_by_method_pattern_file( $pattern_file, $opt );

   my $method = $cfg->{method} || 'GET';

   if ( $opt->{verbose} ) {
      print STDERR "pattern_file=$pattern_file\n";
      print STDERR "pattern_cfg=", Data::Dumper::Dumper($pattern_cfg), "\n";
   }

   if ( !exists $pattern_cfg->{$method} ) {
      croak "cannot find method $method in $pattern_file";
   }

   for my $login ( keys %{ $pattern_cfg->{$method} } ) {
      my $pattern = $pattern_cfg->{$method}->{$login};
      # print "login=$login, pattern=$pattern, sub_url=$cfg->{sub_url}\n";

      if (
         $cfg->{sub_url} =~ /$pattern/
         || "/$cfg->{sub_url}" =~ /$pattern/    # in case the the pattern requires the leading slash
        )
      {
         return $login;
      }
   }

   croak "cannot find login for method=$method, sub_url=$cfg->{sub_url} in $pattern_file";
}

sub main {
   # we don't export anything because this module is called by TPSUP::BATCH.
   print "------------ test swagger -----------------------------\n";
}

main() unless caller();

1
