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
    my ($files, $opt) = @_;

    my $MatchPatterns   = $opt->{MatchPatterns}   ? $opt->{MatchPatterns} : [];
    my $ExcludePatterns = $opt->{ExcludePatterns} ? $opt->{ExcludePatterns} : [];

    if (!@$opt->{MatchPatterns} && $opt->{MatchPattern}) {
        $MatchPatterns = [$opt->{MatchPattern}];
    }

    if (!@$opt->{ExcludePatterns} && $opt->{ExcludePattern}) {
        $ExcludePatterns = [$opt->{ExcludePattern}];
    }

    my @CompiledMatch;
    my @CompiledExclude;
    for my $p (@$MatchPatterns) {
        push @CompiledMatch, qr/$p/;
    }

    for my $p (@$ExcludePatterns) {
        push @CompiledExclude, qr/$p/;
    }

    my $Recursive = $opt->{Recursive};
    my $verbose   = $opt->{verbose};
    my $FindFirstFile = $opt->{FindFirstFile};
    my $PrintCount = $opt->{PrintCount};

    usage("at least one of -m and -x must be specified")
        if !@CompiledMatch && !@CompiledExclude;

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
            my $fh = get_in_fh($f);

            my $count = 0;

            LINE:
            while ( my $line = <$fh> ) {
                if (@CompiledMatch) {
                    for my $p (@CompiledMatch) {
                        if ( $line !~ /$p/ ) {
                            next LINE;
                        }
                    }
                }
                if (@CompiledExclude) {
                    for my $p (@CompiledExclude) {
                        if ( $line =~ /$p/ ) {
                            next LINE;
                        }
                    }
                }

                $verbose && print STDERR "found $f: $line";
                $count++;
                if ( !$PrintCount ) {
                    last;
                }
            }

            close_in_fh($fh);
            if ($count) {
                if ($PrintCount) {
                    print "$count $f\n";
                }
                else {
                    print "$f\n";
                }
            }

        }
    }
}

sub main {
    use TPSUP::TEST qw(test_lines);

    my $test_code = <<'END';
        our @arr = (1, 2,  4,  10, 12); # use "our" to make it global. "my" will not work.
        TPSUP::SEARCH::binary_search_match(\@arr, 10, sub { $_[0] <=> $_[1] });
        TPSUP::SEARCH::binary_search_first(\@arr, sub { $_[0] >= 4 });
END

    test_lines($test_code);

}

main() unless caller();

1
