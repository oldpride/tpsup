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
);

use TPSUP::SEARCH qw(
  binary_search_first
);

sub tpgrep {
   my ( $files, $opt ) = @_;

   my $FileNameOnly   = $opt->{FileNameOnly};
   my $Recursive      = $opt->{Recursive};
   my $verbose        = $opt->{verbose} || 0;
   my $FindFirstFile  = $opt->{FindFirstFile};
   my $PrintCount     = $opt->{PrintCount};
   my $print_filename = $opt->{print_filename};

   my @files2 = tpglob( $files, $opt );

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
      push @MatchCompiled, qr/$p/;
   }

   for my $p (@$ExcludePatterns) {
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
            if ( $opt->{print_output} ) {
               print "$file:$line";
            }
         } else {
            push @lines, $line;
            if ( $opt->{print_output} ) {
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
      for my $path (@files2) {
         my @files;
         if ($Recursive) {
            @files = `find $path -type f|sort`;
            chomp @files;
         } else {
            @files = ($path);
         }

         for my $f (@files) {
            $verbose && print STDERR "scanning file=$f\n";
            my $matched = $grep_1_file->($f);
            push @lines2, @$matched;
         }
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
        TPSUP::GREP::tpgrep($files1, { MatchPattern => 'mypattern' });
      #   grep($files1, { ExcludePattern => 'abc|def' });
      #   grep($files2, { MatchPattern => 'bc', FindFirstFile => 1 });
END

   test_lines($test_code);
}

main() unless caller();

1
