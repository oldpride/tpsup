package TPSUP::TEST;

use strict;
use warnings;
use Carp;
use Data::Dumper;

use base qw( Exporter );
our @EXPORT_OK = qw(
  test_lines
);

sub process_block {
    my ( $block, $opt ) = @_;
    my $verbose = $opt->{verbose};

    my @lines = split /\n/, $block;
    for my $line (@lines) {
        next if $line =~ /^\s*$/;
        next if $line =~ /^\s*#/;

        $line =~ s/^\s+//;   # remove leading spaces
        print "eval: $line\n";
        my $code = "package DUMMY; no strict; $line";
        print "eval $code\n" if $verbose;
        my $result = eval $code;
        if ($@) {
            print "eval error: $@\n";
        }

        if (!$opt->{not_show_result}) {
            print "result: $result\n";
        }
    }
}

sub test_lines {
    my ( $block, $opt ) = @_;

    $opt = {} unless $opt;

    my $pre_code = $opt->{pre_code};
    if ($pre_code) {
        process_block($pre_code, {%$opt, not_show_result=>1});
    }

    process_block($block, $opt);
}

sub main {

  # var declared using "our" which is global to the package. "my" will not work.
    my $pre_code = <<END;
        our \$a = 1;
        our \$b = "hello";
END

    my $test_code = <<'END';
        $a+1;
        $b;
END

    test_lines( $test_code, { pre_code => $pre_code } );
}

main() unless caller;

1
