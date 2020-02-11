package TPSUP::XML;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   query_xml
   explore_xml
   parse_inline_xml_log
);

use Carp;
use Data::Dumper;
use XML::Simple;
#use TPSUP::Expression;
use TPSUP::UTIL qw(
   recursive_handle
   transpose_arrays
   compile_perl_array
);

use YAML;

#use TPSUP::CSV qw(render_csv);
sub query_xml {
   my ($file, $opt) = @_;

   croak "$file is not found" if ! -f $file;
      
   my $ForceArray;
      
   if ($opt->{ForceArray}) {
      my $type = ref $opt->{ForceArray};
      
      if ($type eq 'ARRAY') {
         @$ForceArray = @{$opt->{ForceArray}};
      } else {
         @$ForceArray = split /,/, $opt->{ForceArray};
      }
   } else {
      $ForceArray = [];
   }
      
   my $KeyAttr;

   if ($opt->{KeyAttr}) {
      my $type = ref $opt->{KeyAttr};

      if ($type eq 'ARRAY') {
         for my $pair (@{$opt->{KeyAttr}}) {
            if ($pair =~ /^(.+?)=(.+)/) {
               $KeyAttr->{$1} = $2;
            } else {
               croak "KeyAttr '$pair' in not in format of key=value";
            }
         }
      } elsif ($type eq 'HASH') {
         $KeyAttr = $opt->{KeyAttr};
      } else {
         croak "KeyAttr has unsupport ref type='$type'. only ref to ARRAY or HASH are supported.";
      }
   } else {
      $KeyAttr = [];
   }
      
   if ($opt->{verbose}) {
      print "ForceArray=", Dumper($ForceArray), "\n";
      print    "KeyAttr=", Dumper($KeyAttr), "\n";
   }
      
   # noattr => 1 is to keep newline chars, otherwise, they would be converted into spaces
   # got clue from http://www.perlmonks.org/bare/index.pl/?node_id=249572
   # but this doesn't work
   # my $root = XMLin($file, ForceArray=>$ForceArray, KeyAttr=>$KeyAttr, noattr => 1);
   # neither the following works
   # http://stackoverflow.com/questions/1457333/php-simplexml-doesnt-preserve-line-breaks-in-xml-attributes
   my $root;
      
   if (defined $opt->{AddRootNode}) {
      my $string = "<$opt->{AddRootNode}>\n";
      $string .= `cat $file`;
      $string .= "\n";
      $string .= "</$opt->{AddRootNode}>";
      
      $root = XMLin($string, ForceArray=>$ForceArray, KeyAttr=>$KeyAttr);
   } else {
      $root = XMLin($file, ForceArray=>$ForceArray, KeyAttr=>$KeyAttr);
   }
      
   $opt->{verbose} && print "root = ", Dumper($root);
      
   my $ret;
    
   if (!$opt->{paths} || !@{$opt->{paths}}) {
      push @$ret, $root;
      return $ret;
   }
      
   my $warn = $opt->{verbose} ? 'use' : 'no';
   #TPSUP::Expression::export(%$ref);
      
   for my $p (@{$opt->{paths}}) {
      #my $compiled = eval "$warn warnings; no strict; package TPSUP::Expression; sub { $p } ";
      #my $value = eval "$warn; no strict; $p";
      #my $value = eval $p;
      my $compiled = eval "$warn warnings; no strict; sub { $p } ";
      croak "Bad expression '$p': $@" if $@;
      my $value = $compiled->();

      push @$ret, $value;
   }
   
   return $ret;
}
   
sub explore_xml {
   my ($input, $opt) = @_;
   
   my $opt2 = {%$opt};
   
   if (    $opt->{HandleExps} && @{$opt->{HandleExps}}
        && $opt->{HandleActs} && @{$opt->{HandleActs}} ) {

      my $exps = compile_perl_array($opt->{HandleExps});
      my $acts = compile_perl_array($opt->{HandleActs});
   
      $opt2->{Handlers} = transpose_arrays([$exps, $acts, $opt->{HandleExps}, $opt->{HandleActs}], $opt);
   }
   
   if (    $opt->{FlowExps} && @{$opt->{FlowExps}}
        && $opt->{FlowDirs} && @{$opt->{FlowDirs}} ) {
   
      my $exps = compile_perl_array($opt->{FlowExps});
      my $dirs = $opt->{FlowDirs};
   
      $opt2->{FlowControl} = transpose_arrays([$exps, $dirs, $opt->{FlowExps}, $opt->{FlowDirs}], $opt);
   }
   
   my $ret;
   
   if ($opt->{ExploreXMLInputIsHash}) {
      my $ref = recursive_handle($input, $opt2);
   
      $ret->{error} += $ret->{error};
   } else {
      my $ref = query_xml($input, $opt2);
   
      my $i=0;
      for my $base (@$ref) {
         my $ref = recursive_handle($base, $opt2);
         $i ++;
         $ret->{error} += $ref->{error};
      }
   }
   
   return $ret;
}

# log contains one-line xml message, eg, MQ log
sub parse_inline_xml_log {
   my ($file, $opt) = @_;

   croak "$file is not found" if ! -f $file;
      
   my $ForceArray;
      
   if ($opt->{ForceArray}) {
      my $type = ref $opt->{ForceArray};
      
      if ($type eq 'ARRAY') {
         @$ForceArray = @{$opt->{ForceArray}};
      } else {
         @$ForceArray = split /,/, $opt->{ForceArray};
      }
   } else {
      $ForceArray = [];
   }
      
   my $KeyAttr;

   if ($opt->{KeyAttr}) {
      my $type = ref $opt->{KeyAttr};

      if ($type eq 'ARRAY') {
         for my $pair (@{$opt->{KeyAttr}}) {
            if ($pair =~ /^(.+?)=(.+)/) {
               $KeyAttr->{$1} = $2;
            } else {
               croak "KeyAttr '$pair' in not in format of key=value";
            }
         }
      } elsif ($type eq 'HASH') {
         $KeyAttr = $opt->{KeyAttr};
      } else {
         croak "KeyAttr has unsupport ref type='$type'. only ref to ARRAY or HASH are supported.";
      }
   } else {
      $KeyAttr = [];
   }
      
   if ($opt->{verbose}) {
      print "ForceArray=", Dumper($ForceArray), "\n";
      print    "KeyAttr=", Dumper($KeyAttr), "\n";
   }
      
   # noattr => 1 is to keep newline chars, otherwise, they would be converted into spaces
   # got clue from http://www.perlmonks.org/bare/index.pl/?node_id=249572
   # but this doesn't work
   # my $root = XMLin($file, ForceArray=>$ForceArray, KeyAttr=>$KeyAttr, noattr => 1);
   # neither the following works
   # http://stackoverflow.com/questions/1457333/php-simplexml-doesnt-preserve-line-breaks-in-xml-attributes
      
   my $warn = $opt->{verbose} ? 'use' : 'no';
   #TPSUP::Expression::export(%$ref);
      
   my @compiled_paths;

   for my $p (@{$opt->{paths}}) {
      #my $compiled = eval "$warn warnings; no strict; package TPSUP::Expression; sub { $p } ";
      #my $value = eval "$warn; no strict; $p";
      #my $value = eval $p;
      my $compiled = eval "$warn warnings; no strict; sub { $p } ";
      croak "Bad expression '$p': $@" if $@;
      push @compiled_paths, $compiled;
   }

   my $match_pattern;
   if ($opt->{MatchPattern}) {
      $match_pattern = qr/$opt->{MatchPattern}/;
   }

   my $exclude_pattern;
   if ($opt->{ExcludePattern}) {
      $exclude_pattern = qr/$opt->{ExcludePattern}/;
   }
    
   open my $fh, "<$file" or croak "cannot read $file: $!";

   while(<$fh>) {
      next if   $match_pattern && ! /$match_pattern/;
      next if $exclude_pattern && /$exclude_pattern/;

      if (/^.*?<[?]xml.*?>\s*(<.*>)/) {
         my $string;

         if (defined $opt->{AddRootNode}) {
            $string = "<$opt->{AddRootNode}>$1</$opt->{AddRootNode}>\n";
         } else {
            $string = "$1\n";
         }

         #print $string;
      
         my $root = XMLin($string, ForceArray=>$ForceArray, KeyAttr=>$KeyAttr);
      
         $opt->{verbose} && print "root = ", Dumper($root);

         my $ret;

         if ($opt->{paths} && @{$opt->{paths}}) {
            for my $compiled (@compiled_paths) {
               push @$ret, $compiled->();
            }
         } else {
            $ret = $root;
         }

         $opt->{verbose} && print "ret = ", Dumper($ret);

         if ($opt->{yamlOutput}) {
            print YAML::Dump($ret);
         }
      }
   }
}

   
1
