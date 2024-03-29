package TPSUP::GREP;

use strict;
use warnings;

use base qw( Exporter );
our @EXPORT_OK = qw(
  tpgrep
);

use Carp;
use Data::Dumper;

use TPSUP::FILE qw(
  get_in_fh
  close_in_fh
  tpglob
  tpfind
);

use TPSUP::SEARCH qw(
  binary_search_first
);

sub tpgrep {
   my ( $files, $opt ) = @_;

   my $FileNameOnly    = $opt->{FileNameOnly};
   my $Recursive       = $opt->{Recursive};
   my $MaxDepth        = $opt->{MaxDepth};
   my $verbose         = $opt->{verbose} || 0;
   my $FindFirstFile   = $opt->{FindFirstFile};
   my $PrintCount      = $opt->{PrintCount};
   my $print_output    = $opt->{print_output};
   my $CaseInsensitive = $opt->{CaseInsensitive};

   if ( !$Recursive ) {
      $MaxDepth = 0;
   }

   my $found = tpfind(
      $files,
      {
         %$opt,
         no_print  => 1,
         MaxDepth  => $MaxDepth,
         MatchExps => ['$type ne "dir"']
      }
   );

   my @files2 = map { $_->{path} } @{ $found->{hashes} };

   my $print_filename = 1 if @files2 > 1;

   my $MatchPatterns = $opt->{MatchPatterns} ? $opt->{MatchPatterns} : [];
   my $ExcludePatterns =
     $opt->{ExcludePatterns} ? $opt->{ExcludePatterns} : [];

   if ( !$opt->{MatchPatterns} && $opt->{MatchPattern} ) {
      $MatchPatterns = [ $opt->{MatchPattern} ];
   }

   if ( !$opt->{ExcludePatterns} && $opt->{ExcludePattern} ) {
      $ExcludePatterns = [ $opt->{ExcludePattern} ];
   }

   my @MatchCompiled;
   my @ExcludeCompiled;
   for my $p (@$MatchPatterns) {
      if ($CaseInsensitive) {
         $p = "(?i)$p";    # case-insensitive
      }
      push @MatchCompiled, qr/$p/;
   }

   for my $p (@$ExcludePatterns) {
      if ($CaseInsensitive) {
         $p = "(?i)$p";    # case-insensitive
      }
      push @ExcludeCompiled, qr/$p/;
   }

   usage("at least one of -m and -x must be specified")
     if !@MatchCompiled && !@ExcludeCompiled;

   my @lines2;

   # start - function inside a function
   # https://stackoverflow.com/questions/25399728
   my $grep_1_file = sub {
      my ($file) = @_;
      my @lines;

      my $tf = get_in_fh( $file, $opt );

      while ( my $line = <$tf> ) {
         if ( $verbose > 2 ) {
            print STDERR "line=$line\n";
         }

         if (@MatchCompiled) {
            my $all_matched = 1;
            for my $p (@MatchCompiled) {
               if ( $line !~ /$p/ ) {
                  $all_matched = 0;
                  last;
               }
            }
            if ( !$all_matched ) {
               next;
            }
         }

         if (@ExcludeCompiled) {
            my $to_exclude = 0;
            for my $p (@ExcludeCompiled) {
               if ( $line =~ /$p/ ) {
                  $to_exclude = 1;
                  last;
               }
            }
            if ($to_exclude) {
               next;
            }
         }

         if ($FileNameOnly) {
            push @lines, $file;
            if ( $opt->{print_output} ) {
               print "$file\n";
            }
            last;
         }

         if ($print_filename) {
            push @lines, "$file:$line";
            if ($print_output) {
               print "$file:$line";
            }
         } else {
            push @lines, $line;
            if ($print_output) {
               print $line;
            }
         }
      }

      return \@lines;
   };

   # end of $grep_1_file->()
   # end - function inside a function

   if ($FindFirstFile) {
      my $grep2 = sub {
         my ($f) = @_;
         my $lines = $grep_1_file->($f);
         return scalar(@$lines);
      };

      my $index = binary_search_first( \@files2, $grep2 );
      return $files2[$index];
   } else {
      my %seen_file;
      for my $file (@files2) {
         if ( $seen_file{$file} ) {
            if ($verbose) {
               print STDERR "file=$file already seen. skip\n";
            }
            next;
         } else {
            $seen_file{$file} = 1;
         }

         my $match = $grep_1_file->($file);
         push @lines2, @$match;
      }

      return \@lines2;
   }
}

sub main {
   use TPSUP::TEST qw(test_lines);

   # TPSUP = os.environ.get('TPSUP')
   # files1 = f'{TPSUP}/python3/scripts/ptgrep_test*'
   # files2 = f'{TPSUP}/python3/lib/tpsup/searchtools_test*'
   my $TPSUP  = $ENV{TPSUP};
   my $files1 = "$TPSUP/python3/scripts/ptgrep_test*";
   my $files2 = "$TPSUP/python3/lib/tpsup/searchtools_test*";

   my $test_code = <<'END';
      our $TPSUP  = $ENV{TPSUP};
      our $files1 = "$TPSUP/python3/scripts/ptgrep_test*";
      our  $files2 = "$TPSUP/python3/lib/tpsup/searchtools_test*";
      TPSUP::GREP::tpgrep($files1, { MatchPattern => 'Mypattern', CaseInsensitive => 1 });
      TPSUP::GREP::tpgrep($files1, { ExcludePattern => 'abc|def' });
      TPSUP::GREP::tpgrep($files2, { MatchPattern => 'bc', FindFirstFile => 1 });
      TPSUP::GREP::tpgrep( $files2, { MatchPattern => 'bc', FindFirstFile => 1, sort_name=>'mtime' } );

END

   test_lines($test_code);
}

main() unless caller();

1
