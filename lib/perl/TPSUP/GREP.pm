package TPSUP::GREP;

use strict;
use warnings;

use base qw( Exporter );
our @EXPORT_OK = qw(
  grep
);

use Carp;
use Data::Dumper;

use TPSUP::UTIL qw(
  get_in_fh
  close_in_fh
);

sub grep {
    my ( $files, $opt ) = @_;

    my $MatchPatterns = $opt->{MatchPatterns} ? $opt->{MatchPatterns} : [];
    my $ExcludePatterns =
      $opt->{ExcludePatterns} ? $opt->{ExcludePatterns} : [];

    if ( !@$opt->{MatchPatterns} && $opt->{MatchPattern} ) {
        $MatchPatterns = [ $opt->{MatchPattern} ];
    }

    if ( !@$opt->{ExcludePatterns} && $opt->{ExcludePattern} ) {
        $ExcludePatterns = [ $opt->{ExcludePattern} ];
    }

    my @CompiledMatch;
    my @CompiledExclude;
    for my $p (@$MatchPatterns) {
        push @CompiledMatch, qr/$p/;
    }

    for my $p (@$ExcludePatterns) {
        push @CompiledExclude, qr/$p/;
    }

    my $FileNameOnly   = $opt->{FileNameOnly};
    my $Recursive      = $opt->{Recursive};
    my $verbose        = $opt->{verbose};
    my $FindFirstFile  = $opt->{FindFirstFile};
    my $PrintCount     = $opt->{PrintCount};
    my $print_filename = $opt->{print_filename};

    usage("at least one of -m and -x must be specified")
      if !@CompiledMatch && !@CompiledExclude;

    # https://stackoverflow.com/questions/25399728
    my $grep_1_file = sub {
        my ($file) = @_;
        my @lines;

        my $tf = get_inf_fh( $file, $opt );

        while ( my $line = <$tf> ) {
            if ( $verbose > 2 ) {
                print STDERR "line=$line\n";
            }

            if (@CompiledMatch) {
                my $all_matched = 1;
                for my $p (@CompiledMatch) {
                    if ( $line !~ /$p/ ) {
                        $all_matched = 0;
                        last;
                    }
                }
                if ( !$all_matched ) {
                    next;
                }
            }

            if (@CompiledExclude) {
                my $to_exclude = 0;
                for my $p (@CompiledExclude) {
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
            }
            else {
                push @lines, $line;
                if ( $opt->{print_output} ) {
                    print $line;
                }
            }
        }

        return \@lines;
    };

    for my $path (@$files) {
        my @files;
        if ($Recursive) {
            @files = `find $path -type f|sort`;
            chomp @files;
        }
        else {
            @files = ($path);
        }

        for my $f (@files) {
            $verbose && print STDERR "scanning file=$f\n";
            my $matched = $grep_1_file->($f);
        }
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
        our @arr = (1, 2,  4,  10, 12); # use "our" to make it global. "my" will not work.
        TPSUP::SEARCH::binary_search_match(\@arr, 10, sub { $_[0] <=> $_[1] });
        TPSUP::SEARCH::binary_search_first(\@arr, sub { $_[0] >= 4 });
END

    test_lines($test_code);
}

main() unless caller();

1
