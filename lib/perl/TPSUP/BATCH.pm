package TPSUP::BATCH;

use warnings;
use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   parse_cfg
   parse_batch
   parse_input
   run_batch
   set_all_cfg
   get_all_cfg
);

use Carp;
$SIG{ __DIE__ } = \&Carp::confess; # this stack-trace on all fatal error !!!

use Data::Dumper;
$Data::Dumper::Sortkeys = 1;  # this sorts the Dumper output!
$Data::Dumper::Terse = 1;     # print without "$VAR1="

use TPSUP::UTIL qw(
   get_user
   get_abs_path
   get_in_fh
   close_in_fh
   convert_to_uppercase
   resolve_scalar_var_in_string
   get_first_by_key
);
use TPSUP::DATE qw(get_yyyymmdd);
use TPSUP::SHELL qw(parse_string_like_shell);
use TPSUP::GLOBAL qw($we_return);   # global vars

my $today = get_yyyymmdd();

my $cfg_by_file;
sub parse_cfg {
   my ($cfg_file, $opt) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0; 

   croak "$cfg_file not found"    if ! -f $cfg_file;
   croak "$cfg_file not readable" if ! -r $cfg_file;

   my $cfg_abs_path = get_abs_path($cfg_file);

   return $cfg_by_file->{$cfg_abs_path} if exists $cfg_by_file->{$cfg_abs_path};

   my ($cfgdir, $cfgname) = ($cfg_abs_path =~ m:(^.*)/([^/]+):);

   my $cfg_string = `cat $cfg_file`;

   croak "failed to read $cfg_file: $!" if $?;

   # three ways to include new cfg
   #    require 'cfg.pl'
   #       won't spawn an external process
   #    do 'cfg.pl'
   #       won't spawn an external process
   #    eval `cat cfg.pl`
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

   # extra_args => {
   #    test_switch  => 'tw',
   #    test_value   => 'to=s',
   #    test_array   => { spec=>'ta=s',  type=>'ARRAY', help=>'set an array' },
   #    test_hash    => { spec=>'th=s',  type=>'HASH',  help=>'set a hash'   },
   # },

   # this will create another two attr in $our_cfg
   #   extra_getopts
   #      this is parameter, will feed into tpbatch script's GetOptions()
   #   extra_options
   #      this will store what tpbatch script's GetOptions() got from command line.
   #      then the data will be stored in $opt to pass forward.
   # NOTE:
   #   make sure keys on both sides not using the reserved words, eg
   #      b, batch, s, suite, ...

   if (exists $our_cfg->{extra_args}) {
      my $extra_args = $our_cfg->{extra_args};
      for my $k (keys %$extra_args) { 
         # normalize to hash ref
         my $type = ref($extra_args->{$k});
         if (!$type) {
            # scalar type
            my $spec = $extra_args->{$k};
            delete $extra_args->{$k};
            $extra_args->{$k}->{spec} = $spec;
            $extra_args->{$k}->{type} = 'SCALAR';
            $extra_args->{$k}->{help} = '';
         } elsif ($type eq 'HASH') {
            croak "missing spec in k=$k, extra_args = ", Dumper($extra_args)
               if !$extra_args->{$k}->{spec};
            $extra_args->{$k}->{type} = 'SCALAR' if !$extra_args->{$k}->{type};
            $extra_args->{$k}->{help} = ''       if !$extra_args->{$k}->{help};
         } else {
            confess "type='$type' is not supported. must be HASH. extra_args->{$k}=", 
                  Dumper($extra_args->{$k});
         }

         my $v = $extra_args->{$k};

         my $opt_spec = $v->{spec};
         my $opt_type = $v->{type};
         my $opt_help = $v->{help};

         if ($opt_type eq 'SCALAR') {
            push @{$our_cfg->{extra_getopts}}, 
                 ($opt_spec => \$our_cfg->{extra_options}->{$k});
         } elsif ($opt_type eq 'ARRAY') {
            push @{$our_cfg->{extra_getopts}}, 
                 ($opt_spec => \@{$our_cfg->{extra_options}->{$k}});
         } elsif ($type eq 'HASH') {
            push @{$our_cfg->{extra_getopts}}, 
                 ($opt_spec => \%{$our_cfg->{extra_options}->{$k}});
         } else {
            confess "unsupported opt_type='$opt_type' at key=$k in extra_args = ", 
                  Dumper($extra_args);
         }
      }
   }

   my $parse_hash_cfg_sub = \&parse_hash_cfg;

   my $package = $our_cfg->{package};
   if ($package) {
      eval "require $package";
      if ($@) {
         croak "ERROR in: require $package: $@\n";
         return;
      } else {
         $verbose && print "require $package\n";
      }

      # https://stackoverflow.com/questions/25486449/check-if-subroutine-exists-in-perl
      my $package_sub = $package . "::tpbatch_parse_hash_cfg";
      if (exists(&$package_sub)) {
         $verbose && print STDERR "will use $package_sub to parse hash cfg\n";
         $parse_hash_cfg_sub = \&$package_sub;
      }
   }
   
   $our_cfg = $parse_hash_cfg_sub->($our_cfg, $opt);

   $cfg_by_file->{$cfg_abs_path} = $our_cfg;

   return $our_cfg;
}

sub parse_hash_cfg {
   my ($hash_cfg, $opt) = @_;
   # normalize keys: convert them all to upper case

   # convert keys to uppercase
   for my $attr (qw(keys suits)) {
      if (exists $hash_cfg->{$attr})  {
         $hash_cfg->{$attr} = convert_to_uppercase($hash_cfg->{$attr}, {ConvertKey=>1});
      }
   } 
   for my $attr (qw(aliases keychains)) {
      if (exists $hash_cfg->{$attr})  {
         $hash_cfg->{$attr} = convert_to_uppercase($hash_cfg->{$attr}, {ConvertKey=>1, ConvertValue=>1});
      }
   }

   my @keys  = sort(keys %{$hash_cfg->{keys}});
   my $suits = $hash_cfg->{suits};
   my $suits_string = "\n";
   if ($suits) {
      for my $name (sort(keys %{$suits})) {
         my $suit = $suits->{$name};
         my $section = "      $name\n";
         for my $k (sort (keys %$suit)) {
            $section .= "         $k => " 
                        . (defined($suit->{$k}) ?  $suit->{$k} : 'undef') . "\n";
         }

         $suits_string .= $section;
      }
   }

   my @aliases;
   if ($hash_cfg->{aliases}) {
      for my $k (sort(keys %{$hash_cfg->{aliases}})) {
         my $a = $hash_cfg->{aliases}->{$k};
         push @aliases, "$k=>$a";
      }
   }

   my $usage_detail = "
   keys:    @keys

   aliases: @aliases

   suits:   $suits_string

   keys/suits/aliases are case-insensitive but key's value is case sensitive
   ";

   if (grep {$_ eq 'YYYYMMDD'} @keys) {
      $usage_detail .= "\n   yyyymmdd is default to today $today\n";
   }

   $hash_cfg->{usage_detail} = $usage_detail;

   return $hash_cfg;
}


my $my_cfg;
sub set_all_cfg {
   my ($given_cfg, $opt) = @_;

   my $cfg_type = ref $given_cfg;

   if (!$cfg_type) {
      my $cfg_file = $given_cfg;
      $my_cfg = parse_cfg($cfg_file, $opt);
   } elsif ($cfg_type eq 'HASH') {
      $my_cfg = $given_cfg;
   } else {
      croak "unknown cfg type=$cfg_type, expecting filename (string) or HASH. given_cfg = "
         . Dumper($given_cfg) ;
   }
}


sub get_all_cfg {
   my ($opt) = @_;

   croak "my_cfg is not defined yet" if ! defined $my_cfg;

   return $my_cfg;
}

sub parse_input {
   my ($input, $all_cfg, $opt) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   # water-fall
   # 1. use the parser from cfg.py
   # 2. use the parser from 'package' attribute
   # 3. use the default parser in this module

   my $parse_input_sub;
   
   if (exists &parse_input_sub) {
      $parse_input_sub = \&parse_input_sub;
   } else {
      $parse_input_sub = \&parse_input_default_way;
   }

   my $package = $all_cfg->{package};

   if (defined($package)) {
      my $package_sub = $package . "::tpbatch_parse_input";
      
      if (exists &$package_sub) {
         $verbose && print STDERR "will use $package_sub to parse input\n";
         $parse_input_sub = \&$package_sub;
      }
   }

   return $parse_input_sub->($input, $all_cfg, $opt);
}

sub parse_input_default_way {
   my ($input, $all_cfg, $opt) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   my $keys    = $all_cfg->{keys};
   my $aliases = $all_cfg->{aliases};
   my $suits   = $all_cfg->{suits};

   my $type = ref $input;
   my $input_array;
   if (!$type) {
      $input_array = parse_string_like_shell($input, $opt);
   } elsif ($type eq 'ARRAY') {
      $input_array = $input;
   } else {
      croak "unknown type=$type of input";
   }

   my $known = {};

   for my $pair (@$input_array) {
      if ($pair =~ /^(any|check)$/i) {
         next;
      } elsif ($pair =~ /^(.+?)=(.+)$/) {
         my ($key, $value) = (uc($1), $2);
         # convert key to upper case so that user can use both upper case and lower case
         # on command line.

         if ($key eq 'S' || $key eq 'SUIT') {
            my $suitname = uc($value);
            my $suit = $suits->{$suitname};
            if ($suit) {
               print STDERR "loading suit=$suitname ", Dumper($suit);
               for my $k (sort (keys %$suit)) {
                  # suit won't overwrite other input
                  $known->{$k} = $suit->{$k} if !defined $known->{$k};
               }
            } else {
               print STDERR "unknown suit=$suitname in $pair\n";
               exit 1;
            }
         } elsif (exists $aliases->{$key}) {
            my $key2 = $aliases->{$key};
            $verbose && print STDERR "converted alias=$key to $key2\n";
            $known->{$key2} = $value;
         } else {
            if (!exists $keys->{$key}) {
               print STDERR "ERROR: key=$key is not allowed\n";
               exit 1;
            } else {
               $known->{$key} = $value;
            }
         }
      } else {
         print STDERR "bad format at pair=$pair. expected key=value\n";
         exit 1;
      }
   }

   if ($all_cfg->{keys}->{YYYYMMDD}) {
      $known->{'TODAY'}    = $today;
      $known->{'YYYYMMDD'} = $today if !$known->{YYYYMMDD};
   }

   # apply default value from 'keys' section
   for my $k (keys %{$all_cfg->{keys}}) {
      $known->{$k} = $all_cfg->{keys}->{$k} if ! defined($known->{$k});
   }

   if ($all_cfg->{keychains}) {
      # one key's value is default to another key's value, eg
      #     'DESC'        is default to 'SHORT DESC'
      #     'ASSIGNED TO' is default to 'CALLER NAME'
      for my $k (keys %{$all_cfg->{keychains}}) {
         my $source_k = $all_cfg->{keychains}->{$k};

         if (!exists $all_cfg->{keys}->{$source_k}) {
            croak "source key=$source_k in 'keychains' is not part of 'keys'";
         }

         if (!exists $all_cfg->{keys}->{$k}) {
            croak "key=$k in 'keychains' is not part of 'keys'";
         }

         if ( !defined($known->{$k}) && defined($known->{$source_k}) ) {
            $known->{$k} = $known->{$source_k};
         }
      }
   }

   # check for missing keys
   for my $k (keys %{$all_cfg->{keys}}) {
      if (!defined $known->{$k}) {
         print "ERROR: key=$k is not defined. known = ", Dumper($known);
         exit 1;
      }
   }

   return $known;
}


sub batch_eval_code {
   my ($code, $opt) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   my $dict = $opt->{Dict} ? $opt->{Dict} : {};

   if ($verbose) {
      print "------ begin preparing code ------\n";
      print "original code: $code\n";
   }

   $code = resolve_scalar_var_in_string($code, $dict, $opt);

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
      '\n" ;
   }
   $func->();     # run-time error happens here
}

sub parse_batch {
   my ($given_cfg, $batch, $opt) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   set_all_cfg($given_cfg, $opt);

   my $all_cfg = get_all_cfg($opt);

   $verbose>1 && print "all_cfg=", Dumper($all_cfg);

   my $batch_type = ref($batch);

   my @parsed_batch;
   if (!$batch_type) {
      # $batch is a file name

      my $ifh = get_in_fh($batch);
      while(my $line = <$ifh>) {
         next if $line =~ /^\s*$/;
         next if $line =~ /^\s*#/;

         $verbose && print "parsing: $line";

         my $args = parse_string_like_shell($line, {verbose=>$verbose});

         $verbose && print "parsed: ", Dumper($args);

         if (!defined($args)) {
            die "failed to parse: $line";    
         }

         push @parsed_batch, $args;

      }
      close_in_fh($ifh);
   } elsif ($batch_type eq 'ARRAY') {
      # already parsed
      @parsed_batch = @$batch;
   } else {
      die "unsupported batch type=$batch_type. " . Dumper($batch);
   }

   if (!@parsed_batch) {
      print STDERR "no input parsed from batch = ", Dumper($batch);
      return [];
   }

   $verbose && print STDERR "parsed_batch = ", Dumper(\@parsed_batch);

   for my $input (@parsed_batch) {
      next if ! defined $input;

      # $input is array

      # just validate input syntax, trying to avoid aborting in the middle of a batch.
      # therefore, we don't keep the result
      my $discarded = parse_input($input, $all_cfg, {verbose=>$verbose});
   }
   
   return \@parsed_batch;
}


sub init_resources {
   my ($all_cfg, $opt) = @_;

   my $dryrun = $opt->{dryrun};

   return if exists $opt->{init_resources} && $opt->{init_resources} == 0;

   return if !exists $all_cfg->{resources};

   my $resources = $all_cfg->{resources};

   for my $k (keys %$resources) {
      my $res = $resources->{$k};

      next if (exists($res->{enabled}) && $res->{enabled} == 0);

      if (exists($res->{init_resource}) && !$res->{init_resource} ) {
         # if not initiate it now, we pass back function name and params, so that
         # caller can initiate it at another time
         $resources->{$k}->{driver_call} = {
             method => $res->{method},
             kwargs => {%$opt, driver_cfg=>$res->{cfg}},
         };
      } else {
         $res->{driver} = $res->{method}->({%$opt, driver_cfg=>$res->{cfg}}) if !$dryrun;
      }
   }
   #print __LINE__, " all_cfg = ", Dumper($all_cfg);
}


sub run_batch {
   my ($given_cfg, $batch, $opt) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   $verbose && print "run_batch: opt =" . Dumper($opt);

   my $no_post = $opt->{no_post} ? $opt->{no_post} : 0;

   my $parsed_batch = parse_batch($given_cfg, $batch, $opt);

   set_all_cfg($given_cfg);

   my $all_cfg = get_all_cfg();

   my $cfg_opt = exists($all_cfg->{opt}) ? $all_cfg->{opt} : {};

   my $opt2 = {%$cfg_opt, %$opt}; # combine dicts/kwargs

   init_resources($all_cfg, $opt2);

   $verbose>1 && print " all_cfg = ", Dumper($all_cfg);
   $verbose>1 && print " opt2 = ", Dumper($opt2);

   $verbose && print "all_cfg->{optional_args} = ", Dumper($all_cfg->{optional_args});
   $verbose && print "all_cfg->{option} = ",        Dumper($all_cfg->{option});

   my @pre_checks = $all_cfg->{pre_checks} ? @{$all_cfg->{pre_checks}} : ();
   for my $pc (@pre_checks) {
      if (!batch_eval_code($pc->{check}, $opt)) {
         print STDERR "ERROR: pre_check='$pc->{check}' failed\n";
         if ($pc->{suggestion}) {
            print STDERR "   suggestion: $pc->{suggestion}\n";
         } else {
            print STDERR "   No suggestion\n";
         }
         exit 1;
      } else {
         $verbose && print STDERR "pre_check='$pc->{check}' passed\n";
      }
   }

   my $show_progress = get_first_by_key([$opt, $all_cfg], 'show_progress', {CaseSensitive=>1});

   my $total = scalar(@$parsed_batch);
   my $i = 0;
   my $total_time = 0;
   my $last_time = time();
   my $end_time;

   my $known;

   for my $input (@$parsed_batch) {
      $i ++;
      if ($show_progress || $verbose) {
         print STDERR "\n---- running with input $i of $total----\n";
         print STDERR "input = ", Dumper($input);
      }

      $known = parse_input($input, $all_cfg, {verbose=>$verbose});

      $verbose && print __FILE__ . " " . __LINE__ . " after parse input\n",
                        "we known = ", Dumper($known);

      my $code_sub;

      if (exists &code) {
         $verbose && print STDERR "running code() defined in cfg file\n";
         $code_sub = \&code;
      } else { 
         my $package = $all_cfg->{package};
         if ($package) {
            # https://stackoverflow.com/questions/25486449/check-if-subroutine-exists-in-perl
            my $package_sub = $package . "::tpbatch_code";
            if (exists(&$package_sub)) {
               $verbose && print STDERR "code() is not defined in cfg but $package_sub is defined, using it.\n";
               $code_sub =\&$package_sub;
            }
         } 
      }

      if (defined $code_sub) {
         $code_sub->($all_cfg, $known, $opt2);   # code could update $known too.
      } else {
         print STDERR "code() is not defined anywhere, therefore, not run\n";
      }

      if ($show_progress || $verbose) {
          my $now = time();
          my $duration = $now - $last_time;
          $last_time = $now;
          $total_time += $duration;
          my $average = $total_time/$i;

          print STDERR "round $i duration=$duration, total=$total_time, avg=$average\n";
      }
   }

   if ($show_progress || $verbose) {
      print STDERR "\n----------------- batch ends ---------------------\n";
   }

   # https://stackoverflow.com/questions/25486449/check-if-subroutine-exists-in-perl
   if (exists(&post_batch) && !$no_post) {
      my $s = \&post_batch;
      $s->($all_cfg, $known, $opt2);  # post_batch() could update $known too.
   }
}

sub main {
   my $cfgfile   = "$ENV{TPSUP}/scripts/tpslnm_test.cfg";
   my $batchfile = "$ENV{TPSUP}/scripts/tpslnm_test_batch.txt";

   print "----------------- test parse_cfg() -------------------\n";
   my $all_cfg = parse_cfg($cfgfile);
   print "all_cfg = ", Dumper($all_cfg);

   print "----------------- test parse_batch() -------------------\n";
   my $parsed_batch = parse_batch($all_cfg, $batchfile);
   print "parsed_batch = ", Dumper($parsed_batch);

   print "----------------- test parse_input() -------------------\n";
   my $input = $parsed_batch->[0];
   print "input = ", Dumper($input);
   my $known = parse_input($input, $all_cfg);
   print "all we known = ", Dumper($known);

   print "----------------- test run_batch() -------------------\n";

   # to silence this error: Subroutine TPSUP::BATCH::code redefined at BATCH.pm line 365
   no warnings "redefine";

   # the following 3 ways all work, to override an existing sub code()
   # 1.
   #    sub test_code {...};
   #    *TPSUP::BATCH::code = \&test_code;
   # 2. 
   #    sub test_code {...};
   #    *code = \&test_code;
   # 3.
   #    *code = sub {...};
   *code = sub { 
              my ($all_cfg, $known, $opt) = @_; 
              print "from code, we see known = ", Dumper($known); 
           };
   *post_batch = sub { print "a dummy post_batch\n"; };
   
   run_batch($all_cfg, $parsed_batch, {init_resources=>0});
}


main() unless caller();

1
