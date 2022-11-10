package TPSUP::XML;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   query_xml
   explore_xml
);

use Carp;
use Data::Dumper; 

my $use_LibXML;

BEGIN {
   # XML::LibXML is much more reliable and faster than XML::Simple, but XML::Simple's
   # famous XMLin() can convert XML to HASH in one step, while XML::LibXML doesn't have.
   # anything similar.
   #
   # XML::LibXML::Simple is a wrapper of XML::LibXML to mimic XML::Simple's
   # interface, in particular XMLin()

   eval { use XML::LibXML::Simple };

   if (!$@) {
      $use_LibXML ++;
      #next DONE_XML_IMPORT;
   }

   # XML::Simple is a secondary choice as it is said not reliable
   eval { use XML::Simple };

   if ($@) {
      croak "neither XML::LibXML nor XML::Simple available";
   }

   # direct XML::Simple to try XML::Parser first. otherwise, it uses SAX which is not very stable
   $XML::Simple::PREFERRED_PARSER = 'XML::Parser'; 

   DONE_XML_IMPORT:
}

use TPSUP::UTIL qw(
   recursive_handle
   transpose_arrays
   compile_perl_array
);

use YAML;

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
      
   my $warn = $opt->{verbose} ? 'use' : 'no';
   #TPSUP::Expression::export(%$ref);
      
   my @compiled_paths;

   for my $p (@{$opt->{paths}}) {
      # sometimes it is challenging to use '$' on command like, eg, $r->{body}.
      # therefore, we allow user to use r->{body} and then convert it to $r->{body} here
      $p =~ s/^r->/\$r->/;

      # for backward compatibility: $root=$r
      my $compiled = eval "$warn warnings; no strict; sub { my \$r=shift; \$root=\$r; $p } ";
      croak "Bad expression '$p': $@" if $@;
      push @compiled_paths, $compiled;
   }

   if ($opt->{DumpInlineXml}) {
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
   
         # print the original format
         print;

         if (/^.*?<[?]xml.*?>\s*(<.*>)/) {
            my $string;
   
            if (defined $opt->{AddRootNode}) {
               $string = "<$opt->{AddRootNode}>$1</$opt->{AddRootNode}>\n";
            } else {
               $string = "$1\n";
            }
   
            $string =~ s/&(?![a-z][a-z][a-z];)/&amp;/g;

            #print $string;
         
            my $r;
            eval { $r = XMLin($string, ForceArray=>$ForceArray, KeyAttr=>$KeyAttr) };

            if ($@) {
               print "failed to parse XML\n";
               next;
            }
         
            $opt->{verbose} && print "r = ", Dumper($r);
   
            my $ret;
   
            if ($opt->{paths} && @{$opt->{paths}}) {
               for my $compiled (@compiled_paths) {
                  push @$ret, $compiled->($r);
               }
            } else {
               $ret = $r;
            }
   
            $opt->{verbose} && print "ret = ", Dumper($ret);
   
            if ($opt->{yamlOutput}) {
               print YAML::Dump($ret);
            }
         }
      }
   } else {
      # input is a single XML, can be multi-lines
      my $r;
         
      my $string ="";

      if (defined $opt->{AddRootNode}) {
         $string .= "<$opt->{AddRootNode}>\n";
      }

      $string .= `cat $file`;
      $string .= "\n";

      if (defined $opt->{AddRootNode}) {
         $string .= "</$opt->{AddRootNode}>";
      }

      # bare & is allowed in some HTML but not in XML
      #   https://stackoverflow.com/questions/3493405/do-i-really-need-to-encode-as-amp
      # As we use our xml module to parse html, we need to escape &: 
      #   convert & into &amp; but leave existing &amp; alone.
      # this needs regex lookahead feature
      #    https://www.regular-expressions.info/lookaround.html
      # negative look-ahead: 
      #    "match a q not followed by a u. q(?!u).

      $string =~ s/&(?![a-z][a-z][a-z];)/&amp;/g;
         
      $r = XMLin($string, ForceArray=>$ForceArray, KeyAttr=>$KeyAttr);
         
      $opt->{verbose} && print "r = ", Dumper($r);
         
      my $ret;
       
      if (!$opt->{paths} || !@{$opt->{paths}}) {
         push @$ret, $r;
         return $ret;
      } else {
         for my $compiled (@compiled_paths) {
            push @$ret, $compiled->($r);
         }
      }
         
      return $ret;
   }
}   
      
1
