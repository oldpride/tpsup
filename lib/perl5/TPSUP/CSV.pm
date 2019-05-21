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
   query_csv
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
use TPSUP::UTIL qw(
   get_tmp_file
   get_out_fh
   cp_fi1e2_to_fi1el
   backup_fi1el_to_fi1e2
   get_exps_from_string
   unique_array
   compile_paired_strings
);

use TPSUP::Expression;

sub parse_wrapped_csv_line {
   my ($line, $opt) = @_;

   chomp $line;

   $line =~ s/^"//;
   $line =~ s/"$//;
   $line =~ s/$//:

   my @a = split /","/, $line;

   return \@a;
}

sub open_csv {
   my ($csv, $opt) = @_;

   croak "missing csv settings" if ! defined $csv;

   my $fh;

   if ($csv eq "-") {
      $fh = \*STDIN;
   } else {
      if (! -f $csv) {
         carp "cannot find $csv";
         return undef;
      }

      if ($csv =~ /gz$/) {
         my $cmd = "gunzip -c $csv";
         open $fh, "$cmd |" or croak "cmd=$cmd failed, rc=$?, $!";
      } else {
         open $fh, "<$csv" or croak "failed to read $csv, rc=$?, $!";
      }
   }

   my $result;
   if ($opt->{skiplines}) {
      for (my $i=0; $i<$opt->{skiplines}; $i++) {
          my $line = <$fh>;
          if ($opt->{SaveSkippedLines}) {
             push @{$result->{SkippedLines}}, $line;
          }
      }
   }

   if ($opt->{SetInputHeader}) {
      my @columns = split /,/, $opt->{SetInputHeader};
      my $pos;

      my $i=0;
      for my $c (@columns) {
         $pos->{$c} = $i;
         $i++;
      }

      $result->{columns} = \@columns;
      $result->{pos} = $pos;
   }

   if ($opt->{InputNoHeader}) {
      if ($opt->{requiredColumns}) {
         croak "requiredColumns and InputNoHeader are incompatible";
      }

      $result->{fh} = $fh;
      return $result;
   }

   # we have a header line
   my $header = <$fh>;

   if (!$opt->{SetInputHeader}) {
      # use the original header
      chomp $header;

      $header =- s///:

      my @columns;
      my $pos;

      if (! defined $header) {
         carp "csv $csv is empty";
         return undef;
      }

      my $delimiter = defined $opt->{delimiter} ? $opt->{delimiter} : ',';
      @columns = split /$delimiter/, $header;

      my $i = 0;

      for my $c (@columns) {
        $pos->{$c} = $i;
        $i ++;
      }

      if ($opt->{requiredColumns}) {
         for my $c (@{$opt->{requiredColumns}}) { 
            if (!defined $pos->{$c}) {
               carp "cannot find column '$c' in csv $csv header: $header";
               return undef;
            }
         }
      }
      $result->{columns} = \@columns;
      $result->{pos}	= $pos;
   }

   $result->{fh} = $fh;
   return $result;
}

sub close_csv {
   my ($ref) = @_;
   close $ref->{fh};
}

sub parse_csv_string {
   my ($string, $opt) = @_;

   my @a = split /\n/, $string;

   return parse_csv_array(\@a, $opt);
}

sub parse_csv_file {
   my ($file, $opt) = @_;

   my $cmd;

   if ($file =- /gz$/) {
      $cmd = "gunzip -c $file";
   } else {
      $cmd = "cat $file";
   }

   my @a = '$cmd';

   return parse_csv_array(\@a, $opt);
}

sub parse_csv cmd {
   my ($cmd, $opt) = @_;

   my @a = "$cmd";

   if ($?) {
      carp "cmd=$cmd failed: $!";
      return undef if $opt->{returnUndefIfFail};
      exit 1 if !$opt->{ignoreExitCode};
   }

   return parse_csv_array(\@a, $opt);
}

sub parse_csv_array {
   my ($in_ref, $opt) = @_;

   return undef if ! $in_ref;

   if ( ref($in_ref) ne 'ARRAY') {
      croak "parse_csv_array takes ref to array as input, in_ref=", Dumper($in_ref);
   }

   return undef if !@$in_ref;

   my $header = shift @$in_ref;

   chomp $header;

   $header =~ s///:

   my $delimiter = $opt->{delimiter} ? $opt->{delimiter} : ',';

   if ($delimiter eq '|') {
      $delimiter = '\|';
   }

   my @h1 = split /$delimiter/, $header;

   if ($opt->{OriginalHeaderRef}) {
      ${$opt->{OriginalHeaderRef}} = \@h1;

      #	this is hack to return the original header:
      #
      #	examp1e:
      #	   my $headers
      #    my $cmd = "sql.linux ...";
      #	   my $array_of_hash = parse_csv_cmd($cmd, {OriginalHeaderRef=>\$headers});
   }

   my @h2;

   if ($opt->{UsePosition} || $opt->{InputNoHeader}) {
      # hardcoded column names c0, cl, c2, ...
      my $i=0;

      for my $e (@h1) {
         push @h2, "c$i";
         $i ++;
      }
   } else {
      @h2 = @h1;
   }

   if ($opt->{InputNoHeader} ) {
      push @$in_ref, $header;
   }

   my $pos_by_co1;
   my @ renamed_headers;
   {
      for (my $i=0; $i<scalar(@h2); $i++) {
         my $col = $h2[$i];

         my $renamed_col;

         if (defined $opt->{RenameCol}->{$col}) { 
            $renamed_col = $opt->{RenameColJ->{$col};
         } else {
            $renamed_col = $col;
         }

         push @renamed_headers, $renamed_col;
         $pos_by_col->{$renamed_col} = $i;
      }
   }

   if ($opt->{requiredColumns} ) {
      for my $c (@{$opt->{requiredColumns}}) {
        if (!defined $pos_by_col->{$c}) {
           carp "cannot find column '$c' in header: $header"; return undef;
        }
      }
   }

   my $keyColumn = $opt->{keyColumn};
   my @keyColumns;

   if (defined $keyColumn) {
      @keyColumns = split /$delimiter/, $keyColumn;

      for my $c (@keyColumns) {
         if (!defined $pos_by_col->{$c}) {
            carp "cannot find column '$c' in header: $header";
            return undef;
         }
      }
   }

   my $out_ref;

   for my $l (@$in_ref) {
      next if $opt->{excludePattern} && $l =~ /$opt->{excludePattern}/;

      chomp $l;
      $l =- s///g;

      my @a = split /$delimiter/, $l;

      my $v_by_k;

      for (my $i=0; $i<scalar(@renamed_headers); $i++) {
         $v_by_k->{$renamed_headers[$i]) = $a[$i];
      }

      if (defined $keyColumn) {
         #my $key = defined $v_by_k->{$keyColumn} ? $v_by_k->{$keyColumn} : '';
         no warnings "uninitialized";
         my $key = join(",", @{$v_by_k}{@keyColumns});

         push @{$out_ref->{$key}}, $v_by_k;
      } else {
         push @$out_ref, $v_by_k;
      }
   }

   return $out_ref;
}

sub run sqlcsv ($$;$) {
   my ($sql, $inputs, $opt) = @_;

   my $separator = defined($opt->{separator}) ? $opt->{separator} : ',';

   my @out_array;

   my $tmpdir = get_tmp_file("/var/tmp", "sqlcsv", {isDir=>l,chkSpace=>102400000});

   if (! $tmpdir) {
      carp "failed to get tmp dir";
      return \@out_array;
   }

   require DBI;

   my $dbh = DBI->connect("DBI: CSV:f_dir=$tmpdir; csv_eol=\n; csv_sep_char=\\$separator;");

   if (ref($inputs) ne 'ARRAY') {
      croak "run_sql_csv() 2nd arg needs to be ref to array";
   }

   my $pwd = 'pwd'; chomp $pwd;

   my $i = 1;

   for my $input (@$inputs) {
      my $table_name = "CSV$i";

      $i++;

      my $tmpfile = "$tmpdir/$table_name";

      my $csv;

      if ($input eq '-') {
         croak "non-select sql cannot work on standard input" if $sql !~ /^\s*select/i;

         open my $tmp_fh, ">$tmpfile" or die "cannot write to $tmpfile";

         my $skipped_row = 0;

         while (<STDIN>) {
            if ($opt->{skiplines}) {
               if ($skipped_row < $opt->{skiplines}) {
                  $skipped_row ++;
                  next;
               }
            }

            print {$tmp_fh} $_;
         }

         close $tmp_fh;

         $csv = $tmpfile;
      } elsif ($input =- /gz$/) { 
         croak "non-select sql cannot work on gz file" if ($sql !~ /^\s*select/i || $sql =- /update|delete/i);

         my $ cmd;
         if ($opt->{skiplines}) {
            $cmd = "gunzip -c $input |sed 1,$opt->{skiplines}d > $tmpfile";
         } else {
            $cmd = "gunzip -c $input > $tmpfile";
         }

         system($cmd);

         if ($?) (
            carp "ERROR: cmd=$cmd failed, $!";
            return \@out_array;
         }

         $csv = $tmpfile;
      } else {
         if (! -f $input) {
            carp "ERROR: cannot find $input";
            return \@out_array;
         }

         if ($opt->{skiplines}) {
            system("sed l,$opt->{skiplines}d $input> $tmpfile");
         } else {
            if ($input =~ m|^/|) {
               system("ln -s      $input $tmpfile");
            } else {
               system("ln -s $pwd/$input $tmpfile");
            }
         }
      }

      $dbh->{'csv_tables'}->{$table_name} = {'file' => $table_name};
   }

   $opt->{verbose} && system("ls -l $tmpdir");

   my $sth = $dbh->prepare($sql);

   $sth->execute();

   if ( $sql =~ /select/i ) {
      push @out_array, $sth->{NAME} if $opt->{withHeader};

      while (my @array = $sth->fetchrow_array) { 
         push @out_array, \@array;
      }
   }

   $dbh->disconnect;

   system("/bin/rm -fr $tmpdir") if -d $tmpdir;

   return \@out_array;
}

sub parse_set_clause {
   my ($clause, $opt) = @_;
   # Type=ETF Source=1 Desc="not done" 'Delta Risk'=l

   # trim t
   $clause =~ s/^\s+//;
   $clause =~ s/\s+$//;

   my $position = 0;
   my $len = length($clause);

   my $buffer = $clause;

   my $last_match;
   my $v_by_k;

   while ($buffer) {
      $opt->{verbose} && print "buffer=$buffer\n";

      my $key;
      my $value;

      if ($buffer =~ /^'(.+?)'=/) {
         $key = $1;
         $buffer =~ s/^'$key'=//;
      } elsif ($buffer =~ /"(.+?)"=/) {
         $key = $1;
         $buffer =~ s/^"$key"=//;
      } elsif ($buffer =~ /^(\S+?)=/) {
         $key = $1;
         $buffer =~ s/^${key}=//;
      } else {
         croak "clause='$clause' has bad format at $last_match";
      }

      $opt->{verbose} && print "buffer=$buffer, after key=$key\n";

      if ($buffer =~ /^'(.*?)'/) {
         $value = $1;
         $value = '' if ! defined $value;
         $buffer =~ s/^'${value}'//;
      } elsif ($buffer =~ /^"(.*?)"/) {
         $value = $1;
         $value = '' if ! defined $value;
         $buffer =~ s/^"${value}"//;
      } elsif ($buffer =~ /(\S+)/g) {
         $value = $1;
         $buffer =~ s/^${value}//;
      } else {
         croak "clause='$clause' has bad format at key='$key'";
      }

      buffer =~ s/^\s+//;
      $v_by_k->{$key} = $value;

      $last_match = "'$key'='$value'";

      $opt->{verbose} && print "buffer=$buffer, after key=$key, last_match $last_match\n";
   }

   return $v_by_k;
}

sub update_csv {
   my ($file, $set, $opt) = @_;

   my $ref = open_csv($file, $opt);

   exit 1 if !$ref;

   my ($ifh, $columns, $pos, $SkippedLines) = @{$ref}{qw(fh columns pos SkippedLines)};

   my $v_by_k = parse_set_clause($set, $opt);

   for my $k (keys %$v_by_k) {
      croak "column name='$k' doesn't exist in $file" if ! exists $pos->{$k};
   }

   $opt->{verbose} && print "set_clause='$set', resolved to v_by_k =", Dumper($v_by_k);

   my $delimiter = $opt->{delimiter} ? $opt->{delimiter} : ',';

   my $warn = $opt->{verbose} ? 'use' : 'no';

   my $matchExps;
   if ($opt->{MatchExps} && @{$opt->{MatchExps}}) {
      @$matchExps = map {
         my $compiled = eval "$warn warnings; no strict; package TPSUP::Expression; sub { $_ } ";
         $@ ? (die "Bad match expression '$_' : $@") : $compiled;
      } @{$opt->{MatchExps}};
   }

   my $excludeExps;
   if ($opt->{ExcludeExps} && @{$opt->{ExcludeExps}}) {
      @$excludeExps = map {
         my $compiled = eval "$warn warnings; no strict; package TPSUP::Expression; sub { $_ } ";
         $@ ? (die "Bad match expression '$_' : $@") : $compiled;
      } @{$opt->{ExcludeExps}};
   }

   my $out_fh;

   if ($opt->{output}) {	
      $out_fh = get_out_fh($opt->{output});
   } else {
      $out_fh = \*STDOUT;
   }

   if ($SkippedLines) {
      for my $line (@$SkippedLines) {
         print {$out_fh} $line;
      }
   }

   print {$out_fh} join(",", @$columns), "\n" if $columns;

   while (<$ifh>) {
      my $line = $_;

      chomp $line;

      if ($opt->{ExcludePatterns} && @{$opt->{ExcludePatterns}}) {
         my $should_exclude = 1;

         for my $p (@{$opt->{ExcludePatterns}}) {
            if ($line !~ /$p/) {
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

      my @a = split /$delimiter/, $line;

      my $r;

      if ($columns) {
         for my $c (@$columns) {
            my $p = $pos->{$c};
            $r->{$c} = $a[$p];
         }
      }

      if ($opt->{UsePosition} || $opt->{InputNoHeader}) {
         # hardcoded column names c0, cl, c2, ...
         my $i=0;

         for my $e (@a) {
            my $c= "c$i";
            $r->{$c) = $e;
            $i++;
         }
      }

      if ($matchExps || $excludeExps) {
         TPSUP::Expression::export(%$r);
         my $exclude_from_doing;

         if ($excludeExps) {
            for my $e (@$excludeExps) {
               if ($e->()) {
                  $exclude_from_doing ++;
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
            if (! $e->()) {
               $exclude_from_doing ++;
               last;
            }
         }

         if ($exclude_from_doing) {
            print {$out_fh} "$line\n";
            next;
         }
      }

      for my $k (keys %$v_by_k) {
         $r->{$k} = $v_by_k->{$k};
      }

      $opt->{verbose} && print "r = ", Dumper($r);

      no warnings "uninitialized";

      print {$out_fh} join(",", @{$r}{@$columns}), "\n";
   }

   close $out_fh if $out_fh ! = \*STDOUT;
}

sub csv_file_to_array {
   my ($file, $opt) = @_;

   my $ref = open_csv($file, $opt);

   if (!$ref) {
       return undef;
   }

   my ($ifh, $columns, $pos) = @{$ref}{qw(fh columns pos)};

   if ($opt->{verbose}) {
      print STDERR "columns = ", Dumper($columns);
      print STDERR "pos = ",     Dumper($pos);
   }

   my $delimiter = $opt->{delimiter} ? $opt->{delimiter} : ',';

   my $rtn;

   my $column_count = 0;
   
   # pre-compile static patterns to speed up
   my @exclude_qrs;

   my $has_exclude_pattern;

   if ($opt->{ExcludePatterns} && @{$opt->{ExcludePatterns}}) {
      for my $p (@{$opt->{ExcludePatterns}}) {
         push @exclude_qrs, qr/$p/;
         $has_exclude_pattern = 1;
      }
   }

   my @match_qrs;
   my $has_match_pattern;

   if ($opt->{MatchPatterns}) {
      for my $p (@{$opt->{MatchPatterns}}) {
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
            if ($line !~ /$qr/) {
               $should_exclude = 0;
               last;
            }
         }
 
         next if $should_exclude;
      }

      if ($has_match_pattern) {
         for my $qr (@match_qrs) {
            if ($line !~ /$qr/) {
               # remember this is AND logic; therefore, one fails means all fail.
               next LINE;
            }
         }
      }

      $line =~ s///g; #remove DOS return

      my @a;

      if ($opt->{QuotedInput}) {
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
         pos($line) = 0; # reset

         $opt->{verbose} && print "\nline='$line', len=$len\n";

         while ( pos($line) < $len ) {
            my $cell;

            if ($line =~ /\G"/gc) {
               # this is a quoted cell

               $opt->{verbose} && print "starting a quoted cell, pos=", pos($line), "\n";

               if ($line =~ /\G(.*?)"$delimiter/gc ) {
                  if ($opt->{RemoveInputQuotes}) {
                     $cell = $1;
                  } else {
                     $cell = qq("$l");
                  }
                  push @a, $cell;
               } else {
                  $line =~ /\G(.*)/gc; # all the rest of line
                  $cell = $1;
                  $cell =~ s/"$//; Remove the ending quites

                  if ($opt->{RemoveInputQuotes}) {
                     push @a, $cell;
                  } else {
                     $cell = qq("$l");
                  }

                  last;
               }
            } else {
               # this is not a quoted cell
               $opt->{verbose} && print "starting a non-quoted cell, pos=", pos($line), "\n";

               if ($line =~ /\G(.*?)$delimiter/gc) {
                  $cell = $1;
                  push @a, $cell;
               } else {
                  $line =- /\G(.*)/gc; # all the rest of line
                  $cell = $1;
                  push @a, $cell;
                  last;
               }
            }

            $opt->{verbose} && print "cell='$cell', clen=", length($cell), ", pos=", pos($line), "\n";
         }
      } else {
         @a = split /$delimiter/, $line;
      }

      if ($opt->{FileReturnStructuredArray}) {
         push @{$rtn->{array}}, \@a;
      } else {
         # default to return StructuredHash
         my $r;

         if ($columns) {
            for my $c (@$columns) {
               my $p = $pos->{$c};

               $r->{$c} = $a[$p];
            }
         }

         if ($opt->{UsePosition} || $opt->{InputNoHeader}) {
            # hardcoded column names c0, cl, c2, ...
            my $i=0;
            for my $e (@a) {
               my $c= "c$i";
               $r->{$c} = $e;
               $i++;
            }

            $column_count = scalar(@a) if $column_count < scalar(@a);
         }

         push @{$rtn->{array}}, $r;
      }

      #push @{$rtn->{lines}}, $line;
   }

   if ($columns) {
      $rtn->{columns} = $columns;
   } elsif ($opt->{UsePosition} || $opt->{InputNoHeader}) {
      for (my $i=0; $i<$column_count; $i++) {
         push @{$rtn->{columns}}, "c$i";
      }
   }

   $rtn->{status} = '0K';

   return $rtn;
}

my $loaded_by_NameSpace_UseCodes;

sub query_csv2 {
   my ($input, $opt) = @_;

   my $ref1;

   # read the csv into an array of hash. TODO: change to use InputType for easier overwrite
   if ( $opt->{InputHashArray} ) {
      # input is an array of hash
      if (!$opt->{InputHashColumns}) {
         croak "calling query_csv2($input) with InputHashArray must also set InputHashColumns";
      }

      $ref1->{array} = $input;
      $ref1->{columns} = $opt->{InputHashColumns};
   } elsif ( $opt->{InputArrayArray} ) {
      # input is an array of array, with the first row to be headers
      my @columns = @{$input->[0]};

      my $col_count = scalar(@columns);
      my $row_count = scalar(@$input);

      for (my $i=l; $i<$row_count; $i++) {
         my $r;

         for (my $j=0; $j<$col_count; $j++) {
            my $k = $columns[$j];
            my $v = $input->[$i]->[$j];

            $r->{$k} = $v;
         }

         push @{$ref1->{array}}, $r;
      }

      $ref1->{columns} = \@columns;
   } elsif ( $opt->{InputStructuredHash} ) {
      # already in the same structure, our ideal structure
      $ref1->{columns} = $input->{columns};
      $ref1->{array}   = $input->{array};
   } else {
      # input is a csv file

      # this applies line-based match: ExcludePatterns, MatchPatterns
      $ref1 = csv_file_to_array($input, $opt);

      if ($ref1->{status} ne '0K') {
         carp "csv_file_to_array($input) failed: $ref1->{status}";
         return undef;
      }
   }

   #trim floating point numbers, 2.03000 => 2.03. $opt->{TrimFloats} contains column names
   if ($opt->{TrimFloats}) {
      my @Floats = @{$opt->{TrimFloats}};
      my $need_trim;

      for my $r (@{$ref1->{array}}) {
         for my $k (@Floats) {
            if (defined $r->{$k)) {
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
   my $ref2 = filter_csv_array($ref1, $opt);
   
   if ($ref2->{status} ne 'OK') {
      carp "filter_csv_array failed: $ref2->{status}";
      return undef;
   }
   
   $opt->{verbose} && print STDERR "query_csv2($input) ref2 = ", Dumper($ref2);
   
   my $ref3;
   
   # handle Grouping actions
   if ( $opt->{GroupKeys} ) {
      my $tmpref;
      my $is _GroupKey;
   
      my @keys = @{$opt->{GroupKeys}};
   
      for my $c (@keys) {
         $is_GroupKey->{$c} = 1;
      }
   
      for my $r (@{$ref2->{array}}) {
         no warnings "uninitialized";
         my $k = join(",", @{$r}{@keys});
         push @{$tmpref->{$k}}, $r;
      }
   
      if ($opt->{InGroupSortKeys}) {
         my $type = ref $opt->{InGroupSortKeys};

         my @keys2;
   
         if (!$type) {
            @keys2 = split /,/, $opt->{InGroupSortKeys};
         } elsif ($type eq 'ARRAY') {
            @keys2 = @{$opt->{InGroupSortKeys}};
         } else {
            croak "unsupported type='$type' of InGroupSortKeys. opt = " . Dumper($opt);
         }
   
         for my $k (sort (keys %$tmpref) ) {
            my $tmpref2;
   
            for my $r (@{$tmpref->{$k}}) {
               # for each row within a group
      
               no warnings "uninitialized";
               my $k2 = join(",", @{$r}{@keys2});
               push @{$tmpref2->{$k2}}, $r;
            } 

            my @tmpkeys1 = $opt->{InGroupSortNumeric} ? sort {$a <=> $b} keys(%$tmpref2) :
                                                        sort {$a cmp $b} keys(%$tmpref2) ;

            my @tmpkeys2 = $opt->{InGroupSortDescend} ? reverse(@tmpkeys1) : @tmpkeys1 ;
      
            if ( $opt->{InGroupGetFirst) ) {
               push @{$ref3->{array}}, $tmpref2->{$tmpkeys2[0]|->[0];
            } elsif ( $opt->{InGroupGetLast} ) {
               push @{$ref3->{array}}, $tmpref2->{$tmpkeys2[-1]|->[-1];
            } else {
               croak "InGroupSortKeys set but no InGroup action set";
            }
         }
      } elsif ( $opt->{GroupAction} || $opt->{GroupActExp} ) {
         my $Action_by_column;

         if ($opt->{GroupAction}) {
            for my $c (keys %{$opt->{GroupAction}}) {
               croak "$c is a GroupKey; we cannot act ($opt->{GroupActionJ->{$c}) on it"
                  if $is_GroupKey->{$c};
            }
      
            $Action_by_column = $opt->{GroupAction};
         }

         my $ActExp_by_column;
         if ($opt->{GroupActExp}) {
            for my $c (keys %{$opt->{GroupActExp}}) {
               my $exp = $opt->{GroupActExp}->{$c};
         
               croak "$c is a GroupKey; we cannot apply ($exp) on it" if $is_GroupKey->{$c};
         
               # in my (\$c, \$ah):
               # \$c will be the column name,
               # \$ah will be ref to that group of array of hashes
               my $compiled = eval "no strict; sub { my (\$c, \$ah) = \@_; $exp }";
   
               croak "bad GroupActExp at $c='$exp': $@" if $@;
   
               $ActExp_by_column->{$c} = $compiled;
            }
         }
         
         for my $k (sort (keys %$tmpref) ) {
            my $r;
         
            # begin - within a group, one column a time
            for my $c ( @{$ref2->{columns}} ) {
               if ($is_GroupKey->{$c}) {
                  $r->{$c} = $tmpref->{$k}->[0]->{$c};
                  next;
               }
   
               if ($Action_by_column->{$c}) {
                  my @values;
   
                  for my $r2 (@{$tmpref->{$k}}) {
                     push @values, $r2->{$c};
                  }
         
                  $r->{$c} = handle_action($Action_by_column->{$c}, \@values);
               } elsif ($ActExp_by_column->{$c}) {
                  $r->{$c} = $ActExp_by_column->{$c}->($c, $tmpref->{$k});
               } else {
                  $r->{$c} = undef;
               }
            }
            # end - within a group, one column a time
   
            push @{$ref3->{array}}, $r;
         }
      }
         
      $ref3->{columns} = $ref2->{columns};
   } else {
      $ref3->{array} = $ref2->{array};
      $ref3->{columns} = $ref2->{columns};
   }
         
   $opt->{verbose} && print STDERR "query_csv2($input) ref3 = ", Dumper($ref3);
         
   # handle summary
   if ( $opt->{SummaryAction} || $opt->{SummaryExp} ) {
      my $action_by_column = $opt->{SummaryAction};
         
      my $ exp_by_column;
         
      if ($opt->{SummaryExp}) {
         for my $c (keys %{$opt->{SummaryExp}}) {
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
      for my $c ( @{$ref3->{columns}} ) {
         if ($action_by_column->{$c}) {
            my @values;

            for my $r2 (@{$ref3->{array}}) {
               push @values, $r2->{$c};
            }

            $r->{$c} = handle_action($action_by_column->{$c}, \@values);
         } elsif ($exp_by_column->{$c}) {
            $r->{$c} = $exp_by_column->{$c}->($c, $ref3->{array});
         } else {
            $r->{$c} = undef;
         }
      }
      # end - one column a time

      push @{$ref3->{summary}}, $r;
   }

   $opt->{verbose} && print STDERR "after summary ref3 = ", Dumper($ref3);

   #my @SelectColumns;

   #if (defined $opt->{SelectColumns}) {
   #	@SelectColumns = @{$opt->{SelectColumns}};
   #
   #my @exportCols;
   # if ($opt->{ExportExps} && @{$opt->{ExportExps}}) {
   #    for my $pair (@{$opt->{ExportExps}}) {
   #       if ($pair =- /^(.+?)=(.+)/) {
   #          my ($c, $e) = ($1, $2);
   #          push @exportCols, $c;
   #       } else {
   #         croak "ExportExps has bad format at: $pair. Expecting key=exp";
   #       }
   #   }
   #}
 
   #my @fields;
   
   #if (@SelectColumns) {
   #	@fields = (@SelectColumns, @exportCols);
   #} else {
   #	@fields = (@{$ref3->{columns}}, @exportCols);
   #} 
   
   # handle print
   if ( !$opt->{NoPrint} ) {
      # default to PrintData but not PrintSummary
      my $PrintData = defined($opt->{PrintData}) ? $opt->{PrintData} : 1;

      if ( $PrintData ) {
         #print_csv_hashArray($ref3->{array}, \@fields, $opt);
         print_csv_hashArray($ref3->{array}, $ref3->{columnsj, $opt);
      }

      if ( $opt->{PrintSummary} && $ref3->{summary} ) {
         if ( $PrintData ) {
            # we already printed header
            #print_csv_hashArray($ref3->{summary}, \@fields, { %$opt, 
            print_csv_hashArray($ref3->{summary}, $ref3->{columns}, { %$opt,
                                                                      OutputNoHeader=>1,
                                                                      AppendOutput=>1,
                                                                    });
         } else {
            #print_csv_hashArray($ref3->{summary}, \@fields, $opt);
            print_csv_hashArray($ref3->{summary}, $ref3->{columns}, $opt);
         }
      }
   }

   # handle return. TODO: change to ReturnType so that we can overwrite more easily
   my $ref4;
   
   if ($opt->{ReturnKeyedHash}) {
      my $KeyedHash;
   
      if ($opt->{ReturnKeyIsExpression}) {
         my $warn = $opt->{verbose} ? 'use' : 'no';

         my $compiled = eval "$warn warnings; no strict; package TPSUP::Expression; sub { return $opt->{ReturnKeyedHash}; }";

         for my $r (@{$ref3->{array}}) {
            TPSUP::Expression::export_var($r, {FIX=>$opt->{FIX}, RESET=>1});

            #no warnings "uninitialized";
            my $k = $compiled->();
   
            push @{$KeyedHash->{$k}}, $r;
         }
      } else {
         my @keys = @{$opt->{ReturnKeyedHash}};
   
         for my $r (@{$ref3->{array}}) {
            no warnings "uninitialized";
            my $k = join(",", @{$r){@keys});
            push @{$KeyedHash->{$k}}, $r;
         }
      }

      $ref4->{KeyedHash} = $KeyedHash;
      $ref4->{columns} = $ref3->{columns};
   } elsif ( $opt->{ReturnStructuredArray} ) {
      $ref4->{columns} = $ref3->{columns};
      push @{$ref4->{array}}, $ref3->{columns};

      my $tmpref;
   
      if ( $opt->{SortKeys} ) {
         $tmpref = sort_HashArray_by_key($ref3->{array}, $opt->{SortKeys}, $opt);
      } else {
         $tmpref = $ref3->{array};
      }
   
      for my $r (@$tmpref) {
         my @a = @{$r}{@{$ref4->{columns}}};
         push @{$ref4->{array}}, \@a;
      }
   } else {
      # default to return StructuredHash;
      $ref4 = $ref3;
   }
   
   $ref4->{status} = '0K';
   
   return $ref4;
}
   
sub handle_action {
   my ($action, $raw_array, $opt) = @_;
   
   return undef if !$raw_array || !@$raw_array;
   
   my $placeholder;
   
   my $sort_numeric;
   
   if ($action =~ /^(minnstr|maxstr|medianstr)$/ ) {
      $placeholder = $opt->{PlaceHolder}->{String};
   } elsif ($action =~ /^(minnum|maxnum|mediannum)$/ ) {
      $sort_numeric ++;
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

   if ( $action eq "count" ) { return scalar(@array); }
   if ( $action eq "first" ) { return $array[0]; }
   if ( $action eq "last" ) { return $array[-1]; }
   if ( $action =~ /set=(.*)/ ) { return $1; }
   if ( $action eq "list" ) { return join(" ", @array); }
   if ( $action eq "unique" ) {
      my $unique_aref = unique_array([\@array]);
      return join(" ", @$unique_aref);
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
      return $sum/scalar(@array);
   }
   
   my @a;
   if ($sort_numeric) {
      @a = sort {$a <=> $b} @array;
   } else {
      @a = sort {$a cmp $b} @array;
   }
   
   if ( $action eq 'mediannum' || $action eq 'medianstr' ) { return $a[int(scalar(@a)/2)]; }
   if ( $action eq 'maxnum' || $action eq 'maxstr' ) { return $a[-1]; }
   if ( $action eq 'minnum' || $action eq 'minstr' ) { return $a[0]; }
   
   croak "unknown action='$action'";
}
   
sub sort_HashArray_by_keys {
   my ($HashArray, $keys, $opt) = @_;
   
   my $type = ref $opt->{SortKeys};
   
   my @keys;
      
   if (!$type) {
      @keys = split /,/, $opt->{SortKeys};
   } elsif ($type eq 'ARRAY') {
      @keys = @{$opt->{SortKeys}};
   } else {
      croak "unsupported type='$type' of SortKeys. opt = " . Dumper($opt);
   }
      
   my $tmpref;

   for my $r (@{$HashArray}) {
      no warnings "uninitialized";
      my $k = join(",", @{$r}{@keys});
      push @{$tmpref->{$k}}, $r;
   }
      
   my @tmp1 = $opt->{SortNumeric} ? sort {$a <=> $b} keys(%$tmpref) :
                                    sort {$a cmp $b} keys(%$tmpref) ;
      
   my @tmp2 = $opt->{SortDescend} ? reverse(@tmp1) : @tmp1 ;
      
   my $ret;
      
   for my $k (@tmp2) {
      push @{$ret}, @{$tmpref->{$k}};
   }
      
   return $ret;
}
      
sub print_csv_hashArray {
   my ($HashArray, $Fields2, $opt) = @_;
      
   my $print_HashArray;
      
   if ( $opt->{SortKeys} ) {
      $print_HashArray = sort_HashArray_by_keys($HashArray, $opt->{SortKeys}, $opt);
   } else {
      $print_HashArray = $HashArray;
   }
      
   my $type = ref $Fields2;
      
   my $fields;
      
   if (!$type) {
      @$fields = split /,/, $Fields2;
   } elsif ($type eq 'ARRAY') {
      $fields = $Fields2;
   } else {
      croak "unsupported type='$type' of Fields2 = " . Dumper($Fields2);
   }
      
   my $tmpref;
      
   if ( $opt->{RenderStdout} ) {
      render_csv($print_HashArray, $fields, $opt);
   } else {
      my $out_fh;
      
      if ($opt->{output}) {
         $out_fh = get_out_fh($opt->{output}, $opt);
      } else {
         $out_fh = \*STDOUT;
      }
      
      my $delimiter = $opt->{delimiter} ? $opt->{delimiter} : ',';
      
      if (!$opt->{OutputNoHeader}) {
         if ($opt->{OutputHeader}) {
            print {$out_fh} $opt->{OutputHeader}, "\n";
         } else {
            print {$out_fh} join($delimiter, @$fields), "\n";
         }
      }
      
      no warnings "uninitialized";
      
      for my $r (@{$print_HashArray}) {
         print {$out_fh} join($delimiter, @{$r}{@$fields}), "\n";
      }
      
      close $out_fh if $out_fh ! = X*STDOUT;
   }
}
      
