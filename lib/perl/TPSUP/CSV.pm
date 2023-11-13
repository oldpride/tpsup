package TPSUP::CSV;
use strict;

use base qw( Exporter );
our @EXPORT_OK = qw(
  parse_wrapped_csv_line
  open_csv
  close_csv
  parse_csv_array
  parse_csv_string
  parse_csv_file
  parse_csv_cmd
  run_sqlcsv
  update_csv
  delete_csv
  update_csv_inplace
  delete_csv_inplace
  diff_csv
  diff_csv_long
  render_csv
  find_safe_delimiter
  filter_csv_array
  query_csv2
  print_csv_hashArray
  csv_file_to_array
  join_csv
  cat_csv
  join_query_csv
  csv_to_html
);

use Carp;

use Data::Dumper;
use TPSUP::TMP qw(
  get_tmp_file
);

use TPSUP::UTIL qw(
  cp_file2_to_file1
  backup_filel_to_file2
  get_exps_from_string
  unique_array
  compile_paired_strings
  compile_perl_array
  transpose_arrays
  top_array
);

use TPSUP::FILE qw(get_out_fh);

use TPSUP::Expression;

sub parse_wrapped_csv_line {
   my ( $line, $opt ) = @_;

   chomp $line;

   $line =~ s/^"//;
   $line =~ s/"$//;
   $line =~ s/
$//;

   my @a = split /","/, $line;

   return \@a;
}

sub open_csv {
   my ( $csv, $opt ) = @_;

   croak "missing csv settings" if !defined $csv;

   my $fh;

   if ( $csv eq "-" ) {
      $fh = \*STDIN;
   } else {
      if ( !-f $csv ) {
         carp "cannot find $csv";
         return undef;
      }

      if ( $csv =~ /gz$/ ) {
         my $cmd = "gunzip -c $csv";
         open $fh, "$cmd |" or croak "cmd=$cmd failed, rc=$?, $!";
      } else {
         open $fh, "<$csv" or croak "failed to read $csv, rc=$?, $!";
      }
   }

   my $result;
   if ( $opt->{skiplines} ) {
      for ( my $i = 0 ; $i < $opt->{skiplines} ; $i++ ) {
         my $line = <$fh>;
         if ( $opt->{SaveSkippedLines} ) {
            push @{ $result->{SkippedLines} }, $line;
         }
      }
   }

   if ( $opt->{SetInputHeader} ) {
      my @columns = split /,/, $opt->{SetInputHeader};
      my $pos;

      my $i = 0;
      for my $c (@columns) {
         $pos->{$c} = $i;
         $i++;
      }

      $result->{columns} = \@columns;
      $result->{pos}     = $pos;
   }

   if ( $opt->{InputNoHeader} ) {
      if ( $opt->{requiredColumns} ) {
         croak "requiredColumns and InputNoHeader are incompatible";
      }

      $result->{fh} = $fh;
      return $result;
   }

   # we have a header line
   my $header = <$fh>;

   if ( !$opt->{SetInputHeader} ) {

      # use the original header
      chomp $header;

      $header =~ s/
//;

      my @columns;
      my $pos;

      if ( !defined $header ) {
         carp "csv $csv is empty";
         return undef;
      }

      my $delimiter = defined $opt->{delimiter} ? $opt->{delimiter} : ',';
      if ( $delimiter eq '|' || $delimiter eq '^' ) {
         $delimiter = "\\$delimiter";
      }

      my $columns;
      if ( $opt->{QuotedInput} ) {
         $columns = parse_quoted_line( $header, $delimiter, $opt );
      } else {
         @$columns = split /$delimiter/, $header;
      }

      my $i = 0;

      for my $c (@$columns) {
         $pos->{$c} = $i;
         $i++;
      }

      if ( $opt->{requiredColumns} ) {
         my $type = ref $opt->{requiredColumns};

         my $requiredColumns;
         if ( $type eq 'ARRAY' ) {
            $requiredColumns = $opt->{requiredColumns};
         } else {
            @$requiredColumns = split /,/, $opt->{requiredColumns};
         }

         for my $c (@$requiredColumns) {
            if ( !defined $pos->{$c} ) {
               carp "cannot find column '$c' in csv $csv header: $header";
               return undef;
            }
         }
      }
      $result->{columns} = $columns;
      $result->{pos}     = $pos;
   }

   $result->{fh} = $fh;
   return $result;
}

sub close_csv {
   my ($ref) = @_;
   close $ref->{fh};
}

sub parse_csv_string {
   my ( $string, $opt ) = @_;

   my @a = split /\n/, $string;

   return parse_csv_array( \@a, $opt );
}

sub parse_csv_file {
   my ( $file, $opt ) = @_;

   my $cmd;

   if ( $file =~ /gz$/ ) {
      $cmd = "gunzip -c $file";
   } else {
      $cmd = "cat $file";
   }

   my @a = `$cmd`;

   return parse_csv_array( \@a, $opt );
}

sub parse_csv_cmd {
   my ( $cmd, $opt ) = @_;

   my @a = "$cmd";

   if ($?) {
      carp "cmd=$cmd failed: $!";
      return undef if $opt->{returnUndefIfFail};
      exit 1       if !$opt->{ignoreExitCode};
   }

   return parse_csv_array( \@a, $opt );
}

sub parse_csv_array {
   my ( $in_ref, $opt ) = @_;

   return undef if !$in_ref;

   if ( ref($in_ref) ne 'ARRAY' ) {
      croak "parse_csv_array takes ref to array as input, in_ref=",
        Dumper($in_ref);
   }

   return undef if !@$in_ref;

   my $header = shift @$in_ref;

   chomp $header;

   $header =~ s/
//;

   my $delimiter = $opt->{delimiter} ? $opt->{delimiter} : ',';
   if ( $delimiter eq '|' || $delimiter eq '^' ) {
      $delimiter = "\\$delimiter";
   }

   my $h1;
   if ( $opt->{QuotedInput} ) {
      $h1 = parse_quoted_line( $header, $delimiter, $opt );
   } else {
      @$h1 = split /$delimiter/, $header;
   }

   if ( $opt->{OriginalHeaderRef} ) {
      ${ $opt->{OriginalHeaderRef} } = $h1;

   # this is hack to return the original header:
   #
   # examp1e:
   #    my $headers
   #    my $cmd = "sql.linux ...";
   #    my $array_of_hash = parse_csv_cmd($cmd, {OriginalHeaderRef=>\$headers});
   }

   my @h2;

   if ( $opt->{UsePosition} || $opt->{InputNoHeader} ) {

      # hardcoded column names c0, c1, c2, ...
      my $i = 0;

      for my $e (@$h1) {
         push @h2, "c$i";
         $i++;
      }
   } else {
      @h2 = @$h1;
   }

   if ( $opt->{InputNoHeader} ) {
      push @$in_ref, $header;
   }

   my $pos_by_col;
   my @renamed_headers;
   {
      for ( my $i = 0 ; $i < scalar(@h2) ; $i++ ) {
         my $col = $h2[$i];

         my $renamed_col;

         if ( defined $opt->{RenameCol}->{$col} ) {
            $renamed_col = $opt->{RenameCol}->{$col};
         } else {
            $renamed_col = $col;
         }

         push @renamed_headers, $renamed_col;
         $pos_by_col->{$renamed_col} = $i;
      }
   }

   if ( $opt->{requiredColumns} ) {
      for my $c ( @{ $opt->{requiredColumns} } ) {
         if ( !defined $pos_by_col->{$c} ) {
            carp "cannot find column '$c' in header: $header";
            return undef;
         }
      }
   }

   my $keyColumn = $opt->{keyColumn};
   my @keyColumns;

   if ( defined $keyColumn ) {
      @keyColumns = split /$delimiter/, $keyColumn;

      for my $c (@keyColumns) {
         if ( !defined $pos_by_col->{$c} ) {
            carp "cannot find column '$c' in header: $header";
            return undef;
         }
      }
   }

   my $out_ref;

   for my $l (@$in_ref) {
      next if $opt->{excludePattern} && $l =~ /$opt->{excludePattern}/;

      chomp $l;
      $l =~ s/
//g;

      my $a;
      if ( $opt->{QuotedInput} ) {
         $a = parse_quoted_line( $l, $delimiter, $opt );
      } else {
         @$a = split /$delimiter/, $l;
      }

      my $v_by_k;

      for ( my $i = 0 ; $i < scalar(@renamed_headers) ; $i++ ) {
         $v_by_k->{ $renamed_headers[$i] } = $a->[$i];
      }

      if ( defined $keyColumn ) {

         #my $key = defined $v_by_k->{$keyColumn} ? $v_by_k->{$keyColumn} : '';
         no warnings "uninitialized";
         my $key = join( ",", @{$v_by_k}{@keyColumns} );

         push @{ $out_ref->{$key} }, $v_by_k;
      } else {
         push @$out_ref, $v_by_k;
      }
   }

   return $out_ref;
}

sub run_sqlcsv ($$;$) {
   my ( $sql, $inputs, $opt ) = @_;

   my $separator = defined( $opt->{separator} ) ? $opt->{separator} : ',';

   my @out_array;

   my $tmpdir = get_tmp_file( "/var/tmp", "sqlcsv",
      { isDir => 1, chkSpace => 102400000 } );

   if ( !$tmpdir ) {
      carp "failed to get tmp dir";
      return \@out_array;
   }

   require DBI;

   my $dbh = DBI->connect(
      "DBI:CSV:f_dir=$tmpdir;csv_eol=\n;csv_sep_char=\\$separator;");

   if ( ref($inputs) ne 'ARRAY' ) {
      croak "run_sql_csv() 2nd arg needs to be ref to array";
   }

   my $pwd = `pwd`;
   chomp $pwd;

   my $i = 1;

   for my $input (@$inputs) {
      my $table_name = "CSV$i";

      $i++;

      my $tmpfile = "$tmpdir/$table_name";

      my $csv;

      if ( $input eq '-' ) {
         croak "non-select sql cannot work on standard input"
           if $sql !~ /^\s*select/i;

         open my $tmp_fh, ">$tmpfile" or die "cannot write to $tmpfile";

         my $skipped_row = 0;

         while (<STDIN>) {
            if ( $opt->{skiplines} ) {
               if ( $skipped_row < $opt->{skiplines} ) {
                  $skipped_row++;
                  next;
               }
            }

            print {$tmp_fh} $_;
         }

         close $tmp_fh;

         $csv = $tmpfile;
      } elsif ( $input =~ /gz$/ ) {
         croak "non-select sql cannot work on gz file"
           if ( $sql !~ /^\s*select/i || $sql =~ /update|delete/i );

         my $cmd;
         if ( $opt->{skiplines} ) {
            $cmd = "gunzip -c $input |sed 1,$opt->{skiplines}d > $tmpfile";
         } else {
            $cmd = "gunzip -c $input > $tmpfile";
         }

         system($cmd);

         if ($?) {
            carp "ERROR: cmd=$cmd failed, $!";
            return \@out_array;
         }

         $csv = $tmpfile;
      } else {
         if ( !-f $input ) {
            carp "ERROR: cannot find $input";
            return \@out_array;
         }

         if ( $opt->{skiplines} ) {
            system("sed 1,$opt->{skiplines}d $input> $tmpfile");
         } else {
            if ( $input =~ m|^/| ) {
               system("ln -s      $input $tmpfile");
            } else {
               system("ln -s $pwd/$input $tmpfile");
            }
         }
      }

      $dbh->{'csv_tables'}->{$table_name} = { 'file' => $table_name };
   }

   $opt->{verbose} && system("ls -l $tmpdir");

   my $sth = $dbh->prepare($sql);

   $sth->execute();

   if ( $sql =~ /select/i ) {
      push @out_array, $sth->{NAME} if $opt->{withHeader};

      while ( my @array = $sth->fetchrow_array ) {
         push @out_array, \@array;
      }
   }

   $dbh->disconnect;

   system("/bin/rm -fr $tmpdir") if -d $tmpdir;

   return \@out_array;
}

sub parse_set_clause {
   my ( $clause, $opt ) = @_;

   # Type=ETF Source=1 Desc="not done" 'Delta Risk'=l

   # trim t
   $clause =~ s/^\s+//;
   $clause =~ s/\s+$//;

   my $position = 0;
   my $len      = length($clause);

   my $buffer = $clause;

   my $last_match;
   my $v_by_k;

   while ($buffer) {
      $opt->{verbose} && print "buffer=$buffer\n";

      my $key;
      my $value;

      if ( $buffer =~ /^'(.+?)'=/ ) {
         $key = $1;
         $buffer =~ s/^'$key'=//;
      } elsif ( $buffer =~ /"(.+?)"=/ ) {
         $key = $1;
         $buffer =~ s/^"$key"=//;
      } elsif ( $buffer =~ /^(\S+?)=/ ) {
         $key = $1;
         $buffer =~ s/^${key}=//;
      } else {
         croak "clause='$clause' has bad format at $last_match";
      }

      $opt->{verbose} && print "buffer=$buffer, after key=$key\n";

      if ( $buffer =~ /^'(.*?)'/ ) {
         $value = $1;
         $value = '' if !defined $value;
         $buffer =~ s/^'${value}'//;
      } elsif ( $buffer =~ /^"(.*?)"/ ) {
         $value = $1;
         $value = '' if !defined $value;
         $buffer =~ s/^"${value}"//;
      } elsif ( $buffer =~ /(\S+)/g ) {
         $value = $1;
         $buffer =~ s/^${value}//;
      } else {
         croak "clause='$clause' has bad format at key='$key'";
      }

      $buffer =~ s/^\s+//;
      $v_by_k->{$key} = $value;

      $last_match = "'$key'='$value'";

      $opt->{verbose}
        && print "buffer=$buffer, after key=$key, last_match $last_match\n";
   }

   return $v_by_k;
}

sub update_csv {
   my ( $file, $set, $opt ) = @_;

   my $ref = open_csv( $file, $opt );

   exit 1 if !$ref;

   my ( $ifh, $columns, $pos, $SkippedLines ) =
     @{$ref}{qw(fh columns pos SkippedLines)};

   my $v_by_k = parse_set_clause( $set, $opt );

   for my $k ( keys %$v_by_k ) {
      croak "column name='$k' doesn't exist in $file" if !exists $pos->{$k};
   }

   $opt->{verbose} && print "set_clause='$set', resolved to v_by_k =",
     Dumper($v_by_k);

   my $delimiter = $opt->{delimiter} ? $opt->{delimiter} : ',';
   if ( $delimiter eq '|' || $delimiter eq '^' ) {
      $delimiter = "\\$delimiter";
   }

   my $warn = $opt->{verbose} ? 'use' : 'no';

   my $matchExps;
   if ( $opt->{MatchExps} && @{ $opt->{MatchExps} } ) {
      @$matchExps = map {
         my $compiled = eval
           "$warn warnings; no strict; package TPSUP::Expression; sub { $_ } ";
         $@ ? ( die "Bad match expression '$_' : $@" ) : $compiled;
      } @{ $opt->{MatchExps} };
   }

   my $excludeExps;
   if ( $opt->{ExcludeExps} && @{ $opt->{ExcludeExps} } ) {
      @$excludeExps = map {
         my $compiled = eval
           "$warn warnings; no strict; package TPSUP::Expression; sub { $_ } ";
         $@ ? ( die "Bad match expression '$_' : $@" ) : $compiled;
      } @{ $opt->{ExcludeExps} };
   }

   my $out_fh;

   if ( $opt->{output} ) {
      $out_fh = get_out_fh( $opt->{output} );
   } else {
      $out_fh = \*STDOUT;
   }

   if ($SkippedLines) {
      for my $line (@$SkippedLines) {
         print {$out_fh} $line;
      }
   }

   print {$out_fh} join( ",", @$columns ), "\n" if $columns;

   while (<$ifh>) {
      my $line = $_;

      chomp $line;

      if ( $opt->{ExcludePatterns} && @{ $opt->{ExcludePatterns} } ) {
         my $should_exclude = 1;

         for my $p ( @{ $opt->{ExcludePatterns} } ) {
            if ( $line !~ /$p/ ) {

               # remember this is AND logic; therefore, one fails means all fail
               $should_exclude = 0;
               last;
            }
         }

         if ($should_exclude) {
            print {$out_fh} $line, "\n";
            next;
         }
      }

      my $a;
      if ( $opt->{QuotedInput} ) {
         $a = parse_quoted_line( $line, $delimiter, $opt );
      } else {
         @$a = split /$delimiter/, $line;
      }

      my $r;

      if ($columns) {
         for my $c (@$columns) {
            my $p = $pos->{$c};
            $r->{$c} = $a->[$p];
         }
      }

      if ( $opt->{UsePosition} || $opt->{InputNoHeader} ) {

         # hardcoded column names c0, c1, c2, ...
         my $i = 0;

         for my $e (@$a) {
            my $c = "c$i";
            $r->{$c} = $e;
            $i++;
         }
      }

      if ( $matchExps || $excludeExps ) {
         TPSUP::Expression::export(%$r);
         my $exclude_from_doing;

         if ($excludeExps) {
            for my $e (@$excludeExps) {
               if ( $e->() ) {
                  $exclude_from_doing++;
                  last;
               }
            }
         }

         if ($exclude_from_doing) {
            print {$out_fh} "$line\n";
            next;
         }

         {
            for my $e (@$matchExps) {
               if ( !$e->() ) {
                  $exclude_from_doing++;
                  last;
               }
            }
         }

         if ($exclude_from_doing) {
            print {$out_fh} "$line\n";
            next;
         }
      }

      for my $k ( keys %$v_by_k ) {
         $r->{$k} = $v_by_k->{$k};
      }

      $opt->{verbose} && print "r = ", Dumper($r);

      no warnings "uninitialized";

      print {$out_fh} join( ",", @{$r}{@$columns} ), "\n";
   }

   close $out_fh if $out_fh != \*STDOUT;
}

sub parse_quoted_line {
   my ( $line, $delimiter, $opt ) = @_;

# take the hassle to parse double-quoted csv. (single quote cannot group in csv)
#
# COLLOQ_TY P E,COLLOQ_NAME,COLLOQ_COD E,XDATA
# S,"BELT,FAN",003541547,
# S,"BELT V,FAN",000324244,
# S,SHROUD SPRING SCREW,000868265,
# S,"D" REL VALVE ASSY,000771881,
# S,"YBELT,"V"",000323030,
# S,"YBELT,'V'",000322933,

   my $len = length($line);
   pos($line) = 0;    # reset

   $opt->{verbose} && print "\nline='$line', len=$len\n";

   my @a;

   while ( pos($line) < $len ) {
      my $cell;

      if ( $line =~ /\G"/gc ) {

         # this is a quoted cell
         # 'c' is to keep the current position during repeated matching
         # 'g' is to globally match the pattern repeatedly in the string

         $opt->{verbose} && print "starting a quoted cell, pos=", pos($line),
           "\n";

         if ( $line =~ /\G(.*?)"$delimiter/gc ) {
            if ( $opt->{RemoveInputQuotes} ) {
               $cell = $1;
            } else {
               $cell = qq("$1");
            }
            push @a, $cell;
         } else {
            $line =~ /\G(.*)/gc;    # all the rest of line
            $cell = $1;
            $cell =~ s/"$//;        # Remove the ending quites

            if ( $opt->{RemoveInputQuotes} ) {
               push @a, $cell;
            } else {
               $cell = qq("$1");
            }

            last;
         }
      } else {

         # this is not a quoted cell
         $opt->{verbose} && print "starting a non-quoted cell, pos=",
           pos($line), "\n";

         if ( $line =~ /\G(.*?)$delimiter/gc ) {
            $cell = $1;
            push @a, $cell;
         } else {
            $line =~ /\G(.*)/gc;    # all the rest of line
            $cell = $1;
            push @a, $cell;
            last;
         }
      }

      $opt->{verbose} && print "cell='$cell', clen=", length($cell), ", pos=",
        pos($line), "\n";
   }

   return \@a;
}

sub csv_file_to_array {
   my ( $file, $opt ) = @_;

   my $ref = open_csv( $file, $opt );

   if ( !$ref ) {
      return undef;
   }

   my ( $ifh, $columns, $pos ) = @{$ref}{qw(fh columns pos)};

   if ( $opt->{verbose} ) {
      print STDERR "columns = ", Dumper($columns);
      print STDERR "pos = ",     Dumper($pos);
   }

   my $delimiter = $opt->{delimiter} ? $opt->{delimiter} : ',';
   if ( $delimiter eq '|' || $delimiter eq '^' ) {
      $delimiter = "\\$delimiter";
   }

   my $rtn;

   my $column_count = 0;

   # pre-compile static patterns to speed up
   my @exclude_qrs;

   my $has_exclude_pattern;

   if ( $opt->{ExcludePatterns} && @{ $opt->{ExcludePatterns} } ) {
      for my $p ( @{ $opt->{ExcludePatterns} } ) {
         push @exclude_qrs, qr/$p/;
         $has_exclude_pattern = 1;
      }
   }

   my @match_qrs;
   my $has_match_pattern;

   if ( $opt->{MatchPatterns} ) {
      for my $p ( @{ $opt->{MatchPatterns} } ) {
         push @match_qrs, qr/$p/;
         $has_match_pattern = 1;
      }
   }

 LINE:
   while (<$ifh>) {
      my $line = $_;
      chomp $line;

      if ($has_exclude_pattern) {

         # remember this is AND logic; therefore, one fails means all fail
         my $should_exclude = 1;

         for my $qr (@exclude_qrs) {
            if ( $line !~ /$qr/ ) {
               $should_exclude = 0;
               last;
            }
         }

         next if $should_exclude;
      }

      if ($has_match_pattern) {
         for my $qr (@match_qrs) {
            if ( $line !~ /$qr/ ) {

              # remember this is AND logic; therefore, one fails means all fail.
               next LINE;
            }
         }
      }

      $line =~ s/
//g;    #remove DOS return

      my $a;

      if ( $opt->{QuotedInput} ) {

# take the hassle to parse double-quoted csv. (single quote cannot group in csv)
#
# COLLOQ_TY P E,COLLOQ_NAME,COLLOQ_COD E,XDATA
# S,"BELT,FAN",003541547,
# S,"BELT V,FAN",000324244,
# S,SHROUD SPRING SCREW,000868265,
# S,"D" REL VALVE ASSY,000771881,
# S,"YBELT,"V"",000323030,
# S,"YBELT,'V'",000322933,

         $a = parse_quoted_line( $line, $delimiter, $opt );
      } else {
         @$a = split /$delimiter/, $line;
      }

      if ( $opt->{FileReturnStructuredArray} ) {
         push @{ $rtn->{array} }, $a;
      } else {

         # default to return StructuredHash
         my $r;

         if ($columns) {
            for my $c (@$columns) {
               my $p = $pos->{$c};

               $r->{$c} = $a->[$p];
            }
         }

         if ( $opt->{UsePosition} || $opt->{InputNoHeader} ) {

            # hardcoded column names c0, c1, c2, ...
            my $i = 0;
            for my $e (@$a) {
               my $c = "c$i";
               $r->{$c} = $e;
               $i++;
            }

            $column_count = scalar(@$a) if $column_count < scalar(@$a);
         }

         push @{ $rtn->{array} }, $r;
      }

      #push @{$rtn->{lines}}, $line;
   }

   if ($columns) {
      $rtn->{columns} = $columns;
   } elsif ( $opt->{UsePosition} || $opt->{InputNoHeader} ) {
      for ( my $i = 0 ; $i < $column_count ; $i++ ) {
         push @{ $rtn->{columns} }, "c$i";
      }
   }

   $rtn->{status} = 'OK';

   return $rtn;
}

my $loaded_by_NameSpace_UseCodes;

sub query_csv2 {
   my ( $input, $opt ) = @_;

   my $ref1;

   #  TODO: remove this later
   croak "please change InputHashArray to \$opt->{InputType} = 'HashArray'"
     if $opt->{InputHashArray};
   croak "please change InputArrayArray to \$opt->{InputType} = 'ArrayArray'"
     if $opt->{InputArrayArray};
   croak
"please change InputStructuredHash to \$opt->{InputType} = 'StructuredHash'"
     if $opt->{InputStructuredHash};

   if ( !$opt->{InputType} || $opt->{InputType} eq 'CSV' ) {

      # input is default to a csv file

      # this applies line-based match: ExcludePatterns, MatchPatterns
      $ref1 = csv_file_to_array( $input, $opt );

      if ( $ref1->{status} ne 'OK' ) {
         carp "csv_file_to_array($input) failed: $ref1->{status}";
         return undef;
      }
   } elsif ( $opt->{InputType} eq 'HashArray' ) {

      # input is an array of hash
      if ( !$opt->{InputHashColumns} ) {
         croak
"calling query_csv2($input) with InputType=HashArray must also set InputHashColumns";
      }

      $ref1->{array}   = $input;
      $ref1->{columns} = $opt->{InputHashColumns};
   } elsif ( $opt->{InputType} eq 'ArrayArray' ) {

      # input is an array of array, with the first row to be headers
      my @columns = @{ $input->[0] };

      my $col_count = scalar(@columns);
      my $row_count = scalar(@$input);

      for ( my $i = 1 ; $i < $row_count ; $i++ ) {
         my $r;

         for ( my $j = 0 ; $j < $col_count ; $j++ ) {
            my $k = $columns[$j];
            my $v = $input->[$i]->[$j];

            $r->{$k} = $v;
         }

         push @{ $ref1->{array} }, $r;
      }

      $ref1->{columns} = \@columns;
   } elsif ( $opt->{InputType} eq 'StructuredHash' ) {

      # already in the same structure, our ideal structure
      $ref1->{columns} = $input->{columns};
      $ref1->{array}   = $input->{array};
   } else {
      croak "unsupported InputType=$opt->{InputType}";
   }

#trim floating point numbers, 2.03000 => 2.03. $opt->{TrimFloats} contains column names
   if ( $opt->{TrimFloats} ) {
      my @Floats = @{ $opt->{TrimFloats} };
      my $need_trim;

      for my $r ( @{ $ref1->{array} } ) {
         for my $k (@Floats) {
            if ( defined $r->{$k} ) {
               $r->{$k} =~ s/0+$// if $r->{$k} =~ /\./;
               $r->{$k} =~ s/\.$//;
            }
         }
      }
   }

   $opt->{verbose} && print STDERR "query_csv2($input) ref1 = ", Dumper($ref1);

   # this applies field-based match: ExcludeExps, MatchExps
   # this also adds new columns using TempExps, ExportExps
   # also DeleteColumns
   my $ref2 = filter_csv_array( $ref1, $opt );

   if ( $ref2->{status} ne 'OK' ) {
      carp "filter_csv_array failed: $ref2->{status}";
      return undef;
   }

   $opt->{verbose} && print STDERR "query_csv2($input) ref2 = ", Dumper($ref2);

   my $ref3;

   # handle Grouping actions
   if ( $opt->{GroupKeys} ) {
      my $tmpref;
      my $is_GroupKey;

      my @keys = @{ $opt->{GroupKeys} };

      for my $c (@keys) {
         $is_GroupKey->{$c} = 1;
      }

      for my $r ( @{ $ref2->{array} } ) {
         no warnings "uninitialized";
         my $k = join( ",", @{$r}{@keys} );
         push @{ $tmpref->{$k} }, $r;
      }

      if ( $opt->{InGroupSortKeys} ) {
         my $type = ref $opt->{InGroupSortKeys};

         my @keys2;

         if ( !$type ) {
            @keys2 = split /,/, $opt->{InGroupSortKeys};
         } elsif ( $type eq 'ARRAY' ) {
            @keys2 = @{ $opt->{InGroupSortKeys} };
         } else {
            croak "unsupported type='$type' of InGroupSortKeys. opt = "
              . Dumper($opt);
         }

         for my $k ( sort ( keys %$tmpref ) ) {
            my $tmpref2;

            for my $r ( @{ $tmpref->{$k} } ) {

               # for each row within a group

               no warnings "uninitialized";
               my $k2 = join( ",", @{$r}{@keys2} );
               push @{ $tmpref2->{$k2} }, $r;
            }

            my @tmpkeys1 =
              $opt->{InGroupSortNumeric}
              ? sort { $a <=> $b } keys(%$tmpref2)
              : sort { $a cmp $b } keys(%$tmpref2);

            my @tmpkeys2 =
              $opt->{InGroupSortDescend} ? reverse(@tmpkeys1) : @tmpkeys1;

            if ( $opt->{InGroupGetFirst} ) {
               push @{ $ref3->{array} }, $tmpref2->{ $tmpkeys2[0] }->[0];
            } elsif ( $opt->{InGroupGetLast} ) {
               push @{ $ref3->{array} }, $tmpref2->{ $tmpkeys2[-1] }->[-1];
            } else {
               croak "InGroupSortKeys set but no InGroup action set";
            }
         }
      } elsif ( $opt->{GroupAction} || $opt->{GroupActExp} ) {
         my $Action_by_column;

         if ( $opt->{GroupAction} ) {
            for my $c ( keys %{ $opt->{GroupAction} } ) {
               croak
"$c is a GroupKey; we cannot act ($opt->{GroupAction}->{$c}) on it"
                 if $is_GroupKey->{$c};
            }

            $Action_by_column = $opt->{GroupAction};
         }

         my $ActExp_by_column;
         if ( $opt->{GroupActExp} ) {
            for my $c ( keys %{ $opt->{GroupActExp} } ) {
               my $exp = $opt->{GroupActExp}->{$c};

               croak "$c is a GroupKey; we cannot apply ($exp) on it"
                 if $is_GroupKey->{$c};

               # in my (\$c, \$ah):
               # \$c will be the column name,
               # \$ah will be ref to that group of array of hashes
               my $compiled =
                 eval "no strict; sub { my (\$c, \$ah) = \@_; $exp }";

               croak "bad GroupActExp at $c='$exp': $@" if $@;

               $ActExp_by_column->{$c} = $compiled;
            }
         }

         for my $k ( sort ( keys %$tmpref ) ) {
            my $r;

            # begin - within a group, one column a time
            for my $c ( @{ $ref2->{columns} } ) {
               if ( $is_GroupKey->{$c} ) {
                  $r->{$c} = $tmpref->{$k}->[0]->{$c};
                  next;
               }

               if ( $Action_by_column->{$c} ) {
                  my @values;

                  for my $r2 ( @{ $tmpref->{$k} } ) {
                     push @values, $r2->{$c};
                  }

                  $r->{$c} = handle_action( $Action_by_column->{$c}, \@values );
               } elsif ( $ActExp_by_column->{$c} ) {
                  $r->{$c} = $ActExp_by_column->{$c}->( $c, $tmpref->{$k} );
               } else {
                  $r->{$c} = undef;
               }
            }

            # end - within a group, one column a time

            push @{ $ref3->{array} }, $r;
         }
      }

      $ref3->{columns} = $ref2->{columns};
   } else {
      $ref3->{array}   = $ref2->{array};
      $ref3->{columns} = $ref2->{columns};
   }

   $opt->{verbose} && print STDERR "query_csv2($input) ref3 = ", Dumper($ref3);

   # handle summary
   if ( $opt->{SummaryAction} || $opt->{SummaryExp} ) {
      my $action_by_column = $opt->{SummaryAction};

      my $exp_by_column;

      if ( $opt->{SummaryExp} ) {
         for my $c ( keys %{ $opt->{SummaryExp} } ) {
            my $exp = $opt->{SummaryExp}->{$c};

            # in my (\$c, \$ah):
            # \$c will be the column name,
            # \$ah will be ref to array of hashes
            my $compiled = eval "no strict; sub { my (\$c, \$ah) = \@_; $exp }";

            croak "bad SummaryExp at $c='$exp': $@" if $@;

            $exp_by_column->{$c} = $compiled;
         }
      }

      my $r;

      # begin - one column a time
      for my $c ( @{ $ref3->{columns} } ) {
         if ( $action_by_column->{$c} ) {
            my @values;

            for my $r2 ( @{ $ref3->{array} } ) {
               push @values, $r2->{$c};
            }

            $r->{$c} = handle_action( $action_by_column->{$c}, \@values );
         } elsif ( $exp_by_column->{$c} ) {
            $r->{$c} = $exp_by_column->{$c}->( $c, $ref3->{array} );
         } else {
            $r->{$c} = undef;
         }
      }

      # end - one column a time

      push @{ $ref3->{summary} }, $r;
   }

   $opt->{verbose} && print STDERR "after summary ref3 = ", Dumper($ref3);

   #my @SelectColumns;

   #if (defined $opt->{SelectColumns}) {
   # @SelectColumns = @{$opt->{SelectColumns}};
   #
   #my @exportCols;
   # if ($opt->{ExportExps} && @{$opt->{ExportExps}}) {
   #    for my $pair (@{$opt->{ExportExps}}) {
   #       if ($pair =~ /^(.+?)=(.+)/) {
   #          my ($c, $e) = ($1, $2);
   #          push @exportCols, $c;
   #       } else {
   #         croak "ExportExps has bad format at: $pair. Expecting key=exp";
   #       }
   #   }
   #}

   #my @fields;

   #if (@SelectColumns) {
   # @fields = (@SelectColumns, @exportCols);
   #} else {
   # @fields = (@{$ref3->{columns}}, @exportCols);
   #}

   # handle print
   if ( !$opt->{NoPrint} ) {

      # default to PrintData but not PrintSummary
      my $PrintData = defined( $opt->{PrintData} ) ? $opt->{PrintData} : 1;

      if ($PrintData) {

         #print_csv_hashArray($ref3->{array}, \@fields, $opt);
         print_csv_hashArray( $ref3->{array}, $ref3->{columns}, $opt );
      }

      if ( $opt->{PrintSummary} && $ref3->{summary} ) {
         if ($PrintData) {

            # we already printed header
            #print_csv_hashArray($ref3->{summary}, \@fields, { %$opt,
            print_csv_hashArray(
               $ref3->{summary},
               $ref3->{columns},
               {
                  %$opt,
                  OutputNoHeader => 1,
                  AppendOutput   => 1,
               }
            );
         } else {

            #print_csv_hashArray($ref3->{summary}, \@fields, $opt);
            print_csv_hashArray( $ref3->{summary}, $ref3->{columns}, $opt );
         }
      }
   }

   my $ref4;

   if ( !$opt->{ReturnType} || $opt->{ReturnType} eq 'StructuredHash' ) {

      # default to return StructuredHash;

      $ref4->{columns} = $ref3->{columns};

      my $tmp;
      if ( $opt->{SortKeys} ) {
         $tmp =
           sort_HashArray_by_keys( $ref3->{array}, $opt->{SortKeys}, $opt );
      } else {
         $tmp = $ref3->{array};
      }

      $ref4->{array} = top_array( $tmp, $opt->{PrintCsvMaxRows} );
   } elsif ( $opt->{ReturnType} =~ /^ExpKeyedHash=(.+)/ ) {
      my $ExpKey = $1;

      my $warn     = $opt->{verbose} ? 'use' : 'no';
      my $compiled = eval
"$warn warnings; no strict; package TPSUP::Expression; sub { return $opt->{ExpKey}; }";

      my $KeyedHash;

      for my $r ( @{ $ref3->{array} } ) {
         TPSUP::Expression::export_var( $r,
            { FIX => $opt->{FIX}, RESET => 1 } );

         #no warnings "uninitialized";
         my $k = $compiled->();

         push @{ $KeyedHash->{$k} }, $r;
      }
      $ref4->{KeyedHash} = $KeyedHash;
      $ref4->{columns}   = $ref3->{columns};
   } elsif ( $opt->{ReturnType} =~ /^StringKeyedHash=(.+)/ ) {

      # StringKeyedHash=name,email
      my $key_string = $1;

      my @keys = split /,/, $key_string;

      my $KeyedHash;

      for my $r ( @{ $ref3->{array} } ) {
         no warnings "uninitialized";
         my $k = join( ",", @{$r}{@keys} );
         push @{ $KeyedHash->{$k} }, $r;
      }

      $ref4->{KeyedHash} = $KeyedHash;
      $ref4->{columns}   = $ref3->{columns};

   } elsif ( $opt->{ReturnType} =~ /^RefKeyedHash/ ) {
      my @keys = @{ $opt->{ReturnRefKey} };

      my $KeyedHash;

      for my $r ( @{ $ref3->{array} } ) {
         no warnings "uninitialized";
         my $k = join( ",", @{$r}{@keys} );
         push @{ $KeyedHash->{$k} }, $r;
      }

      $ref4->{KeyedHash} = $KeyedHash;
      $ref4->{columns}   = $ref3->{columns};

   } elsif ( $opt->{ReturnType} eq 'StructuredArray' ) {

      # $ref3->{array} is      an array of hashes
      # $ref4->{array} will be an array of arrays

      $ref4->{columns} = $ref3->{columns};
      push @{ $ref4->{array} }, $ref3->{columns};

      my $tmpArrayHash;

      if ( $opt->{SortKeys} ) {
         $tmpArrayHash =
           sort_HashArray_by_keys( $ref3->{array}, $opt->{SortKeys}, $opt );
      } else {
         $tmpArrayHash = $ref3->{array};
      }

      my $top_part = top_array( $$tmpArrayHash, $opt->{PrintCsvMaxRows} );

      # convert array of hashes to array of arrays
      for my $r (@$top_part) {
         my @a = @{$r}{ @{ $ref4->{columns} } };
         push @{ $ref4->{array} }, \@a;
      }
   } else {
      croak "unsupported ReturnType=$opt->{ReturnType}";
   }

   $ref4->{status} = 'OK';

   return $ref4;
}

sub handle_action {
   my ( $action, $raw_array, $opt ) = @_;

   return undef if !$raw_array || !@$raw_array;

   my $placeholder;

   my $sort_numeric;

   if ( $action =~ /^(minnstr|maxstr|medianstr)$/ ) {
      $placeholder = $opt->{PlaceHolder}->{String};
   } elsif ( $action =~ /^(minnum|maxnum|mediannum)$/ ) {
      $sort_numeric++;
      $placeholder = $opt->{PlaceHolder}->{Number};
   }

   my @array;

   for my $e (@$raw_array) {
      if ( !defined($e) ) {
         push @array, $placeholder if defined $placeholder;
      } else {
         push @array, $e;
      }
   }

   return undef if !@array;

   if ( $action eq "count" )    { return scalar(@array); }
   if ( $action eq "first" )    { return $array[0]; }
   if ( $action eq "last" )     { return $array[-1]; }
   if ( $action =~ /set=(.*)/ ) { return $1; }
   if ( $action eq "list" )     { return join( " ", @array ); }
   if ( $action eq "unique" ) {
      my $unique_aref = unique_array( [ \@array ] );
      return join( " ", @$unique_aref );
   }

   if ( $action eq 'sum' ) {
      my $sum;
      for my $e (@array) {
         $sum += $e;
      }
      return $sum;
   }

   if ( $action eq 'avg' ) {
      my $sum = 0;

      for my $e (@array) {
         $sum += $e;
      }
      return $sum / scalar(@array);
   }

   my @a;
   if ($sort_numeric) {
      @a = sort { $a <=> $b } @array;
   } else {
      @a = sort { $a cmp $b } @array;
   }

   if ( $action eq 'mediannum' || $action eq 'medianstr' ) {
      return $a[ int( scalar(@a) / 2 ) ];
   }
   if ( $action eq 'maxnum' || $action eq 'maxstr' ) { return $a[-1]; }
   if ( $action eq 'minnum' || $action eq 'minstr' ) { return $a[0]; }

   croak "unknown action='$action'";
}

sub sort_HashArray_by_keys {
   my ( $HashArray, $keys, $opt ) = @_;

   my $type = ref $opt->{SortKeys};

   my @keys;

   if ( !$type ) {
      @keys = split /,/, $opt->{SortKeys};
   } elsif ( $type eq 'ARRAY' ) {
      @keys = @{ $opt->{SortKeys} };
   } else {
      croak "unsupported type='$type' of SortKeys. opt = " . Dumper($opt);
   }

   my $tmpref;

   for my $r ( @{$HashArray} ) {
      no warnings "uninitialized";
      my $k = join( ",", @{$r}{@keys} );
      push @{ $tmpref->{$k} }, $r;
   }

   my @tmp1 =
     $opt->{SortNumeric}
     ? sort { $a <=> $b } keys(%$tmpref)
     : sort { $a cmp $b } keys(%$tmpref);

   my @tmp2 = $opt->{SortDescend} ? reverse(@tmp1) : @tmp1;

   my $ret;

   for my $k (@tmp2) {
      push @{$ret}, @{ $tmpref->{$k} };
   }

   return $ret;
}

sub print_csv_hashArray {
   my ( $HashArray, $Fields2, $opt ) = @_;

   my $print_HashArray;

   if ( $opt->{SortKeys} ) {
      $print_HashArray =
        sort_HashArray_by_keys( $HashArray, $opt->{SortKeys}, $opt );
   } else {
      $print_HashArray = $HashArray;
   }

   my $type = ref $Fields2;

   my $fields;

   if ( !$type ) {
      @$fields = split /,/, $Fields2;
   } elsif ( $type eq 'ARRAY' ) {
      $fields = $Fields2;
   } else {
      croak "unsupported type='$type' of Fields2 = " . Dumper($Fields2);
   }

   my $tmpref;

   if ( $opt->{RenderStdout} ) {
      render_csv( $print_HashArray, $fields, $opt );
   } else {
      my $out_fh;

      if ( $opt->{output} ) {
         $out_fh = get_out_fh( $opt->{output}, $opt );
      } else {
         $out_fh = \*STDOUT;
      }

      my $delimiter = $opt->{delimiter} ? $opt->{delimiter} : ',';

      # this delimiter is for output, therefore, don't escape for | or ^
      #if ($delimiter eq '|' || $delimiter eq '^') {
      #   $delimiter = "\\$delimiter";
      #}

      if ( !$opt->{OutputNoHeader} ) {
         if ( $opt->{OutputHeader} ) {
            print {$out_fh} $opt->{OutputHeader}, "\n";
         } else {
            print {$out_fh} join( $delimiter, @$fields ), "\n";
         }
      }

      no warnings "uninitialized";

      my $count = 0;
      for my $r ( @{$print_HashArray} ) {
         last if $opt->{PrintCsvMaxRows} && $count >= $opt->{PrintCsvMaxRows};
         print {$out_fh} join( $delimiter, @{$r}{@$fields} ), "\n";
         $count++;
      }

      close $out_fh if $out_fh != \*STDOUT;
   }
}

sub update_csv_inplace {
   my ( $file, $set_clause, $opt ) = @_;

   my ( $package, $prog, $line ) = caller;

   $prog =~ s:.*/::;

   my $tmpfile1 = get_tmp_file( "/var/tmp", "${prog}", { AddIndex => 1 } );

   update_csv( $file, $set_clause, { output => $tmpfile1, %$opt } );

   return cp_file2_to_file1( $tmpfile1, $file, $opt );
}

sub delete_csv_inplace {
   my ( $file, $opt ) = @_;

   my ( $package, $prog, $line ) = caller;

   $prog =~ s:.*/::;

   my $tmpfile1 = get_tmp_file( "/var/tmp", "${prog}", { AddIndex => 1 } );

   delete_csv( $file, { output => $tmpfile1, %$opt } );

   return cp_file2_to_file1( $tmpfile1, $file, $opt );
}

sub delete_csv {
   my ( $file, $opt ) = @_;

   my $ref = open_csv( $file, $opt );

   exit 1 if !$ref;

   croak "missing MatchExps" if !$opt->{MatchExps} || !@{ $opt->{MatchExps} };

   my ( $ifh, $columns, $pos, $SkippedLines ) =
     @{$ref}{qw(fh columns pos SkippedLines)};

   my $delimiter = $opt->{delimiter} ? $opt->{delimiter} : ', ';
   if ( $delimiter eq '|' || $delimiter eq '^' ) {
      $delimiter = "\\$delimiter";
   }

   my $warn = $opt->{verbose} ? 'use' : 'no';

   my $matchExps;
   if ( $opt->{MatchExps} && @{ $opt->{MatchExps} } ) {
      @$matchExps = map {
         my $compiled = eval
           "$warn warnings; no strict; package TPSUP::Expression; sub { $_ } ";
         $@ ? ( die "Bad match expression '$_' : $@" ) : $compiled;
      } @{ $opt->{MatchExps} };
   }

   my $excludeExps;
   if ( $opt->{ExcludeExps} && @{ $opt->{ExcludeExps} } ) {
      @$excludeExps = map {
         my $compiled = eval
           "$warn warnings; no strict; package TPSUP::Expression; sub { $_ } ";
         $@ ? ( die "Bad match expression '$_' : $@" ) : $compiled;
      } @{ $opt->{ExcludeExps} };
   }

   my $exportExps;
   if ( $opt->{ExportExps} && @{ $opt->{ExportExps} } ) {
      @$exportExps = map {
         my $compiled = eval
           "$warn warnings; no strict; package TPSUP::Expression; sub { $_ } ";
         $@ ? ( die "Bad match expression '$_' : $@" ) : $compiled;
      } @{ $opt->{ExportExps} };
   }

   my $out_fh;

   if ( $opt->{output} ) {
      $out_fh = get_out_fh( $opt->{output} );
   } else {
      $out_fh = \*STDOUT;
   }

   if ($SkippedLines) {
      for my $line (@$SkippedLines) {
         print {$out_fh} $line;
      }
   }

   print {$out_fh} join( ",", @$columns ), "\n" if $columns;

   while (<$ifh>) {
      my $line = $_;
      chomp $line;

      if ( $opt->{ExcludePatterns} && @{ $opt->{ExcludePatterns} } ) {
         my $should_exclude = 1;

         for my $p ( @{ $opt->{ExcludePatterns} } ) {
            if ( $line !~ /$p/ ) {

               # remember this is AND logic; therefore, one fails means all fail
               $should_exclude = 0;
               last;
            }
         }

         if ($should_exclude) {
            print {$out_fh} $line, "\n";
            next;
         }
      }

      my $a;

      if ( $opt->{QuotedInput} ) {
         $a = parse_quoted_line( $line, $delimiter, $opt );
      } else {
         @$a = split /$delimiter/, $line;
      }

      my $r;

      if ($columns) {
         for my $c (@$columns) {
            my $p = $pos->{$c};
            $r->{$c} = $a->[$p];
         }
      }

      if ( $opt->{UsePosition} || $opt->{InputNoHeader} ) {

         # hardcoded column names c0, c1, c2, ...
         my $i = 0;
         for my $e (@$a) {
            my $c = "c$i";
            $r->{$c} = $e;
            $i++;
         }
      }

      if ( $matchExps || $excludeExps || $exportExps ) {
         TPSUP::Expression::export(%$r);
      }

      if ( $matchExps || $excludeExps ) {
         my $exclude_from_doing;

         if ($excludeExps) {
            for my $e (@$excludeExps) {
               if ( $e->() ) {
                  $exclude_from_doing++;
                  last;
               }
            }
         }

         if ($exclude_from_doing) {
            print {$out_fh} "$line\n";
            next;
         }

         {
            for my $e (@$matchExps) {
               if ( !$e->() ) {
                  $exclude_from_doing++;
                  last;
               }
            }
         }

         if ($exclude_from_doing) {
            print {$out_fh} "$line\n";
            next;
         }

         # we delete by not printing the orginal line
      }
   }

   close $out_fh if $out_fh != \*STDOUT;
}

sub diff_csv_long {
   my ( $csvs, $ref_keys, $cmp_keys, $opt ) = @_;

   # $csv is a ref to array of file names
   # $ref_keys is a ref to array of ref to array
   # $cmp_keys is a ref to array of cmp to array

   my $num_files = scalar(@$csvs);

   croak "need at least 2 csvs to diff. you have $num_files" if $num_files < 2;

   if ( $opt->{SameHeader} ) {
      my $refkeys = $ref_keys->[0];

      my $is_ref_key;
      for my $k (@$refkeys) {
         $is_ref_key->{$k}++;
      }

      my $refs;
      my $first_file_columns;
      my $exist_key;
      my $maxrow_by_key;

      for ( my $i = 0 ; $i < $num_files ; $i++ ) {
         my $ref = query_csv2(
            $csvs->[$i],
            {
               ReturnType   => 'RefKeyedHash',
               ReturnRefKey => $refkeys,
               NoPrint      => 1,
               %$opt
            }
         );
         croak "query_csv2($csvs->[$i]) failed: $ref->{status}"
           if $ref->{status} ne 'OK';

         $refs->[$i] = $ref->{KeyedHash};

         # $refs->[$i] is a ref to hash of arrays

         for my $key ( sort ( keys %{ $refs->[$i] } ) ) {
            $exist_key->{$key}++;

            my $count = scalar( @{ $refs->[$i]->{$key} } );

            if ( $opt->{RequireUniqueKey} ) {
               if ( $count > 1 ) {
                  croak "$csvs->[$i] has dup ref key "
                    . join( ",", @$refkeys )
                    . "=$key $count times";
               }
            } else {
               if ( !$maxrow_by_key->{$key} ) {
                  $maxrow_by_key->{$key} = $count;
               } elsif ( $maxrow_by_key->{$key} < $count ) {
                  $maxrow_by_key->{$key} = $count;
               }
            }
         }

         if ( $i == 0 ) {
            $first_file_columns = $ref->{columns};
         }
      }

      my @cmpkeys;

      if ( $cmp_keys->[0] && scalar( @{ $cmp_keys->[0] } ) ) {
         @cmpkeys = @{ $cmp_keys->[0] };
      } else {
         for my $k (@$first_file_columns) {
            next if $is_ref_key->{$k};
            push @cmpkeys, $k;
         }
      }

      my $num_cmp_keys = scalar(@cmpkeys);

      my @header_row = ( @$refkeys, "ChangeSummary" );

      for my $ck (@cmpkeys) {
         for ( my $i = 1 ; $i <= $num_files ; $i++ ) {
            push @header_row, "$ck\@$i";
         }
      }

      my $out_fh;

      if ( $opt->{DiffCsvOutput} ) {
         if ( $opt->{DiffCsvOutput} eq '-' ) {
            $out_fh = \*STDOUT;
         } else {
            $out_fh = get_out_fh( $opt->{DiffCsvOutput} );
         }

         if ( $opt->{DiffCsvHeader} ) {
            print {$out_fh} $opt->{DiffCsvHeader}, "\n";
         } else {
            print {$out_fh} join( ",", @header_row ), "\n";
         }
      }

      my $placeholder = $opt->{Placeholder};

      my $common_by_key;
      my $diff_by_key;

      for my $key ( sort ( keys %$exist_key ) ) {
         for ( my $m = 0 ; $m < $maxrow_by_key->{$key} ; $m++ ) {
            my @row;
            my $comment;

            #juxtapose
            for my $k (@cmpkeys) {
               for ( my $i = 0 ; $i < $num_files ; $i++ ) {

         # use staircase tests to prevent perl from creating new data structures
                  if (  defined $refs->[$i]
                     && defined $refs->[$i]->{$key}
                     && defined $refs->[$i]->{$key}->[$m] )
                  {
                     push @row, $refs->[$i]->{$key}->[$m]->{$k};
                  } else {
                     push @row, undef;
                  }
               }
            }

            my @last_cells;

         # use staircase tests to prevent perl from creating new data structures
            if (  defined $refs->[0]
               && defined $refs->[0]->{$key}
               && defined $refs->[0]->{$key}->[$m] )
            {
               @last_cells = @{ $refs->[0]->{$key}->[$m] }{@cmpkeys};
            } else {
               for my $ck (@cmpkeys) {
                  push @last_cells, undef;
               }
            }

            # $ perl -e 'if ( "" =~ /^(0|)$/) (print "match\n";}'
            # match
            # so we can use '^(0|)$' as placeholder for undefined cell

            my $mismatched;

         # use staircase tests to prevent perl from creating new data structures
            if (  !defined $refs->[0]
               || !defined $refs->[0]->{$key}
               || !defined $refs->[0]->{$key}->[$m] )
            {
               $comment = "new";
               $mismatched++;
            }

          CMP:
            for ( my $i = 1 ; $i < $num_files ; $i++ ) {
               if ( !exists $refs->[$i]->{$key}->[$m] ) {
                  $comment = "missing" if $comment ne "new";
               }

               for ( my $j = 0 ; $j < $num_cmp_keys ; $j++ ) {
                  my $cmp_key = $cmpkeys[$j];

                  my $this_cell = $refs->[$i]->{$key}->[$m]->{$cmp_key};

                  if ( !defined( $last_cells[$j] ) ) {
                     if ( defined($this_cell) ) {
                        if ( defined($placeholder) ) {
                           if ( "$this_cell" !~ /$placeholder/ ) {
                              $mismatched++;
                              $comment .= " $cmp_key"
                                if $comment !~ /^(new|missing)$/;

                              #last CMP;
                           }
                        } else {
                           $mismatched++;
                           $comment .= " $cmp_key"
                             if $comment !~ /^(new|missing)$/;

                           #last CMP;
                        }
                     }
                  } else {

                     # defined($last_cells[$j])
                     if ( !defined($this_cell) ) {
                        if ( defined($placeholder) ) {
                           if ( "$last_cells[$j]" !~ /$placeholder/ ) {
                              $mismatched++;
                              $comment .= " $cmp_key"
                                if $comment !~ /^(new|missing)$/;

                              #last CMP;
                           }
                        } else {
                           $mismatched++;
                           $comment .= " $cmp_key"
                             if $comment !~ /^(new|missing)$/;

                           #last CMP;
                        }
                     } else {

                        # defined($this_cell) && defined($last_cells[$j])
                        if ( defined($placeholder) ) {
                           if (  "$last_cells[$j]" =~ /$placeholder/
                              && "$this_cell" =~ /$placeholder/ )
                           {
                              # counted as a match
                              next;
                           } elsif ( "$last_cells[$j]" ne "$this_cell" ) {
                              $mismatched++;
                              $comment .= " $cmp_key"
                                if $comment !~ /^(new|missing)$/;

                              #last CMP;
                           }
                        } else {
                           if ( "$last_cells[$j]" ne "$this_cell" ) {
                              $mismatched++;
                              $comment .= " $cmp_key"
                                if $comment !~ /^(new|missing)$/;

                              #last CMP;
                           }
                        }
                     }
                  }
               }
            }

            unshift @row, split( /,/, $key ), $comment;    #output row

            if ($mismatched) {
               push @{ $diff_by_key->{$key} }, \@row;
               no warnings 'uninitialized';
               print {$out_fh} join( ",", @row ), "\n"
                 if $out_fh && !$opt->{CommonOnly};
            } else {
               push @{ $common_by_key->{$key} }, \@row;
               no warnings 'uninitialized';
               print {$out_fh} join( ",", @row ), "\n"
                 if $out_fh && $opt->{PrintCommon};
            }
         }
      }

      close $out_fh if $out_fh && $out_fh != \*STDOUT;

      my $ret;

      $ret->{header} = \@header_row;
      $ret->{common} = $common_by_key;
      $ret->{diff}   = $diff_by_key;

      return $ret;
   } else {
      croak "unbalanced args: $num_files csvs vs "
        . scalar(@$ref_keys)
        . " set of ref keys"
        if scalar(@$ref_keys) != $num_files;

      croak "unbalanced args: $num_files csvs vs "
        . scalar(@$cmp_keys)
        . " set of cmp keys"
        if scalar(@$cmp_keys) != $num_files;

      my $num_ref_keys = scalar( @{ $ref_keys->[0] } );

      my $num_cmp_keys = scalar( @{ $cmp_keys->[0] } );
      my @header_row =
        map { $_ . '@0' } ( @{ $ref_keys->[0] }, @{ $cmp_keys->[0] } );

      for ( my $i = 1 ; $i < $num_files ; $i++ ) {
         my $new_num_ref_keys = scalar( @{ $ref_keys->[$i] } );

         if ( $num_ref_keys != $new_num_ref_keys ) {
            croak
"inconsistent number of ref keys: $num_ref_keys vs $new_num_ref_keys";
         }

         my $new_num_cmp_keys = scalar( @{ $cmp_keys->[$i] } );

         if ( $num_cmp_keys != $new_num_cmp_keys ) {
            croak
"inconsistent number of cmp keys: $num_cmp_keys vs $new_num_cmp_keys";
         }

         push @header_row, map { $_ . "\@$i" } @{ $cmp_keys->[$i] };
      }

      my $out_fh;

      if ( $opt->{DiffCsvOutput} ) {
         if ( $opt->{DiffCsvOutput} eq '-' ) {
            $out_fh = \*STDOUT;
         } else {
            $out_fh = get_out_fh( $opt->{DiffCsvOutput} );
         }

         if ( $opt->{DiffCsvHeader} ) {
            print {$out_fh} $opt->{DiffCsvHeader}, "\n";
         } else {
            print {$out_fh} join( ",", @header_row ), "\n";
         }
      }

      my $exist_key;
      my $refs;
      my $maxrow_by_key;    # max number of rows for the key

      for ( my $i = 0 ; $i < $num_files ; $i++ ) {
         my $ref = query_csv2(
            $csvs->[$i],
            {
               ReturnType      => 'RefKeyedHash',
               ReturnRefKey    => $ref_keys->[$i],
               requiredColumns => $cmp_keys->[$i],
               NoPrint         => 1,
               %$opt
            }
         );
         croak "query_csv2($csvs->[$i]) failed" if $ref->{status} ne 'OK';

         $ref->{KeyedHash} = {} if !$ref->{KeyedHash};

         $refs->[$i] = $ref->{KeyedHash};

         # $refs->[$i] is a ref to hash of arrays

         for my $key ( sort ( keys %{ $refs->[$i] } ) ) {
            $exist_key->{$key}++;

            my $count = scalar( @{ $refs->[$i]->{$key} } );

            if ( $opt->{RequireUniqueKey} ) {
               if ( $count > 1 ) {
                  croak "$csvs->[$i] has dup ref key "
                    . join( ",", @{ $ref_keys->[$i] } )
                    . "=$key $count times";
               }
            } else {
               if ( !$maxrow_by_key->{$key} ) {
                  $maxrow_by_key->{$key} = $count;
               } elsif ( $maxrow_by_key->{$key} < $count ) {
                  $maxrow_by_key->{$key} = $count;
               }
            }
         }
      }

      my $placeholder = $opt->{Placeholder};

      my $common_by_key;
      my $diff_by_key;

      for my $key ( sort ( keys %$exist_key ) ) {
         for ( my $m = 0 ; $m < $maxrow_by_key->{$key} ; $m++ ) {
            my @row = split /,/, $key;    #output row

            for ( my $i = 0 ; $i < $num_files ; $i++ ) {
               push @row,
                 @{ $refs->[$i]->{$key}->[$m] }{ @{ $cmp_keys->[$i] } };
            }

            my @last_cells =
              @{ $refs->[0]->{$key}->[$m] }{ @{ $cmp_keys->[0] } };

            # $ perl -e 'if ( "" =~ /^(0|)$/) { print "match\n";}'
            # match
            # so we can use '^(0|)$' as placeholder for undefined cell

            my $mismatched;

          CMP:
            for ( my $i = 1 ; $i < $num_files ; $i++ ) {
               for ( my $j = 0 ; $j < $num_cmp_keys ; $j++ ) {
                  my $cmp_key = $cmp_keys->[$i]->[$j];

                  my $this_cell = $refs->[$i]->{$key}->[$m]->{$cmp_key};

                  if ( !defined( $last_cells[$j] ) ) {
                     if ( defined($this_cell) ) {
                        if ( defined($placeholder) ) {
                           if ( "$this_cell" !~ /$placeholder/ ) {
                              $mismatched++;
                              last CMP;
                           }
                        } else {
                           $mismatched++;
                           last CMP;
                        }
                     }
                  } else {

                     # defined($last_cells[$j])
                     if ( !defined($this_cell) ) {
                        if ( defined($placeholder) ) {
                           if ( "$last_cells[$j]" !~ /$placeholder/ ) {
                              $mismatched++;
                              last CMP;
                           }
                        } else {
                           $mismatched++;
                           last CMP;
                        }
                     } else {

                        # defined($this_cell) && defined($last_cells[$j])
                        if ( defined($placeholder) ) {
                           if (  "$last_cells[$j]" =~ /$placeholder/
                              && "$this_cell" =~ /$placeholder/ )
                           {
                              # counted as a match
                              next;
                           } elsif ( "$last_cells[$j]" ne "$this_cell" ) {
                              $mismatched++;
                              last CMP;
                           }
                        } else {
                           if ( "$last_cells[$j]" ne "$this_cell" ) {
                              $mismatched++;
                              last CMP;
                           }
                        }
                     }
                  }
               }
            }

            if ($mismatched) {
               push @{ $diff_by_key->{$key} }, \@row;
               no warnings 'uninitialized';
               print {$out_fh} join( ",", @row ), "\n"
                 if $out_fh && !$opt->{CommonOnly};
            } else {
               push @{ $common_by_key->{$key} }, \@row;
               no warnings 'uninitialized';
               print {$out_fh} join( ",", @row ), "\n"
                 if $out_fh && $opt->{PrintCommon};
            }
         }
      }

      close $out_fh if $out_fh && $out_fh != \*STDOUT;

      my $ret;

      $ret->{header} = \@header_row;
      $ret->{common} = $common_by_key;
      $ret->{diff}   = $diff_by_key;

      return $ret;
   }
}

sub diff_csv {
   my ( $csv1, $csv2, $keys1, $keys2, $opt ) = @_;

   my $result1 = query_csv2(
      $csv1,
      {
         ReturnType   => 'RefKeyedHash',
         ReturnRefKey => $keys1,
         NoPrint      => 1,
         %$opt
      }
   );

   croak "cannot parse $csv1" if !$result1;

   my $result2 = query_csv2(
      $csv2,
      {
         ReturnType   => 'RefKeyedHash',
         ReturnRefKey => $keys2,
         NoPrint      => 1,
         %$opt
      }
   );

   croak "cannot parse $csv2" if !$result2;

   my $ref1 = $result1->{KeyedHash};
   my $ref2 = $result2->{KeyedHash};

   my $OnlyIn1;
   my $OnlyIn2;
   my $InBoth;

   if ( $opt->{UnixDiff} ) {
      my ( $package, $prog, $line ) = caller;

      $prog =~ s:.*/::;

      my $tmpfile1 = get_tmp_file( "/var/tmp", "${prog}", { AddIndex => 1 } );
      my $tmpfile2 = get_tmp_file( "/var/tmp", "${prog}", { AddIndex => 1 } );

      write_keys_to_file( $ref1, $tmpfile1, $opt );
      write_keys_to_file( $ref2, $tmpfile2, $opt );

      my $switches = $opt->{UnixDiffSwitch} ? $opt->{UnixDiffSwitch} : '';

      system("diff $switches $tmpfile1 $tmpfile2");
   }

   if ( $opt->{DiffUnique} ) {
      for my $k ( sort ( keys %$ref1 ) ) {
         if ( !$ref2->{$k} ) {
            $OnlyIn1->{$k}++;
         } else {
            $InBoth->{$k}++;
         }
      }

      for my $k ( sort ( keys %$ref2 ) ) {
         if ( !$ref1->{$k} ) {
            $OnlyIn2->{$k}++;
         }
      }

      return ( $OnlyIn1, $OnlyIn2, $InBoth );
   } else {

      # non-Unique diff: needs to count the repeats of the same keys
      for my $k ( sort ( keys %$ref1 ) ) {
         if ( !$ref2->{$k} ) {
            $OnlyIn1->{$k} = scalar( @{ $ref1->{$k} } );
         } else {
            my $count1 = scalar( @{ $ref1->{$k} } );
            my $count2 = scalar( @{ $ref2->{$k} } );

            if ( $count1 > $count2 ) {
               $OnlyIn1->{$k} = $count1 - $count2;
               $InBoth->{$k}  = $count2;
            } elsif ( $count1 < $count2 ) {
               $OnlyIn2->{$k} = $count2 - $count1;
               $InBoth->{$k}  = $count1;
            } else {

               # $countl == $count2
               $InBoth->{$k} = $count1;
            }
         }
      }

      for my $k ( sort ( keys %$ref2 ) ) {
         if ( !$ref1->{$k} ) {
            $OnlyIn2->{$k} = scalar( @{ $ref2->{$k} } );
         }
      }

      return ( $OnlyIn1, $OnlyIn2, $InBoth );
   }
}

sub write_keys_to_file {
   my ( $ref, $file, $opt ) = @_;

   open my $out_fh, ">$file" or croak "cannot write to $file";

   for my $k ( sort ( keys %$ref ) ) {
      if ( $opt->{DiffUnique} ) {
         print {$out_fh} "$k\n";
      } else {
         my $count = scalar( @{ $ref->{$k} } );

         for ( my $i = 0 ; $i < $count ; $i++ ) {
            print {$out_fh} "$k\n";
         }
      }
   }

   close $out_fh;
}

sub render_csv {
   my ( $rows, $fields, $opt ) = @_;

   if ($rows) {
      my $type = ref $rows;
      croak "wrong ref type '$type'. expecting 'ARRAY'" if $type ne 'ARRAY';
   }

   my $row_type = $opt->{ROW_TYPE} ? $opt->{ROW_TYPE} : 'HASH';
   croak "unsupport $row_type=$row_type"
     if $row_type ne 'ARRAY' && $row_type ne 'HASH';
   my $row_is_hash = $row_type eq 'HASH' ? 1 : 0;

   my $num_fields = scalar(@$fields);

   my $max_by_field;

   {
      for my $f (@$fields) {
         my $len = length($f);
         $max_by_field->{$f} = $len;
      }
   }

   my $count = 0;
   my $max   = $opt->{PrintCsvMaxRows};
   for my $r (@$rows) {
      last if defined($max) && $count >= $max;

      $count++;

      for ( my $i = 0 ; $i < $num_fields ; $i++ ) {
         my $f     = $fields->[$i];
         my $value = $row_is_hash ? $r->{$f} : $r->[$i];

         next if !defined $value;

         my $len = length($value);

         if ( $max_by_field->{$f} < $len ) {
            $max_by_field->{$f} = $len;
         }
      }
   }

   my $out_fh;
   if ( $opt->{interactive} ) {
      my $cmd = "less -S";

      open $out_fh, "|$cmd" or croak "cmd=$cmd failed: $!";
   } elsif ( $opt->{out_fh} ) {
      $out_fh = $opt->{out_fh};
   } else {
      $out_fh = \*STDOUT;
   }

   for ( my $i = 0 ; $i < $num_fields ; $i++ ) {
      my $f       = $fields->[$i];
      my $max     = $max_by_field->{$f};
      my $buffLen = $max - length($f);

      print {$out_fh} ' | ', unless $i == 0;

      print {$out_fh} +( ' ' x $buffLen ), $f;
   }
   print {$out_fh} "\n";

   {
      # print {$out_fh} the bar right under the header
      my $length = 3 * ( $num_fields - 1 );

      for my $f (@$fields) {
         $length += $max_by_field->{$f};
      }

      print {$out_fh} +( '=' x $length );
   }
   print {$out_fh} "\n";

   $count = 0;
   for my $r (@$rows) {
      if ( defined($max) && $count >= $max ) {
         if ( $opt->{PrintCsvMaxRowsWarn} ) {
            my $total = scalar(@$rows);
            print "WARN: truncated at $max rows, total $total rows\n";
         }
         last;
      }
      $count++;

      for ( my $i = 0 ; $i < $num_fields ; $i++ ) {
         my $f   = $fields->[$i];
         my $max = $max_by_field->{$f};

         my $v;
         if ($row_is_hash) {
            $v = defined( $r->{$f} ) ? "$r->{$f}" : "";
         } else {
            $v = defined( $r->[$i] ) ? "$r->[$i]" : "";
         }
         my $buffLen = $max - length($v);

         print {$out_fh} ' | ', unless $i == 0;

         print {$out_fh} +( ' ' x $buffLen ), $v;
      }
      print {$out_fh} "\n";
   }

   close $out_fh if $out_fh != \*STDOUT && !$opt->{out_fh};
}

sub find_safe_delimiter {
   my ( $rows, $fields, $opt ) = @_;

   # @$rows are array of hashes
   # find an safe delimiter

   my $safe_delimiter;

   my @possible_delimiters = ( ',', '|', ':', '%', ';', '', '', '' );

 DELIMITER:
   for my $d (@possible_delimiters) {
      for my $r (@$rows) {
         for my $v ( @{$r}{@$fields} ) {
            next if !$v;

            # TODO: precompile the regex
            if ( "$v" =~ /$d/ ) {
               next DELIMITER;
            }
         }
      }

      $safe_delimiter = $d;
      last;
   }

   return $safe_delimiter;
}

sub filter_csv_array {
   my ( $input, $opt ) = @_;
   my $ret;

   my $csv_array;
   my $columns;

   if ( !$opt->{FilterInputType}
      || $opt->{FilterInputType} eq 'StructuredHash' )
   {
      # default and ideal input, $opt->{FilterInputType} = StructuredHash
      $columns   = $input->{columns};
      $csv_array = $input->{array};
   } elsif ( $opt->{FilterInputType} eq 'HashArray' ) {

      # Input is array of hashes

      if ( !$opt->{InputHashColumns} ) {
         croak "InputType=HashArray must have InputHashColumns set";
      }

      $columns   = $opt->{InputHashColumns};
      $csv_array = $input;
   } elsif ( $opt->{FilterInputType} eq 'ArrayArray' ) {

      # Input is array of array, the first line is header
      if ( !$csv_array || !@$csv_array ) {
         $ret->{status} = "ERROR: csv_array is empty";
         return $ret;
      }

      $columns   = shift @$input;
      $csv_array = $input;
   } else {
      croak "unsupported FilterInputType=$opt->{FilterInputType}";
   }

   my $num_col = scalar(@$columns);

   my $pos;

   for ( my $i = 0 ; $i < $num_col ; $i++ ) {
      my $c = $columns->[$i];
      $pos->{$c} = $i;
   }

   my @SelectColumns;
   if ( defined $opt->{SelectColumns} ) {
      @SelectColumns = @{ $opt->{SelectColumns} };
   }

   for my $oc (@SelectColumns) {
      if ( !defined $pos->{$oc} ) {
         if ( !( $opt->{UsePosition} && $oc =~ /^c\d+$/ ) ) {
            my $msg = "Selected Column='$oc' isn't part of header="
              . join( ",", @$columns );
            carp $msg;

            $ret->{status} = "ERROR: $msg";

            return $ret;
         }
      }
   }

   my $DQuoteC;
   my $DQuoteColumns;

   if ( $opt->{DQuoteColumns} ) {
      my $type = ref $opt->{DQuoteColumns};

      if ( !$type ) {
         @$DQuoteColumns = split /,/, $opt->{DQuoteColumns};
      } elsif ( $type eq 'ARRAY' ) {
         $DQuoteColumns = $opt->{DQuoteColumns};
      } else {
         croak "unsupported type='$type' of \$opt->{DQuoteColumns} = "
           . Dumper( $opt->{DQuoteColumns} );
      }

      for my $c (@$DQuoteColumns) {
         $DQuoteC->{$c}++;
      }
   }

   my $warn = $opt->{verbose} ? 'use' : 'no';

   my $matchExps;
   if ( $opt->{MatchExps} && @{ $opt->{MatchExps} } ) {
      @$matchExps = map { TPSUP::Expression::compile_exp( $_, $opt ) }
        @{ $opt->{MatchExps} };
   }

   my $excludeExps;
   if ( $opt->{ExcludeExps} && @{ $opt->{ExcludeExps} } ) {
      @$excludeExps = map { TPSUP::Expression::compile_exp( $_, $opt ) }
        @{ $opt->{ExcludeExps} };
   }

   my $Exps;
   my $Cols;

   my $expcfg;

   for my $attr (qw(TempExps ExportExps)) {
      if ( $opt->{$attr} ) {
         $expcfg->{$attr} = compile_paired_strings( $opt->{$attr}, $opt );
      }
   }

   my $exportExps = $expcfg->{ExportExps}->{Exps};
   my @exportCols =
     $expcfg->{ExportExps}->{Cols} ? @{ $expcfg->{ExportExps}->{Cols} } : ();

   my $tempExps = $expcfg->{TempExps}->{Exps};
   my @tempCols =
     $expcfg->{TempExps}->{Cols} ? @{ $expcfg->{TempExps}->{Cols} } : ();

   my @fields;

   if ( defined $opt->{SelectColumns} ) {
      @fields = ( @SelectColumns, @exportCols );
   } elsif ( defined $opt->{DeleteColumns} ) {
      my $delete_column;

      for my $c ( @{ $opt->{DeleteColumns} } ) {
         $delete_column->{$c} = 1;
      }

      for my $c (@$columns) {
         next if $delete_column->{$c};

         push @fields, $c;
      }

      push @fields, @exportCols;
   } else {
      @fields = ( @$columns, @exportCols );
   }

   my @out_array;

   if (  $opt->{FilterReturnType}
      && $opt->{FilterReturnType} eq 'StructuredArray' )
   {
      push @out_array, \@fields;
   }

   my $match_count = 0;

   for my $row (@$csv_array) {
      my $r;

      if ( $opt->{FilterInputArrayArray} ) {

         # this is an array to , so convert it into hash
         @{$r}{@$columns} = @$row;

         if ( $opt->{UsePosition} || $opt->{InputNoHeader} ) {

            # hardcoded column names c0, c1, c2, ...
            my $i = 0;
            for my $e (@$row) {
               my $c = "c$i";
               $r->{$c} = $e;
               $i++;
            }
         }
      } else {

         # otherwise $csv_array is an array hashes
         $r = $row;
      }

      if ( $matchExps || $excludeExps || $exportExps || $tempExps ) {
         my $r2 = {

            # internal
            _row => $match_count,

            # external from user
            %$r,
         };

         TPSUP::Expression::export_var( $r2,
            { FIX => $opt->{FIX}, RESET => 1 } );

         if (@tempCols) {
            my $temp_r;

            for ( my $i = 0 ; $i < @tempCols ; $i++ ) {
               my $c = $tempCols[$i];
               my $v = $tempExps->[$i]->();

               $r->{$c}      = $v;
               $temp_r->{$c} = $v;
            }

            TPSUP::Expression::export_var( $temp_r, { FIX => $opt->{FIX} } )
              ;    # don't RESET here
         }

         if ( $opt->{verbose} ) {
            print STDERR "calling dump_var({FIX=>$opt->{FIX}}) from ",
              __FILE__, " line ", __LINE__, "\n";
            TPSUP::Expression::dump_var( { FIX => $opt->{FIX} } );
         }
      }

      if ( $matchExps || $excludeExps ) {
         my $exclude_from_doing;

         if ($excludeExps) {
            for my $e (@$excludeExps) {
               if ( $e->() ) {
                  $exclude_from_doing++;
                  last;
               }
            }
         }

         if ($exclude_from_doing) {
            next;
         }

         {
            for my $e (@$matchExps) {
               if ( !$e->() ) {
                  $exclude_from_doing++;
                  last;
               }
            }
         }

         if ($exclude_from_doing) {
            next;
         }
      }

      # matched
      $match_count++;

      if (@exportCols) {
         for ( my $i = 0 ; $i < @exportCols ; $i++ ) {
            my $c = $exportCols[$i];
            $r->{$c} = $exportExps->[$i]->();
         }
      }

      if ($DQuoteC) {
         for my $c (@$DQuoteColumns) {
            if ( exists $r->{$c} ) {
               if ( defined( $r->{$c} ) ) {
                  $r->{$c} = qq("$r->{$c}");
               } else {
                  $$r->{$c} = qq("");
               }
            }
         }
      }

      if ( !$opt->{FilterReturnType}
         || $opt->{FilterReturnType} eq 'StructuredHash' )
      {
         # default to return StructuredHash
         push @out_array, $r;
      } elsif ( $opt->{FilterReturnType} eq 'StructuredArray' ) {
         push @out_array, @{$r}{@fields};
      } else {
         croak "unsupported FilterReturnType=$opt->{FilterReturnType}";
      }
   }

   $ret->{array}   = \@out_array;
   $ret->{columns} = \@fields;
   $ret->{status}  = 'OK';

   return $ret;
}

sub join_csv {
   my ( $csvs, $ref_keys, $join_keys, $opt ) = @_;

   # $csv is a ref to array of file names
   # $ref_keys is a ref to array of array
   # $join_keys is a ref to array of array

   my $num_files = scalar(@$csvs);

   croak "need at least 2 csvs to join, you have $num_files" if $num_files < 2;

   croak "unbalanced args: $num_files csvs vs "
     . scalar(@$ref_keys)
     . " set of ref keys"
     if scalar(@$ref_keys) != $num_files;

   croak
     "csv files number ($num_files) is less than number of set of join keys "
     . scalar(@$join_keys)
     if scalar(@$join_keys) > $num_files;

   my @header_row;

   for ( my $i = 0 ; $i < $num_files ; $i++ ) {
      next if !defined $join_keys->[$i];    # this file has no columns to join

      if ( $opt->{JoinUseSuffixedHeader} ) {
         push @header_row, map { $_ . "\@$i" } @{ $join_keys->[$i] };
      } else {
         push @header_row, @{ $join_keys->[$i] };
      }
   }

   if ( $opt->{JoinCsvHeader} ) {
      @header_row = split /,/, $opt->{JoinCsvHeader};
   }

   my $out_fh;

   if ( $opt->{JoinCsvOutput} ) {
      if ( $opt->{JoinOutput} eq '-' ) {
         $out_fh = \*STDOUT;
      } else {
         $out_fh = get_out_fh( $opt->{JoinCsvOutput} );
      }

      print {$out_fh} join( ",", @header_row ), "\n";
   }

   my $exist_key;
   my $refs;
   my $maxrow_by_key;    # max number of rows for the key

   for ( my $i = 0 ; $i < $num_files ; $i++ ) {
      my $ref = query_csv2(
         $csvs->[$i],
         {
            ReturnType      => 'RefKeyedHash',
            ReturnRefKey    => $ref_keys->[$i],
            requiredColumns => $join_keys->[$i],
            NoPrint         => 1,
            %$opt
         }
      );

      croak "failed to parse $csvs->[$i]" if $ref->{status} ne 'OK';

      $refs->[$i] = $ref->{KeyedHash};

      $opt->{verbose} && print STDERR "ref = ", Dumper($ref);

      for my $key ( sort ( keys %{ $refs->[$i] } ) ) {
         $exist_key->{$key}++;

         my $count = scalar( @{ $refs->[$i]->{$key} } );

         if ( $opt->{JoinRequireUniqueKey} ) {
            if ( $count > 1 ) {
               croak "$csvs->[$i] has dup ref key "
                 . join( ",", @{ $ref_keys->[$i] } )
                 . "=$key $count times";
            }
         } else {
            if ( !$maxrow_by_key->{$key} ) {
               $maxrow_by_key->{$key} = $count;
            } elsif ( $maxrow_by_key->{$key} < $count ) {
               $maxrow_by_key->{$key} = $count;
            }
         }
      }
   }

   $opt->{verbose} && print STDERR "maxrow_by_key = ", Dumper($maxrow_by_key);

   my $ret;

 KEY:
   for my $key ( sort ( keys %$exist_key ) ) {
      for ( my $m = 0 ; $m < $maxrow_by_key->{$key} ; $m++ ) {

         # one record (row) a time
         my @row;

         for ( my $i = 0 ; $i < $num_files ; $i++ ) {
            if ( $opt->{JoinIgnoreMissingRef}
               && !defined( $refs->[$i]->{$key}->[$m] ) )
            {
               next KEY;
            }

            next
              if !defined $join_keys->[$i];   # this file has no columns to join

            # Allow missing ref keys, use undef as placeholder
            push @row, @{ $refs->[$i]->{$key}->[$m] }{ @{ $join_keys->[$i] } };
         }

         print {$out_fh} join( ",", @row ), "\n" if $out_fh;

         if ( $opt->{JoinReturnStructuredArray} ) {
            push @{ $ret->{array} }, \@row;
         } else {

            # convert the record (row) from array to hash
            my $r;

            @{$r}{@header_row} = @row;

            if ( $opt->{JoinReturnKeyedHash} ) {
               push @{ $ret->{KeyedHash}->{$key} }, \@row;
            } else {

               # default to JoinReturnStructuredHash
               push @{ $ret->{array} }, $r;
            }
         }
      }
   }

   close $out_fh if $out_fh && $out_fh != \*STDOUT;

   $ret->{columns} = \@header_row;
   $ret->{status}  = 'OK';

   return $ret;
}

sub cat_csv {
   my ( $csvs, $opt ) = @_;

   # begin - for the first csv
   my $out_fh;
   my $ret;
   {
      my $i = 0;

      my $ref = query_csv2(
         $csvs->[$i],
         {
            NoPrint => 1,
            %$opt
         }
      );

      croak "failed to parse $csvs->[$i]" if $ref->{status} ne 'OK';

      my $header_row;
      if ( $opt->{CatCsvHeader} ) {
         @$header_row = split /,/, $opt->{CatCsvHeader};
      } else {
         $header_row = $ref->{columns};
      }

      $ret->{columns} = $header_row;

      if ( $opt->{CatCsvOutput} ) {
         if ( $opt->{CatOutput} eq '-' ) {
            $out_fh = \*STDOUT;
         } else {
            $out_fh = get_out_fh( $opt->{CatCsvOutput}, $opt );
         }
      }

      my @selectColumns =
          $opt->{CatCsvColumns}->[$i] ? @{ $opt->{CatCsvColumns}->[$i] }
        : $opt->{CatCsvColumns}->[0]  ? @{ $opt->{CatCsvColumns}->[0] }
        :                               ();

      if ( !@selectColumns ) {
         print {$out_fh} join( ",", @$header_row ), "\n";
      } else {
         print {$out_fh} join( ",", @selectColumns ), "\n";
      }

      for my $r ( @{ $ref->{array} } ) {
         if ( !@selectColumns ) {
            push @{ $ret->{array} }, $r;
            print {$out_fh} join( ",", @{$r}{ @{ $ref->{columns} } } ), "\n"
              if $out_fh;
         } else {
            my $new_r;
            @{$new_r}{@selectColumns} = @{$r}{@selectColumns};

            push @{ $ret->{array} }, $new_r;
            print {$out_fh} join( ",", @{$r}{@selectColumns} ), "\n" if $out_fh;
         }
      }
   }

   # end - for the first csv

   # for the rest csvs
   for ( my $i = 1 ; $i < scalar(@$csvs) ; $i++ ) {
      my $ref = query_csv2(
         $csvs->[$i],
         {
            NoPrint => 1,
            %$opt
         }
      );

      croak "failed to parse $csvs->[$i]" if $ref->{status} ne 'OK';

      my @selectColumns =
          $opt->{CatCsvColumns}->[$i] ? @{ $opt->{CatCsvColumns}->[$i] }
        : $opt->{CatCsvColumns}->[0]  ? @{ $opt->{CatCsvColumns}->[0] }
        :                               ();

      for my $r ( @{ $ref->{array} } ) {
         if ( !@selectColumns ) {
            push @{ $ret->{array} }, $r;
            print {$out_fh} join( ",", @{$r}{ @{ $ref->{columns} } } ), "\n"
              if $out_fh;
         } else {
            my $new_r;
            @{$new_r}{@selectColumns} = @{$r}{@selectColumns};

            push @{ $ret->{array} }, $new_r;
            print {$out_fh} join( ",", @{$r}{@selectColumns} ), "\n" if $out_fh;
         }
      }
   }

   close $out_fh if $out_fh && $out_fh != \*STDOUT;

   $ret->{status} = 'OK';

   return $ret;
}

sub join_query_csv {
   my ( $csvs, $exp, $opt ) = @_;

   my $total_csv = scalar(@$csvs);

   my @arefs;

   my @header_row;
   my @TableNames;

   my $pre_join_opt = { NoPrint => 1 };

   for my $k (
      qw(
      ExcludePatterns MatchPatterns
      ExcludeExps MatchExps
      delimiter
      InputStructuredHash
      )
     )
   {
      $pre_join_opt->{$k} = $opt->{$k} if exists $opt->{$k};
   }

   for ( my $i = 0 ; $i < scalar(@$csvs) ; $i++ ) {
      my $ref = query_csv2( $csvs->[$i], $pre_join_opt );

      croak "failed to parse $csvs->[$i]" if $ref->{status} ne 'OK';

      $arefs[$i] = $ref->{array};

      if ( $opt->{JQTableNames}->[$i] ) {
         $TableNames[$i] = $opt->{JQTableNames}->[$i];
      } else {
         $TableNames[$i] = sprintf( "t%d", $i + 1 );  # example: first csv is t1
      }

      for my $c ( @{ $ref->{columns} } ) {
         push @header_row,
           "$TableNames[$i]_$c";    # example: first csv's column c3: tl.c3
      }
   }

   my $total_records;
   my $formula;
   my @pos;
   my @max;

   # start position is (0,0,0...)
   # end position is (subtotal1-1, subtotal2-1, ...)

   for ( my $i = 0 ; $i < $total_csv ; $i++ ) {
      my $subtotal = scalar( @{ $arefs[$i] } );

      push @pos, 0;

      push @max, $subtotal;

      if ( !defined $total_records ) {
         $formula       = "$subtotal";
         $total_records = $subtotal;
      } else {
         $formula .= "*$subtotal";
         $total_records = $total_records * $subtotal;
      }
   }

   $opt->{verbose}
     && print STDERR "will parse total records = $formula = $total_records\n";

   my $ref1;

   if ( $total_records == 0 ) {
      $ref1->{array}  = [];
      $ref1->{status} = 'OK';
      return $ref1;
   }

   my $last = $total_csv - 1;

   my $compiled = TPSUP::Expression::compile_exp( $exp, $opt );

   my @joined_array;

 RECORD:
   while (1) {
      $opt->{verbose} && print STDERR "pos=", join( " ", @pos ), ", max=",
        join( " ", @max ), "\n";

      # process this record
      my $joined;

      for ( my $i = 0 ; $i < $total_csv ; $i++ ) {
         my $href = $arefs[$i]->[ $pos[$i] ];

         for my $k ( keys %{$href} ) {
            $joined->{"$TableNames[$i]_$k"} = $href->{$k};
         }
      }

      TPSUP::Expression::export_var( $joined, { RESET => 1 } );

      $opt->{verbose} && TPSUP::Expression::dump_var();

      if ( $compiled->() ) {
         $opt->{verbose} && print STDERR "joined = ", Dumper($joined);
         push @joined_array, $joined;
      }

      # increment the position by one
      my $addone = 1;

      for ( my $i = $last ; $i >= 0 ; $i-- ) {
         if ( !$addone ) {

     # this digit is not full yet, so nothing needs doing for digits above this.
     # increment is done

            next RECORD;
         }

         # $addone == 1
         $pos[$i]++;
         $addone = 0;    #reset $addone after increment

         if ( $pos[$i] == $max[$i] ) {

            # this digit is full

            if ( $i == 0 ) {

               # this is the last digit, meaning we are done with all records
               last RECORD;
            } else {
               $pos[$i] = 0;    # reset this digit
               $addone = 1;     # set $addone for next loop (digit)

               next;
            }
         } elsif ( $pos[$i] > $max[$i] ) {
            croak "should have never been here (col $i): pos=",
              join( " ", @pos ),
              ", max=", join( " ", @max );
         }
      }
   }

   $ref1->{status}  = 'OK';
   $ref1->{columns} = \@header_row;
   $ref1->{array}   = \@joined_array;

   my $post_join_opt = {
      output => $opt->{JQOutput},
      %$opt
   };

   for my $k ( keys %$pre_join_opt ) {
      delete $post_join_opt->{$k} if exists $pre_join_opt->{$k};
   }

   $post_join_opt->{InputType} = 'StructuredHash';

   my $ref2 = query_csv2( $ref1, $post_join_opt );

   return $ref2;
}

sub csv_to_html {
   my ( $csv, $opt ) = @_;

   my $html = "";

   if ( !$opt->{TableOnly} ) {
      $html .= "<HTML><body bgcolor=white>";

      my $title = defined $opt->{CSVHTMLTitle} ? $opt->{CSVHTMLTitle} : "";

      $html .= "<title>$title</title>\n";

      #$html .= "<div align='left'>\n";
   }

   my $default_AttrVals_by_column;
   if ( $opt->{ColAttrVal} ) {
      for my $ColAttrVals ( @{ $opt->{ColAttrVal} } ) {

         # student=color=red;score=color=red

         for my $col_attr_val ( split /;/, $ColAttrVals ) {

            # student=color=red

            my ( $col, $attr_val ) = split /=/, $col_attr_val, 2;

            # student, color=red

            push @{ $default_AttrVals_by_column->{$col} }, $attr_val;
         }
      }
   }

   my $handlers;
   if ( $opt->{HTMLRowExp} && @{ $opt->{HTMLRowExp} } ) {
      my $exps = compile_perl_array( $opt->{HTMLRowExp} );
      my $acts = $opt->{HTMLRowAct};

      $handlers = transpose_arrays( [ $exps, $acts, $opt->{HTMLRowExp} ] );
   }

   my $ref = query_csv2(
      $csv,
      {
         ReturnType => 'StructuredHash',
         NoPrint    => 1,
         %$opt
      }
   );

   if ( $ref->{status} ne 'OK' ) {
      print STDERR "failed to parse csv, status=$ref->{status}\n";
      return undef;
   }

   my @columns = @{ $ref->{columns} };

   $html .=
     "<TABLE CELLPADDING='1' CELLSPACING='1' BORDER='1' bordercolor=black>\n";

   # header
   {
      my $string = "<TR>";

      for my $c (@columns) {
         $string .= "<td>$c</td>";
      }

      $string .= "</TR>";
      $html   .= "$string\n";
   }

   for my $row ( @{ $ref->{array} } ) {

      #print Dumper($row);

      my $act_AttrVals_by_column;

      if ( $handlers && @$handlers ) {
         TPSUP::Expression::export_var( $row, { RESET => 1 } );

         if ( $opt->{verbose} ) {
            $TPSUP::Expression::verbose = 1;
         }

         for my $h (@$handlers) {
            my ( $compiled, $ColAttrVals, $uncompiled ) = @$h;

            #print "uncompiled = $uncompiled\n";

            if ( $compiled->() ) {

               #print "matched\n";

               if ($ColAttrVals) {

                  # student=color=red;score=color=red

                  for my $col_attr_val ( split /;/, $ColAttrVals ) {

                     # student=color=red

                     my ( $col, $attr_val ) = split /=/, $col_attr_val, 2;

                     # student, color=red

                     push @{ $act_AttrVals_by_column->{$col} }, $attr_val;
                  }
               }
            }
         }
      }

      my $string = "<TR>";

      no warnings "uninitialized";
      for my $c (@columns) {
         $string .= "<td";
         if ( exists $act_AttrVals_by_column->{$c} ) {
            for my $attr_val ( @{ $act_AttrVals_by_column->{$c} } ) {
               $string .= " $attr_val";
            }
         } elsif ( exists $default_AttrVals_by_column->{$c} ) {
            for my $attr_val ( @{ $default_AttrVals_by_column->{$c} } ) {
               $string .= " $attr_val";
            }
         }
         $string .= ">$row->{$c}</td>";
      }

      $string .= "</TR>";

      $html .= "$string\n";
   }

   $html .= "</TABLE>\n";

   if ( !$opt->{TableOnly} ) {
      $html .= "</body></html>\n";
   }

   return $html;
}

1
