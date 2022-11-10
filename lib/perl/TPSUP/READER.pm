package TPSUP::READER;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   spot
);


use Carp;
$SIG{ __DIE__ } = \&Carp::confess; # this stack-trace on all fatal error !!!

use Data::Dumper;
$Data::Dumper::Terse = 1;     # print without "$VAR1="
$Data::Dumper::Sortkeys = 1;  # this sorts the Dumper output!

use TPSUP::UTIL qw(get_in_fh);

#use LWP;

# https://www.tutorialspoint.com/perl/perl_object_oriented.htm
sub new {
   my $class = shift;
   my $self = {
      input => shift,
      opt   => shift,
   };

   $self->{generator} = get_generator($self->{input}, $self->{opt});
   $self->{context_pre} = [];
   $self->{context_max} = defined $self->{opt}->{context_max} ? 
                                  $self->{opt}->{context_max} : 3;

   # we will +1 before using this. and therefore equivalently start with 0.
   $self->{context_idx} = $self->{context_max} -1;  

   bless $self, $class;
   return $self;
}

sub next_line {
   my $self = shift;

   my $line = $self->{generator}->();

   my           ($context_pre, $context_idx, $context_max) = 
      @{$self}{qw(context_pre, $context_idx, $context_max)};

   if ($context_max > 0) {
      # if $context_max == 0, we don't have context_pre
      $context_idx ++;
      $context_idx - $context_max if $context_idx >= $context_max;
      $context_pre->[$context_idx] = $line;
      $self->{context_idx} = $context_idx;
   }

   return $line;
}

sub context_pre {
   my $self = shift;

   my           ($context_pre, $context_idx, $context_max) = 
      @{$self}{qw(context_pre, $context_idx, $context_max)};

   my @a;
   if ($context_max >0) {
      for (my $i=$context_idx-$context_max+1; $i<$context_idx+1; $i++) {
         my $normalized_i = $i>=0 ? $i : $i+$context_max;
         push @a, $context_pre->[$normalized_i]; 
      }
      return \@a;
   } else {
      return [];
   }
}

sub get_generator {
   my ($input, $opt) = @_;

   my $input_type = $opt->{input_type} ? $opt->{input_type} : 'string';

   if ($input_type eq 'string') {
      my @lines = split/\n/, $input;
      return sub {
         return shift(@lines); 
      };
   } elsif ($input_type eq 'file') {
      my $in_fh = get_in_fh($input, $opt);
      return sub {
          my $line = <$in_fh>;
          chomp $line;
          return $line;
      }
   } else {
      die "unsupported input_type='$input_type'\n";
   }
}

sub spot {
   my ($input, $key, $opt) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   my $reader = TPSUP::READER->new($input, $opt);

   my $sub_name = "spot_$key";

   if (exists &$sub_name) {
      my $sub = \&$sub_name;
      return $sub->($reader, $opt);
   } else {
      die "sub $sub_name is not defined\n";
   }
}

sub spot_error {
   my ($reader, $opt) = @_;

   my $ret = [];
   while (my $line = $reader->next_line()) {
      if (spot_error_in_line($line)) {    
         push @$ret, $line; 
      }
   }

   return $ret;
}

sub spot_error_in_line {
   my ($line, $opt) = @_;

   # we can also use non-capture grouping (?:...)
   if ($line =~ /err\s*(Msg|Message)|error|fatal|severe|exception/i) {
      # replace quotes with spaces
      $line =~ s:['"]: :g;

      my $line2 = $line;

      # remove non-errors
      #    error=0,
      #    errMsg []
      # $line2 =~ s:(err|error|fatal|severe|exception)(\s|_|-)*(Msg|Mesg|Message)?[s]?\s*(are\s*|is\s*|=\s*)?(0\b|\[\s*\])::ig;
      $line2 =~ s:(err|error|fatal|severe|exception)(\s|_|-)*(Msg|Mesg|Message)?[s]?\s*((are|is|=)\s*)?(0\b|\[\s*\])::ig;
      # notes:
      #   cannot add word border \b after ']'
      #   ((...)\s*)?, we used nested group

      # if there is an error, please call me
      $line2 =~ s:if\s*(I|it|you|they|she|he|there)\s*(has|have|had|is|are)(\s*a|\s*an)?\s*(error|fatal|severe|exception)::ig;

      if ($line2 eq $line) {
         return $line;
      } else {
         return spot_error_in_line($line2);
      }
   }

   return undef;
}

sub spot_logfile {
   my ($reader, $opt) = @_;

   # regex notes:
   #   - (?:...)  is non-capturing group
   #     adding ? at the end, (?:...)?, makes the whole group optional
   #   - nested regex capture group is counted by the order of opening  parenthesis (

   my $ret = [];
   while (my $line = $reader->next_line()) {
      #  log file: /var/log/syslog
      if ( $line =~ /\blog(?:\s*(?:file|dir|path))?[^\/]{0,30}(\/\S+?\/\S+)/i) {
         push @$ret, $1; 
      }
   }

   return $ret;

}


sub main {
   my $string = <<'END';
this is line 1
this is line 2
this is line 3
this is line 4
this is line 5  flag this: ERROR: process dead
this is line 6    process id = 10000
this is line 7
this is line 8
this is line 9  don't flag this: if there is an error, please call me
this is line 10
this is line 11
this is line 12
this is line 13 flag this: Exception: java crashed
this is line 14    java stack1
this is line 15 use log file: /var/log/syslog
this is line 16
this is line 17
this is line 18 don't flag this: msgid=0, price=23.99, qty=100, error=0, msg=filled
this is line 19
this is line 21 don't flag this: found error message []
this is line 22
this is line 23
this is line 24
this is line 25 flag this: FATAL: unknown id
this is line 26
this is line 27
this is line 28
this is line 29
this is line 30
END

   { 
      print "------------ spot error -----------------------------\n";
      my $lines = TPSUP::READER::spot($string, 'error', {verbose=>0});
      print join("\n", @$lines), "\n";
   }

   {
      print "------------ spot logfile -----------------------------\n";
      my $lines = TPSUP::READER::spot($string, 'logfile', {verbose=>0});
      print join("\n", @$lines), "\n";
   }

   print "\n";
}

main() unless caller();

1
