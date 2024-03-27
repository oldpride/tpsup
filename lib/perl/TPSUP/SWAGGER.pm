package TPSUP::SWAGGER;

# swagger is web interface for RESTful API (web service)
# swagger calls curl to connect to the RESTful API
# therefore, without swagger, you can still use curl to connect to the RESTful API.
# swagger is just a wrapper around curl.
# in this module, only "sub_ui" part is for swagger.
# the rest is for curl. therefore, this module is mainly for curl.

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
      if ( swagger_eval_code( $validator, { %$opt, dict => $dict } ) ) {
         $verbose && print STDERR "validator test passed\n";
      } else {
         print STDERR "validator test failed: $validator\n";
         exit 1;
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

      #  entry     => 'swagger-tian',
      # entry_func => \&TPSUP::SWAGGER::get_swagger_entry,
      # entry_func overrides entry. entry_func is a subroutine reference.

      my $entry_name = $cfg->{entry};
      my $entry_func = $cfg->{entry_func};
      my $method     = $cfg->{method} ? $cfg->{method} : 'GET';
      my $Accept     = $cfg->{Accept} ? $cfg->{Accept} : 'application/json';

      # if entry_func overrides entry.
      if ($entry_func) {
         $entry_name = $entry_func->( $cfg, $dict, $opt );
      }

      # there are two places mentioning json
      #    --header 'Content-Type: application/json'
      #    --header 'Accept: application/json'
      # the 1st is for input when POST data. the 2nd is for output

      #  -w, --write-out <format>
      #   Make curl display information on stdout after a completed transfer.
      # we use -w to get http status code.

      my $command = "$flag_string -w '\nhttp_code: \%{http_code}\n' -X $method --header 'Accept: $Accept'";
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

            $post_data = resolve_scalar_var_in_string( $post_data, $dict, $opt );
            $command .= " --header 'Content-Type: application/json' -d '$post_data'";
         }
      }

      $command .= " '$base_url/$sub_url'";

      # if ( $Accept =~ /json/ && $cfg->{json} && !$opt->{nojson} ) {
      #    # 'Accept' is from caller of cfg
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
         if ($rc) {
            print @lines;
            print STDERR "ERROR: command failed: rc=$rc\n";
            exit 1;
         } else {
            my $status_line = pop @lines;

            if ( $Accept =~ /json/ && $cfg->{json} && !$opt->{nojson} ) {
               # 'Accept' is from caller of cfg
               # 'json' is from cfg
               # 'nojson' is from caller - likely from command line
               my $json_cmd = "python -m json.tool";
               open my $ofh, "|$json_cmd" or die "cmd=$json_cmd failed: $!";
               print $ofh @lines;
               close $ofh;
               print STDERR $status_line;
            } else {
               print @lines;
               STDOUT->autoflush(1);    # flush STDOUT so that we can see the status line on bottom
               print STDERR $status_line;
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
      base_urls  => { type => 'ARRAY', required => 1 },
      op         => { type => 'HASH',  required => 1 },
      entry      => { type => 'SCALAR' },
      entry_func => { type => 'CODE' },
   },
   '^/cfg/([^/]+?)/op/([^/]+?)/$' => {
      sub_url   => { type => 'SCALAR', required => 1 },
      num_args  => { type => 'SCALAR', pattern  => qr/^\d+$/ },
      json      => { type => 'SCALAR', pattern  => qr/^\d+$/ },
      method    => { type => 'SCALAR', pattern  => qr/^(GET|POST|DELETE)$/ },
      Accept    => { type => 'SCALAR' },
      comment   => { type => 'SCALAR' },
      validator => { type => 'SCALAR' },
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
   } else {
      $entry_decide_file = $cfg->{meta}->{cfg_abs_path};
      $entry_decide_file =~ s/_batch.cfg/_pattern.cfg/;
   }
   my $pattern_file = $entry_decide_file;
   #    print "pattern_file=$pattern_file\n";
   my $pattern_cfg = parse_login_by_method_pattern_file( $pattern_file, $opt );
   #    print "pattern_by_login=", Data::Dumper::Dumper($pattern_by_login), "\n";

   my $method = $cfg->{method} || 'GET';

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
   print "------------ test swagger -----------------------------\n";
}

main() unless caller();

1
