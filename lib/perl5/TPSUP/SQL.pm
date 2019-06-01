package TPSUP::SQL;

use strict;
use base qw( Exporter );
our @EXPORT_OK = qw(
      get_dbh
      run_sql
      unlock_conn
);
      
use Carp;
use DBI;
use Data::Dumper;
use TPSUP::UTIL qw(get_tmp_file get_out_fh tpeng_unlock);
use TPSUP::CSV qw(parse_csv_file);
sub unlock_conn {
      
   my ($nickname, $opt) = @_;

   my $connfile;
      
   if ($opt->{connfile}) {
      $connfile = $opt->{connfile};
   } else {
      my $homedir = (getpwuid($<))[7];
      my $hiddendir = "$homedir/.tpsup";
      $connfile = "$hiddendir/conn.csv";
   }
      
   croak "missing $connfile for sql connection" if ! -f $connfile;
      
   my $file_mode = sprintf("%04o", (stat($connfile))[2] & 07777);
   croak "$connfile permissions is $file_mode not expected 0600\n" if "$file_mode" ne "0600";
   my $ref = parse_csv_file($connfile, {keyColumn=>'nickname'});
      
   my $rows = $ref->{$nickname};
      
   croak "nickname='$nickname' doesn't exist in $connfile" if !$rows;
      
   my $r;
      
   @{$r}{qw(string login locked_password)} = @{$rows->[0]}{qw(string login password)};
   $r->{unlocked_password} = tpeng_unlock($r->{locked_password});
      
   # dbi:Oracle:host=AHOST.abc.com;service_name=AHOST.abc.com;port=1501
   my $string = $r->{string};
      
   if ($string =~ /^dbi:(.+?):(.+)/i) {
      $r->{company} = $1;
      
      my $pairs = $2;
      
      for my $pair (split /;/, $pairs) {
         if ($pair =~ /^(.+?)=(.+)/) {
            my $key   = lc($1);
            my $value = $2;
      
            if (exists $r->{$key}) {
               print STDERR "$connfile has dup key '$key' in nickname '$nickname': $string\n";
            }
      
            $r->{$key} = $value;
         }
      }
   }
      
   return $r;
}
      
my $dbh_by_key;
my $current_dbh;
      
sub get_dbh {
   my ($opt) = @_;
      
   my $dbh;
      
   if ($opt->{nickname}) {
      my $nickname = $opt->{nickname};
         
      if (exists $dbh_by_key->{$nickname}) {
         $current_dbh = $dbh_by_key->{$nickname};
         return $current_dbh;
      }
         
      my $conn_info = unlock_conn($nickname, $opt);
         
      my ($string, $login, $password) = @{$conn_info}{qw(string login unlocked_password)};
         
      $dbh = DBI->connect($string, $login, $password);
         
      $dbh_by_key->{$nickname} = $dbh;
      $dbh_by_key->{"$string;$login"} = $dbh;
      $current_dbh = $dbh;
      return $dbh;
   } elsif ($opt->{dbiArray}) {
      # my $dbh =DBI->connect("dbi:Oracle:host=AHOST.ABC.COM;sid=ADB;port=1501", "ADB_USER", 'xxxx');

      my ($string, $login, $password) = ($opt->{dbiArray}->[0], $opt->{dbiArray}->[1], $opt->{dbiArray}->[2]);
      
      if (exists $dbh_by_key->{"$string;$login"}) {
         $current_dbh = $dbh_by_key->{"$string;$login"};
         return $current_dbh;
      }

      if ($opt->{dbiPasswordLocked}) {
         $dbh = DBI->connect($string, $login, tpeng_unlock($password));
      } else {
         $dbh = DBI->connect($string, $login,              $password );
      }
      
      $dbh_by_key->{"$string;$login"} = $dbh;
      $current_dbh = $dbh;
      return $dbh;
   } elsif ($current_dbh) {
      return $current_dbh;
   } else {
      croak "need to run dbh with nickname or dbiArray";
   }
}
      
sub run_sql {
   my ($sql, $opt) = @_;
      
   my $dbh = get_dbh($opt);
      
   if (!$dbh) {
      return undef;
   }
      
   if ($opt->{TrimSql}) {
      # trim the ending: ; go quit
      $sql =~ s/;\s*$//s;
      $sql =~ s/quit\s*$//s;
      $sql =~ s/go\s*$//s;
      
      #do two rounds
      $sql =~ s/;\s*$//s;
      $sql =~ s/quit\s*$//s;
      $sql =~ s/go\s*$//s;
   }
      
   my $sth = $dbh->prepare($sql);

   if (!$sth) {
      print STDERR "failed at preparing sql\n";
      return undef;
   }
      
   my $rows = $sth->execute();
      
   if ( ! $rows ) {
      print STDERR "failed at executing sql\n";
      return undef;
   }
      
   if ($opt->{NonQuery}) {
      return [];
   }
      
   my $OutputDelimiter = defined $opt->{OutputDelimiter} ? $opt->{OutputDelimiter} : ',';
      
   my $out_fh;
   if ($opt->{outfh}) {
      $out_fh = $opt->{outfh};
   } elsif ($opt->{output}) {
      $out_fh = get_out_fh($opt->{output});
   }
      
   my $ReturnDetail;
   my $return_aref;
      
   if ($opt->{OutputHeader}) {
      my @user_headers = split /,/, $opt->{OutputHeader};
      $ReturnDetail->{headers} = \@user_headers;
      
      if (!$opt->{noheader}) {
         print {$out_fh} join($OutputDelimiter, @user_headers), "\n" if $out_fh;
      }
   } elsif ($sth->{NAME}) {
      @{$ReturnDetail->{headers}} = @{$sth->{NAME}};

      if (!$opt->{noheader}) {
         print {$out_fh} join($OutputDelimiter, @{$sth->{NAME}}), "\n" if $out_fh;
      }
   }
      
   my $count=0;
   if (!$opt->{LowMemory}) {
      my $ref = $sth->fetchall_arrayref();

      if (defined $opt->{maxout}) {
         my $i;
         my $maxin = scalar(@$ref);
      
         for ($i=$count; $i<$opt->{maxout}&&$i<$maxin; $i++) {
            push @$return_aref, $ref->[$i];
         }
      
         $ count = $i;
      } else {
         push @$return_aref, @$ref;
      }
   } else {
      # low memory mode, not keeping the hash in memory
      while (my $arrayref = $sth->fetchrow_arrayref()) {
         $count ++;

         last if defined($opt->{maxout}) && $count > $opt->{maxout};

         print {$out_fh} join(",", @$arrayref ), "\n";
      }
      
      #return a ref to empty array to indicate query successful but returned nothing
      return [];
   }
      
   while ( $$sth{syb_more_results} ) {
      $opt->{verbose} && print "# more results:\n";
      
      my $ref = $sth->fetchall_arrayref();
      
      if (defined $opt->{maxout}) {
         my $i;
         my $maxin = scalar(@$ref);
      
         for ($i=$count; $i<$opt->{maxout}&&$i<$maxin; $i++) {
            push @$return_aref, $ref->[$i];
         }
      
         $count = $i;
      } else {
         push @$return_aref, @$ref;
      }
   }
     
   if ($out_fh) {
      # no warnings for the join
      no warnings 'uninitialized';
      
      for my $array_ref ( @$return_aref ) {
         print {$out_fh} join($OutputDelimiter, @$array_ref ), "\n";
      }
   }
      
   if ($opt->{ReturnDetail}) {
      $ReturnDetail->{aref} = $return_aref;
      return $ReturnDetail;
   } else {
      return $return_aref;
   }
}
      
1
      
