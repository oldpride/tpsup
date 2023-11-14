package TPSUP::FILE;

use strict;
use warnings;

use base qw( Exporter );
our @EXPORT_OK = qw(
  get_in_fh
  get_out_fh
  close_in_fh
  close_out_fh
  tpglob
  sorted_files
  sorted_files_by_mtime
  get_latest_files
  tpfind
  convert_filemode
  get_mtime
);

use Carp;
use Data::Dumper;

sub get_in_fh {
   my ( $input, $opt ) = @_;

   my $verbose = $opt->{verbose};

   my $in_fh;

   if ( !defined($input) || $input eq '-' ) {
      $in_fh = \*STDIN;
      if ( -t STDIN ) {    # test tty
         print STDERR
           "hit Enter and then Control+D to finish input on commmand line\n";
      }
      $verbose && print STDERR "get_in_fh() opened STDIN\n";
   } else {
      my ( $host, $path );

      my $ssh_host;

      if ( $input =~ m|^([^/]+?):(.+)| ) {

         # user@hostname:tpsup/profile
         ( $host, $path ) = ( $1, $2 );

         $ssh_host =
"ssh -n -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes $host";
      } else {
         $ssh_host = "";
         $path     = $input;

         croak "$input is not found or is not a file" if !-f $input;
      }

      my $Tail     = $opt->{Tail};        # tail -12  filename
      my $Head     = $opt->{Head};        # head -n 5 filename
      my $SkipHead = $opt->{SkipHead};    # sed 1,3d  filename

      my $cmd;

      # transformation
      if ( $path =~ /gz$/ ) {
         $cmd = "gunzip -c $path";
      } else {
         $cmd = "cat $path";
      }

      if ( defined $Tail ) {
         $cmd = "$cmd|tail -$Tail";
         $cmd =~ s/cat $path|tail -$Tail/tail -$Tail $path/;    # optimize
      }

      if ( defined $Head ) {
         $cmd = "$cmd|Head -n $Head";
         $cmd =~ s/cat $path|Head -n $Head/Head -n $Head $path/;    # optimize
      }

      if ( defined $SkipHead ) {
         $cmd = "$cmd|sed 1,${SkipHead}d";
         $cmd =~
           s/cat $path|sed 1,${SkipHead}d/sed 1,${SkipHead}d $path/;  # optimize
      }

      if ( $opt->{Backward} ) {
         $cmd = "$cmd|tac";
         $cmd =~ s/cat $path|tac/tac $path/;                          # optimize
      }

      if ($ssh_host) {
         $cmd = qq($ssh_host "$cmd");
      }

      my $pipe = "|";

      if ( $cmd eq "cat $path" ) {
         $pipe = "";
         $cmd  = "<$path";
      }

      $verbose && print STDERR "cmd=$cmd\n";
      open $in_fh, "$cmd $pipe" or croak "cmd=$cmd failed: $!";
   }

   return $in_fh;
}

sub get_out_fh {
   my ( $output, $opt ) = @_;

   my $out_fh;

   if ( !defined($output) || $output eq '-' ) {
      $out_fh = \*STDOUT;
   } else {

      #confess __FILE__, " ", __LINE__, " output=$output\n";
      my ($outdir) = ( $output =~ m:^(/.+/): );

      if ( !defined($outdir) || !"$outdir" ) {
         $outdir = ".";
      }

      if ( !-d $outdir ) {
         system("mkdir -p $outdir");

         croak "cannot mkdir -p $outdir" if $?;
      }

      if ( $opt->{AppendOutput} ) {
         open $out_fh, ">>$output" or croak "cannot append to $output: $!";
      } else {
         open $out_fh, ">$output" or croak "cannot write to $output: $!";
      }
   }

   return $out_fh;
}

sub close_in_fh {
   my ( $fh, $opt ) = @_;

   close $fh if $fh != \*STDIN;
}

sub close_out_fh {
   my ( $fh, $opt ) = @_;

   close $fh if $fh != \*STDOUT && $fh != \*STDERR;
}

sub tpglob {
   my ( $pattern, $opt ) = @_;

   my $sort    = $opt->{sort};
   my $reverse = $opt->{reverse};

   my @patterns;
   my $type = ref($pattern);
   if ( !$type ) {

      # scalar
      @patterns = split /\s+/, $pattern;
   } elsif ( $type eq 'ARRAY' ) {

      # array
      @patterns = @$pattern;
   } else {
      croak "tpglob: pattern must be scalar or array";
   }

   my @files;
   for my $p (@patterns) {
      my @files2 = grep { -e $_ } glob($p);
      if (@files2) {
         push @files, @files2;
      } else {
         print STDERR "tpglob: no file matches pattern '$p'\n";
      }
   }

   if ( !$sort ) {
      return @files;
   } elsif ( $sort eq 'time' ) {
      return sorted_files_by_mtime( \@files, { reverse => $reverse } );
   } elsif ( $sort eq 'name' ) {
      my @files2 = sort { $a cmp $b } @files;
      if ($reverse) {
         return reverse @files2;
      } else {
         return @files2;
      }
   } else {
      croak "tpglob: unknown sort option '$sort'";
   }

}

sub sorted_files {
   my ( $files, $opt ) = @_;

   my $globbed   = $opt->{globbed};
   my $reverse   = $opt->{reverse};
   my $sort_func = $opt->{sort_func};

   my @files2;
   if ( !$globbed ) {
      @files2 = tpglob( $files, $opt );
   } else {
      @files2 = @$files;
   }

   if ( !$sort_func ) {
      $sort_func = sub { $_[0] cmp $_[1] };
   }

   my @sorted_files = sort { $sort_func->( $a, $b ) } @files2;
   return $reverse ? reverse @sorted_files : @sorted_files;
}

my $mtime_by_file;

sub get_mtime {
   my $file = shift;

   if ( !$mtime_by_file->{$file} ) {

      # my @array = lstat($file);
      # my (
      #     $dev,  $ino,   $mode,  $nlink, $uid,     $gid, $rdev,
      #     $size, $atime, $mtime, $ctime, $blksize, $blocks
      # ) = @array;
      $mtime_by_file->{$file} = ( stat($file) )[9];
   }

   return $mtime_by_file->{$file};
}

sub convert_filemode {
   my ( $input, $action ) = @_;

   my $mode;
   if ( $action eq 'int2oct' ) {
      $mode = sprintf( "%04o", $input );
   } elsif ( $action eq 'oct2int' ) {
      $mode = oct($input);
   } elsif ( $action eq 'int2str' ) {
      $mode = sprintf( "%04b", $input );

      # use left shift to convert octal to string
   } else {
      croak "unknown action=$action";
   }

}

sub sorted_files_by_mtime {
   my ( $files, $opt ) = @_;

   my $sort_func = sub {
      my ( $f1, $f2 ) = @_;
      my $mtime1 = get_mtime($f1);
      my $mtime2 = get_mtime($f2);
      return $mtime1 <=> $mtime2;
   };

   my $opt2 = $opt ? $opt : {};
   return sorted_files( $files, { %$opt2, sort_func => $sort_func } );
}

sub get_latest_files {
   my ( $files, $opt ) = @_;

   my $opt2         = $opt ? $opt : {};
   my @sorted_files = sorted_files_by_mtime( $files, { %$opt2, reverse => 1 } );
   return \@sorted_files;
}

sub tpfind {
   my ( $paths, $opt ) = @_;

   # use 'require' instead of 'use' to break module dependency loop because
   # TPSUP::UTIL also uses TPSUP::FILE.
   #    use TPSUP::UTIL qw(
   #      get_user_by_uid
   #      get_group_by_gid
   #      compile_perl_array
   #      transpose_arrays
   #    );
   require TPSUP::UTIL;

   my $verbose    = $opt->{verbose} || 0;
   my $no_print   = $opt->{no_print};
   my $find_dump  = $opt->{find_dump};
   my $find_ls    = $opt->{find_ls};
   my $find_print = $opt->{find_print};
   my $MaxDepth   = $opt->{MaxDepth};
   my $MaxCount   = $opt->{MaxCount};
   my $Enrich     = $opt->{Enrich} || $find_ls;

   # compile Exps into package TPSUP::Expression (namespace)
   my $MatchExps;
   if ( $opt->{MatchExps} && @{ $opt->{MatchExps} } ) {
      $MatchExps = TPSUP::UTIL::compile_perl_array( $opt->{MatchExps} );
   }

   print STDERR "MatchExps=", Dumper($MatchExps) if $verbose;

   my $Handlers;
   if (  $opt->{HandleExps}
      && @{ $opt->{HandleExps} }
      && $opt->{HandleActs}
      && @{ $opt->{HandleActs} } )
   {

      my $exps = TPSUP::UTIL::compile_perl_array( $opt->{HandleExps} );
      my $acts = TPSUP::UTIL::compile_perl_array( $opt->{HandleActs} );

      $Handlers = TPSUP::UTIL::transpose_arrays(
         [ $exps, $acts, $opt->{HandleExps}, $opt->{HandleActs} ], $opt );
   }

   my $FlowControl;
   if (  $opt->{FlowExps}
      && @{ $opt->{FlowExps} }
      && $opt->{FlowDirs}
      && @{ $opt->{FlowDirs} } )
   {

      my $exps = TPSUP::UTIL::compile_perl_array( $opt->{FlowExps} );
      my $dirs = $opt->{FlowDirs};

      $FlowControl =
        TPSUP::UTIL::transpose_arrays(
         [ $exps, $dirs, $opt->{FlowExps}, $opt->{FlowDirs} ], $opt );
   }

   # no_print is used to suppress printing the path, for example,
   # when another function calls tpfind() to get a list of files.
   if ( !$no_print ) {

      # find_print is the default way of print
      $find_print = $find_print
        || (!$find_dump
         && !$find_ls
         && !$Handlers
         && !$FlowControl );
   }

   my $ret = { error => 0, count => 0, hashes => [] };

   # start - function inside function
   my $tpfind_print = sub {
      my $r = shift;

      if ($find_dump) {
         print Dumper($r);
      } elsif ($find_ls) {
         print
"$r->{mode_oct} $r->{owner} $r->{group} $r->{size} $r->{mt_string} $r->{path}\n";
      } elsif ($find_print) {
         print "$r->{path}\n";
      }
   };

   my $now = time();

   my $process_node = sub {
      my $path = shift;

      my $result = {};

      if ( $verbose > 1 ) {
         print "process_node() is checking $path\n";
      }

      my $type =
          ( -f $path ) ? 'file'
        : ( -d $path ) ? 'dir'
        : ( -l $path ) ? 'link'
        :                'unknown';

      my (
         $dev,  $ino,   $mode,  $nlink, $uid,     $gid, $rdev,
         $size, $atime, $mtime, $ctime, $blksize, $blocks
      ) = lstat($path);

      my $user = TPSUP::UTIL::get_user_by_uid($uid);
      $user = $uid if !$user;

      my $group = TPSUP::UTIL::get_group_by_gid($gid);
      $group = $gid if !$group;

      my $short = $path;
      $short =~ s:.*/::;

      my $r;

   # mystery: for some reason, 'user' cannot be used in the expresssion. changed
   # to use 'owner' instead
   # @{$r}{qw(path type mode uid gid size mtime user group now)}
   #  = ($path, $type, $mode, $uid, $gid, $size, $mtime, $user, $group, $now);

      @{$r}{
         qw(path    type   mode   uid   gid   size   mtime   owner  group   now   short)
        } = (
         $path,  $type, $mode,  $uid, $gid, $size,
         $mtime, $user, $group, $now, $short
        );

      $r->{mode_oct} = sprintf(
         "%04o", $mode    #& 07777
      );

      if ($Enrich) {
         my ( $sec, $min, $hour, $mday, $mon, $year, $wday, $yday, $isdst ) =
           localtime($mtime);
         $r->{mt_string} = sprintf(
            "%04d%02d%02d-%02d:%02d:%02d",
            $year + 1900,
            $mon + 1, $mday, $hour, $min, $sec
         );
         $r->{mt_yyyymmdd} =
           sprintf( "%04d%02d%02d", $year + 1900, $mon + 1, $mday );
      }

      print "r=", Dumper($r) if $verbose > 1;

      if ( $Handlers || $FlowControl || $MatchExps ) {

         TPSUP::Expression::export_var( $r, { RESET => 1 } );

#TPSUP::Expression::dump_var(); # I can see 'user' was populated even at this step

         if ($verbose) {
            $TPSUP::Expression::verbose = 1;
         }
      }

      if ($FlowControl) {
         for my $row (@$FlowControl) {
            my ( $match, $direction, $match_code, $direction_code ) = @$row;

            if ( $match->() ) {
               if ($verbose) {
                  print STDERR "flow exp matched: $match_code\n",
                    "flow direction: $direction_code\n";
               }

               if ( $direction eq 'prune' ) {
                  $result->{direction} = 'prune';
                  next;
               } elsif ( $direction eq 'exit' ) {
                  $result->{direction} = 'exit';
                  return $result;
               } else {
                  croak "unknown FlowControl driection='$direction'";
               }
            }
         }
      }

      my $count_path = 1;

      if ($Handlers) {
         $count_path = 0;
       ROW:
         for my $row (@$Handlers) {
            my ( $match, $action, $match_code, $action_code ) = @$row;

            if ( $match->() ) {
               $count_path = 1;
               if ($verbose) {
                  print STDERR "handler exp matched: $match_code\n",
                    "handler action:  $action_code\n";
               }
            } else {
               next ROW;
            }

            if ( !$action->() ) {
               print STDERR "ERROR: action failed at path=$path\n";
               $result->{error}++;
            }
         }
      }

      if ($MatchExps) {
         $count_path = 0;

         # MatchExps doesn't affect flow control;
         # it only affects whether to count or print the path
         # therefore, we put this after FlowControl
         my $match_all = 1;
         for my $i ( 0 .. $#$MatchExps ) {
            my $match = $MatchExps->[$i];
            my $code  = $opt->{MatchExps}->[$i];

            if ( $match->() ) {
               if ($verbose) {
                  print STDERR "matched: $code\n";
               }
            } else {
               $match_all = 0;
               last;
            }
         }
         if ( !$match_all ) {
            return $result;
         } else {
            $count_path = 1;
         }
      }

      if ($count_path) {
         push @{ $ret->{hashes} }, $r;
         $ret->{count}++;
         $tpfind_print->($r);
      }

      return $result;
   };

   # end - function inside function

   my @globbed_paths = tpglob( $paths, $opt );

   my @pathLevels;
   for my $path (@globbed_paths) {
      my $pathLevel = [ $path, 0 ];
      push @pathLevels, $pathLevel;
   }

   my %seen;

   while ( my $pathLevel = shift @pathLevels ) {
      if ($MaxCount) {
         last if $ret->{count} >= $MaxCount;
      }
      my ( $path, $level ) = @$pathLevel;
      my $result = $process_node->($path);
      if ( exists $result->{direction} ) {
         if ( $result->{direction} eq 'prune' ) {
            next;
         } elsif ( $result->{direction} eq 'exit' ) {
            return $ret;
         }
      }

      next if defined($MaxDepth) && $level >= $MaxDepth;

      if ( -d $path ) {
         opendir( DIR, $path ) or die "Cannot open $path\n";
         my @shorts = readdir(DIR);
         closedir(DIR);
         for my $short (@shorts) {
            next
              if $short eq '.'
              || $short eq '..'
              || $short eq '.git'
              || $short eq '.snapshot'
              || $short eq '.idea'
              || $short eq '.vscode'
              || $short eq '__pycache__';

            my $path2 = "$path/$short";
            next if $seen{$path2};
            $seen{$path2} = 1;

            my $pathLevel = [ $path2, $level + 1 ];
            push @pathLevels, $pathLevel;

         }
      }
   }

   return $ret;
}

sub main {
   require TPSUP::TEST;

   # use 'our' in test code, not 'my'
   my $test_code = <<'END';
        TPSUP::FILE::tpglob( "non-exist-file" );
        our $TPSUP = $ENV{TPSUP};
        our $files = "$TPSUP/python3/lib/tpsup/searchtools_test*";
        TPSUP::FILE::tpglob([$files]);
        TPSUP::FILE::sorted_files_by_mtime($files);
        TPSUP::FILE::sorted_files_by_mtime($files, {reverse=>1});
        ${TPSUP::FILE::get_latest_files($files)}[0];     # convert result to array
        @{TPSUP::FILE::get_latest_files($files) }[0..1]; # slice
END

   TPSUP::TEST::test_lines($test_code);
}

main() unless caller();

###################################################################
package TPSUP::Expression;

no strict 'refs';

# the following causes error.
# use TPSUP::FILE qw(get_in_fh close_in_fh);

our $path;

sub getline {
   my ($opt) = @_;

   my $ifh = TPSUP::FILE::get_in_fh( $path, $opt );
   my $count;
   my $ret_type;
   if ( defined $opt->{count} ) {
      $count    = $opt->{count};
      $ret_type = 'array';
   } else {
      $count    = 1;
      $ret_type = 'scalar';
   }

   my @lines;
   my $i = 0;
   while ( my $line = <$ifh> ) {
      chomp $line;
      push @lines, $line;

      $i++;
      last if $i >= $count;
   }
   TPSUP::FILE::close_in_fh($ifh);

   if ( $ret_type eq 'array' ) {
      return @lines;
   } else {
      return $lines[0];
   }
}

1
