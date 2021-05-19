package TPSUP::SQL;

#use strict;
no strict 'refs' ;
use base qw( Exporter );
our @EXPORT_OK = qw(
      get_dbh
      run_sql
      unlock_conn
      array_to_InClause
      dump_conn_csv
);
      
use Carp;
use DBI;
use JSON;
use Data::Dumper;
use TPSUP::UTIL qw(get_tmp_file get_out_fh render_arrays);
use TPSUP::LOCK qw(tpeng_unlock);
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
   my $ref = parse_csv_file($connfile, {keyColumn=>'nickname',
                                        QuotedInput=>1,
                                        RemoveInputQuotes=>1,
                                       });
      
   croak "failed to parse $connfile" if !$ref;

   my $rows_by_lc;
   my $seen_lc;
   for my $n (keys %$ref) {
      my $lc = lc($n);

      if ($seen_lc->{$lc}) {
         print STDERR "WARN: $lc is duplicated: $seen_lc->{$lc}, $n\n";
      } else {
         $seen_lc->{$lc} = $n;
      }

      $rows_by_lc->{$lc} = $ref->{$n};
   }

   my $lc_nickname = lc($nickname);

   my $rows = $rows_by_lc->{$lc_nickname};
      
   croak "nickname='$nickname' lowercase='$lc_nickname' doesn't exist in $connfile"
      if !$rows;
      
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

sub dump_conn_csv {
   my ($connfile, $opt) = @_;

   croak "missing $connfile for sql connection" if ! -f $connfile;
      
   my $ref = parse_csv_file($connfile, {keyColumn=>'nickname',
                                        QuotedInput=>1,
                                        RemoveInputQuotes=>1,
                                       });

   return if !$ref;
      
   for my $nickname (sort (keys %$ref)) {
      my $rows = $ref->{$nickname};
      
      for my $r (@$rows) {
         my $r2;
         @{$r2}{qw(string login locked_password)} = @{$r}{qw(string login password)};
         $r2->{unlocked_password} = tpeng_unlock($r->{password});
         $r2->{nickname} = $nickname;
      
         print join(",", @{$r2}{qw(string login unlocked_password)}), "\n";
      }
   }
      
   return;
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

      # how to add a method during runtime
      # https://www.perlmonks.org/?node_id=755089
      # https://stackoverflow.com/questions/4185482/how-to-convert-perl-objects-into-json-and-vice-versa/4185679#4185679
      # https://stackoverflow.com/questions/28373405/add-new-method-to-existing-object-in-perl
      
      # how to unbless an object
      # https://stackoverflow.com/questions/25508197/unblessing-perl-objects-and-constructing-the-to-json-method-for-convert-blessed
      
      # i tried to use this to dump $dbh, but always get an empty hash.
     
      # either of the following will add a method dynamically 
      #*DBI::db::TO_JSON = sub { return { %{ shift() } }; };
      sub DBI::db::TO_JSON { return { %{ shift() } }; }

         
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


sub dump_object {
   my ($obj, $opt) = @_;

   # https://stackoverflow.com/questions/4185482/how-to-convert-perl-objects-into-json-and-vice-versa/4185679#4185679
   # https://stackoverflow.com/questions/28373405/add-new-method-to-existing-object-in-perl
   $opt->{verbose} && print STDERR "Dumper(\$obj) = ", Dumper($obj);

   # the following didn't work. i keeps getting
   #     Can't use an undefined value as a HASH reference
   #
   # no strict;
   # $obj->{__actions}{TO_JSON} 
   #    = sub { return { %{ shift() } }; };

   my $json = JSON->new->allow_nonref;
   # $json->allow_blessed([1]);  # this simple returns null
   $json->convert_blessed([1]);  

   return $json->pretty->encode( $obj ); # pretty-printing
}
      

sub run_sql {
   my ($sql, $opt) = @_;

   my $original_sql = $sql;
      
   my $dbh = get_dbh($opt);
      
   if (!$dbh) {
      return undef;
   }
      
   # https://metacpan.org/pod/distribution/DBI/DBI.pm#LongReadLen
   # need to handle some adhoc attributes, for example, 
   #    $dbh->{LongReadLen} = size
   # is used to handle extra long cell

   my $saved_attr = {};

   if (exists($opt->{dbh_attr}) && defined($opt->{dbh_attr})) {
      # $opt->{verbose} && print STDERR "original dbh = ", Dumper($dbh);
      # original dbh = $VAR1 = bless( {}, 'DBI::db' );

      $opt->{verbose} && print STDERR "original dbh = ", dump_object($dbh);

      for my $k (keys %{$opt->{dbh_attr}}) {
         # first save the existing setting
         if (exists($dbh->{$k})) {
            $saved_attr->{$k} = $dbh->{$k};
         }

         # set the attr
         if (defined($opt->{dbh_attr}->{$k}) && "$opt->{dbh_attr}->{$k}" eq "_delete_") {
            delete $dbh->{$k};
         } else {
            $dbh->{$k} = $opt->{dbh_attr}->{$k};
            $opt->{verbose} && print STDERR "\$dbh->{$k} = $dbh->{$k}\n";
         }
      }

      #$dbh->{LongReadLen} = 12800;

      $opt->{verbose} && print STDERR "modifed dump_object(\$dbh) = ", dump_object($dbh);
      $opt->{verbose} && print STDERR "modifed      Dumper(\$dbh) = ",      Dumper($dbh);
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
      
   $opt->{verbose} && $sql ne $original_sql && print STDERR "\nfinalized sql = $sql\n";

   my $sth = $dbh->prepare($sql);

   # restore the dbh attr after prepare()
   # note: if prepare() failed, the restore may not be done
   if (exists($opt->{dbh_attr}) && defined($opt->{dbh_attr})) {
      for my $k (keys %{$opt->{dbh_attr}}) {
         if (exists($saved_attr->{$k})) {
            $dbh->{$k} = $saved_attr->{$k};
         } else {
            delete $dbh->{$k};
         }
      }

      $opt->{verbose} && print STDERR "restored dbh = ", dump_object($dbh);
   }

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
   my $headers = [];
      
   if ($opt->{OutputHeader}) {
      $headers = [split /,/, $opt->{OutputHeader}];
   } elsif ($sth->{NAME}) {
      $headers = $sth->{NAME};
   }

   $ReturnDetail->{headers} = $headers;

   if (!$opt->{noheader} && !$opt->{RenderOutput}) {
      print {$out_fh} join($OutputDelimiter, @$headers), "\n" if $out_fh;
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
      if ($opt->{RenderOutput}) {
         TPSUP::UTIL::render_arrays([$headers, @$return_aref], {%$opt, RenderHeader=>1});
      } else {
         # no warnings for the join
         no warnings 'uninitialized';
         
         for my $array_ref ( @$return_aref ) {
            print {$out_fh} join($OutputDelimiter, @$array_ref ), "\n";
         }
      }
   }
      
   if ($opt->{ReturnDetail}) {
      $ReturnDetail->{aref} = $return_aref;
      return $ReturnDetail;
   } else {
      return $return_aref;
   }
}

sub array_to_InClause {
   my ($aref, $opt) = @_;

   die "array_to_InClause() received empty array. SQL doesn't allow empty in-clause: in ()" if !$aref || !@$aref;

   return "'" . join("', '", @$aref) . "'";
}


sub main {
   print "\n\ntest run_sql\n\n";
   my $sql = "
     SELECT m.firstname, m.lastname, r.ranking
       FROM   tblMembers m, tblAssignment a, tblRanking r
      WHERE m.id = a.MemberId and r.id = a.RankingId
   ";

   run_sql($sql, {nickname=>'tian@tiandb', RenderOutput=>1, output=>'-'});

   print "\n\ntest dump_conn_csv\n\n";

   my $homedir = (getpwuid($<))[7];
   my $hiddendir = "$homedir/.tpsup";
   $connfile = "$hiddendir/conn.csv";
   dump_conn_csv($connfile);
}

main() unless caller();
      
1
