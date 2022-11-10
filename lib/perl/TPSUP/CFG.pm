package TPSUP::CFG;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   parse_simple_cfg
   check_hash_cfg_syntax
);

use warnings;
use Data::Dumper;
use Carp;
use TPSUP::UTIL qw(get_in_fh close_in_fh);

sub check_hash_cfg_syntax {
   my ($cfg, $syntax, $opt) = @_;

   my $error = 0;
   my $message = "";

   for my $k (keys %$cfg) {
      my $v = $cfg->{$k};

      if (!$syntax->{$k}) {
         $message .= "key=$k is not allowed\n";
         $error ++;
         next;
      }

      my $expected_type = $syntax->{$k}->{type};
      my   $actual_type = ref $v;
      $actual_type = 'SCALAR' if !$actual_type;

      if (defined $expected_type) {

         if ($expected_type ne $actual_type) { 
            $message 
               .= "key=$k type mismatch: expected=$expected_type vs actual=$actual_type\n";
            $error ++;
            next;
         }
      }

      my $pattern = $syntax->{$k}->{pattern};
      if (defined $pattern) {
         if ($v !~ /$pattern/) { 
            $message .= "key=$k value=$v not matching expected pattern\n";
            $error ++;
            next;
         }
      }
   }

   for my $k (keys %$syntax) {
      my $v = $syntax->{$k};
      if ($v->{required} && !exists $cfg->{$k}) {
         $message .= "required key=$k is missing\n";
         $error ++;
         next;
      }
   }
   return { error=>$error, message=>$message };
}

sub parse_simple_cfg {
   my ($file, $opt) = @_;
   
   my $CfgKey = $opt->{CfgKey} ? $opt->{CfgKey} : 'name';

   my $ifh = get_in_fh($file, $opt);

   my $result;
   my $current;

   while(my $line = <$ifh>) {
      chomp $line;

      next if $line =~ /^\s*$/;
      next if $line =~ /^\s*#/;

      if ($line =~ /^([^=]+)=(.*)/) {
         my ($key, $value) = ($1, $2);

         if ($key eq $CfgKey) {
            my $name = $value;
            if ($result->{$name}) {
               croak "duplicate CfgKey $CfgKey=$name";
            }

            $result->{$name}->{$CfgKey} = $value;
            $current = $result->{$name};
         } else {
            if (!$current) {
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

   print Dumper(parse_simple_cfg($file));

   print << "END";

--------------------- test parse_simple_cfg() ----------------------------------

END

   my $swagger_syntax = {
      base => {
          base_urls => { type => 'ARRAY', required=>1 },
          op        => { type => 'HASH',  required=>1 },
          entry     => { type => 'SCALAR' },
      },
      op => {
          sub_url   => { type => 'SCALAR', required=>1 },
          num_args  => { type => 'SCALAR', pattern=>qr/^\d+$/ },
          json      => { type => 'SCALAR', pattern=>qr/^\d+$/ },
          method    => { type => 'SCALAR', pattern=>qr/^POST$/ },
          comment   => { type => 'SCALAR' },
          validator => { type => 'SCALAR' },
          post_data => { type => 'SCALAR' },
          test_str  => { type => 'ARRAY'  },
      },
   };
   
   my $swagger_cfg = {
         mybase1 =>{
            base_urls => ['https://myhost1.abc.com:9100'],
            entry     => 'swagger-tian',
            op        => {
               myop1_1 => {
                  num_args  => 1,
                  sub_url   => 'app1/api/run_myop1_1',
                  json      => 1,
                  method    => 'POST',
                  post_data => '{{A0}}',
                  validator => qq("{{A0}}" =~ /hello/),
                  comment   => 'run myop1_1',
                  test_str  => [ "abc",  qq("{'hello world'}") ],  # two tests here
               },
               myop1_2 => {
                  sub_url   => 'app1/api/run_myop1_2',
                  json      => 1,
                  method    => 'POST',
                  post_data => qq('["hard coded"]'),
                  comment   => 'run myop1',
               },
            },
         },
   };

   for my $k (keys %$swagger_cfg) {
      my $base_cfg = $swagger_cfg->{$k};
      my $result = check_hash_cfg_syntax($base_cfg, $swagger_syntax->{base});
      print "base=$k, result=", Dumper($result);

      for my $k2 (keys %{$base_cfg->{op}}) {
         my $op_cfg = $base_cfg->{op}->{$k2};
         my $result2 = check_hash_cfg_syntax($op_cfg, $swagger_syntax->{op});
         print "op=$k2, result2=", Dumper($result2);
      }
   }
}

main() unless caller();


1
