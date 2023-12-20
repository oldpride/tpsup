package TPSUP::UTIL;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
  get_patterns_from_log
  cp_file2_to_file1
  backup_filel_to_file2
  get_abs_path
  get_abs_cwd
  get_exps_from_string
  get_ExpHash_from_ArrayOfStrings
  get_user
  get_homedir
  get_homedir_by_user
  recursive_handle
  transpose_arrays
  compile_perl
  compile_perl_array
  compile_paired_strings
  eval_perl
  chkperl
  get_user_by_uid
  get_group_by_gid
  insert_namespace_code
  insert_namespace_file
  insert_namespaces
  unique_array
  sort_unique
  trim_path
  reduce_path
  get_java
  glob2regex
  get_timestamp
  get_setting_from_env
  get_setting_from_profile
  source_profile
  resolve_string_in_env
  should_do_it
  hit_enter_to_continue
  looper
  get_items
  get_value_by_key_case_insensitive
  get_first_by_key
  unify_hash
  unify_array_hash
  get_node_list
  add_line_number_to_code
  arrays_to_hashes
  hashes_to_arrays
  top_array
  tail_array
  parse_rc
  resolve_scalar_var_in_string
  convert_to_uppercase
  tp_join
  tp_quote_wrap
  gen_combinations_from_a
  gen_combinations_from_aa
  sort_pattern
);

use Carp;
use Data::Dumper;
use IO::Select;
use Cwd;
use Cwd 'abs_path';
use TPSUP::Expression;

# UTIL is a basic module, so it should not hard-depend on other modules.
# therefore, we use 'require' instead of 'use' here,
# this breaks module-depency look during compile time.
require TPSUP::FILE;
require TPSUP::TMP;

sub get_setting_from_env {
   my ( $VarName, $VarToFile, $FileName, $opt ) = @_;

   # 1. if $VarName is defined in env, return this.
   # 2. if $VarToFile is defined in env, search $VarName in file named by $VarToFile.
   #    return if found.
   # 3. if $FileName exists, search $VarName in $FileName. return if found.
   # 4. return undef

   return $ENV{$VarName} if exists $ENV{$VarName};

   if ( exists $ENV{$VarToFile} ) {
      my $value = get_setting_from_profile( $VarName, $ENV{$VarToFile} );
      if ( !defined $value ) {
         confess "cannot find $VarName in $VarName or $VarToFile=$ENV{$VarToFile}";
      }
      return $value;
   } else {
      my $value = get_setting_from_profile( $VarName, $FileName );
      if ( !defined $value ) {
         confess "cannot find $VarName in $VarName or $FileName";
      }
      return $value;
   }
}

sub get_setting_from_profile {
   my ( $VarName, $FileName, $opt ) = @_;

   my @env = `/bin/bash -c "set -o allexport; . $FileName; env"`;
   chomp @env;

   for my $line (@env) {
      if ( $line =~ /^${VarName}=(.*)/ ) {
         return $1;
      }
   }

   return undef;
}

sub source_profile {
   my ( $profile, $opt ) = @_;

   my @env = `/bin/bash -c ". $profile; env"`;
   chomp @env;

   for my $line (@env) {
      if ( $line =~ /^([^=\s]+?)=(.*)/ ) {
         my ( $k, $v ) = ( $1, $2 );

         $v = '' if !defined $v;

         # exclude functions because they tend to be multilines and cause errors.
         # BASH_FUNC_tpproxy%%=() {  local usage;
         # BASH_FUNC_tpsup()=() {  local usage;
         next if $v =~ /^\(\)/;

         $ENV{$k} = $v;
      }
   }
}

sub resolve_string_in_env {
   my ( $string, $opt ) = @_;

   # resolve a string without executing: < > `

   $string =~ s/[>]/.greaterthan./g;
   $string =~ s/[<]/.lessthan./g;
   $string =~ s/[`]/.backtick./g;

   my $resolved = `bash -c \"echo $string\"`;
   chomp $resolved;

   $resolved =~ s/[.]greaterthan[.]/>/g;
   $resolved =~ s/[.]lessthan[.]/</g;
   $resolved =~ s/[.]backtick[.]/`/g;

   return $resolved;
}

sub get_timestamp {
   my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) = localtime(time);
   return sprintf( "%04d%02d%02d %02d:%02d:%02d", $year + 1900, $mon + 1, $mday, $hour, $min, $sec );
}

sub get_patterns_from_log {
   my ( $log, $match_pattern, $opt ) = @_;

   my $exclude_pattern = $opt->{ExcludePattern};

   my $ErasePattern = defined $opt->{ErasePattern} ? qr/$opt->{ErasePattern}/ : undef;
   my $BeginPattern = defined $opt->{BeginPattern} ? qr/$opt->{BeginPattern}/ : undef;
   my $EndPattern   = defined $opt->{EndPattern}   ? qr/$opt->{EndPattern}/   : undef;

   my $fh = TPSUP::FILE::get_in_fh($log);

   my $ret;

   my $begun;
   my $end;

   while (<$fh>) {
      my $line = $_;

      chomp $line;

      last if $end;

      if ( $BeginPattern && !$begun ) {
         if ( $line =~ /$BeginPattern/ ) {
            $begun++;
         } else {
            next;
         }
      }

      if ($EndPattern) {
         if ( $line =~ /$EndPattern/ ) {
            $end++;
         }
      }

      next if defined $exclude_pattern && $line =~ /$exclude_pattern/;

      next if $line !~ /$match_pattern/;

      my $pattern = $line;

      #$pattern =~ s/\d+/./g; # convert number into .

      if ($ErasePattern) {
         $pattern =~ s/$ErasePattern/./g;
      }

      if ( !$ret->{$pattern} ) {
         $ret->{$pattern}->{first} = $line;
         $ret->{$pattern}->{count}++;
      } else {
         $ret->{$pattern}->{last} = $line;
         $ret->{$pattern}->{count}++;
      }
   }

   close $fh if $fh != \*STDIN;

   return $ret;
}

sub cp_file2_to_file1 {

   # overwrite file1 with file2's content
   my ( $file2, $file1, $opt ) = @_;

   if ( $opt->{ShowDiff} ) {
      my $cmd = "diff $file1 $file2";

      $opt->{PrintCmd} && print "Diff cmd - $cmd\n";
      my $diff_rc = system("$cmd");
      $diff_rc = $diff_rc >> 8;

      if ( !$diff_rc ) {
         print "No difference\n";
         return "No change because no difference";
      }
   }

   if ( !should_do_it( { FORCE => $opt->{NoPrompt} } ) ) {
      return "You didn't answer yes, meaning not to change";
   }

   if ( !$opt->{NoBackup} ) {
      my ( $package, $prog, $line ) = caller;

      $prog =~ s:.*/::;

      my $tmpfile = TPSUP::TMP::get_tmp_file( "/var/tmp", "${prog}", { AddIndex => 1 } );

      my $rc = backup_file1_to_file2( $file1, $tmpfile, $opt );

      return "Backup failed" if $rc;
   }

   my $cmd = "/bin/cp $file2 $file1";

   $opt->{PrintCmd} && print "Copy cmd - $cmd\n";

   my $rc = system($cmd);

   if ($rc) {
      return "Update failed";
   } else {
      return "Updated";
   }
}

sub backup_file1_to_file2 {
   my ( $file, $backup, $opt ) = @_;

   my $cmd = "/bin/cp $file $backup";

   $opt->{PrintCmd} && print "Backup cmd = $cmd\n";

   my $rc = system($cmd);

   return $rc;
}

my $step_count = 0;

sub hit_enter_to_continue {
   my ($opt) = @_;

   if ( defined( $opt->{InitialSteps} ) ) {
      $step_count = $opt->{InitialSteps};
   }

   if ( $step_count > 0 ) {
      $step_count--;
   } else {
      print "Hit Enter to continue (enter a number to skip steps)\n";
      my $answer = readline(*STDIN);
      if ( $answer =~ /^(\d+)/ ) {
         $step_count = $answer;
      }
   }

   return 1;
}

sub should_do_it {
   my ($opt) = @_;

   if ( $opt->{DRYRUN} ) {
      print STDERR "DRY-RUN or CHECK ONLY\n";
      return 0;
   }

   if ( $opt->{FORCE} ) {
      return 1;
   } else {
      my $default = $opt->{DEFAULT} ? $opt->{DEFAULT} : 'N';
      print "Do you want to do this? Y/N [$default]\n";
      my $answer = readline(*STDIN);

      chomp $answer;

      if ( $answer eq '' ) {
         $answer = $default;
      }

      if ( $answer !~ /^\s*[yY]/ ) {
         print STDERR "Your answer is '$answer', not 'Yes'; won't do this\n";
         return 0;
      } else {
         return 1;
      }
   }
}

sub get_abs_path {
   my ($path) = @_;

   # $ perl -e 'use Cwd 'abs_path'; print abs_path("tpsup/scripts/../autopath"), "\n";'
   # /home/gpt/tpsup/autopath
   # $ perl -e 'use Cwd 'abs_path'; print abs_path("./tpsup/scripts/../autopath"), "\n";'
   # /home/gpt/tpsup/autopath
   # $ perl -e 'use Cwd 'abs_path'; print abs_path(".//tpsup/scripts/../autopath/"), "\n";'
   # /home/gpt/tpsup/autopath

   return abs_path($path);
}

sub get_abs_cwd {
   my $cwd = getcwd();

   return abs_path($cwd);
}

my $user;

sub get_user {
   return $user if $user;

   my $line = `id`;

   #uid=9020(tian) gid=7296(unix)

   ($user) = ( $line =~ /^.+?\((.+?)\)/ );

   die "cannot figure out user from 'id' command: $line" if !$user;

   return $user;
}

my $homedir_by_user;

sub get_homedir_by_user {
   my ($user) = @_;

   $user = get_user() if !$user;

   # http://stackoverflow.com/questions/3526420/how-do-i-get-the-current-user-in-perl-in-a-portable-way

   return $homedir_by_user->{$user} if exists $homedir_by_user->{$user};

   my $line = `getent passwd $user`;

   if ( !$line ) {
      $homedir_by_user->{$user} = undef;
      return undef;
   }

   #tian:x:9020:7296:UNIX User,APP,2254201:/home/tian:/bin/ksh

   my @a = split /:/, $line;

   my $homedir = $a[5];

   $homedir_by_user->{$user} = $homedir;

   return $homedir;
}

sub get_homedir {
   return get_homedir_by_user();
}

sub get_exps_from_string {
   my ( $string, $opt ) = @_;

   my $delimiter = $opt->{delimiter} ? $opt->{delimiter} : ',';

   # ${55),substr(${126),4,6),substr("abc",1,1),...
   # CumQty=${14),Price=sprintf("%.2f",${44}),Open/Close=${77}

   my @a = split //, $string;

   my @exps;
   my $current_exp = '';
   my @nesttings;    #parenthsis nests
   my $quote_char;
   my $quote_pos;

   my $i = 0;

   for my $c (@a) {
      $i++;    #$i effectively starts from 1

      if ($quote_char) {

         # a quote already started

         $current_exp .= $c;

         if ( $c eq $quote_char ) {

            # this is a closing quote: " matches " or ' matches '.
            $quote_char = '';
         }

         next;
      }

      if ( $c eq "'" || $c eq '"' ) {

         # starts a new quote
         $current_exp .= $c;

         $quote_char = $c;

         $quote_pos = $i;

         next;
      }

      if ( $c eq '(' ) {

         # starts a new nest

         $current_exp .= $c;

         push @nesttings, $i;

         next;
      }

      if ( $c eq ')' ) {

         # closes a nest
         $current_exp .= $c;

         if ( !@nesttings ) {
            carp "string '$string' has unmatched $c at position $i. (starting from 1)";
            return undef;
         }

         pop @nesttings;

         next;
      }

      if ( $c eq $delimiter && !@nesttings ) {

         # got a complete exp

         push @exps, $current_exp;

         $current_exp = '';    # reset $current_exp
      } else {
         $current_exp .= $c;
      }
   }

   push @exps, $current_exp;

   if ($quote_char) {
      carp "string '$string' has unmatched $quote_char at position $quote_pos. (starting from 1)";
      return undef;
   }

   if (@nesttings) {
      carp "string '$string' has unmatched '(', last one at position $nesttings[-1]. (starting from 1)";
      return undef;
   }

   return \@exps;
}

sub get_ExpHash_from_ArrayOfStrings {
   my ( $ArrayOfStrings, $opt ) = @_;

   my $ret;

   for my $string (@$ArrayOfStrings) {

      # CumQty=${14},Price=sprintf("%.2f",${44}),Open/Close=${77}

      my $pairs = get_exps_from_string( $string, $opt );

      for my $p (@$pairs) {

         # Price=sprintf("%.2f",${44})

         if ( $p =~ /^(.+?)=(.+)/ ) {
            my ( $k, $v ) = ( $1, $2 );
            $ret->{$k} = $v;
         } else {
            if ( $opt->{SkipBadExp} ) {
               carp "bad format at '$p'. expecting 'key=value'";
            } else {
               croak "bad format at '$p'. expecting 'key=value'";
            }
         }
      }
   }

   return $ret;
}

sub transpose_arrays {
   my ( $arrays, $opt ) = @_;

   $opt->{verbose} && print STDERR "transpose_arrays arrays = ", Dumper($arrays);

   my @out_array;

   return \@out_array if !$arrays;

   my $type = ref $arrays;

   $type = "" if !$type;

   croak "wrong type='$type' when calling transpose_arrays"
     if !$type || $type ne 'ARRAY';

   my $num_arrays = scalar(@$arrays);

   my $max;

   my $i;

   for my $a (@$arrays) {
      $i++;

      my $count;

      if ( !$a ) {
         $count = 0;
      } else {
         my $type = ref $a;

         $type = "" if !$type;

         croak "sub array ref $i wrong type='$type' when calling transpose_arrays"
           if !$type || $type ne 'ARRAY';

         $count = scalar(@$a);
      }

      if ( !defined $max ) {
         $max = $count;
      } else {
         if ( !$opt->{TranposeLooseSize} ) {
            croak "transpose_arrays input arrays have different sizes: $max vs $count"
              if $max != $count;
         }

         if ( $max < $count ) {
            $max = $count;
         }
      }
   }

   return \@out_array if !$max;

   for ( my $i = 0 ; $i < $max ; $i++ ) {
      my @a;

      for ( my $j = 0 ; $j < $num_arrays ; $j++ ) {
         push @a, $arrays->[$j]->[$i];
      }

      push @out_array, \@a;
   }

   return \@out_array;
}

sub recursive_handle {
   my ( $ref, $opt ) = @_;

   # <?xml version="1.0"?>
   # <topology>
   #    <match name='A_B'/>
   #    <match name='C_D'/>
   #    <match name='E_F'/>
   # </topology>
   #
   # 1. before first call
   # $opt = {
   #    XMLpath  => '$root',   # default to '$root'
   #    XMLlevel => 0,         # default to 0
   #    XMLnodes => ['$root'], # default to [$path]
   #    XMLtypes => ['HASH'],  # default to let the called function to find
   # };
   # recursive_handle($ref, $opt);
   #
   # 2. before the second call
   # $opt = {
   #    XMLpath  => '$root->{match}',
   #    XMLlevel => 1,
   #    XMLnodes => ['$root', 'match'],
   #    XMLtypes => ['HASH', 'ARRAY'],
   # };
   # recursive_handle($ref, $opt);
   #
   # 3. before the 3rd call
   # $opt = {
   #    XMLpath => '$root->{match}->[0]',
   #    XMLlevel => 2,
   #    XMLnodes => ['$root', 'match', 0],
   #    XMLtypes => ['HASH', 'ARRAY', 'HASH'],
   # };
   # recursive_handle($ref, $opt);

   my ( $path, $level, $nodes, $types ) =
     @{$opt}{qw(XMLpath XMLlevel XMLnodes XMLtypes)};

   $path = '$root' if !defined $path;
   print "$path\n" if $opt->{verbose} || $opt->{RecursivePrint};

   $level = 0 if !defined $level;

   $nodes = [$path] if !defined $nodes;
   my $node = $nodes->[-1];

   my $type;

   if ($types) {
      $type = $types->[-1];
   } else {
      $type  = ref $ref;
      $types = [$type];
   }

   $type = '' if !$type;

   my $value =
       $type eq ''       ? $ref
     : $type eq 'SCALAR' ? $ref
     :                     undef;

   my $r;

   @{$r}{qw(path   type   node   value  current   level   nodes   types)} =
     ( $path, $type, $node, $value, $ref, $level, $nodes, $types );

   if (  $opt->{Handlers} && @{ $opt->{Handlers} }
      || $opt->{FlowControl} && @{ $opt->{FlowControl} } )
   {

      TPSUP::Expression::export_var( $r, { RESET => 1 } );

      if ( $opt->{verbose} ) {
         $TPSUP::Expression::verbose = 1;
      }
   }

   my $ret;
   $ret->{error} = 0;

   if ( $opt->{Handlers} ) {
    ROW:
      for my $row ( @{ $opt->{Handlers} } ) {
         my ( $match, $action, $match_code, $action_code ) = @$row;

         if ( $match->() ) {
            if ( $opt->{verbose} ) {
               print STDERR "matched: $match_code\n", "action: $action_code\n";
            }
         } else {
            next ROW;
         }

         if ( !$action->() ) {
            print STDERR "ERROR: failed at path=$path\n";

            if ( $opt->{verbose} ) {
               print STDERR "r = ", Dumper($r);

               print STDERR "TPSUP::Expression vars =\n";
               TPSUP::Expression::dump_var();
            }

            $ret->{error}++;
         }
      }
   }

   if ( $opt->{FlowControl} ) {
      for my $row ( @{ $opt->{FlowControl} } ) {
         my ( $match, $direction, $match_code, $direction_code ) = @$row;

         if ( $match->() ) {
            if ( $opt->{verbose} ) {
               print STDERR "matched:   $match_code\n", "direction: $direction_code\n";
            }

            if ( $direction eq 'prune' ) {
               return $ret;
            } elsif ( $direction eq 'exit' ) {
               $ret->{exit}++;
               return $ret;
            } else {
               croak "unknown FlowControl driection='$direction'";
            }
         }
      }
   }

   if ( !$type || $type eq 'SCALAR' ) {

      # end node

      return $ret;
   }

   $level++;

   # RecursiveDepth is for flow control, violation means return to calling function
   my $max_depth = $opt->{RecursiveDepth};

   if ( $max_depth && $level > $max_depth ) {
      return $ret;
   }

   # RecursiveMax is for safety, violation means exit
   my $max_level = defined $opt->{RecursiveMax} ? $opt->{RecursiveMax} : 100;

   if ( $level > $max_level ) {
      croak "recursive level($level) > max_level($max_level), path=$path";
   }

   if ( $type eq 'ARRAY' ) {
      my $i = 0;

      for my $r (@$ref) {
         my $opt2;
         %$opt2 = %$opt;

         $opt2->{XMLlevel} = $level;

         $opt2->{XMLpath} = $path . "->[$i]";

         $opt2->{XMLnodes} = [ @$nodes, $i ];

         my $new_type = ref $r;
         $opt2->{XMLtypes} = [ @$types, $new_type ];

         $i++;

         $opt->{verbose} && print STDERR "entering $opt2->{XMLpath}, $opt2=", Dumper($opt2);

         my $ref = recursive_handle( $r, $opt2 );

         $ret->{error} += $ref->{error};

         if ( $ref->{exit} ) {
            $ret->{exit}++;
            last;
         }
      }

      return $ret;
   } elsif ( $type eq 'HASH' ) {
      for my $k ( keys %$ref ) {
         my $v = $ref->{$k};

         my $opt2;
         %$opt2 = %$opt;

         $opt2->{XMLlevel} = $level;

         $opt2->{XMLpath} = $path . "->{$k}";

         $opt2->{XMLnodes} = [ @$nodes, $k ];

         my $new_type = ref $v;
         $opt2->{XMLtypes} = [ @$types, $new_type ];

         $opt->{verbose} && print STDERR "entering $opt2->{XMLpath}, $opt2=", Dumper($opt2);

         my $ref = recursive_handle( $v, $opt2 );

         if ( $ref->{exit} ) {
            $ret->{exit}++;
            last;
         }
      }

      return $ret;
   }

   croak "path=$path, cannot handle type=$type";
}

sub chkperl {
   my ( $string, $opt ) = @_;

   # BeginCode is to
   # 1. declare avariable, especially when 'strict' and 'warnings'
   #    are turned on. For example, in order to check the syntax of
   #        $a == $b+1
   #    we can add BeginCode => 'my $a=2; my $b=1;'
   # 2. use name space, for example, add
   #    package DUMMY;
   # 3. add
   #       use strict;
   #       use warnings;
   #
   # Note: BeginCode is just to make the code compilable
   my $BeginCode =
       defined $opt->{BeginCode} ? $opt->{BeginCode}
     : $opt->{verbose}           ? "use warnings; no strict;"
     :                             "no  warnings; no strict;";

   my $code = "
$BeginCode
sub { 
$string 
}
";

   my $compiled = eval $code;

   if ($@) {
      my $numbered_code = add_line_number_to_code($code);
      print STDERR "ERROR: failed to compile
$numbered_code
$@\n";
      return 0;
   } else {
      print STDERR "OK: compiled. string=$string\n" if $opt->{verbose};
      return 1;
   }
}

sub compile_perl {
   my ( $string, $opt ) = @_;

   my $ret;

   my $warn = $opt->{verbose} ? "use" : "no";

   my $wrapped = "$warn warnings; no strict; package TPSUP::Expression; sub { $string }";

   my $compiled;
   $compiled = eval $wrapped;

   $ret->{error}    = $@;
   $ret->{numbered} = add_line_number_to_code($wrapped);
   $ret->{compiled} = $compiled;

   return $ret;
}

sub eval_perl {
   my ( $string, $opt ) = @_;

   my $r1 = compile_perl($string);
   croak "$r1->{numbered}\n\n$r1->{error}: $string" if $r1->{error};

   return $r1->{compiled}->();
}

sub compile_perl_array {
   my ( $in_array, $opt ) = @_;

   my @out_array;    # compiled code

   return undef if !$in_array;

   my $type = ref $in_array;
   $type = '' if !$type;

   croak "compile_perl_array() input wrong type='$type', expecting ARRAY"
     if !$type || $type ne 'ARRAY';

   for my $string (@$in_array) {
      my $ref = compile_perl( $string, $opt );

      croak "$ref->{numbered}\n\n$ref->{error}: $string" if $ref->{error};

      push @out_array, $ref->{compiled};
   }

   return \@out_array;
}

sub compile_paired_strings {
   my ( $input, $opt ) = @_;

   my @strings;

   my $type = ref $input;
   if ( !$type ) {
      @strings = ($input);
   } elsif ( $type eq 'ARRAY' ) {
      @strings = @{$input};
   } else {
      croak "unsupported type='$type'. must be scalar or a ref to ARRAY, input = " . Dumper($input);
   }

   my $ret;

   for my $string (@strings) {

      # string:
      # 'CumQty=${14},Price=sprintf("%.2f",${44}),Open/Close=${77}'
      # break it into pairs
      # ('CumQty=${14}', 'Price=sprintf("%.2f",${44})', 'Open/Close=${77}')

      my $pairs = get_exps_from_string( $string, $opt );
      for my $pair (@$pairs) {
         if ( $pair =~ /^(.+?)=(.+)/ ) {
            my ( $c, $e ) = ( $1, $2 );
            push @{ $ret->{Cols} }, $c;

            my $compiled = TPSUP::Expression::compile_exp( $e, $opt );

            push @{ $ret->{Exps} }, $compiled;

            $ret->{Hash}->{$c} = $compiled;
         } else {
            croak "bad Exp pair: '$pair'. Expecting 'key=exp'. from '$string'";
         }
      }
   }

   return $ret;
}

my $user_by_uid;

sub get_user_by_uid {
   my ($uid) = @_;

   if ( !exists $user_by_uid->{$uid} ) {

      # http://stackoverflow.com/questions/2899518/how-can-i-map-uids-to-user-names-using-perl-library-functions
      my @a = getpwuid($uid);
      $user_by_uid->{$uid} = $a[0];
   }

   return $user_by_uid->{$uid};
}

my $group_by_gid;

sub get_group_by_gid {
   my ($gid) = @_;

   if ( !exists $group_by_gid->{$gid} ) {

      # http://stackoverflow.com/questions/2899518/how-can-i-map-uids-to-user-names-using-perl-library-functions
      my @a = getgrgid($gid);
      $group_by_gid->{$gid} = $a[0];
   }

   return $group_by_gid->{$gid};
}

sub insert_namespace_code {
   my ( $namespace, $code, $opt ) = @_;

   #   if ($namespace eq 'main') {
   #      if ($opt->{verbose}) {
   #          print <<"EOF"
   #eval "$code";
   #EOF
   #      }
   #
   #      eval "$code";
   #   } else {
   if ( $opt->{verbose} ) {
      print <<"EOF";
eval "package $namespace; $code";
EOF
   }
   eval "package $namespace; $code";

   #   }

   if ($@) {
      carp "namespace='$namespace' failed to load code='$code': $@";

      if ( $opt->{SkipBadCode} ) {
         return 0;
      } else {
         exit 1;
      }
   }

   return 1;
}

sub insert_namespace_file {
   my ( $namespace, $file, $opt ) = @_;

   my $code = `cat $file`;

   return insert_namespace_code( $namespace, $code, $opt );
}

sub insert_namespaces {
   my ( $ref, $type, $opt ) = @_;
   my $error = 0;

   for my $pair (@$ref) {

      # TPSUP::FIX,TPSUP::CSV=/home/tian/tpsup/scripts/tpcsv2_test_codefile.pl

      if ( $pair =~ /^(.+?)=(.+)/s ) {
         my ( $namespaces, $string ) = ( $1, $2 );

         for my $ns ( split /,/, $namespaces ) {
            if ( $type eq 'file' ) {
               insert_namespace_file( $ns, $string, $opt ) || $error++;
            } elsif ( $type eq 'code' ) {
               insert_namespace_code( $ns, $string, $opt ) || $error++;
            } else {
               croak "unknowtype='$type' when calling insert_namespaces().";
            }
         }
      } else {
         croak "bad format at '$pair'; expecting 'namespace1,namespace2,...=string'";
      }
   }

   return 0 if $error;

   return 1;
}

sub unique_array {
   my ( $in_arrays, $opt ) = @_;

   #$in_arrays is a ref to array of arrays

   my $CaseInsensitive =
     ( exists( $opt->{CaseInsensitive} ) && $opt->{CaseInsensitive} ) ? 1 : 0;

   my @out_array;
   my $seen;

   for my $in_array (@$in_arrays) {
      for my $e (@$in_array) {
         my $k = $CaseInsensitive ? uc($e) : $e;

         next if $seen->{$k};

         push @out_array, $e;

         $seen->{$k} = 1;
      }
   }

   return \@out_array;
}

sub sort_unique {
   my ( $in_arrays, $opt ) = @_;

   #$in_arrays is a ref to array of arrays

   my $seen;

   for my $in_array (@$in_arrays) {
      for my $e (@$in_array) {
         $seen->{$e}++;
      }
   }

   my @out_array;

   if ( $opt->{SortUniqueNumeric} ) {
      @out_array = sort { $a <=> $b } keys(%$seen);
   } else {
      @out_array = sort { $a cmp $b } keys(%$seen);
   }

   return \@out_array;
}

sub trim_path {
   my ( $path, $opt ) = @_;

   # /a/b/c/../d -> /a/b/d

   my $cwd = Cwd::abs_path();

   if ( $path eq '.' ) {
      $path = $cwd;
   } elsif ( $path =~ m:/^[.]/(.*): ) {
      my $rest = $1;

      $path = "$cwd/$rest";
   } elsif ( $path eq '..' ) {
      $path = "$cwd/..";
   } elsif ( $path = -m:^[.][.]/(.*)$: ) {
      my $rest = $1;

      $path = "$cwd/../$rest";
   }

   my @a1 = split /\/+/, $path;
   shift @a1;    # shift away the undef before the first /

   my @a2;

   for my $e (@a1) {
      if ( $e eq '.' ) {

         # convert /a/./b to /a/b
         next;
      } elsif ( $e eq '..' ) {

         # convert /a/b/../c to /a/c
         pop @a2;
         next;
      } else {
         push @a2, $e;
         next;
      }
   }

   my $newpath = '/' . join( '/', @a2 );

   return $newpath;
}

sub reduce_path {
   my ( $old_path, $opt ) = @_;

   # pathl::path2::path3:pathl:path2 -> pathl::path2::path3

   my @old = split /:/, $old_path;

   my $seen;

   my @new;

   my $i = 0;

   for my $p (@old) {
      if ( $seen->{$p} ) {
         print STDERR "dropping duplicate at $i: '$p'\n" if $opt->{verbose};
      } else {
         $seen->{$p}++;
         push @new, $p;
      }

      $i++;
   }

   my $new_path = join( ":", @new );

   return $new_path;
}

sub get_java {
   my ($opt) = @_;

   my $result;

   my $java;

   if ( $opt->{java} ) {
      $java = $opt->{java};

      if ( !-f $java ) {
         $result->{error} = "$java not found";
         return $result;
      }
   } else {
      $java = "which java";
      chomp $java;

      if ( !$java ) {
         my $other_familiar_places = [ '/dir1/java/*/bin/java', '/dir2/java/*/bin/java', ];

         for my $pattern (@$other_familiar_places) {
            $java = `/bin/ls -1 $pattern|tail -1`;

            if ($java) {
               chomp $java;
               print STDERR "but found java=$java\n";
               last;
            }
         }

         if ( !$java ) {
            $result->{error} = "java not found";
            return $result;
         }
      }
   }

   $result->{java} = $java;

   my @lines = `$java -version 2>&1`;
   chomp @lines;

   # $ java -version
   # java version "1.6.0_22"
   # Java(TM) SE Runtime Environment (build 1.6.0_22-b04)
   # Java HotSpot(TM) 64-Bit Server VM (build 17.1-b03, mixed mode)

   # $ java -version
   # java version "1.5.0_85"
   # Java(TM) 2 Runtime Environment, Standard Edition (build 1.5.0_85-bll)
   # Java HotSpot(TM) Server VM (build 1.5.0_85-bll, mixed mode)

   my $version_main;
   my $version_long;

   for my $line (@lines) {
      if ( $line =~ /java version "(.+?)"/ ) {
         $version_long = $1;

         if ( $version_long =~ /^(\d+[.]\d+)/ ) {
            $version_main = $1;
         }

         last;
      }
   }

   if ( !$version_main ) {
      $result->{error} = "cannot fingure out java version from 'java -version' output:\n@lines";
      return $result;
   }

   $result->{version_main} = $version_main;
   $result->{version_long} = $version_long;

   return $result;
}

sub glob2regex {
   my ( $glob, $opt ) = @_;

   my $regex = $glob;

   $regex =~ s/[.]/\[.\]/g;
   $regex =~ s/[?]/./g;
   $regex =~ s/[*]/.*/g;

   return $regex;
}

# generator/iterator to loop through fh or array
sub looper {
   my ( $input, $opt ) = @_;

   my $type = ref $input;

   my $i = -1;
   my $max;
   if ( $type eq 'ARRAY' ) {
      $max = scalar(@$input);
   }

   return sub {
      if ( $type eq 'GLOB' ) {
         my $line = <$input>;
         return $line;
      } elsif ( $type eq 'ARRAY' ) {
         $i++;

         if ( $i < $max ) {
            return $input->[$i];
         } else {
            return undef;
         }
      } else {
         croak "unsupported type=$type";
         return undef;
      }
   }
}

sub get_items {
   my ( $input, $opt ) = @_;

   my $type = ref $input;
   my $fh;
   my $need_close;

   my $get_line;

   my $delimiter = $opt->{InlineDelimiter};

   if ( !$type ) {

      # $input is a file name
      $fh       = TPSUP::FILE::get_in_fh( $input, $opt );
      $get_line = looper($fh);                              # generator/iterator
   } elsif ( $type eq 'GLOB' ) {

      # $ perl -e 'print ref(\*STDIN), "\n";'
      # GLOB
      # $ perl -e 'open my $fh, "<UTIL.pm"; print ref($fh), "\n";'
      # GLOB
      $fh       = $input;
      $get_line = looper($fh);
   } elsif ( $type eq 'ARRAY' ) {
      $get_line = looper($input);
   } else {
      croak "don't know how to handle input with ref type=$type";
   }

   my @result;

   my $MatchPattern   = $opt->{MatchPattern}   ? qr/$opt->{MatchPattern}/i   : undef;
   my $ExcludePattern = $opt->{ExcludePattern} ? qr/$opt->{ExcludePattern}/i : undef;

   while ( defined( my $line = $get_line->() ) ) {
      chomp $line;

      next if $line =~ /^\s*$/;    # skip blank lines

      if ( !$opt->{NotTrimComment} ) {
         next if $line =~ /^\s*#/;    # skip comment lines
         $line =~ s/#.*//;            # remove in-line comment
      }

      next if defined $MatchPattern   && $line !~ /$MatchPattern/;
      next if defined $ExcludePattern && $line =~ /$ExcludePattern/;

      $line =~ s/^\s+//;    # trim leading  spaces
      $line =~ s/\s+$//;    # trim trailing spaces

      if ($delimiter) {
         push @result, split( /$delimiter/, $line );
      } else {

         # each line is an item. this will allow a string item with space in the middle
         # for example CHL's HK exchange ticker is "941 HK"
         push @result, $line;
      }
   }

   close $fh if $need_close;

   if ( $opt->{ReturnHashCount} ) {
      my $ret;
      for my $i (@result) {
         $ret->{$i}++;
      }
      return $ret;
   } else {
      return \@result;
   }
}

sub get_value_by_key_case_insensitive {
   my ( $value_by_key, $key, $opt ) = @_;

   $opt->{verbose} && print "UTIL.pm ", __LINE__, " value_by_key = ", Dumper($value_by_key);

   return $value_by_key->{$key}
     if exists $value_by_key->{$key};    #lucky that case matched

   my $uc_key = uc($key);

   for my $k ( keys %$value_by_key ) {
      my $uc_k = uc($k);

      return $value_by_key->{$k} if $uc_key eq $uc_k;
   }

   if ( exists $opt->{default} ) {
      return $opt->{default};
   } else {
      confess "key=$key has no match even if case-insensitive in ", Dumper($value_by_key);
   }
}

sub get_first_by_key {
   my ( $array_of_hash, $key, $opt ) = @_;

   #print __FILE__, ':', __LINE__, "\n";
   #carp "stack after = ";

   my $type = ref $array_of_hash;

   croak "ref type='$type' is not ARRAY" if $type ne 'ARRAY';

   for my $href (@$array_of_hash) {
      next if !$href;

      if ( $opt->{CaseSensitive} ) {
         return $href->{$key} if defined $href->{$key};
      } else {

         # try case in-sensitive
         my $v;
         eval {
            # no default here, we need it to fail, to be undef, when not found
            $v = get_value_by_key_case_insensitive( $href, $key );
         };
         return $v if defined $v;
      }
   }

   if ( defined $opt->{default} ) {
      return $opt->{default};
   } else {
      return undef;
   }
}

sub unify_hash {
   my ( $old_ref, $default_subkey, $opt ) = @_;

   #    $old_key_pattern => {
   #       'BOOKID',
   #       'TRADEID'   => '.+?',
   #       'FILLEDQTY' => {pattern=>'\d+', numeric=>1},
   #    },
   #
   #    $new_key_pattern = unify_hash($old_key_pattern, 'pattern');
   #
   # it will look like:
   #
   #    $new_key_pattern => {
   #       'BOOKID'    => {pattern=>'BOOKID'},
   #       'TRADEID'   => {pattern=>'.+?'},
   #       'FILLEDQTY' => {pattern=>'\d+', numeric=>1},
   #    },

   my $new_ref;

   for my $key ( keys %$old_ref ) {
      if ( !defined $old_ref->{$key} ) {
         $new_ref->{$key} = { $default_subkey => $key };
         next;
      }

      my $type = ref $old_ref->{$key};
      if ( !$type ) {
         $new_ref->{$key} = { $default_subkey => $old_ref->{$key} };
      } elsif ( $type eq 'HASH' ) {
         $new_ref->{$key} = $old_ref->{$key};
      } else {
         croak "unsupported type=$type at key=$key " . Dumper($old_ref);
      }
   }

   return $new_ref;
}

sub unify_array_hash {
   my ( $old_array, $key, $opt ) = @_;

   #    $old_array => [
   #       'orders',
   #       { table => 'trades', flag => 'critical'},
   #       'booking',
   #    },
   #
   #    $new_array = unify_array_hash($old_array, 'table');
   #
   #  it will look like:
   #
   #    $new_array => [
   #       { table => 'orders'},
   #       { table => 'trades', flag => 'critical'},
   #       { table => 'booking'},
   #    },

   my $new_array = [];

   return $new_array if !defined $old_array;

   my $type = ref $old_array;
   croak "old_array is not a ref to ARRAY: old_array=" . Dumper($old_array)
     if !$type || $type ne 'ARRAY';

   for my $row (@$old_array) {
      my $type = ref $row;

      if ( !$type ) {
         push @$new_array, { $key => $row };
      } elsif ( $type eq 'HASH' ) {
         if ( defined $row->{$key} ) {
            push @$new_array, $row;
         } else {
            croak "missing key='$key' at row=", Dumper($row);
         }
      } else {
         croak "unsupported type=$type at row=" . Dumper($row);
      }
   }

   return $new_array;
}

sub get_node_list {
   my ( $addr, $path, $opt ) = @_;

   my $depth     = $opt->{NodeDepth}    ? $opt->{NodeDepth}    : 0;
   my $max_depth = $opt->{MaxNodeDepth} ? $opt->{MaxNodeDepth} : 100;

   my @pairs;

   my $type = ref($addr);

   if ( !$type || ( $type ne 'ARRAY' && $type ne 'HASH' ) ) {
      push @pairs, { "$path" => $addr };
   } elsif ( $type eq 'ARRAY' ) {
      croak "get_node_list() reached maxdepth $max_depth"
        if $depth >= $max_depth;

      my $i = 0;
      for my $e (@$addr) {
         push @pairs, @{ get_node_list( $addr->[$i], "$path" . "->[$i]", { %$opt, NodeDepth => $depth + 1, } ) };
         $i++;
      }
   } else {

      # ($type eq 'HASH') {

      croak "get_node_list() reached maxdepth $max_depth"
        if $depth >= $max_depth;

      for my $k ( sort ( keys %$addr ) ) {
         push @pairs, @{ get_node_list( $addr->{$k}, "$path" . "->{$k}", { %$opt, NodeDepth => $depth + 1, } ) };
      }
   }

   return \@pairs;
}

sub add_line_number_to_code {
   my ( $code, $opt ) = @_;

   my $type = ref($code);

   my $lines;
   if ( !$type ) {
      @$lines = split /\n/, $code;
   } elsif ( $type eq 'ARRAY' ) {
      $lines = $code;
   } else {
      croak "add_line_number_to_code() arg1 has unsupported type='$type'.\n";
   }

   my $i = 0;
   my @lines2;
   for my $l (@$lines) {
      $i++;
      push @lines2, sprintf( '%4d %s', $i, $l );
   }

   return join( "\n", @lines2 );
}

sub arrays_to_hashes {
   my ( $arrays, $headers ) = @_;

   my @hashes;
   return \@hashes if !$arrays || !@$arrays;

   croak "headers is not defined" if !$headers;
   croak "headers is empty"       if !@$headers;

   for my $aref (@$arrays) {
      my $href;
      @{$href}{@$headers} = @$aref;
      push @hashes, $href;
   }

   return \@hashes;
}

sub hashes_to_arrays {
   my ( $hashes, $headers ) = @_;

   my @arrays;
   return \@arrays if !$hashes || !@$hashes;

   croak "headers is not defined" if !$headers;
   croak "headers is empty"       if !@$headers;

   for my $href (@$hashes) {
      my $aref;
      @$aref = @{$href}{@$headers};
      push @arrays, $aref;
   }

   return \@arrays;
}

sub top_array {

   # get top slice of an array
   my ( $aref, $max, $opt ) = @_;

   return $aref if !defined $max;

   my @output;

   my $count = 0;
   for my $row (@$aref) {
      if ( $count < $max ) {
         push @output, $row;
      } else {
         last;
      }
      $count++;
   }

   return \@output;
}

sub tail_array {

   # get tail slice of an array
   my ( $aref, $max, $opt ) = @_;

   return $aref if !defined $max;

   my @output;

   my $total = scalar(@$aref);
   my $start = $total - $max;
   $start = 0 if $start < 0;

   for ( my $i = $start ; $i < $total ; $i++ ) {
      push @output, $aref->[$i];
   }

   return \@output;
}

sub parse_rc {
   my ( $code, $opt ) = @_;

   # $code is perl's $?, different from shell's $?

   my $sig = 0;
   my $rc  = 0;
   my $msg = "";

   if ( $code == -1 ) {
      $rc  = 255;
      $msg = "failed to execute";
   } else {
      $sig = $code & 127;

      if ($sig) {
         $msg =
           sprintf "sig=%d, %s", $sig,
           ( $code & 128 ) ? 'CORED !!!'
           : ( $sig == 6 || $sig == 11 ) ? 'coredump disabled'
           :                               'no coredump';
      }
      $rc = $code;
      $rc = $rc & 0xffff;
      $rc >>= 8;
   }

   return { rc => $rc, sig => $sig, msg => $msg };
}

sub convert_to_uppercase {
   my ( $h, $opt ) = @_;

   # convert keys or values to uppercases

   return $h if !$h;

   my $type = ref $h;

   if ( !$type ) {

      # this is a scalar, must be the hash value
      if ( $opt->{ConvertValue} ) {
         return uc($h);
      } else {
         return $h;
      }
   } elsif ( $type eq 'HASH' ) {
      my $h2 = {};
      for my $k ( keys %$h ) {
         my $uc = $opt->{ConvertKey} ? uc($k) : $k;

         if ( $k ne $uc && exists( $h->{$uc} ) ) {
            confess "both '$k' and '$uc' are keys of hash = ", Dumper($h);
         }
         my $converted = convert_to_uppercase( $h->{$k}, $opt );
         $h2->{$uc} = $converted;
      }

      return $h2;
   } elsif ( $type eq 'ARRAY' ) {
      my @h2;
      for my $e (@$h) {
         push @h2, convert_to_uppercase( $e, $opt );
      }

      return \@h2;
   } else {
      return $h;    # unchange
   }
}

sub tp_quote_wrap {
   my ( $e, $opt ) = @_;

   my $e2;

   my $vunerable_chars = '\s';
   if ( $opt->{ShellArg} ) {
      $vunerable_chars = '[\s|]';
   }

   if ( $e =~ /$vunerable_chars/ ) {

      # elemet has space inside
      if ( $e =~ /^'.*'$/ ) {

         # element is already enclosed
         $e2 = $e;
      } elsif ( $e =~ /^".*"$/ ) {

         # element is already enclosed
         $e2 = $e;
      } elsif ( $e =~ /'/ && $e =~ /"/ ) {

         # element has both ' and ", we leave it alone
         $e2 = $e;
      } elsif ( $e =~ /'/ ) {

         # if element has ', we enclose it with "
         $e2 = qq("$e");
      } elsif ( $e =~ /"/ ) {

         # if element has ", we enclose it with '
         $e2 = "'$e'";
      } else {

         # we enclose it with '
         $e2 = "'$e'";
      }
   } else {

      # elemet has no space inside, we leave it alone
      $e2 = "$e";
   }

   return $e2;
}

sub tp_join {
   my ( $a1, $opt ) = @_;

   return "" if !defined $a1;
   my $type = ref($a1);
   croak "only support ARRAY. we got=" . Dumper($a1)
     if ( !$type || $type ne 'ARRAY' );

   # join a array into a string:
   # default delimiter is space.
   # if an array element has space/tab inside, use ' or " to enclose it.
   my $delimiter = defined $opt->{delimiter} ? $opt->{delimiter} : " ";

   my $a2 = [];
   for my $e (@$a1) {
      my $e2 = tp_quote_wrap($e);
      push @$a2, $e2;
   }

   return join( $delimiter, @$a2 );
}

sub resolve_scalar_var_in_string {
   my ( $clause, $Dict, $opt ) = @_;

   # this function relies on %$Dict, not %vars or %known,
   return $clause if !$clause;

   # scalar_vars is enclosed by double curlies {{...=default}},
   # but exclude {{pattern::...} and {{where::...}}
   # /s mean stream, ie, multiline
   # my @scalar_vars = ($clause =~ /\{\{([0-9a-zA-Z_.-]+)\}\}/sg);  # get all scalar vars
   my @vars_defaults = ( $clause =~ /\{\{([0-9a-zA-Z_.-]+)(=.{0,200}?)?\}\}/sg );

   # there are 2 '?':
   #    the 1st '?' is for ungreedy match
   #    the 2nd '?' says the (...) is optional
   # example:
   #    .... {{VAR1=default1}}|{{VAR2=default2}}
   # default can be multi-line
   # default will be undef in the array if not defined.

   my $defaults_by_var;
   my @scalar_vars;
   while (@vars_defaults) {
      my $var     = shift @vars_defaults;
      my $default = shift @vars_defaults;
      if ( defined $default ) {
         $default =~ s/^=//;
      }

      push @scalar_vars,                  $var;
      push @{ $defaults_by_var->{$var} }, $default;

      # note: @scalar_vars may have dups and we don't want to remove dups because
      #       the dup var may have different default.
      #       one scenario we cannot handle yet: for the same var, some has default
      #       and some doesn't. if the var is not in %known, then, will be problem.
   }

   return $clause if !@scalar_vars;    # return when no variable found

   my $yyyymmdd = get_first_by_key( [ $Dict, $opt ], 'YYYYMMDD' );

   my $Dict2 = {};                     # this is a local Dict to avoid polluting caller's $Dict

   if ($yyyymmdd) {
      if ( $yyyymmdd =~ /^(\d{4})(\d{2})(\d{2})$/ ) {
         my ( $yyyy, $mm, $dd ) = ( $1, $2, $3 );
         $Dict2->{yyyymmdd} = $yyyymmdd;
         $Dict2->{yyyy}     = $yyyy;
         $Dict2->{mm}       = $mm;
         $Dict2->{dd}       = $dd;
      } else {
         confess "YYYYMMDD='$yyyymmdd' is in bad format";
      }
   }

   $opt = {} if !$opt;
   my $old_clause = $clause;

   my $idx_by_var;    # this is handle dup var
   for my $var (@scalar_vars) {
      if ( exists $idx_by_var->{$var} ) {
         $idx_by_var->{$var}++;
      } else {
         $idx_by_var->{$var} = 0;
      }
      my $idx = $idx_by_var->{$var};

      my $value;

      # add 'use strict; use warnings;' to catch syntax errors. for example, once
      # i didn't define $opt, eval{} just failed silently without setting any error in $@.
      eval {
         use strict;
         use warnings;
         $value = get_value_by_key_case_insensitive( { %$Dict, %$Dict2, %$opt }, $var );
      };
      if ($@) {
         if ( $opt->{verbose} ) {
            print "cannot resolve var=$var in clause=$clause: $@\n";
            print "Dict = ", Dumper( { %$Dict, %$Dict2, %$opt } );
         }

         my $default = $defaults_by_var->{$var}->[$idx];
         if ( defined $default ) {
            $opt->{verbose} && print "var=$var default=$default\n";
            $value = $default;
         } else {
            $opt->{verbose} && print "var=$var default is undefined.\n";
         }
      }

      next if !defined $value;

      # $clause =~ s/\{\{$var\}\}/$value/igs;
      # don't do global replacement because dup var may have different default
      $clause =~ s/\{\{$var(=.{0,200}?)?\}\}/$value/is;
      $opt->{verbose} && print "replaced #${idx} {{$var}} with '$value'\n";
   }

   return $clause
     if $clause eq $old_clause;    # return when nothing can be resolved.

   # use the following to guard against deadloop
   my $level = defined $opt->{level} ? $opt->{level} : 0;
   $level++;
   my $max_level = 10;
   croak "max_level=$max_level reached when trying to resolve clause=$clause. use verbose mode to debug"
     if $level >= $max_level;

   # recursive call
   $clause = resolve_scalar_var_in_string( $clause, $Dict, { %$opt, level => $level } );

   return $clause;
}

sub gen_combinations_from_a {
   my ( $array, $number_of_items, $opt ) = @_;

   # select 2 from (1,2,3), we get (1,2), (1,3), (2,3)
   # TODO: need to convert recursion to loop if need to handle large data set.

   if ( $number_of_items < 1 ) {
      croak "number_of_items=$number_of_items cannot be less than 1";
   }

   if ( $number_of_items > @$array ) {
      croak "number_of_items to be selected=$number_of_items > total=" . scalar(@$array);
   }

   if ( $number_of_items == @$array ) {
      return [$array];
   }

   my @combos;
   if ( $number_of_items == 1 ) {
      for my $e (@$array) {
         push @combos, [$e];
      }
      return \@combos;
   }

   my @a    = @$array;
   my $head = shift @a;

   # combos without head
   @combos = @{ gen_combinations_from_a( \@a, $number_of_items ) };

   # combos with head
   my $combos2 = gen_combinations_from_a( \@a, $number_of_items - 1 );

   for my $c (@$combos2) {
      push @combos, [ $head, @$c ];
   }

   return \@combos;
}

sub gen_combinations_from_aa {
   my ( $array_of_array, $opt ) = @_;

   # select 1  from each ([1,2], ["A", "B"]),
   # we get ([1,"A"], [1, "B"], [2, "A"], [2, "B"])
   # TODO: need to convert recursion to loop if need to handle large data set.

   return $array_of_array if !@{$array_of_array};

   my @a = @$array_of_array;

   my $head = shift @a;

   my @combos;
   if ( !@a ) {
      for my $e (@$head) {
         push @combos, [$e];
      }
   } else {
      my $sub_combos = gen_combinations_from_aa( \@a );

      for my $e (@$head) {
         for my $sc (@$sub_combos) {
            push @combos, [ $e, @$sc ];
         }
      }
   }

   return \@combos;
}

sub sort_pattern {
   my ( $array, $pattern, $opt ) = @_;

   return $array if !$array || !@$array;

   my $strings_by_key;

   for my $line (@$array) {
      my @keys = ( $line =~ /$pattern/ );
      if (@keys) {
         my $key = join( ",", @keys );
         push @{ $strings_by_key->{$key} }, $line;
      } else {
         $opt->{verbose} && print "pattern=$pattern didn't match: $line\n";
      }
   }

   my @sorted;
   my @sorted_keys =
     $opt->{numeric}
     ? sort { $a <=> $b } keys(%$strings_by_key)
     : sort keys(%$strings_by_key);

   $opt->{verbose} && print "sorted_keys=", Dumper( \@sorted_keys );

   for my $key (@sorted_keys) {
      push @sorted, @{ $strings_by_key->{$key} };
   }

   return \@sorted;
}

sub main {
   use TPSUP::TEST qw(test_lines);

   # for multiple lines of a declaration, do it outside of the test code; and put it into DUMMY namespace.
   $DUMMY::h = {
         a => "hello",
         b => {
            c => "world",
            d => 1,
         },
         e => [qw(kingdom comes)],
         f => [ { g => 'galois' } ],
         j => sub { sleep 1 },
      };


   my $test_code = <<'END';
      TPSUP::UTIL::convert_to_uppercase( $h, { ConvertKey   => 1 } );
      TPSUP::UTIL::convert_to_uppercase( $h, { ConvertValue => 1 } );
      TPSUP::UTIL::convert_to_uppercase( $h, { ConvertKey   => 1, ConvertValue => 1 } );

      TPSUP::UTIL::resolve_string_in_env('$HOME/junk');
      TPSUP::UTIL::resolve_string_in_env('>>$HOME/junk');
      TPSUP::UTIL::resolve_string_in_env('<$HOME/junk');
      TPSUP::UTIL::resolve_string_in_env('$HOME/`date +%Y%m%d`.log');
      TPSUP::UTIL::get_items("UTIL_test_get_items.txt", { InlineDelimiter => '\s+' }); # multiple per line
      TPSUP::UTIL::get_items("UTIL_test_get_items.txt"); # one per line

      our @a = ( "abc12.dat", "abc1.dat", "abc2.dat", "abc9.dat", "abc101.dat", );
      TPSUP::UTIL::sort_pattern( \@a, '^...(\d+).dat', { numeric => 1, verbose => 1 } );

      TPSUP::UTIL::gen_combinations_from_a( [1,2,3,4], 2 );
      TPSUP::UTIL::gen_combinations_from_aa( [[ 1, 2 ], [ 'A', 'B' ], [ 'a', 'b' ]] );

      TPSUP::UTIL::get_value_by_key_case_insensitive( { bottom => 3, top => 4 }, 'Top', { default => 5 } );

      TPSUP::UTIL::get_first_by_key([ {a=> 1,b=>2},{bottom=> 3, top=>4} ],'Top', {default=>5,verbose=>1});

      TPSUP::UTIL::unify_hash( {'TRADEID'=>'.+?', 'FILLEDQTY'=>{pattern =>'\d+', numeric=>1}}, 'pattern');
   
      TPSUP::UTIL::tp_join( ["no_need_wrapping", "has space", "'already wrapped'", "isn't wrapped"] );

      our $our_cfg;
      our %known;
      eval `cat $ENV{TPSUP}/scripts/tptrace_test_trace.cfg`;
      TPSUP::UTIL::get_node_list( $our_cfg, '$our_cfg' );
   
END

   test_lines($test_code);

   print "\n------------------------------------------------\n";
   print "test get_items() on array, multiple items per element\n";
   {
      my $string = "
abc
   def ghi # leading space, ending space, multiple in one line, in-line comment 
# commented line and blank line

jkl
";

      my @array = split /\n/, $string;
      my $a     = get_items( \@array, { InlineDelimiter => '\s+' } );
      print join( "\n", @$a ), "\n";
   }

}

main() unless caller();

1
