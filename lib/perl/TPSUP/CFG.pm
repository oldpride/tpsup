package TPSUP::CFG;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
  check_syntax
  check_syntax_1_node
  check_syntax_1_node_1_syntax
  parse_simple_cfg
);

use warnings;
use Data::Dumper;
$Data::Dumper::Terse    = 1;
$Data::Dumper::SortKeys = 1;
use Carp;
use TPSUP::FILE qw(get_in_fh close_in_fh);
use TPSUP::NAMESPACE;

sub check_syntax {
   my ( $node, $syntax, $opt ) = @_;

   $opt ||= {};
   my $verbose = $opt->{verbose} || 0;
   my $path    = $opt->{path}    || "/";

   my $fatal = 0;
   if ( $opt->{fatal} ) {
      $fatal = 1;
      delete $opt->{fatal};    # don't pass it to recursive calls !!!
   }

   my $error   = 0;
   my $checked = "";
   my $message = "";
   my $matched = "";

   my $node_type = ref $node;
   if ( $node_type eq 'HASH' ) {
      my $result = check_syntax_1_node( $node, $syntax, $path, $opt );
      $verbose && print "after checking path=$path, result=", Dumper($result);
      $error += $result->{error};
      $checked .= $result->{checked};
      $message .= $result->{message};
      $matched .= $result->{matched};

      foreach my $k ( keys %$node ) {
         $verbose && print "checking $path$k/\n";
         # recursive call
         my $result = check_syntax( $node->{$k}, $syntax, { %$opt, path => "$path$k/" } );
         $error += $result->{error};
         $checked .= $result->{checked};
         $message .= $result->{message};
         $matched .= $result->{matched};
      }
   } elsif ( $node_type eq 'ARRAY' ) {
      for ( my $i = 0 ; $i < scalar @$node ; $i++ ) {
         $verbose && print "checking $path$i/\n";
         # recursive call
         my $result = check_syntax( $node->[$i], $syntax, { %$opt, path => "$path$i/" } );
         $error += $result->{error};
         $checked .= $result->{checked};
         $message .= $result->{message};
         $matched .= $result->{matched};
      }
   } else {
      # do nothing for other types.
   }

   if ($fatal) {
      if ($error) {
         croak "syntax error: $message";
      } elsif ( !$checked ) {
         croak "no syntax check performed";
      } elsif ( !$matched ) {
         croak "no syntax matched";
      }
   }

   return { error => $error, message => $message, checked => $checked, matched => $matched };
}

sub check_syntax_1_node {
   my ( $node, $syntax, $path, $opt ) = @_;

   my $verbose = $opt->{verbose} || 0;

   my $error   = 0;
   my $checked = "";
   my $message = "";
   my $matched = "";

   my $node_type = ref $node;
   if ( $node_type ne 'HASH' ) {
      die "node_type=$node_type is not hash. should never be here. node=" . Dumper($node);
   }

   foreach my $p ( keys %$syntax ) {
      $verbose && print "comparing path=$path pattern=$p\n";
      if ( $path =~ /$p/ ) {
         my $node_syntax = $syntax->{$p};

         my $m = "pattern=$p matched path=$path\n";
         $matched .= $m;
         $verbose && print $m;

         my $result = check_syntax_1_node_1_syntax( $node, $node_syntax, $path, $opt );
         $error += $result->{error};
         $checked .= $result->{checked};
         $message .= $result->{message};
      }
   }

   return { error => $error, message => $message, checked => $checked, matched => $matched };
}

sub check_syntax_1_node_1_syntax {
   my ( $node, $node_syntax, $path, $opt ) = @_;

   my $allowUnkownKey = $opt->{allowUnkownKey} || 0;

   my $error   = 0;
   my $checked = "";
   my $message = "";

   # this function does not do "matching", therefore doesn't update 'matched'
   # my $matched = "";

   foreach my $k ( keys %$node ) {
      $checked .= "checked path=$path key=$k\n";
      my $v = $node->{$k};

      if ( !exists $node_syntax->{$k} ) {
         if ( !$allowUnkownKey ) {
            $message .= "$path key=$k is not allowed\n";
            $error++;
         }
         next;
      }

      my $expected_type = $node_syntax->{$k}->{type};
      my $actual_type   = ref $v || 'SCALAR';

      if ( defined $expected_type ) {
         if ( $expected_type ne $actual_type ) {
            $message .= "$path key=$k type mismatch: expected=$expected_type vs actual=$actual_type\n";
            $error++;
            next;
         }
      }

      my $pattern = $node_syntax->{$k}->{pattern};
      if ( defined $pattern ) {
         if ( $v !~ /$pattern/ ) {
            $message .= "$path key=$k value=$v not matching expected pattern\n";
            $error++;
            next;
         }
      }
   }

   foreach my $k ( keys %$node_syntax ) {
      $checked .= "checked path=$path required key=$k\n";
      my $v        = $node_syntax->{$k};
      my $required = $v->{required} || 0;

      if ( $required && !exists $node->{$k} ) {
         $message .= "$path required key=$k is missing\n";
         $error++;
         next;
      }
   }

   return { error => $error, message => $message, checked => $checked };
}

# note: TPSUP::BATCH doesn't use this function, because TPSUP::BATCH needs to source
# the code into its own namespace, not TPSUP::Expression's.
# this function sources the code into TPSUP::Expression's namespace.
sub source_perl_string_to_dict {
   my ( $perl_string, $varname, $opt ) = @_;

   require TPSUP::Expression;
   TPSUP::Expression::run_code($perl_string);

   my $varname_type = ref $varname;
   if ( !$varname_type ) {
      # access a namespace's variable by variable name
      # python can do this by using getattr(module, attribute), much easier
      my $var = TPSUP::NAMESPACE::getattr( "TPSUP::Expression", $varname, $opt );
      return $var;
   } elsif ( $varname_type ne 'ARRAY' ) {
      my $ret = {};
      for my $varname2 (@$varname) {
         my $var = TPSUP::NAMESPACE::getattr( "TPSUP::Expression", $varname2, $opt );
         $ret->{$varname2} = $var;
      }
      return $ret;
   } else {
      croak "varname must be a scalar or an array reference";
   }
}

sub source_perl_file_to_dict {
   my ( $perl_file, $varnames ) = @_;

   my $perl_string;
   open my $fh, '<', $perl_file or croak "cannot open $perl_file: $!";
   {
      local $/;
      $perl_string = <$fh>;
   }
   close $fh;

   return source_perl_string_to_dict( $perl_string, $varnames );
}

sub parse_simple_cfg {
   my ( $file, $opt ) = @_;

   my $CfgKey = $opt->{CfgKey} ? $opt->{CfgKey} : 'name';

   my $ifh = get_in_fh( $file, $opt );

   my $result;
   my $current;

   while ( my $line = <$ifh> ) {
      chomp $line;

      next if $line =~ /^\s*$/;
      next if $line =~ /^\s*#/;

      if ( $line =~ /^([^=]+)=(.*)/ ) {
         my ( $key, $value ) = ( $1, $2 );

         if ( $key eq $CfgKey ) {
            my $name = $value;
            if ( $result->{$name} ) {
               croak "duplicate CfgKey $CfgKey=$name";
            }

            $result->{$name}->{$CfgKey} = $value;
            $current = $result->{$name};
         } else {
            if ( !$current ) {
               croak "CfgKey $CfgKey must be defined first";
            }

            $current->{$key} = $value;
         }
      }
   }

   close_in_fh($ifh);

   return $result;
}

sub main {
   print << "END";

--------------------- test parse_simple_cfg() ----------------------------------

END

   my $file = "$ENV{TPSUP}/scripts/log_pattern.cfg";

   print << "EOF";
parse $file

EOF

   print Dumper( parse_simple_cfg($file) );

   print << "END";

--------------------- test chk_syntax() ----------------------------------

END

   my $module_dir       = "$ENV{TPSUP}/lib/perl/TPSUP";
   my $test_cfg_file    = "$module_dir/CFG_test_cfg.pl";
   my $test_syntax_file = "$module_dir/CFG_test_syntax.pl";

   my $our_cfg = source_perl_file_to_dict( $test_cfg_file, 'our_cfg' );
   print "our_cfg=", Dumper($our_cfg);
   my $our_syntax = source_perl_file_to_dict( $test_syntax_file, 'our_syntax' );
   print "our_syntax=", Dumper($our_syntax);

   my $result = check_syntax( $our_cfg, $our_syntax, );
   print "result=", Dumper($result);
}

main() unless caller();

1
