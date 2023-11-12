package TPSUP::SQL;

use strict;

#no strict 'refs' ;
use base qw( Exporter );
our @EXPORT_OK = qw(
  get_dbh
  run_sql
  dbh_do
  unlock_conn
  array_to_InClause
  dump_conn_csv
);

use Carp;
use DBI;
use JSON;
use Data::Dumper;
use TPSUP::UTIL qw(get_tmp_file render_arrays);
use TPSUP::FILE qw(get_out_fh);
use TPSUP::LOCK qw(tpeng_unlock);
use TPSUP::CSV  qw(parse_csv_file);

sub unlock_conn {
   my ( $nickname, $opt ) = @_;

   my $connfile;

   if ( $opt->{connfile} ) {
      $connfile = $opt->{connfile};
   } else {
      my $homedir   = ( getpwuid($<) )[7];
      my $hiddendir = "$homedir/.tpsup";
      $connfile = "$hiddendir/conn.csv";
   }

   croak "missing $connfile for sql connection" if !-f $connfile;

   my $file_mode = sprintf( "%04o", ( stat($connfile) )[2] & 07777 );
   croak "$connfile permissions is $file_mode not expected 0600\n"
     if "$file_mode" ne "0600";
   my $ref = parse_csv_file(
      $connfile,
      {
         keyColumn         => 'nickname',
         QuotedInput       => 1,
         RemoveInputQuotes => 1,
      }
   );

   croak "failed to parse $connfile" if !$ref;

   my $rows_by_lc;
   my $seen_lc;
   for my $n ( keys %$ref ) {
      my $lc = lc($n);

      if ( $seen_lc->{$lc} ) {
         print STDERR "WARN: $lc is duplicated: $seen_lc->{$lc}, $n\n";
      } else {
         $seen_lc->{$lc} = $n;
      }

      $rows_by_lc->{$lc} = $ref->{$n};
   }

   my $lc_nickname = lc($nickname);

   my $rows = $rows_by_lc->{$lc_nickname};

   croak
     "nickname='$nickname' lowercase='$lc_nickname' doesn't exist in $connfile"
     if !$rows;

   my $r;

   @{$r}{qw(string login locked_password)} =
     @{ $rows->[0] }{qw(string login password)};
   $r->{unlocked_password} = tpeng_unlock( $r->{locked_password} );

   # dbi:Oracle:host=AHOST.abc.com;service_name=AHOST.abc.com;port=1501
   my $string = $r->{string};

   if ( $string =~ /^dbi:(.+?):(.+)/i ) {
      $r->{company} = $1;

      my $pairs = $2;

      for my $pair ( split /;/, $pairs ) {
         if ( $pair =~ /^(.+?)=(.+)/ ) {
            my $key   = lc($1);
            my $value = $2;

            if ( exists $r->{$key} ) {
               print STDERR
"$connfile has dup key '$key' in nickname '$nickname': $string\n";
            }

            $r->{$key} = $value;
         }
      }
   }

   return $r;
}

sub dump_conn_csv {
   my ( $connfile, $opt ) = @_;

   croak "missing $connfile for sql connection" if !-f $connfile;

   my $ref = parse_csv_file(
      $connfile,
      {
         keyColumn         => 'nickname',
         QuotedInput       => 1,
         RemoveInputQuotes => 1,
      }
   );

   return if !$ref;

   for my $nickname ( sort ( keys %$ref ) ) {
      my $rows = $ref->{$nickname};

      for my $r (@$rows) {
         my $r2;
         @{$r2}{qw(string login locked_password)} =
           @{$r}{qw(string login password)};
         $r2->{unlocked_password} = tpeng_unlock( $r->{password} );
         $r2->{nickname}          = $nickname;

         print join( ",", @{$r2}{qw(string login unlocked_password)} ), "\n";
      }
   }

   return;
}

my $dbh_by_key;
my $current_dbh;

sub get_dbh {
   my ($opt) = @_;

   my $dbh;

   if ( $opt->{nickname} ) {
      my $nickname = $opt->{nickname};

      if ( exists $dbh_by_key->{$nickname} ) {
         $current_dbh = $dbh_by_key->{$nickname};
         return $current_dbh;
      }

      my $conn_info = unlock_conn( $nickname, $opt );

      my ( $string, $login, $password ) =
        @{$conn_info}{qw(string login unlocked_password)};

      if ( $opt->{PrintConnInfo} ) {
         print STDERR "connection=$string, login=$login\n";
      }

      $dbh = DBI->connect( $string, $login, $password );

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

      $dbh_by_key->{$nickname}        = $dbh;
      $dbh_by_key->{"$string;$login"} = $dbh;
      $current_dbh                    = $dbh;
      return $dbh;
   } elsif ( $opt->{dbiArray} ) {

# my $dbh =DBI->connect("dbi:Oracle:host=AHOST.ABC.COM;sid=ADB;port=1501", "ADB_USER", 'xxxx');

      my ( $string, $login, $password ) = (
         $opt->{dbiArray}->[0],
         $opt->{dbiArray}->[1],
         $opt->{dbiArray}->[2]
      );

      if ( exists $dbh_by_key->{"$string;$login"} ) {
         $current_dbh = $dbh_by_key->{"$string;$login"};
         return $current_dbh;
      }

      if ( $opt->{dbiPasswordLocked} ) {
         $dbh = DBI->connect( $string, $login, tpeng_unlock($password) );
      } else {
         $dbh = DBI->connect( $string, $login, $password );
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
   my ( $obj, $opt ) = @_;

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
   $json->convert_blessed( [1] );

   return $json->pretty->encode($obj);    # pretty-printing
}

sub dbh_do {
   my ( $sql, $opt ) = @_;

   # this is to run $dbh->do() for statement like
   # SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED ;
   # SELECT * FROM TABLE_NAME ;
   # COMMIT ;

   my $dbh = get_dbh($opt);

   $dbh->do($sql);
}

sub parse_sql {
   my ( $sql, $opt ) = @_;

   my $verbose = $opt->{verbose};

# this is to handle multi-commands sql
# https://stackoverflow.com/questions/22709497/perl-dbi-mysql-how-to-run-multiple-queries-statements

   # first remove multi-line comments /* ... */
   $sql =~ s:/[*].*?[*]/::gs;

   # then remove singlem-line comments -- ...
   $sql =~ s:--.*::g;

   # to test: test_remove_sql_comment.pl

   if ( $opt->{NotSplitAtSemiColon} ) {

      # then we split at GO
      my @sqls = split /;\s*GO\s*;/i,
        $sql;    # # split separator can be a multi-line string
      my @sqls2;

      # add back GO statement as we use it to determine restart point
      for my $s (@sqls) {
         push @sqls2, $s;
         push @sqls2, 'GO';
      }

      pop @sqls2;    # remove the last 'GO' as it the default

      return @sqls2;
   } else {

      # then split into single command
      my @sqls = split /;/, $sql;
      @sqls = grep { !/^\s*$/ } @sqls;

      $verbose > 1 && print "sqls = ", Dumper( \@sqls );

      return @sqls;
   }
}

sub handle_output_out_fh {
   my ($opt) = @_;

   my $out_fh;
   my $out_fh_need_closing;
   if ( $opt->{out_fh} ) {
      $out_fh = $opt->{out_fh};
   } elsif ( $opt->{output} ) {
      $out_fh              = get_out_fh( $opt->{output} );
      $out_fh_need_closing = 1;
   }

   return ( $out_fh, $out_fh_need_closing );
}

sub run_sql {
   my ( $sql, $opt ) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   my @sqls = parse_sql( $sql, $opt );

   my ( $out_fh, $out_fh_need_closing ) = handle_output_out_fh($opt);

   my $looking_for_GO
     ;    # if a command failed, we skip following commands upto the next GO.
   my $ret;
   for my $s (@sqls) {

      # $ perl -e '("quit;" =~ /^\s*QUIT\s*;?$/i) && print "yes\n";'
      # $ perl -e '("quit" =~ /^\s*QUIT\s*;?$/i) && print "yes\n";'
      # $ perl -e '(" quit " =~ /^\s*QUIT\s*;?$/i) && print "yes\n";'
      last if $s =~ /^\s*QUIT\s*;?$/i;

# 'GO' vs ';'
# https://stackoverflow.com/questions/1517527/what-is-the-difference-between-
# and-go-in-t-sql
# "
#    GO is not actually a T-SQL command. The GO command was introduced by Microsoft
#    tools as a way to separate batch statements such as the end of a stored
#    procedure. GO is supported by the Microsoft SQL stack tools but is not
#    formally part of other tools.
#    "GO" is similar to ; in many cases, but does in fact signify the end of a batch.
#    Each batch is committed when the "GO" statement is called, so if you have:
#       SELECT * FROM table-that-does-not-exist;
#       SELECT * FROM good-table;
#    in your batch, then the good-table select will never get called because the
#    first select will cause an error.
#
#    If you instead had:
#       SELECT * FROM table-that-does-not-exist
#       GO
#       SELECT * FROM good-table
#       GO
#    The first select statement still causes an error, but since the second statement
#    is in its own batch, it will still execute.
#    GO has nothing to do with committing a transaction.
# "
      if ($looking_for_GO) {

         # if a command failed, we skip following commands upto the next GO.
         if ( $s =~ /^\s*GO\s*;?$/i ) {
            $looking_for_GO = 0;
         }
         next;
      }

      next if $s =~ /^\s*GO\s*;?$/i;

      $opt->{verbose} > 1 && print "single sql = $sql\n";
      $ret = run_single_sql( $s, { %$opt, out_fh => $out_fh } );

      #print "ret = ", Dumper($ret);

      if ( !defined $ret ) {

         # undefined $ret indicates failed command
         if ( $opt->{IfFail} && $opt->{IfFail} =~ /Proceed/i ) {
            next;
         } else {

            # if failed, skip following commands up to the next GO.
            $looking_for_GO = 1;
            next;
         }
      }
   }

   close($out_fh) if $out_fh_need_closing && $out_fh != \*STDOUT;

   return $ret;    # return the last result. If it was a failure, $ret is undef.
}

sub run_single_sql {
   my ( $sql, $opt ) = @_;

   my $verbose = $opt->{verbose} ? $opt->{verbose} : 0;

   my $original_sql = $sql;

   my $dbh = get_dbh($opt);

   if ( !$dbh ) {
      carp "Failed to get dbh";
      return undef;
   }

   # https://metacpan.org/pod/distribution/DBI/DBI.pm#LongReadLen
   # need to handle some adhoc attributes, for example,
   #    $dbh->{LongReadLen} = size
   # is used to handle extra long cell

   my $saved_attr = {};

   if ( exists( $opt->{dbh_attr} ) && defined( $opt->{dbh_attr} ) ) {

      # $opt->{verbose} && print STDERR "original dbh = ", Dumper($dbh);
      # original dbh = $VAR1 = bless( {}, 'DBI::db' );

      $verbose && print STDERR "original dbh = ", dump_object($dbh);

      for my $k ( keys %{ $opt->{dbh_attr} } ) {

         # first save the existing setting
         if ( exists( $dbh->{$k} ) ) {
            $saved_attr->{$k} = $dbh->{$k};
         }

         # set the attr
         if ( defined( $opt->{dbh_attr}->{$k} )
            && "$opt->{dbh_attr}->{$k}" eq "_delete_" )
         {
            delete $dbh->{$k};
         } else {
            $dbh->{$k} = $opt->{dbh_attr}->{$k};
            $verbose > 1 && print STDERR "\$dbh->{$k} = $dbh->{$k}\n";
         }
      }

      #$dbh->{LongReadLen} = 12800;

      $verbose && print STDERR "modifed dump_object(\$dbh) = ",
        dump_object($dbh);
      $verbose && print STDERR "modifed      Dumper(\$dbh) = ", Dumper($dbh);
   }

   # if ($opt->{TrimSql}) {
   #    # trim the ending: ; go quit
   #    $sql =~ s/;\s*$//s;
   #    $sql =~ s/quit\s*$//s;
   #    $sql =~ s/go\s*$//s;
   #
   #    #do two rounds
   #    $sql =~ s/;\s*$//s;
   #    $sql =~ s/quit\s*$//s;
   #    $sql =~ s/go\s*$//s;
   # }

   $verbose && $sql ne $original_sql && print STDERR "\nfinalized sql = $sql\n";

   my $sth = $dbh->prepare($sql);

   # restore the dbh attr after prepare()
   # note: if prepare() failed, the restore may not be done
   if ( exists( $opt->{dbh_attr} ) && defined( $opt->{dbh_attr} ) ) {
      for my $k ( keys %{ $opt->{dbh_attr} } ) {
         if ( exists( $saved_attr->{$k} ) ) {
            $dbh->{$k} = $saved_attr->{$k};
         } else {
            delete $dbh->{$k};
         }
      }

      $verbose && print STDERR "restored dbh = ", dump_object($dbh);
   }

   if ( !$sth ) {
      carp "failed at preparing sql: " . $dbh->errstr;
      print STDERR "failed sql = $sql\n";
      return undef;
   }

# https://stackoverflow.com/questions/6923230/how-do-i-get-the-number-of-affected-rows-when-i-use-dbis-prepare-execute-for-no
# From the documentation about the execute method in DBI:
#    For a non-"SELECT" statement, "execute" returns the number of rows affected, if
#    known. If no rows were affected, then "execute" returns "0E0", which Perl will
#    treat as 0 but will regard as true. Note that it is not an error for no rows to
#    be affected by a statement. If the number of rows affected is not known,
#    then "execute" returns -1.
   my $rows = $sth->execute();
   $verbose > 1 && print STDERR "rows = ", Dumper($rows);

   if ( !$rows ) {
      carp "failed at executing sql: " . $sth->errstr;
      print STDERR "failed sql = $sql\n";
      return undef;
   }

# RowsInCache doesn't seem to work in mysql. RawRowsInCaches always undef when i tested.
# looks like it is not implemented in mysql driver.
# from https://metacpan.org/pod/DBI#RowsInCache
#    If the driver supports a local row cache for SELECT statements, then this
#    attribute holds the number of un-fetched rows in the cache. If the driver doesn't,
#    then it returns undef. Note that some drivers pre-fetch rows on execute, whereas
#     others wait till the first fetch.
   $verbose > 1 && print STDERR "RowsInCache = ", Dumper( $sth->{RowsInCache} );

#if (!$sth->{RowsInCache}) {
#   #return a ref to empty array to indicate query successful but returned nothing
#   return [];
#}

# there is no reliable way for DBI to tell us whether rows are returned by command
#    https://metacpan.org/pod/DBI#rows
# if we do a eval {fetchall}, it will work but will print nasty errors
#    DBD::mysql::st FETCH failed: statement contains no result at /home/tian/sitebase/
#    github/tpsup/lib/perl/TPSUP/SQL.pm line 384.
# the above error message is in DBD::mysql source code
#    DBD-mysql-4.050/dbdimp.c
# I don't see a way to silence it without changing the source code

# https://metacpan.org/pod/DBI chat room folks told me use 'Active', working in mysql.
# https://metacpan.org/pod/DBI#Active
#   The Active attribute is true if the handle object is "active". This is rarely used
#   in applications. The exact meaning of active is somewhat vague at the moment. For a
#   database handle it typically means that the handle is connected to a database
#   ($dbh->disconnect sets Active off). For a statement handle it typically means that
#   the handle is a SELECT that may have more data to fetch. (Fetching all the data or
#   calling $sth->finish sets Active off.)
   $verbose > 1 && print STDERR "Active = ", Dumper( $sth->{Active} );

   $verbose > 1 && print STDERR "dhb driver name = ", $dbh->{Driver}{Name},
     "\n";

   my $has_result;

   if ( $dbh->{Driver}{Name} =~ /Active_not_supported_driver/i ) {

      # use this when 'Active' attribute is not implemented in driver
      # hope we will never have to come here.
      if ( $sql =~ /^\s*(SELECT|SHOW|PRINT|DISPLAY)/i ) {
         $has_result = 1;
      } elsif ( $sql =~ /^\s*WITH\s.*\(.+?\)\s*SELECT/is ) {

         # WITH PeopleAndTZs AS
         # (
         #    SELECT * FROM (VALUES
         #      ('Rob',   'Cen. Australia Standard Time'),
         #      ('Paul',  'New Zealand Standard Time')
         #    ) t (person, tz)
         # )
         # SELECT tz.person,
         #   FROM PeopleAndTZs tz;
         $has_result = 1;
      } elsif ( $sql =~
         /^\s*(CREATE|DROP|INSERT|UPDATE|DELETE|GRANT|SET|BEGIN|COMMIT)/i )
      {
         $has_result = 0;
      } else {

   # this includes stored procedures, hard to tell whether output will come out.
   # this part is let command-line to decide
         $has_result = !$opt->{NonQuery};
      }
   } else {

      # we rely on 'Active' attribute
      $has_result = 1 if $sth->{Active};
   }

   if ( !$has_result ) {

      # int($rows) is to convert string '0E0' to integer 0.
      print STDERR
        "1 non-query command executed successfully, affected rows = ",
        defined($rows) ? int($rows) : 'unknown',
        ".\n";
      return []
        ;  #return empty array to indicate query successful but returned nothing
   }

   my $OutputDelimiter =
     defined $opt->{OutputDelimiter} ? $opt->{OutputDelimiter} : ',';

   my ( $out_fh, $out_fh_need_closing ) = handle_output_out_fh($opt);

   my $ReturnDetail;
   my $return_aref;
   my $headers = [];

   if ( $opt->{OutputHeader} ) {
      $headers = [ split /,/, $opt->{OutputHeader} ];
   } elsif ( $sth->{NAME} ) {
      $headers = $sth->{NAME};
   }

   $ReturnDetail->{headers} = $headers;

   if ( !$opt->{noheader} && !$opt->{RenderOutput} ) {
      print {$out_fh} join( $OutputDelimiter, @$headers ), "\n" if $out_fh;
   }

   my $count = 0;
   if ( !$opt->{LowMemory} ) {
      my $ref = $sth->fetchall_arrayref();
      if ( defined $opt->{maxout} ) {
         my $i;
         my $maxin = scalar(@$ref);

         for ( $i = $count ; $i < $opt->{maxout} && $i < $maxin ; $i++ ) {
            push @$return_aref, $ref->[$i];
         }

         $count = $i;
      } else {
         push @$return_aref, @$ref;
      }
   } else {

      # low memory mode, not keeping the hash in memory
      while ( my $arrayref = $sth->fetchrow_arrayref() ) {
         $count++;

         last if defined( $opt->{maxout} ) && $count > $opt->{maxout};

         print {$out_fh} join( ",", @$arrayref ), "\n" if $out_fh;
      }

      close($out_fh) if $out_fh_need_closing && $out_fh != \*STDOUT;

      return []
        ;  #return empty array to indicate query successful but returned nothing
   }

   while ( $$sth{syb_more_results} ) {
      $verbose && print "# more results:\n";

      my $ref = $sth->fetchall_arrayref();

      if ( defined $opt->{maxout} ) {
         my $i;
         my $maxin = scalar(@$ref);

         for ( $i = $count ; $i < $opt->{maxout} && $i < $maxin ; $i++ ) {
            push @$return_aref, $ref->[$i];
         }

         $count = $i;
      } else {
         push @$return_aref, @$ref;
      }
   }

   if ($out_fh) {
      if ( $opt->{RenderOutput} ) {
         TPSUP::UTIL::render_arrays( [ $headers, @$return_aref ],
            { %$opt, RenderHeader => 1 } );
      } else {

         # no warnings for the join
         no warnings 'uninitialized';

         for my $array_ref (@$return_aref) {
            print {$out_fh} join( $OutputDelimiter, @$array_ref ), "\n";
         }
      }
      close($out_fh) if $out_fh_need_closing && $out_fh != \*STDOUT;
   }

   if ( $opt->{ReturnDetail} ) {
      $ReturnDetail->{aref} = $return_aref;
      return $ReturnDetail;
   } else {
      return $return_aref;
   }
}

sub array_to_InClause {
   my ( $aref, $opt ) = @_;

   die
"array_to_InClause() received empty array. SQL doesn't allow empty in-clause: in ()"
     if !$aref || !@$aref;

   return "'" . join( "', '", @$aref ) . "'";
}

sub main {
   print "\n\ntest run_sql\n\n";
   my $sql = "
     SELECT m.firstname, m.lastname, r.ranking
       FROM   tblMembers m, tblAssignment a, tblRanking r
      WHERE m.id = a.MemberId and r.id = a.RankingId
   ";

   run_sql( $sql,
      { nickname => 'tian@tiandb', RenderOutput => 1, output => '-' } );

   print "\n\ntest dump_conn_csv\n\n";

   my $homedir   = ( getpwuid($<) )[7];
   my $hiddendir = "$homedir/.tpsup";
   my $connfile  = "$hiddendir/conn.csv";
   dump_conn_csv($connfile);
}

main() unless caller();

1
