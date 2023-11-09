package TPSUP::FILE;

use strict;
use warnings;

use base qw( Exporter );
our @EXPORT_OK = qw(
  tpglob
);

use Carp;
use Data::Dumper;

sub tpglob {
    my ( $pattern, $flags ) = @_;

    my @patterns;
    my $type = ref($pattern);
    if ( !$type ) {

        # scalar
        @patterns = split /\s+/, $pattern;
    }
    elsif ( $type eq 'ARRAY' ) {

        # array
        @patterns = @$pattern;
    }
    else {
        croak "tpglob: pattern must be scalar or array";
    }

    my @files;
    for my $p (@patterns) {
        my @files2 = glob($p);
        if (@files2) {
            push @files, @files2;
        }
        else {
            print STDERR "tpglob: no file matches pattern '$p'\n";
        }
    }

    # print "tpglob: files=", Dumper( \@files );
    return @files;
}

sub sorted_files {
    my ( $files, $opt ) = @_;

    my $globbed   = $opt->{globbed};
    my $reverse   = $opt->{reverse};
    my $sort_func = $opt->{sort_func};

    my @files2;
    if ( !$globbed ) {
        @files2 = tpglob( $files, $opt );
    }
    else {
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
        $mtime_by_file->{$file} = ( stat($file) )[9];
    }

    return $mtime_by_file->{$file};
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

    my $opt2 = $opt ? $opt : {};
    my @sorted_files =
      sorted_files_by_mtime( $files, { %$opt2, reverse => 1 } );
    return \@sorted_files;
}

sub main {

    use TPSUP::TEST qw(test_lines);

    # TPSUP = os.environ.get('TPSUP')
    # files1 = f'{TPSUP}/python3/scripts/ptgrep_test*'
    # files2 = f'{TPSUP}/python3/lib/tpsup/searchtools_test*'

    # use 'our' in test code, not 'my'
    my $test_code = <<'END';
        our $TPSUP = $ENV{TPSUP};
        our $files = "$TPSUP/python3/lib/tpsup/searchtools_test*";
        TPSUP::FILE::tpglob([$files]);
        TPSUP::FILE::sorted_files_by_mtime($files);
        TPSUP::FILE::sorted_files_by_mtime($files, {reverse=>1});
        ${TPSUP::FILE::get_latest_files($files)}[0];     # array from result
        @{TPSUP::FILE::get_latest_files($files) }[0..1]; # slice
END

    test_lines($test_code);
}

main() unless caller();

1
