package TPSUP::TRACER;

use warnings;
use strict;

use base qw( Exporter );

# most subs don't need exporting because we will work in the same namespace
our @EXPORT_OK = qw(
  get_all_cfg
  parse_cfg
  get_keys_in_uppercase
  trace
);

use Data::Dumper;
$Data::Dumper::Sortkeys = 1;    # this sorts the Dumper output!
$Data::Dumper::Terse    = 1;    # print without "$VAR1="
use Getopt::Long;

use Carp;
my $saved_die_handler = $SIG{__DIE__};
$SIG{__DIE__} = \&Carp::confess;    # this stack-trace on all fatal error !!!

# we need this stack trace to catch run-time compile errors because we are using
# eval() intensively.

use TPSUP::SQL   qw(run_sql get_dbh dbh_do);
use TPSUP::CSV   qw(query_csv2);
use TPSUP::PRINT qw(render_arrays);
use TPSUP::UTIL  qw(
  get_abs_path
  get_first_by_key
  get_value_by_key_case_insensitive
  unify_hash
  unify_array_hash
  add_line_number_to_code
  get_node_list
  chkperl
  arrays_to_hashes
  hashes_to_arrays
  unique_array
  top_array
  tail_array
  resolve_scalar_var_in_string
  tp_quote_wrap
);

use TPSUP::FILE qw(get_in_fh close_in_fh tpfind);
use TPSUP::LOG  qw(
  get_log_sections
  get_log_section_headers
  eval_exp_to_sub
);
use TPSUP::DATE qw(get_yyyymmdd);
use strict;

# Use 'our' to make %known a package variable (gloabl variable) for user friendly coding
# because user will write plenty code using %known in cfg file
our %known = ();

# Using 'my %known = ()' would have made %known a lexical variable, limited by scoping.
# Sometimes it could run out of scope with error:
#    Variable "%known" is not available at (eval 10) line 1.
# In this situation, we would have to add a seemingly useless statement or assignment to
# bring %known back into scope. for example,
#    my $dummy = \%known;
# Therefore, using 'our %known = ()' seems to be a better choice.
# https://stackoverflow.com/questions/69559859/perl-eval-scope/

# perl 'my' vs 'our'
#
# my is a way to declare non-package variables, that are:
#
#    private
#    new
#    non-global
#    separate from any package, so that the variable cannot be accessed in the form of $package_name::variable.
#
# our variables are package variables, and thus automatically:
#
#    global variables
#    definitely not private
#    not necessarily new
#    can be accessed outside the package (or lexical scope) with the qualified namespace,
#    as $package_name::variable.

# like %know,these are also our 'reserved' words and requires 'our' so that eval'ed code
# in method=cmd will find it.
#
# we call the following GLOBAL BUFFER, to contrast global config, global vars, and
# global %known.
our %vars;         # entity-level vars
our $row_count;    # from cmd, db, log extract, whereever @lines/@arrays/@hashes is used.
our @lines;        # from cmd output, array of strings
our $output;       # from cmd output
our $rc;           # from cmd output
our @arrays;       # from db  output, array of arrays
our @headers;      # from db  output, array
our @hashes;       # from db/log extraction and section, array of hashes
our %hash1;        # converted from @hashes using $entity_cfg->{output_key}
our %r;            # only used by update_knowledge_from_row

# backoffice tracer is to search through the live cycle
#
# there are many search points, each from different user's perspective
#
# find the centeral point
#    this is the databases table has the most information.
#    the script will first try to reach this place, and then start trace life cycle
#
# modulize and each moduele can be called in multiple ways:
#   different combination of search key words

sub parse_input {
   my ( $input, $opt ) = @_;

   my $type = ref $input;
   my $input_array;
   if ( !$type ) {
      @$input_array = split /\s/, $input;
   } elsif ( $type eq 'ARRAY' ) {
      $input_array = $input;
   } else {
      croak "unknown type=$type of input";
   }

   my $ref = {};

   for my $pair (@$input_array) {
      if ( $pair =~ /^(any|check)$/i ) {

         # just ignore this. this allows us to run the script without specify key=value
      } elsif ( $pair =~ /^(.+?)=(.+)$/ ) {
         my ( $key, $value ) = ( uc($1), $2 );

         # convert key to upper case so that user can use both upper case and lower case
         # on command line.
         if ( $key =~ /QTY/ ) {
            $value =~ s/,//g;    #decommify
         }

         $ref->{$key} = $value;
      } else {
         print "\nERROR: '$pair' is not in 'key=value' format\n\n";
         exit 1;
      }
   }

   if ( $opt->{AliasMap} ) {
      for my $alias ( keys %{ $opt->{AliasMap} } ) {
         my $key = uc( $opt->{AliasMap}->{$alias} );

         if ( defined $ref->{ uc($alias) } ) {
            $ref->{$key} = $ref->{ uc($alias) };    # remember that $ref's keys are all upper case
         }
      }
   }

   check_allowed_keys( $ref, $opt->{AllowedKeys}, $opt );

   return $ref;
}

sub check_allowed_keys {
   my ( $href, $list, $opt ) = @_;

   return if !$list;
   return if !$href;

   my $allowed;
   for my $k (@$list) {
      $allowed->{ uc($k) } = 1;    # convert all keys to upper case as we go
   }

   for my $k ( keys %$href ) {
      if ( !$allowed->{$k} ) {
         print "'$k' is not a allowed key\n";
         exit 1;
      }
   }
}

sub get_keys_in_uppercase {
   my ( $cfg_by_entity, $opt ) = @_;

   my $seen;

   for my $entity ( keys %$cfg_by_entity ) {
      my $wc = $cfg_by_entity->{$entity}->{method_cfg}->{where_clause};
      next if !$wc;

      for my $k ( keys(%$wc) ) {
         $seen->{ uc($k) }++;
      }
   }

   if ( $opt->{ExtraKeys} ) {
      for my $k ( @{ $opt->{ExtraKeys} } ) {
         $seen->{ uc($k) }++;
      }
   }

   if ( $opt->{AliasMap} ) {
      my $alias_map = $opt->{AliasMap};
      for my $a ( keys(%$alias_map) ) {
         my $v = $alias_map->{$a};
         if ( !$seen->{ uc($v) } ) {
            print "'$v' is used in alias map but not seen in original keys even if case insensitive. seen keys = "
              . Dumper($seen);
            exit 1;
         }

         $seen->{ uc($v) }++;
         $seen->{ uc($a) }++;
      }
   }

   if ( $opt->{key_pattern} ) {
      for my $k ( keys %{ $opt->{key_pattern} } ) {
         $seen->{ uc($k) }++;
      }
   }

   my @keys = sort( keys %$seen );

   return @keys;
}

sub resolve_a_clause {
   my ( $clause, $Dict, $opt ) = @_;

   # first substitute the scalar var in {{...}}
   $opt->{verbose} && print "line ", __LINE__, " before substitution, clause = $clause, Dict = ", Dumper($Dict);

   $clause = resolve_scalar_var_in_string( $clause, $Dict, $opt );

   $opt->{verbose} && print "line ", __LINE__, " after substitution, clause = $clause\n";

   # we don't need this because we used 'our' to declare %known.
   # had we used 'my', we would have needed this.
   #my $touch_to_activate = \%known;

   # then eval() other vars, eg, $known{YYYYMMDD}
   my $clause2 = tracer_eval_code( $clause, { %$opt, Dict => $Dict } );

   return $clause2;
}

sub resolve_vars_array {
   my ( $vars, $Dict, $opt ) = @_;

   return {} if !$vars;

   # vars is a ref to array.
   my $type = ref $vars;
   croak "vars type is not ARRAY. vars = " . Dumper($vars)
     if !( $type && $type eq 'ARRAY' );

   my $ref;

   # copy to avoid modifying original data
   my $Dict2;
   %$Dict2 = %$Dict;
   my @vars2 = @$vars;

   while (@vars2) {
      my $k = shift @vars2;
      my $v = shift @vars2;

      my $v2 = resolve_a_clause( $v, $Dict2, $opt );

      $ref->{$k}   = $v2;
      $Dict2->{$k} = $v2;    # previous variables will be used to resolve later variables
   }

   return $ref;
}

sub cmd_output_string {
   my ( $cmd, $opt ) = @_;
   my $string = `$cmd`;
   chomp $string;
   return $string;
}

sub process_code {
   my ( $entity, $method_cfg, $opt ) = @_;

   # all handling have been done by caller, process_entity
}

my $method_syntax = {
   code => {
      required => [],
      optional => [],
   },
   db => {
      required => [qw(db db_type)],
      optional => [
         qw(table template where_clause order_clause example_clause
           extra_clause header)
      ],
   },
   cmd => {
      required => [qw(type value)],
      optional => [
         qw(example file grep logic MatchPattern ExcludePattern
           extract)
      ],
   },
   log => {
      required => [qw(log extract)],
      optional => [qw(MatchPattern ExcludePattern)],
   },
   section => {
      required => [qw(log ExtractPatterns)],
      optional => [
         qw( PreMatch   PreExclude
           PostMatch PostExclude
           BeginPattern EndPattern
           KeyAttr KeyDefault)
      ],
   },
   path => {
      required => [qw(paths)],
      optional => [qw(RecursiveMax HandleExp)],
   },
};

my $attr_syntax = {
   tests => {
      required => [qw(test)],
      optional => [qw(if_success if_failed condition)],
   },
};

my $entity_syntax = {
   required => [qw(method)],
   optional => [
      qw(method_cfg AllowZero AllowMultiple comment top tail update_key
        code pre_code post_code vars condition tests csv_filter
        MaxColumnWidth output_key)
   ],
};

sub resolve_files {
   my ( $cfg, $files_k, $opt ) = @_;

   my $files_v = get_value_by_key_case_insensitive( $cfg, $files_k );

   if ( !$files_v ) {
      croak "cannot find key='$files_k' (case-insensitive) in cfg=", Dumper($cfg);
   }

   # file => '/a/app.log /b/app.log' # multiple files, space separated
   # file => [ '/a/app.log', '/b/app.log' ] # multiple files using array
   # file => '{{adir}}/app.log}} {{bdir}}/app.log' # with vars
   # file => 'get_logs()' # paths are returned by a expression
   # file => '"/a/app.log"' # path returned by expressiobn
   # file => ['/cygdrive/c/program files/a/app.log']   # use array to specify path containing space
   # file => '"/cygdrive/c/program files/a/app.log"'   # use expression (str) for path containing space

   my @files;
   my $type = ref $files_v;
   if ( !$type ) {
      # if user used string, try to split by space.
      my $resolved = resolve_scalar_var_in_string( $files_v, { %known, %vars } );
      @files = split /\s+/, $resolved;
   } elsif ( $type eq 'ARRAY' ) {
      # if user used ARRAY, don't split it by space.
      for my $f (@$files_v) {
         my $resolved = resolve_scalar_var_in_string( $f, { %known, %vars } );
         push @files, $resolved;
      }
   } else {
      croak "unsupported type='$type' at files_v=" . Dumper($files_v);
   }

   # print "files = ", Dumper(@files);
   # exit 1;

   my @files2;
   for my $f (@files) {
      if ( $f =~ /^['"]*\// ) {
         # this is a full path
         #  /a/app.log
         #  "/a/app.log"
         #  '/a/app.log'
         push @files2, $f;
      } else {
         # this is a expression
         my $resolved = resolve_a_clause( $f, { %known, %vars }, $opt );
         push @files2, $resolved;
      }
   }

   my $files_str = '"' . join( '" "', @files2 ) . '"';

   croak "attr='file' is not resolved to any files at cfg=" . Dumper($cfg) if !$files_str;

   return $files_str;
}

sub process_cmd {
   my ( $entity, $method_cfg, $opt ) = @_;

   my $verbose = $opt->{verbose};

   my $cmd;
   if ( $opt->{isExample} ) {
      $cmd = $method_cfg->{example};
      if ( !defined($cmd) ) {
         print
           "ERROR: entity='$entity' attr='example' is not defined in method_cfg = ",
           Dumper($method_cfg);
         exit 1;
      }
   } elsif ( $method_cfg->{type} eq 'cmd' ) {
      $cmd = $method_cfg->{value};
   } elsif ( $method_cfg->{type} eq 'grep_keys' ) {
      my $files_str = resolve_files( $method_cfg, 'file' );

      my $grep_keys = get_value_by_key_case_insensitive( $method_cfg, 'value' );
      croak "attr='value' is not defined at method_cfg=" . Dumper($method_cfg)
        if !defined $grep_keys;

      my @patterns;
      for my $row (@$grep_keys) {
         my $type = ref $row;
         if ( !$type ) {
            my $key   = $row;
            my $value = get_first_by_key( [ \%vars, \%known ], $key );
            if ( defined $value ) {
               push @patterns, $value;
               print "$method_cfg->{type} using $key=$value\n";
            }
         } elsif ( $type eq 'HASH' ) {
            my $key = $row->{key};
            confess "attr='key' is not defined at row=" . Dumper($row)
              if !defined $key;

            my $value = get_first_by_key( [ \%vars, \%known ], $key );
            if ( defined $value ) {
               my $pattern = $row->{pattern};
               croak "attr='pattern' is not defined at row=" . Dumper($row)
                 if !defined $pattern;

               my $resolved_pattern = resolve_scalar_var_in_string( $pattern, { %known, %vars, opt_value => $value } );

               push @patterns, $resolved_pattern;
               print "$method_cfg->{type} using $key=$resolved_pattern\n";
            }
         } else {
            confess "unsupported type='$type' at row=" . Dumper($row);
         }
      }

      if ( !@patterns ) {
         print "none of the keys is defined in cmd = " . Dumper($method_cfg);
         return;
      }

      my $logic = get_value_by_key_case_insensitive( $method_cfg, 'logic', { default => 'OR' } );
      my $grep  = get_value_by_key_case_insensitive( $method_cfg, 'grep',  { default => 'zgrep -E' } );

      print "$method_cfg->{type} using logic = $logic\n";

      # zgrep can handle both compressed and uncompressed files, but cannot recursive
      # zgrep -E is like egrep

      if ( $logic eq 'OR' ) {
         $cmd = "$grep '" . join( '|', @patterns ) . "' $files_str";
      } elsif ( $logic =~ /AND/i ) {
         $patterns[0] = "$grep '$patterns[0]' $files_str";
         $cmd = join( " | egrep ", @patterns );
      } else {
         croak "unsupported logic='$logic' at cmd = " . Dumper($method_cfg);
      }
   } elsif ( $method_cfg->{type} eq 'pipe' ) {

      # 2D array,
      #    outer loop is connected by pipe
      #    inner loop is for OR logic for grep command.
      #
      # method_cfg => {
      #    type  => 'pipe',
      #    value => [
      #       ['grep=grep -E', 'OR11', 'OR12'],
      #       ['grep=grep -v -E', 'OR21', 'OR22'],
      #       ['grep=grep -E ',   'OR31', 'OR32'],
      #       ['cmd=grep -v -E "{{JUNK1=j1}}|{{JUNK2=j2}}"'],
      #       ['cmd=tail -10'],
      #    ],
      #    file => '/a/app.log',
      # },
      #
      #  if only $known{OR11}, $known{OR12}, $known{OR21} are defined, this will generate
      #    grep -E '{{OR11}}|{{OR12}}' app.log |grep -v -E '{{OR21}}'|grep -v "j1|j2"|tail -10
      #
      #  other value:
      #      ['tpgrepl=tpgrepl', 'TRADEID|ORDERID', 'x=BOOKID'],

      my $files_str = resolve_files( $method_cfg, 'file' );

      my $rows = get_value_by_key_case_insensitive( $method_cfg, 'value' );
      croak "attr='value' is not defined at method_cfg=" . Dumper($method_cfg)
        if !defined $rows;

      my @commands;
      for my $r (@$rows) {
         my $cmd2;
         if ( $r->[0] =~ /^grep=(.+)/ ) {
            $cmd2 = $1;

            my $r_length = scalar(@$r);
            if ( $r_length == 1 ) {
               croak "'grep' expects more elements, at " . Dumper($r);
            }

            my @values;
            for ( my $i = 1 ; $i < $r_length ; $i++ ) {
               my $k = $r->[$i];
               my $v = get_first_by_key( [ \%vars, \%known ], $k );
               if ( defined $v ) {
                  push @values, $v;
               }
            }

            next if !@values;

            $cmd2 .= " '" . join( '|', @values ) . "'";
         } elsif ( $r->[0] =~ /^tpgrepl=(.+)/ ) {
            $cmd2 = $1;

            # example:
            #    ['tpgrepl=tpgrepl', 'TRADEID|ORDERID', 'x=BOOKID'],

            my $r_length = scalar(@$r);
            if ( $r_length == 1 ) {
               croak "'tpgrepl' expects more elements, at " . Dumper($r);
            }

            my $some_key_defined;
            for ( my $i = 1 ; $i < $r_length ; $i++ ) {
               my $s = $r->[$i];

               # example: 'TRADEID|ORDERID'

               my $keys;
               my $is_exclude;
               if ( $s =~ /^x=(.+)/ ) {

                  # this is exclude
                  $keys       = $1;
                  $is_exclude = 1;
               } else {

                  # this is match
                  $keys = $s;
                  $keys =~ s/^m=//;
               }

               my @values;
               for my $k ( split( /[|]/, $keys ) ) {

                  # split 'TRADEID|ORDERID' into two
                  my $v = get_first_by_key( [ \%vars, \%known ], $k );

                  if ( defined $v ) {
                     push @values, $v;
                  }
               }
               next if !@values;

               $some_key_defined = 1;
               my $pattern = join( "|", @values );
               $pattern = tp_quote_wrap( $pattern, { ShellArg => 1 } );

               if ($is_exclude) {
                  $cmd2 .= " -x $pattern";
               } else {
                  $cmd2 .= " -m $pattern";
               }
            }

            next if !$some_key_defined;
         } elsif ( $r->[0] =~ /^cmd=(.+)/ ) {
            $cmd2 = resolve_scalar_var_in_string( $1, { %known, %vars } );
         } else {
            croak "unsupported row at " . Dumper($r);
         }

         if ( !@commands ) {

            # for first command
            $cmd2 .= " $files_str" if defined $files_str;
         }
         push @commands, $cmd2;
      }

      if ( !@commands ) {
         print "'method_cfg didn't resolve to any command. " . Dumper($method_cfg);
         return;
      } else {
         $cmd = join( "|", @commands );
      }
   } else {
      croak "unsupported type='$method_cfg->{type}' in cmd = ", Dumper($method_cfg);
   }

   # when combining hashes, make sure not poluting $known and $Dict
   $cmd = resolve_scalar_var_in_string( $cmd, { %known, %vars }, $opt );

   print "running cmd=$cmd\n";

   open my $fh, "$cmd|" or croak "couldn't run cmd=$cmd: $!";

   my $extract_pattern = $method_cfg->{extract};
   my $MaxExtracts     = $opt->{MaxExtracts};

   if ($extract_pattern) {
      print "extract info from output\n";
      my ( $h, $extracts ) = extract_from_fh(
         $fh,
         $extract_pattern,
         {
            %$opt,
            MatchPattern   => $method_cfg->{MatchPattern},
            ExcludePattern => $method_cfg->{ExcludePattern},
         },
      );

      # update global buffer
      @hashes    = @{$extracts};
      @headers   = @$h;
      $row_count = scalar(@hashes);
      @arrays    = @{ hashes_to_arrays( \@hashes, \@headers ) };
   } else {
      my $CompiledMatch;
      my $CompiledExclude;
      if ( defined( $method_cfg->{MatchPattern} ) ) {
         $CompiledMatch = qr/$method_cfg->{MatchPattern}/;
      }
      if ( defined( $method_cfg->{ExcludePattern} ) ) {
         $CompiledExclude = qr/$method_cfg->{ExcludePattern}/;
      }

      $verbose && print "\n---- output begin ----\n";
      my $count = 0;
      while ( my $line = <$fh> ) {
         next if defined($CompiledMatch)   && $line !~ /$CompiledMatch/;
         next if defined($CompiledExclude) && $line =~ /$CompiledExclude/;

         $verbose && print $line;
         push @lines, $line;

         $count++;
         if ( $count >= $MaxExtracts ) {
            print "(stopped extraction as we hit MaxExtracts=$MaxExtracts)";
            last;
         }
      }
      $verbose && print "---- output end ----\n\n";
   }

   close($fh);
   $rc = $?;

   $row_count = $extract_pattern ? scalar(@hashes) : scalar(@lines);
   $output    = '' . join( '', @lines );
}

sub perform_tests {
   my ( $tests, $opt ) = @_;

   my $verbose = $opt->{verbose};

   return if !$tests || !@$tests;

   $verbose && print "\n---- testing result ----\n\n";

   for my $item (@$tests) {
      my ( $test, $if_success, $if_failed, $condition ) =
        @{$item}{qw(test   if_success   if_failed   condition)};

      next if !defined $test;

      if ( defined($condition) ) {
         if ( !tracer_eval_code( $condition, $opt ) ) {
            print "OK, condition=$condition failed. skipped test\n";
            next;
         }
      }
      if ( tracer_eval_code( $test, $opt ) ) {
         $verbose && print "test success\n";
         tracer_eval_code( $if_success, $opt ) if defined $if_success;
      } else {
         $verbose && print "test failed\n";
         tracer_eval_code( $if_failed, $opt ) if defined $if_failed;
      }
   }
}

sub extract_from_fh {
   my ( $fh, $extract_pattern, $opt ) = @_;

   my $verbose     = $opt->{verbose} ? $opt->{verbose} : 0;
   my $MaxExtracts = $opt->{MaxExtracts};

   # https://stackoverflow.com/questions/2304577/how-can-i-store-regex-captures-in-an-array-in-perl
   # extract_pattern => 'orderid=(?<ORDERID>{{pattern::ORDERID}}),.*tradeid=(?<TRADEID>{{pattern::TRADEID}}),.*sid=(?<SID>{{pattern::SID}}),.*filledqty=(?<FILLEDQTY>{{pattern::FILLEDQTY}}),',

   my @capture_keys = ( $extract_pattern =~ /\?<([a-zA-Z0-9_]+?)>/g );
   my $headers      = unique_array( [ \@capture_keys ] );

   print "origial extract_pattern = $extract_pattern\n";
   $extract_pattern = apply_key_pattern( $extract_pattern, $opt );
   $extract_pattern = resolve_scalar_var_in_string( $extract_pattern, { %vars, %known }, $opt );
   print "resolved extract_pattern = $extract_pattern\n";

   my $CompiledExtract = qr/$extract_pattern/;
   my $CompiledMatch;
   my $CompiledExclude;
   if ( defined( $opt->{MatchPattern} ) ) {
      $CompiledMatch = qr/$opt->{MatchPattern}/;
   }
   if ( defined( $opt->{ExcludePattern} ) ) {
      $CompiledExclude = qr/$opt->{ExcludePattern}/;
   }

   my $match_count = 0;
   my @tally;

   $verbose && print "\n---- match begin -----\n";
   while ( my $line = <$fh> ) {
      next if defined($CompiledMatch)   && $line !~ /$CompiledMatch/;
      next if defined($CompiledExclude) && $line =~ /$CompiledExclude/;

      if ( $line =~ /$CompiledExtract/ ) {
         $verbose && print "matched: $line";

         next if !%+;

         my %match = %+;

         $verbose && print "matched = ", Dumper(%match);

         push @lines, $line;
         push @tally, \%match;

         $match_count++;

         if ( $match_count >= $MaxExtracts ) {
            print "(stopped extraction as we hit MaxExtracts=$MaxExtracts)";
            last;
         }
      } else {
         $verbose > 1 && print "unmatched: $line";
      }
   }
   $verbose && print "---- match end -----\n";

   return ( $headers, \@tally );
}

sub apply_key_pattern {
   my ( $string, $opt ) = @_;

   # line_pattern => 'orderid=(?<ORDERID>{{pattern::ORDERID}}),.*tradeid=(?<TRADEID>{{pattern::TRADEID}}),.*sid=(?<SID>{{pattern::SID}}),.*filledqty=(?<FILLEDQTY>{{pattern::FILLEDQTY}}),',

   my $scalar_key_pattern = qr/\{\{pattern::([0-9a-zA-Z_.-]+)\}\}/;

   my @needed_keys = ( $string =~ /$scalar_key_pattern/g );    # get all matches

   my $all_cfg = get_all_cfg();

   my $key_pattern = $all_cfg->{key_pattern};

   for my $k (@needed_keys) {
      confess "'{{pattern::$k}}' in '$string' but '$k' is not defined in key_pattern=" . Dumper($key_pattern)
        if !$key_pattern->{$k};
   }

   for my $k (@needed_keys) {
      my $substitue =
        defined $known{$k} ? $known{$k} : $key_pattern->{$k}->{pattern};
      $string =~ s/\{\{pattern::$k\}\}/$substitue/g;
   }

   return $string;
}

sub process_log {
   my ( $entity, $method_cfg, $opt ) = @_;

   my $verbose = $opt->{verbose};

   my $log = $method_cfg->{log};

   my $resolved_log = resolve_a_clause( $log, { %vars, %known }, $opt );

   $verbose && print "resolved log = $resolved_log\n";

   my @logs;
   my $log_type = ref $resolved_log;
   if ( !$log_type ) {
      @logs = ($resolved_log);
   } elsif ( $log_type eq 'ARRAY' ) {
      @logs = @$resolved_log;
   } else {
      croak "unsuppported resolved log type=$log_type, resolved log=" . Dumper($resolved_log);
   }

   my $extract_pattern = $method_cfg->{extract};
   my $MaxExtracts     = $opt->{MaxExtracts};

   for my $log (@logs) {
      my $fh = get_in_fh($log);
      print "extract info from $log\n";
      my ( $h, $extracts ) = extract_from_fh(
         $fh,
         $extract_pattern,
         {
            %$opt,
            MatchPattern   => $method_cfg->{MatchPattern},
            ExcludePattern => $method_cfg->{ExcludePattern},
         },
      );

      # update global buffer
      push @hashes, @$extracts;
      @headers = @$h;
      close_in_fh($fh);

      my $count = scalar(@hashes);
      if ( $count >= $MaxExtracts ) {
         print "(stopped extraction as count=$count >= MaxExtracts=$MaxExtracts)";
         last;
      }
   }

   # update global buffer
   $row_count = scalar(@hashes);
   @arrays    = @{ hashes_to_arrays( \@hashes, \@headers ) };
}

sub process_section {
   my ( $entity, $method_cfg, $opt ) = @_;

   my $verbose = $opt->{verbose};

   my $log = $method_cfg->{log};

   my $resolved_log = resolve_a_clause( $log, { %vars, %known }, $opt );

   print "resolved log = $resolved_log\n\n";

   my @logs;
   my $log_type = ref $resolved_log;
   if ( !$log_type ) {
      @logs = ($resolved_log);
   } elsif ( $log_type eq 'ARRAY' ) {
      @logs = @$resolved_log;
   } else {
      croak "unsuppported resolved log type=$log_type, resolved log=" . Dumper($resolved_log);
   }

   my $MaxExtracts = $opt->{MaxExtracts};
   my $count       = 0;
   for my $l (@logs) {
      my $sections = get_log_sections( $l, $method_cfg, { %$opt, MaxSections => $MaxExtracts } );

      if ($sections) {
         push @hashes, @$sections;

         for my $section (@hashes) {
            if ( $section->{lines} ) {
               $verbose > 1 && print @{ $section->{lines} };
               push @lines, @{ $section->{lines} };
            }
         }

         $count += scalar(@$sections);
         last if $count >= $MaxExtracts;
      }
   }

   @headers =
     @{ get_log_section_headers( $method_cfg->{ExtractPatterns}, $opt ) };
   @arrays    = @{ hashes_to_arrays( \@hashes, \@headers ) };
   $row_count = scalar(@hashes);
}

sub apply_csv_filter_href {
   my ( $filter1, $opt ) = @_;

   return if !defined $filter1;    # do nothing if no filter
   my $type = ref($filter1);
   $type = "" if !$type;

   if ( $type ne 'HASH' ) {
      croak "wrong type='$type'. Only HASH is supported";
   }

   # example of $filter1:
   #            {
   #             ExportExps => [
   #                'weight=$STATUS eq "COMPLETED" ? 0 : $STATUS eq "PARTIAL" ? 1 : 2',
   #                ],
   #              SortKeys => [ 'weight' ],
   #            },

   my $filter2;
   my $changed;
   for my $k ( sort ( keys %$filter1 ) ) {
      if ( $k =~ /Exps/ ) {
         my $Exps1 = $filter1->{$k};
         next if !$Exps1 || !@$Exps1;

         my $Exps2 = [];
         for my $e1 (@$Exps1) {
            my $e2 = resolve_scalar_var_in_string( $e1, { %vars, %known }, $opt );
            $e2 = apply_key_pattern( $e2, $opt );

            $changed++ if $e2 ne $e1;
            push @$Exps2, $e2;
         }

         $filter2->{$k} = $Exps2;
      } else {
         $filter2->{$k} = $filter1->{$k};
      }
   }

   if ($changed) {
      print "original filter1 = ", Dumper($filter1);
      print "resolved filter2 = ", Dumper($filter2);
   } else {
      print "static filter2 = ", Dumper($filter2);
   }

   return $filter2;
}

sub apply_csv_filter {

   # this sub relies on gloabl buffer and only affects global buffer
   my ( $filters, $opt ) = @_;

   return if !defined $filters;    # do nothing if no filter
   my $type = ref($filters);
   $type = "" if !$type;

   if ( $type ne 'ARRAY' && $type ne 'HASH' ) {
      croak "wrong type='$type'. Only ARRAY and HASH are supported";
   } elsif ( $type eq 'HASH' ) {
      $filters = [ [], $filters ];
   }

   # examples:
   # can be array, which depending knowledge keys
   # $csv_filter => [
   #          [
   #            [ ], # depending keys, like entry_points
   #            {
   #             ExportExps => [
   #                'weight=$STATUS eq "COMPLETED" ? 0 : $STATUS eq "PARTIAL" ? 1 : 2',
   #                ],
   #              SortKeys => [ 'weight' ],
   #            },
   #          ]
   #       ],
   # can be Hash
   # $csv_filter =>
   #       {
   #          ExportExps => [
   #             'weight=$STATUS eq "COMPLETED" ? 0 : $STATUS eq "PARTIAL" ? 1 : 2',
   #             ],
   #          SortKeys => [ 'weight' ],
   #       },

   my $filter3 = {};
 ROW:
   for my $row (@$filters) {
      my ( $keys, $href ) = @$row;

      for my $k (@$keys) {
         next ROW if !defined $known{$k};
      }

      my $filter4 = apply_csv_filter_href( $href, $opt );
      $filter3 = { %$filter3, %$filter4 };
   }

   if ( $type eq 'ARRAY' ) {

      # if $type was HASH, it was already printed by apply_csv_filter()
      # if $type was ARRAY, we print the finalized filter
      print "filter3 = ", Dumper($filter3);
   }

   my $PrintCsvMaxRows = $opt->{MaxExtracts};

   my $StructuredHashArray = query_csv2(
      { columns => \@headers, array => \@hashes },    # these are in global buffer
      {
         InputType           => 'StructuredHash',
         RenderStdout        => 1,
         PrintCsvMaxRows     => $PrintCsvMaxRows,
         PrintCsvMaxRowsWarn => 1,
         NoPrint             => !$opt->{verbose},
         %$filter3
      }
   );

   # update global buffer
   @headers   = @{ $StructuredHashArray->{columns} };
   @hashes    = @{ $StructuredHashArray->{array} };
   @arrays    = @{ hashes_to_arrays( \@hashes, \@headers ) };
   $row_count = scalar(@hashes);

   return;    #this sub affects global buffer, therefore, nothing to return
}

sub run_cmd {
   my ( $cmd, $opt ) = @_;

   print "\ncmd = $cmd\n\n";

   system($cmd);
}

sub craft_sql {
   my ( $entity, $method_cfg, $dict, $opt ) = @_;

   my $footer = "";

   my $MaxExtracts = $opt->{MaxExtracts};

   my $template = $method_cfg->{template};
   if ($template) {

      # for example

      # select  *
      # from (
      #   select
      #     PosQty - LAG(PosQty, 1, 0) OVER (Order By LastUpdateTime) as TradeQty,
      #     '{{YYYYMMDD}}' as day,
      #     *
      #    from
      #     Position (nolock)
      #   where
      #     1 = 1
      #     {{where::YYYYMMDD}}
      #     {{where::ACCOUNT}}
      #     {{where::SECURITYID}}
      #     {{where::LE}}
      #     and PosQty is not null
      #   )
      # where
      #   1=1
      #   {{where::QTY}}

      # will be resolved to

      # select  *
      # from (
      #   select
      #     PosQty - LAG(PosQty, 1, 0) OVER (Order By LastUpdateTime) as TradeQty,
      #     '20211101' as day,
      #     *
      #    from
      #     Position (nolock)
      #   where
      #     TradeDate = '20211101'
      #     and Account = 'BLK12345'
      #     and SecurityId = '437855'
      #     and LegalEntity = 'ABC'
      #     and PosQty is not null
      #   )
      # where TradeQty = 2000

      # note:
      #   use where:: to difference regular var to be replaced by $dict and var to
      #   be replaced by where_clause. YYYYMMDD above is an example
      # default template is shown below

   } else {
      my $table = defined $method_cfg->{table} ? $method_cfg->{table} : $entity;

      my $db_type = $method_cfg->{db_type};

      # nolock setting is easy in MSSQL using DBD
      #
      # however, for mysql, i am not sure what to do yet
      #
      # i followed the following two links
      #    https://stackoverflow.com/questions/917640/any-way-to-select-without-causing-locking-in-mysql
      #    https://www.perlmonks.org/?node_id=1074673

      my $mssql_specific1 = "";
      my $mssql_specific2 = "";

      my $mysql_specific1 = "";

      my $is_mssql;
      my $is_mysql;

      if ($db_type) {
         if ( $db_type =~ /mssql/i ) {
            $is_mssql = 1;

            $mssql_specific1 = "top $MaxExtracts";
            $mssql_specific2 = 'with (nolock)';
         } elsif ( $db_type =~ /mysql/i ) {
            $is_mysql = 1;

            $mysql_specific1 = "LIMIT $MaxExtracts;";
         }
      }

      my $header = $method_cfg->{header} ? $method_cfg->{header} : '*';

      # header's function can be replaced by template
      # example
      #    table  => 'mytable',
      #    header => 'count(*) as TotalRows',
      #    where_clause => { YYYYMMDD => 'TradeDate' },
      # can be replaced by
      #    template => '
      #       select count(*) as TotalRows
      #         from mytable
      #         where 1=1
      #               {{where::YYYYMMDD}}
      #    ',
      #    where_clause => { YYYYMMDD => 'TradeDate' },

      # this is the default template
      $template = " 
      select $mssql_specific1 $header
        from $table $mssql_specific2
       where 1 = 1
{{where_clause}}
      ";
      $footer = "$mysql_specific1";
   }

   my $wc = $method_cfg->{where_clause};

   my $where_block = "";
   if ($wc) {
      for my $key ( sort keys(%$wc) ) {
         my $opt_value = get_first_by_key( [ $opt, $dict ], $key );
         if ( !defined $opt_value ) {
            $template =~ s/\{\{where::$key\}\}//g;
            next;
         }

         my $info = $wc->{$key};
         my $type = ref($info);

         my ( $clause, $column, $numeric, $if_exp, $else_clause );

         my $string;

         if ( $type eq 'HASH' ) {
            ( $clause, $column, $numeric, $if_exp, $else_clause ) =
              @{$info}{qw(clause   column   numeric   if_exp   else_clause)};

            # if 'if_exp' is defined
            #    if 'if_exp' is true, then the clause is added;
            #    otherwise, optional 'else_clause" is added.
            # if 'if_exp' is not defined, then clause is added.

            if ( defined($if_exp) ) {
               if ( !tracer_eval_code( $if_exp, $opt ) ) {
                  if ( defined($else_clause) ) {

                     # if 'if_exp' is defined and is false and 'else_clause' is defined,
                     # then use else_clause as clause
                     $clause = $else_clause;
                  } else {
                     next;
                  }
               }
            }

            if ($clause) {
               $clause = resolve_scalar_var_in_string( $clause, { %$dict, opt_value => $opt_value }, $opt );
               $string = "and $clause";
            } elsif ( !defined $column ) {
               $column = $key;
            }
         } else {
            $column = $info;
         }

         if ( !$string ) {
            if ($numeric) {
               $opt_value =~ s/,//g;    #decommify
               $string = "and $column =  $opt_value";
            } else {
               $string = "and $column = '$opt_value'";
            }
         }

         $where_block .= "             $string\n";
         $template =~ s/\{\{where::$key\}\}/$string/g;
      }
   }

   $template =~ s/\{\{where_clause\}\}/$where_block/g;

   if ( $opt->{isExample} ) {
      my $ec = $method_cfg->{example_clause};
      if ($ec) {

         #$sql .= "             and $ec\n";
         $template .= "             and $ec\n";
      }
   }

   my $sql = $template;

   my $extra_clause = $method_cfg->{extra_clause};
   if ($extra_clause) {
      $sql .= "             and $extra_clause\n";
   }

   my $TrimSql = get_first_by_key( [ $opt, $method_cfg ], 'TrimSql' );
   if ($TrimSql) {

      # make Trim optional because it is actually easier to modify the sql with \
      # the '1=1' - we only need to comment out a unneeded clause with '--'

      # trim unnecessary where clause
      if ( $sql =~ /where 1 = 1\n$/s ) {    # multiline regex
                                            # trim
                                            #       select  *
                                            #         from tblMembers
                                            #        where 1 = 1
                                            #  to
                                            #
                                            #       select  *
                                            #         from tblMembers

         $sql =~ s/[^\n]*where 1 = 1\n$//s; # multiline regex
      } elsif ( $sql =~ /where 1 = 1\n\s*and/s ) {    # multiline regex
                                                      # trim
                                                      #       select  *
                                                      #         from tblMembers
                                                      #        where 1 = 1
                                                      #              and lastname = 'Tianhua'
                                                      #  to
                                                      #
                                                      #       select  *
                                                      #         from tblMembers
                                                      #        where lastname = 'Tianhua'

         $sql =~ s/where 1 = 1\n\s*and/where /s;      # multiline regex
      }
   }

   my $order_clause = $method_cfg->{order_clause};
   if ($order_clause) {
      $sql .= "             $order_clause\n";
   }

   $sql .= $footer;

   # resolve the rest scalar vars at the last moment to avoid resolve where_clause vars.
   my $resolved_sql = resolve_scalar_var_in_string( $sql, $dict, $opt );

   return $resolved_sql;
}

sub process_db {
   my ( $entity, $method_cfg, $opt ) = @_;

   my $table = $method_cfg->{table} ? $method_cfg->{table} : $entity;

   my $sql = craft_sql( $table, $method_cfg, { %vars, %known }, $opt );

   my $db_type = $method_cfg->{db_type};
   my $db      = $method_cfg->{db};

   my $is_mysql;
   if ($db_type) {
      if ( $db_type =~ /mysql/i ) {
         $is_mysql = 1;
      }
   }

   if ($is_mysql) {
      my $dbh = get_dbh( { nickname => $db } );
      $dbh->{AutoCommit} = 0;    # Disable global leverl, so we can SET FOR TRANSACTION LEVEL

      my $setting = 'SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED ;';
      print "$setting\n\n";
      $dbh->do($setting);
   }

   print qq(sql $db "$sql"\n\n);
   my $result = run_sql(
      $sql,
      {
         nickname     => $db,
         RenderOutput => 1,
         ReturnDetail => 1,

         # we don't print output here, we will print after
         # csv_filter. But if under debug, we print.
         output => $opt->{verbose} ? '-' : undef,
      }
   );
   print "\n";

   if ($is_mysql) {
      my $setting = 'COMMIT ;';
      print "$setting\n\n";
      dbh_do( $setting, { nickname => $db } );
   }

   if ( $result && $result->{aref} ) {

      # set the global buffer for post_code
      @arrays    = @{ $result->{aref} };
      @headers   = @{ $result->{headers} };
      @hashes    = @{ arrays_to_hashes( \@arrays, \@headers ) };
      $row_count = scalar(@arrays);
   }
}

sub process_path {
   my ( $entity, $method_cfg, $opt ) = @_;

   my $verbose = $opt->{verbose};

   my ( $paths, $RecursiveMax, $HandleExp ) =
     @{$method_cfg}{qw(paths   RecursiveMax   HandleExp)};

   # $file = resolve_scalar_var_in_string($file, {%known, %vars});
   my @resolved_paths =
     map { resolve_scalar_var_in_string( $_, { %known, %vars } ) } @$paths;

   #$RecursiveMax = 1 if ! defined $RecursiveMax;  # 1 means one level, not recursive

   if ($HandleExp) {
      $HandleExp = resolve_scalar_var_in_string( $HandleExp, { %known, %vars } );
   } else {
      $HandleExp = 1;
   }

   my $HandleAct = 'push @TPSUP::TRACER::hashes, get_all()';
   if ($verbose) {
      $HandleAct = 'print "matched $path\n"; ' . $HandleAct;
   }

   my $opt2 = {
      %$opt,
      Enrich       => 1,
      RecursiveMax => $RecursiveMax,
      HandleExps   => [$HandleExp],
      HandleActs   => [$HandleAct],
      verbose      => $verbose,
   };

   $verbose && print "opt2 = ", Dumper($opt2);

   tpfind( \@resolved_paths, $opt2 );

   $row_count = scalar(@hashes);
}

sub reset_global_buffer {

   # this only reset global buffer, not global config, nor global vars, neither %known.

   # all these should be reserved words
   my $all_cfg = get_all_cfg();

   %vars      = %{ $all_cfg->{global_vars} };
   @lines     = ();
   @arrays    = ();
   @headers   = ();
   @hashes    = ();
   %hash1     = ();
   %r         = ();
   $row_count = 0;
   $rc        = undef;
   $output    = undef;
}

sub print_global_buffer {

   # mainly for debug purpose
   print "\nprint global buffer \n";
   print '%vars      =', Dumper( \%vars );
   print '@lines     =', Dumper( \@lines );
   print '@arrays    =', Dumper( \@arrays );
   print '@headers   =', Dumper( \@headers );
   print '@hashes    =', Dumper( \@hashes );
   print '%hash1     =', Dumper( \%hash1 );
   print '%r         =', Dumper( \%r );
   print '$row_count =', Dumper($row_count);
   print '$rc        =', Dumper($rc);
   print '$output    =', Dumper($output);
   print "\n";
}

my $processor_by_method = {
   code    => \&process_code,
   db      => \&process_db,
   cmd     => \&process_cmd,
   log     => \&process_log,
   path    => \&process_path,
   section => \&process_section,
};

sub process_entity {
   my ( $entity, $entity_cfg, $opt ) = @_;

   # this pushes back up the setting
   $opt->{verbose} = $opt->{verbose} ? $opt->{verbose} : 0;
   my $verbose = $opt->{verbose};

   $verbose > 1 && print "$entity entity_cfg = ", Dumper($entity_cfg);

   my $entity_vars = $entity_cfg->{vars};
   if ($entity_vars) {
      $entity_vars = resolve_vars_array( $entity_vars, { %vars, %known, entity => $entity }, $opt );
      $verbose && print "resolved entity=$entity entity_vars=", Dumper($entity_vars);
   } else {
      $entity_vars = { entity => $entity };
   }

   # we check entity-level condition after resolving entity-level vars.
   # if we need to set up a condition before resolving entity-level vars, do it in
   # the trace_route. If trace_route cannot help, for example, when isExample is true,
   # then convert the var section into using pre_code to update %known

   %vars = ( %vars, %$entity_vars );
   $verbose && print "vars = ", Dumper( \%vars );

   my $condition = $entity_cfg->{condition};

   if (
      defined($condition)

      # && !$opt->{isExample}     # condition needs to apply to example too
      && !tracer_eval_code( $condition, $opt )
     )
   {
      print "\nskipped entity=$entity due to failed condition: $condition\n\n";
      return;
   }

   print <<"EOF";

-----------------------------------------------------------

process $entity

EOF

   my $comment =
     get_first_by_key( [ $opt, $entity_cfg ], 'comment', { default => '' } );
   if ($comment) {
      $comment = resolve_scalar_var_in_string( $comment, { %vars, %known }, $opt );
      print "$comment\n\n";
   }

   my $method    = $entity_cfg->{method};
   my $processor = $processor_by_method->{$method};

   croak "unsupported method=$method at entity='$entity'" if !$processor;

   tracer_eval_code( $entity_cfg->{pre_code}, $opt )
     if defined $entity_cfg->{pre_code};

   # $MaxExtracts is different from 'Top'
   #    'Top' is only to limit display
   #    'MaxExtracts' is only to limit memory usage
   #my $MaxExtracts
   #   = get_first_by_key([$opt, $entity_cfg], 'MaxExtracts', {default=>10000});
   #$opt->{MaxExtracts} = $MaxExtracts;
   $opt->{MaxExtracts} = $opt->{MaxExtracts} ? $opt->{MaxExtracts} : 10000;

   my $method_cfg = $entity_cfg->{method_cfg};

   $processor->( $entity, $method_cfg, $opt );

   my $output_key = $entity_cfg->{output_key};
   if ($output_key) {

      # converted from hash array to a single hash
      for my $row (@hashes) {
         my $v = $row->{$output_key};

         if ( !defined $v ) {
            die "ERROR: output_key=$output_key is not defined in row=", Dumper($row);
         }

         push @{ $hash1{$v} }, $row;
      }
   }

   $verbose > 1 && print_global_buffer();

   tracer_eval_code( $entity_cfg->{code}, $opt ) if defined $entity_cfg->{code};

   $verbose > 1 && print_global_buffer();

   # should 'example' be applyed by filter?
   #     pro: this can help find specific example
   #     con: without filter, it opens up more example, avoid not finding any example
   #if (!$opt->{isExample}) {
   #   # this affects global variables
   #   apply_csv_filter($entity_cfg->{csv_filter});
   #}
   apply_csv_filter( $entity_cfg->{csv_filter}, $opt );

   my $Tail =
     get_first_by_key( [ $opt, $entity_cfg ], 'tail', { default => undef } );
   my $Top = get_first_by_key( [ $opt, $entity_cfg ], 'top', { default => 5 } );

   # display the top results
   if (@lines) {
      print "----- lines begin ------\n";

      #print @lines[0..$Top];  # array slice will insert undef element if beyond range.
      if ($Tail) {
         print @{ tail_array( \@lines, $Tail ) };
      } else {
         print @{ top_array( \@lines, $Top ) };
      }
      print "----- lines end ------\n";
      print "\n";

      # $row_count is not reliable
      #    - sometime the code forgot updating it
      #    - it is ambiguous: scalar(@lines) and scalar(@hashes) may not be the same.
      my $count = scalar(@lines);
      if ($Tail) {
         print "(Truncated. Total $count, only displayed tail $Tail.)\n"
           if $count > $Tail;
      } else {
         print "(Truncated. Total $count, only displayed top  $Top.)\n"
           if $count > $Top;
      }
   }

   if (@headers) {
      my $MaxColumnWidth = $entity_cfg->{MaxColumnWidth};
      print "MaxColumnWidth = $MaxColumnWidth\n" if defined $MaxColumnWidth;

      render_arrays(
         \@hashes,
         {
            %$opt,
            MaxColumnWidth  => $MaxColumnWidth,
            MaxRows => $Top,
            headers         => \@headers,
            RenderHeader    => 1,
         }
      );
      print "\n";
      my $count = scalar(@hashes);
      print "(Truncated. Total $count, only displayed top $Top.)\n"
        if $count > $Top;
   }

   if ( @hashes && ( $verbose || !@headers ) ) {

      # we print this only when we didn't call render_arrays() or verbose mode
      print Dumper( top_array( \@hashes, $Top ) );
      print "\n";
      my $count = scalar(@hashes);
      print "(Truncated. Total $count, only displayed top $Top.)\n"
        if $count > $Top;
   }

   if ( !$opt->{isExample} ) {
      my $AllowZero     = get_first_by_key( [ $opt, $entity_cfg ], 'AllowZero',     { default => 0 } );
      my $AllowMultiple = get_first_by_key( [ $opt, $entity_cfg ], 'AllowMultiple', { default => 0 } );

      if ( !$row_count ) {
         if ($AllowZero) {
            print "WARN: matched 0 rows. but AllowZero=$AllowZero.\n\n";
         } else {
            print "ERROR: matched 0 rows.\n\n";
            if ( exists $entity_cfg->{method_cfg} ) {
               print "methond_cfg = ", Dumper( $entity_cfg->{method_cfg} );
            }
            die "(no need stack trace)";
         }
      } elsif ( $row_count > 1 ) {
         if ($AllowMultiple) {
            print
"WARN:  matched multiple ($row_count) rows, but AllowMultiple=$AllowMultiple, so we will use the 1st one.\n\n";
         } else {
            print "ERROR: matched multiple ($row_count) rows. please narrow your search.\n\n";
            if ( exists $entity_cfg->{method_cfg} ) {
               print "methond_cfg = ", Dumper( $entity_cfg->{method_cfg} );
            }
            die "(no need stack trace)";
         }
      }
   }

   if ( $hashes[0] ) {

      # only return the first row
      # %r is a global var
      %r = %{ $hashes[0] };
   }

   if ( exists $entity_cfg->{method_cfg}->{where_clause} ) {
      my $update_key =
        unify_hash( $entity_cfg->{method_cfg}->{where_clause}, 'column' );
      update_knowledge_from_rows( \%r, $update_key, $opt ) if $update_key;
   }

   if ( exists $entity_cfg->{update_key} ) {
      my $update_key = $entity_cfg->{update_key};
      update_knowledge_from_rows( \%r, $update_key, $opt ) if $update_key;
   }

   return if $opt->{isExample};

   # update_knowledge first and then run 'tests' and 'post_code', so that they
   # could use new knowledge
   perform_tests( $entity_cfg->{tests}, $opt );    # tests can be undef

   tracer_eval_code( $entity_cfg->{post_code}, $opt )
     if defined $entity_cfg->{post_code};

   print "knowledge = ", Dumper( \%known );

   return \%r;
}

sub update_knowledge_from_rows {
   my ( $row, $cfg, $opt ) = @_;

   #print __LINE__, "\n";

   return if !$row || !(%$row);    # 'if (%hash)' is to test hash emptiness
   return if !$cfg;

   my $type = ref $row;
   $type = '' if !$type;
   if ( $type ne 'HASH' ) {
      confess "unsupported type='$type'. need to be HASH. row=", Dumper($row);
   }

   %r = %$row;

   # $key_cfg is mapping between $known's keys and $rows' keys (column names), as they may
   # be different in spelling
   # $key_cfg = {
   #    known_key1 => 'row_key1',  # this converted to below after unify_hash() call.
   #    known_key1 => { column=>row_key1 },
   #    known_key2 => { column=>row_key2, flag2=>value },
   #    known_key3 => { flag3=>value },    # here we default column = known_key3
   #    known_key4 => {},                  # here we default column = known_key4
   #    ...
   # },

   for my $k ( keys %$cfg ) {
      my $kc = $cfg->{$k};

      my $kc_type = ref($kc);
      if ( !$kc_type ) {
         $kc = { column => $k };
      }

      my $condition =
        defined( $kc->{condition} )
        ? $kc->{condition}
        : $kc->{update_knowledge};

      if ( defined($condition) && $condition !~ /\{\{new_value\}\}/ ) {

         # if condition doesn't need {{new_value}}, we can evaluate it earlier
         if ( !tracer_eval_code( $condition, $opt ) ) {
            next;
         }
      }

      # in where_clause/update_key, $known's key is mapped to row's column.
      # in key_pattern,  $known's key is also the row's key.
      # column key can have multiple column names. we will use the first defined column
      # to update knowledge
      #   {column=>'TRDQTY,ORDQTY',
      #    clause=>'(TRDQTY={{opt_value}} or ORDQTY={{opt_value}})',
      #   }
      my $kc_column = defined $kc->{column} ? $kc->{column} : $k;
      my @columns   = split /,/, $kc_column;

      my $code = $kc->{code};

      my $new_value;
      for my $column (@columns) {
         my $without_prefix = $column;
         $without_prefix =~ s:^.+[.]::;

         $new_value = get_value_by_key_case_insensitive( $row, $without_prefix, { default => undef } );

         if (  !defined($new_value)
            && !( defined($code) && $code =~ /\{\{new_value\}\}/ ) )
         {
            # if code is not defined, or defined without using {{value}}, no need $new_value
            print "selected row's '$without_prefix' is not defined.\n";
            next;
         }
         last;
      }

      if ( defined($condition) && $condition =~ /\{\{new_value\}\}/ ) {
         if ( !tracer_eval_code( $condition, { %$opt, Dict => { %vars, %known, new_value => $new_value } } ) ) {
            next;
         }
      }

      if ( defined($code) ) {
         my $v = tracer_eval_code( $code, { %$opt, Dict => { %vars, %known, new_value => $new_value } } );
         update_knowledge( $k, $v, { KeyConfig => $kc } );
      } else {
         update_knowledge( $k, $new_value, { KeyConfig => $kc } )
           if defined $new_value;
      }
   }
}

sub update_knowledge {
   my ( $k, $new_value, $opt ) = @_;

   my $kc          = $opt->{KeyConfig};
   my $column      = defined $kc->{column} ? $kc->{column} : $k;
   my $known_value = $known{$k};

   if ( defined $known_value ) {
      my $mismatch;

      if ( $kc->{numeric} ) {
         if ( $known_value =~ /,/ ) {
            $known_value =~ s/,//g;
            $known{$k} = $known_value;
         }
         $mismatch++ if $known_value != $new_value;
      } else {
         $mismatch++ if $known_value ne $new_value;
      }

      die "\nconflict at $column: known='$known_value', new='$new_value'\n\n"
        if $mismatch;
   } else {
      $known{$k} = $new_value;
      print "\nadded knowledge key='$k' from $column=", Dumper($new_value), "\n";

      my $all_cfg = get_all_cfg();

      my $extender = $all_cfg->{extender_by_key}->{$k};
      if ( defined $extender ) {
         print "\nextending knowledge from key='$k'\n\n";

         # extender->() is out of this scope, therefore it  needs to take %known as a variable
         $extender->( \%known, $k );
      }
   }
}

sub update_error {
   my ( $msg, $opt ) = @_;

   $known{ERROR_COUNT}++;
   push @{ $known{ERRORS} }, $msg;

   print "ERROR: $msg\n";
}

sub update_ok {
   my ( $msg, $opt ) = @_;

   push @{ $known{OK} }, $msg;

   print "OK: $msg\n";
}

sub update_todo {
   my ( $msg, $opt ) = @_;

   push @{ $known{TODO} }, $msg;

   print "TODO: $msg\n";
}

my $cfg_by_file;

sub parse_cfg {
   my ( $cfg_file, $opt ) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 1;

   if ( exists $cfg_by_file->{$cfg_file} ) {
      return $cfg_by_file->{$cfg_file};
   }

   croak "$cfg_file not found"    if !-f $cfg_file;
   croak "$cfg_file not readable" if !-r $cfg_file;

   my $cfg_abs_path = get_abs_path($cfg_file);
   my ( $cfgdir, $cfgname ) = ( $cfg_abs_path =~ m:(^.*)/([^/]+): );

   my $cfg_string = `cat $cfg_file`;

   croak "failed to read $cfg_file: $!" if $?;

   #print __LINE__, " current namespace = ", __PACKAGE__, "\n";
   #print __LINE__, " known = ", Dumper(\%known);

   # no neede the following
   #   $cfg_string = "
   #   package TPSUP::TRACER;
   #   $cfg_string
   #   ";

   # three ways to include new code
   #    require 'code.pl'
   #       won't spawn an external process
   #    do 'code.pl'
   #       won't spawn an external process
   #    eval `cat code.pl`
   #       only eval keeps the current lexical scope.

   # use 'our' here to allow us use it again in the cfg file and make the cfg file
   # capable of a standlone perl file, so that we can check the cfg file's syntax
   # by its own.
   our $our_cfg;
   eval $cfg_string;
   if ($@) {

      # add this line in case the caller set up a trap
      $cfg_by_file->{$cfg_file} = $our_cfg;

      croak "ERROR in parsing $cfg_file: $@\n";
      return;
   }

   # make data structure consistent
   for my $k (qw(trace_route)) {
      if ( defined $our_cfg->{$k} ) {
         $our_cfg->{$k} = unify_array_hash( $our_cfg->{$k}, 'entity' );
      }
   }

   # 'vars' is array of pairs of key=>value
   # 'value' is an expression, therefore, we need to use two different quotes.
   # unshift put the key=value to the front, therefore, allow cfg file to overwrite it.
   unshift @{ $our_cfg->{vars} }, ( cfgdir  => "'$cfgdir'" );
   unshift @{ $our_cfg->{vars} }, ( cfgname => "'$cfgname'" );

   if ( exists $our_cfg->{key_pattern} ) {
      $our_cfg->{key_pattern} =
        unify_hash( $our_cfg->{key_pattern}, 'pattern' );
   } else {
      $our_cfg->{key_pattern} = {};
   }

   my ( $cfg_by_entity, $alias_map, $extra_keys, $entry_points, $trace_route, $extend_key_map ) = @{$our_cfg}{
      qw(
        cfg_by_entity   alias_map   extra_keys   entry_points   trace_route   extend_key_map)
   };

   # checking for required attributes
   croak "missing cfg_by_entity in $cfg_file" if !defined $cfg_by_entity;

   my @entities      = sort( keys %$cfg_by_entity );
   my @required_attr = qw(method);

   my $failed = 0;
   for my $e (@entities) {
      my $entity_cfg = $cfg_by_entity->{$e};

      my $type = ref $entity_cfg;
      $type = '' if !defined($type);
      if ( $type ne 'HASH' ) {
         die "ERROR: entity=$e, cfg has wrong type='$type'. ", Dumper($entity_cfg);
      }

      if ( !check_cfg_keys( $entity_cfg, $entity_syntax, $opt ) ) {
         print "ERROR: entity=$e, entity_cfg check failed\n\n";
         $failed++;
      }

      my $method     = $entity_cfg->{method};
      my $method_cfg = $entity_cfg->{method_cfg};

      if ( $method eq 'code' ) {
         if ($method_cfg) {
            print "entity=$e is method=$method which should not have method_cg\n";
            $failed++;
            next;
         }
      }

      if ( !$method_syntax->{$method} ) {
         print "method=$method in entity=$e but not in defined method_syntax\n";
         $failed++;
      }

      if ( !check_cfg_keys( $method_cfg, $method_syntax->{$method}, $opt ) ) {
         print "ERROR: entity=$e, method_cfg check failed\n";
         $failed++;
      }

      my $tests = $entity_cfg->{tests};
      if ($tests) {
         for my $test (@$tests) {
            if ( !check_cfg_keys( $test, $attr_syntax->{tests}, $opt ) ) {
               print "ERROR: a test in entity=$e attr=tests check failed\n";
               $failed++;
            }
         }
      }
   }

   exit 1 if $failed;

   my @allowed_keys = get_keys_in_uppercase(
      $cfg_by_entity,
      {
         AliasMap    => $alias_map,
         ExtraKeys   => $extra_keys,
         key_pattern => $our_cfg->{key_pattern},
      }
   );

   my @trace_route_entities = get_keys_from_array( $trace_route, 'entity' );

   for my $e (@trace_route_entities) {
      if ( !$cfg_by_entity->{$e} ) {
         die "entity '$e' in trace_route is not defined. file=$cfg_file.\n";
      }
   }

   my $usage_detail = "
   keys: @allowed_keys

   entities are: @entities

   keys and entities are case-insensitive

   trace route: @trace_route_entities
   ";

   if ( grep { $_ eq 'YYYYMMDD' } @allowed_keys ) {
      my $today = get_yyyymmdd();
      $usage_detail .= "\n   yyyymmdd is default to today $today\n";
   }

   my $extender_by_key;    # this provides the quick access to the extender function
   my @extender_keys;      # this provides the order of the map
   if ( $extend_key_map && @$extend_key_map ) {
      for my $row (@$extend_key_map) {
         my ( $k, $func ) = @$row;

         push @extender_keys, $k;

         $extender_by_key->{$k} = $func;
      }

      # add this into entity cfg so that later we only need to pass entity cfg
      for my $e (@entities) {
         $cfg_by_entity->{$e}->{extender_by_key} = $extender_by_key;
      }
   }

   @{$our_cfg}{
      qw(
        allowed_keys   entities   trace_route_entities   extender_keys  extender_by_key  usage_detail)
     }
     = ( \@allowed_keys, \@entities, \@trace_route_entities, \@extender_keys, $extender_by_key, $usage_detail );

   for my $e (@entities) {

      # push down some higher-level config because we may pass the lower config only
      my $entity_cfg = $cfg_by_entity->{$e};

      $entity_cfg->{entity} = $e;

      #croak "
      #ERROR: found entity-level condition in entity=$e.
      #entity-level condition is not supported any more.
      #either move up to 'trace_route'
      #or move down to cmds, ...
      #" if defined $entity_cfg->{condition};

   }

   $cfg_by_file->{$cfg_file} = $our_cfg;

   #$opt->{verbose} && print "our_cfg = ", Dumper($our_cfg);

   # check syntax
   my $BeginCode = <<'END';
package TRACER_DUMMY;
use strict;
use warnings;
our (%known,%our_cfg,$row_count,$rc,$output,@lines,@arrays,@hashes,%hash1,%r);
END
   my $node_pairs = get_node_list( $our_cfg, 'our_cfg', $opt );

   my @eval_patterns = (
      qr/\{vars\}->\[\d*[13579]\]$/,    # vars are pairs. odd-numberred are values.
      qr/\{(condition|code|pre_code|post_code|test|if_fail|if_success|update_knowledge|Exps)\}$/,
   );

   $failed = 0;                         #restart count

   while (@$node_pairs) {
      my $node = shift @$node_pairs;
      my $addr = shift @$node_pairs;

      #print "node: $node\n";

      for my $p (@eval_patterns) {
         if ( $node =~ /$p/ ) {
            $verbose > 1 && print "matched $node\n";
            my $clause = $addr;

            # replace all scalar vars {{...}} with 1,
            # but exclude {{pattern::...} and {{where::...}}
            $clause =~ s/\{\{([0-9a-zA-Z_.-]+)\}\}/1/g;

            if (
               !chkperl(
                  $clause,
                  {
                     %$opt,
                     BeginCode => $BeginCode,
                     verbose   => ( $verbose > 1 ),
                  }
               )
              )
            {
               $failed = 1;
               print "ERROR: failed to compile node: $node\n";
               print "In order to test compilation, we temporarily substituted vars in {{}} with '1'\n";
            }
         }
      }
   }

   croak "some perl code failed to compile" if $failed;

   return $our_cfg;
}

sub check_cfg_keys {
   my ( $cfg, $syntax, $opt ) = @_;

   my $verbose = $opt->{verbose};

   my $failed = 0;
   for my $a ( @{ $syntax->{required} } ) {
      if ( !defined $cfg->{$a} ) {
         print "missing required attr='$a' in cfg\n";
         $failed++;
      }
   }

   my $allowed_attr;
   for my $a ( ( @{ $syntax->{required} }, @{ $syntax->{optional} } ) ) {
      $allowed_attr->{$a} = 1;
   }

   for my $a ( keys %$cfg ) {
      if ( !$allowed_attr->{$a} ) {
         print "ERROR: attr='$a' is not allowed in cfg\n";
         $failed++;
      }
   }

   if ($failed) {
      print "ERROR: found at least $failed errors.\n";
      $verbose && print "cfg = ",    Dumper($cfg);
      $verbose && print "syntax = ", Dumper($syntax);
      return 0;
   }

   return 1;
}

sub get_keys_from_array {
   my ( $rows, $key_name, $opt ) = @_;

   my @keys;

   for my $row (@$rows) {
      my $type = ref $row;

      if ( !$type ) {
         push @keys, $row;
      } elsif ( $type eq 'HASH' ) {
         push @keys, $row->{$key_name};
      } else {
         croak "unsupported type='$type' in " . Dumper($rows) . " at " . Dumper($row);
      }
   }

   return @keys;
}

my $my_cfg;

sub set_all_cfg {
   my ( $given_cfg, $opt ) = @_;

   my $cfg_type = ref $given_cfg;

   if ( !$cfg_type ) {
      my $cfg_file = $given_cfg;
      $my_cfg = parse_cfg( $cfg_file, $opt );
   } elsif ( $cfg_type eq 'HASH' ) {
      $my_cfg = $given_cfg;
   } else {
      croak "unknown cfg type=$cfg_type, expecting file name (string) or HASH. given_cfg = " . Dumper($given_cfg);
   }
}

sub get_all_cfg {
   my ($opt) = @_;

   croak "all_cfg is not defined yet" if !defined $my_cfg;

   return $my_cfg;
}

sub trace {
   my ( $given_cfg, $input, $opt ) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   set_all_cfg($given_cfg);

   my $all_cfg = get_all_cfg();

   $verbose > 1 && print "all_cfg=", Dumper($all_cfg);

   my ( $cfg_by_entity, $entry_points, $trace_route ) = @{$all_cfg}{
      qw(
        cfg_by_entity   entry_points   trace_route)
   };

   if ( $opt->{TraceString} ) {
      my @selected_entities = split /,/, $opt->{TraceString};

      my @new_trace_route = ();

    SELECTED:
      for my $e (@selected_entities) {

         # if the entity is already in the configured trace route, add it with the config.
         for my $t (@$trace_route) {
            if ( $e eq $t->{entity} ) {
               push @new_trace_route, $t;
               next SELECTED;
            }
         }

         # if the entity is not in the configured trace route, add it here.
         push @new_trace_route, { entity => $e };
      }

      $trace_route  = \@new_trace_route;    # set new trace route
      $entry_points = [];                   # we skip all entry points too

      $opt->{verbose} && print "trace_route=",  Dumper($trace_route);
      $opt->{verbose} && print "entry_points=", Dumper($entry_points);
   }

   my $parsed_input = parse_input(
      $input,
      {
         AliasMap    => $all_cfg->{alias_map},
         AllowedKeys => $all_cfg->{allowed_keys},
      }
   );

   # these keys has precedence to populate because extender func may need this info.
   for my $k (qw(YYYYMMDD)) {
      update_knowledge( $k, $parsed_input->{$k} )
        if defined $parsed_input->{$k};
   }

   if ( grep { $_ eq 'YYYYMMDD' } @{ $all_cfg->{allowed_keys} } ) {
      my $today = get_yyyymmdd();
      if ( !$known{YYYYMMDD} ) {
         update_knowledge( 'YYYYMMDD', $today );
      }
      update_knowledge( 'TODAY', $today );
   }

   for my $k ( keys %$parsed_input ) {
      update_knowledge( $k, $parsed_input->{$k} );
   }

   print "knowledge from input = ", Dumper( \%known );

   if ( $all_cfg->{vars} ) {
      my $global_vars = resolve_vars_array( $all_cfg->{vars}, \%known, $opt );
      $all_cfg->{global_vars} = $global_vars;
   } else {
      $all_cfg->{global_vars} = {};
   }

   print "global_vars=", Dumper( $all_cfg->{global_vars} );

   if ( $known{EXAMPLE} ) {
      my $entity     = $known{EXAMPLE};
      my $entity_cfg = get_value_by_key_case_insensitive( $cfg_by_entity, $entity );

      my $opt2 = {
         %$opt,
         AllowMultiple => 1,    # not abort when multiple results
         Top           => 5,    # display upto 5 results
         isExample     => 1,
      };

      reset_global_buffer();    # only reset buffer not $known neither global cfg
      $vars{entity} = $entity;

      process_entity( $entity, $entity_cfg, $opt2 );

      print "knowledge = ", Dumper( \%known );
      return;
   }

   my $SkipTrace = {};
   if ( $opt->{SkipTrace} ) {
      if ( $opt->{SkipTrace} =~ /^all$/i ) {
         $trace_route = [];
      } else {
         for my $t ( split( /,/, $opt->{SkipTrace} ) ) {
            $SkipTrace->{$t} = 1;
         }

         $verbose && print "SkipTrace = ", Dumper($SkipTrace);
      }
   }

   if ( $opt->{ForceThrough} && !$verbose ) {

      # use the default die handler is less verbose when force through as we will
      # print failures many times
      $SIG{__DIE__} = $saved_die_handler;
   }

   my $result;

   if ( @$trace_route && !$opt->{SkipEntry} && $entry_points ) {
    ROW:
      for my $row (@$entry_points) {
         my ( $keys, $entities ) = @$row;

         for my $k (@$keys) {
            next ROW if !defined $known{$k};
         }

         print "matched entry point: [@$keys] [@$entities]\n";

         for my $entity (@$entities) {
            next if $SkipTrace->{$entity};

            my $entity_cfg = get_value_by_key_case_insensitive( $cfg_by_entity, $entity );

            eval { $result->{$entity} = process_entity( $entity, $entity_cfg, $opt ); };
            if ($@) {

               # don't print stack trace for easy understanding errors.
               print "$@" if $@ !~ /\(no need stack trace\)/;
               exit 1     if !$opt->{ForceThrough};
            }
         }

         last;
      }
   }

   my @trace_route_entities =
     grep { !$SkipTrace->{$_} } get_keys_from_array( $trace_route, 'entity' );

   if ( !@trace_route_entities ) {
      print "\n\nnothing to trace\n\n";
      return;
   }

   print "\n\nstart tracing: @trace_route_entities\n\n";

   for my $row (@$trace_route) {
      my $entity = $row->{entity};
      my $opt2   = { %$opt, %$row };

      next if $SkipTrace->{$entity};

      if ( exists $result->{$entity} && !$row->{reentry} ) {
         print <<"EOF";
-------------------------------------------------------------------
entity=$entity had been traced before

EOF
         next;
      }

      reset_global_buffer();    # only reset buffer not $known neither global cfg
      $vars{entity} = $entity;

      my $condition = $row->{condition};

      next if defined($condition) && !tracer_eval_code( $condition, $opt );

      my $entity_cfg = get_value_by_key_case_insensitive( $cfg_by_entity, $entity, { default => undef } );
      die "ERROR: entity=$entity is not configured\n" if !$entity_cfg;

      eval { $result->{$entity} = process_entity( $entity, $entity_cfg, $opt2 ); };
      if ($@) {
         print "$@" if $@ !~ /\(no need stack trace\)/;
         exit 1     if !$opt->{ForceThrough};
      }
   }
}

sub tracer_eval_code {
   my ( $code, $opt ) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   # this relies on global buffer that are specific to TPSUP::TRACER
   # default dictionary is {%vars, %known}
   my $dict = $opt->{Dict} ? $opt->{Dict} : { %vars, %known };

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

sub main {
   print "\n---- test vars only ----\n\n";

   trace(
      "$ENV{TPSUP}/scripts/tptrace_test_var.cfg",
      ['tradeid=trd001'],
      {
         SkipTrace => 'all',
         SkipEntry => 1,
         verbose   => 0,
      }
   );

   print "\n---- test process_db, but not updating knowledge ----\n\n";

   my $method_cfg = {
      db           => 'tian@tiandb',
      db_type      => 'mysql',
      where_clause => {
         FIRSTNAME => 'firstname',
         LASTNAME  => 'lastname',
      },
      order_clause   => 'order by LastName',
      example_clause => "",
     },

     %known = ( FIRSTNAME => 'Han' );

   my $table = 'tblMembers';

   my $member = process_db( $table, $method_cfg, { MaxExtracts => 10000, verbose => 1 } );

   print "member = ", Dumper($member);

   print "\n---- next ----\n\n";
   reset_global_buffer();
   %known = ();

   trace( "$ENV{TPSUP}/scripts/tptrace_test.cfg", ['example=applog_cmd_extract'], { verbose => 0 } );

   print "\n---- next ----\n\n";

   reset_global_buffer();
   %known = ();

   trace( "$ENV{TPSUP}/scripts/tptrace_test.cfg", ['example=applog_log'], { verbose => 0 } );

   print "\n---- next ----\n\n";

   reset_global_buffer();
   %known = ();

   trace(
      "$ENV{TPSUP}/scripts/tptrace_test.cfg",
      [
         'sec=IBM',        'sendercomp=BLKC',
         'orderqty=4,500', 'yyyymmdd=20211129',
         'tradeqty=600'
      ],

      #{verbose=>1}
   );

}

main() unless caller();

1
