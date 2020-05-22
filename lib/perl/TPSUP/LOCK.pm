package TPSUP::LOCK;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
   tpeng_lock
   tpeng_unlock
   get_entry_by_key
   tpentry_cmd
);

use Carp;
use Data::Dumper;
use TPSUP::CSV qw(query_csv2);

sub tpeng_lock($;$) {
   my $MAGIC = 'AccioConfundoLumosNox';
   my $len = length($_[0]);
   my $salt = $_[1] || $MAGIC;
   my $magic = substr( $salt x $len, 0, $len );

   return uri_escape($_[0]^$magic);
}

sub tpeng_unlock($;$) {
   my $MAGIC = 'AccioConfundoLumosNox';
   my $dec = uri_unescape($_[0]);
   my $salt = $_[1] || $MAGIC;
   my $len = length($dec);
   my $magic = substr( $salt x $len, 0, $len );

   return $dec^$magic;
}
    
my $entry_by_book_key;

sub get_entry_by_key {
   my ($key, $opt) = @_;
   
   my $book = get_filename($opt);

   return $entry_by_book_key->{$book}->{$key}
      if exists $entry_by_book_key->{$book}->{$key};

   my $map = parse_book($opt);

   if (! exists $map->{$key}) {
      $entry_by_book_key->{$book}->{$key} = undef;
      return undef;
   }

   if (@{$map->{$key}} > 1) {
      print STDERR "WARN: duplicate key=$key in $book. selected the first one\n";
   }

   my $ref = $map->{$key}->[0];

   my $cmdpattern = $ref->{commandpattern};
   if (!$cmdpattern || $cmdpattern =~ /^\s*$/) {
      print STDERR "ERROR: key=$key commandpattern is not defined\n";
      $entry_by_book_key->{$book}->{$key} = undef;
      return undef;
   }

   $ref->{decoded} = tpeng_unlock($ref->{encoded});

   $entry_by_book_key->{$book}->{$key} = $ref;

   return $entry_by_book_key->{$book}->{$key};
}

my $map_by_book;

sub parse_book {
   my ($opt) = @_;
   my $book = get_filename($opt);
   
   return $map_by_book->{$book} if exists $map_by_book->{$book};

   croak "$book not found" if ! -f $book;
   
   my $file_mode = sprintf("%04o", (stat($book))[2] & 07777);
   croak "$book permissions is $file_mode not expected 0600\n" if "$file_mode" ne "0600";
   
   # example ~/.tpsup/book.csv
   # key,user,encoded,commandpattern,setting,comment
   # swagger,sys.admin,^/usr/bin/curl$|/sqlplus$,%29%06%0F%05%00,'a=1;b=john, sam, and joe',test swagger

   my $result = query_csv2($book, 
                           {requiredColumns=>"key,user,encoded,commandpattern,setting,comment",
                            QuotedInput=>1,
                            RemoveInputQuotes=>1,
                            ReturnType=>'StringKeyedHash=key',
                            NoPrint=>1,
                            }
                           );

   $map_by_book->{$book} = $result->{KeyedHash};

   return $map_by_book->{$book};
}

sub get_filename {
   my ($opt) = @_;

   if ($opt->{book}) {
      return $opt->{book};
   } else {
      my $homedir = (getpwuid($<))[7];
      my $hiddendir = "$homedir/.tpsup";
      return "$hiddendir/book.csv";
   }
}

sub tpentry_cmd {
   my ($cmd, $opt) = @_;

   my $rc;

   if (ref($cmd) eq 'ARRAY') {
      # $cmd is array ref

      # make a copy
      my @cmd2 = @$cmd;

      my $executable = $cmd2[0];

      my $count = scalar(@cmd2);
      for (my $i=0; $i<$count; $i++) {
         # eval/or do/die = try/catch/throw
         # https://perlmaven.com/fatal-errors-in-external-modules
         eval {
            $cmd2[$i] = entry_substitute($cmd2[$i], $executable, $opt);
         } or do {
            print STDERR "$@\n";
            return 1;
         };
      }
      $rc = system(@cmd2);   # system() can take both string and array
   } else {
      # $cmd is a string

      my @cmd2 = split /\s/, $cmd, 2;
      my $executable = $cmd2[0];

      # eval/or do/die = try/catch/throw
      # https://perlmaven.com/fatal-errors-in-external-modules
      eval {
         $cmd = entry_substitute($cmd, $executable,  $opt);
      } or do {
         print STDERR "$@\n";
         return 1;
      };
      $rc = system($cmd);   # system() can take both string and array
   }

   $rc = $rc >> 8;

   return $rc;
}

sub entry_substitute {
   my ($string, $executable, $opt) = @_;

   while (1) {
      if ($string =~ /tpentry\{(.+?)\}\{(.+?)\}/) {
         my $key = $1;
         my $attr = $2;
         my $entry = get_entry_by_key($key);
         if (! defined($entry)) {
            # add "\n" to die so that it will not print line number
            #    "cannot resolve tpentry{key}"
            # vs
            #    "cannot resolve tpentry{key} at LOCK.pm line 179"
            die "cannot resolve tpentry{$key}\n";
         }

         # this is and added security feature so that it won't be easy to trick out the
         # secret, eg,
         #    tpentry -- echo tpentry{key}{decoded}     
         if ($executable !~ /$entry->{commandpattern}/) {
            die "tpentry{$key}: executable=$executable is not allowed to access information.\n";
         }

         if (! exists $entry->{$attr}) {
            die "tpentry{$key}: attr=$attr not found\n";
         }

         my $value = $entry->{$attr};

         $string =~ s/tpentry\{$key\}\{$attr\}/$value/g;
      } else {
         last;
      }
   }

   return $string;
}

######################################################################################
# begin: extracted from
# .../perl5/site_perl/5.10.0/URI/Escape.pm

sub uri_escape {
   my($text) = @_;

   return undef unless defined $text;

   # Build a. char->hex map
   my %escapes;
   for (0..255) {
      $escapes{chr($_)} = sprintf("%%%02X", $_);
   }

   my $RFC3986 = qr/[^A-Za-z0-9\-\._~]/;

   $text =~ s/($RFC3986)/$escapes{$1} || _fail_hi($1)/ge;

   $text;
}

sub uri_unescape {
   # Note from RFC1630: "Sequences which start with a percent sign
   # but are not followed by two hexadecimal characters are reserved
   # for future extension"
   my $str = shift;
   if (@_ && wantarray) {
      # not executed for the common case of a single argument
      my @str = ($str, @_); # need to copy
      for (@str) {
         s/%([0-9A-Fa-f]{2})/chr(hex($1))/eg;
      }
      return @str;
   }
   $str =~ s/%([0-9A-Fa-f]{2})/chr(hex($1))/eg if defined $str;
   $str;
}

sub _fail_hi {
   my $chr = shift;
   Carp::croak(sprintf "Can't escape \\x{%04X)", ord($chr));
}

# end: extracted from
# .../perl5/site_perl/5.10.0/URI/Escape.pm
#################H######HH#####H#############H########H###################H####

sub main {
   use Data::Dumper;
   print "parse_book() =", Dumper(parse_book());
   print "swagger =", Dumper(get_entry_by_key("swagger"));

   my $cmd = "/usr/bin/curl -u tpentry{swagger}{user}:tpentry{swagger}{decoded} -X GET --header 'Accept: text/plain' https://abc.org/LCA2/index.php";
   tpentry_cmd($cmd, {verbose=>1});

   $cmd = "curl -u tpentry{swagger}{user}:tpentry{swagger}{decoded} -X GET --header 'Accept: text/plain' https://abc.org/LCA2/index.php";
   tpentry_cmd($cmd, {verbose=>1});
}

main() unless caller();


1
