package TPSUP::HTML;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   parse_table
);


use Carp;
#$SIG{ __DIE__ } = \&Carp::confess; # this stack-trace on all fatal error !!!

use Data::Dumper;
$Data::Dumper::Terse = 1;     # print without "$VAR1="
$Data::Dumper::Sortkeys = 1;  # this sorts the Dumper output!


#BEGIN {
#   # XML::LibXML is much more reliable and faster than XML::Simple, but XML::Simple's
#   # famous XMLin() can convert XML to HASH in one step, while XML::LibXML doesn't have.
#   # anything similar.
#   #
#   # XML::LibXML::Simple is a wrapper of XML::LibXML to mimic XML::Simple's
#   # interface, in particular XMLin()
#
#   my $use_LibXML;
#   my $verbose = $ENV{TPSUP_DEBUG} ? $ENV{TPSUP_DEBUG} : 0;
#
#   eval { use XML::LibXML::Simple };
#
#   if ($@) {
#      $verbose && print STDERR "use XML::LibXML::Simple failed; $@\n";
#   } else {
#      $use_LibXML ++;
#      $XML::LibXML::Simple::PREFERRED_PARSER = 'XML::Parser';
#      $verbose && print STDERR "use XML::LibXML::Simple\n";
#   }
#
#   if (!$use_LibXML) {
#      # XML::Simple is a secondary choice as it is said not reliable
#      eval { use XML::Simple };
#   
#      if ($@) {
#         croak "use XML::Simple failed: $@";
#      } else {
#         $verbose && print STDERR "use XML::Simple\n";
#   
#         # direct XML::Simple to try XML::Parser first. otherwise, it uses SAX which is not very stable
#         $XML::Simple::PREFERRED_PARSER = 'XML::Parser';
#      }
#   }
#}

use XML::Simple;
$XML::Simple::PREFERRED_PARSER = 'XML::Parser';

sub parse_table {
   my ($table_string, $opt) = @_;

   # $table is either of the following
   #   <tr>...</tr><tr></tr>
   #   <thead>...</thead><tr></tr>
   #   one of the above wrapped in <tbody>...</tbody> 
   #   one of the above wrapped in <table>...</table> 

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   # peel string
   $table_string =~ s:<table.*?>::;
   $table_string =~ s:</table>::;
   $table_string =~ s:<tbody.*?>::;
   $table_string =~ s:</tbody>::;

   # since we removed <table> and <tbody>, we need a root element
   $table_string = "<fakeroot>$table_string</fakeroot>";

   # bare & is allowed in some HTML but not in XML
   #   https://stackoverflow.com/questions/3493405/do-i-really-need-to-encode-as-amp
   # As we use our xml module to parse html, we need to escape &:
   #   convert & into &amp; but leave existing &amp; alone.
   # this needs regex lookahead feature
   #    https://www.regular-expressions.info/lookaround.html
   # negative look-ahead:
   #    "match a q not followed by a u. q(?!u).

   $table_string =~ s/&(?![a-z][a-z][a-z];)/&amp;/g;

   $verbose>1 && print "table_string = ", $table_string, "\n";

   my $result = XMLin($table_string, 
      KeyAttr     => {},
      ForceArray  => [ 'tr', 'td', 'th'],
      SuppressEmpty => '',
   );

   $verbose>1 && print "result = ", Dumper($result);

   my $ret;
   if ($result) {
      if ($result->{thead}->{tr}->[0]->{th}) {
         $ret->{columns} = $result->{thead}->{tr}->[0]->{th}; 
      }
      if ($result->{tr}) {
         for my $r (@{$result->{tr}}) {
            push @{$ret->{rows}}, $r->{td}; 
         }
      }
   }

   return $ret;
}


sub main {
   my $string = <<'END';
      <table style="width:100%">
        <thead>
        <tr>
          <th>Firstname</th>
          <th>Lastname</th>
          <th>Age</th>
        </tr>
        </thead>
        <tr>
          <td>Jill</td>
          <td>Smith</td>
          <td>50</td>
        </tr>
        <tr>
          <td>Eve</td>
          <td>Jackson</td>
          <td>94</td>
        </tr>
        <tr>
          <!-- test escaped &amp; -->
          <td>Tom</td>
          <td>Lee &amp; Chung</td>
          <td>65</td>
        </tr>
        <tr>
          <!-- test non-escaped &amp; -->
          <td>Tom2</td>
          <td>Lee & Chung</td>
          <td>65</td>
        </tr>
        <tr>
          <!-- test missing info -->
          <td>Zach</td>
          <td></td>
          <td></td>
        </tr>
        <caption>this is a test caption</caption>
      </table>
END

   print "------------ parse_table -----------------------------\n";
   my $result = parse_table($string);
   print "result = ", Dumper($result);

   require TPSUP::CSV;
   TPSUP::CSV::render_csv($result->{rows}, $result->{columns}, {ROW_TYPE=>'ARRAY'});

   print join(",", @{$result->{columns}}), "\n";
   for my $r (@{$result->{rows}}) {
      print join(",", @$r), "\n";
   }
}

main() unless caller();

1
