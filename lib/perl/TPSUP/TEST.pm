package TPSUP::TEST;

use strict;
use warnings;
use Carp;
use Data::Dumper;

use base qw( Exporter );
our @EXPORT_OK = qw(
    test_lines
);


sub test_lines {
    my ($block, $opt) = @_;

    my $pre_code = $opt->{pre_code};
    if ($pre_code) {
        my @lines = split /\n/, $pre_code;
        for my $line (@lines) {
            next if $line =~ /^\s*$/;
            next if $line =~ /^\s*#/;
            my $code = "package TPSUP::DUMMY; $line";
            print "eval $code\n";
            eval $code;
        }
    }

    my @lines = split /\n/, $block;

    for my $line (@lines) {
        next if $line =~ /^\s*$/;
        next if $line =~ /^\s*#/;

        
        my $code = "package TPSUP::DUMMY; $line";
        print "eval $code\n";
        my $result = eval $code;
        if ($@) {
            print "eval error: $@\n";;
        }
        print "result=$result\n";
    }
}

sub main {

    my $pre_code = <<'END';
        our $a = 1;
END

    my $test_code = <<'END';
        
        # $a = 100;
        $a+1;
        $a+2;
END

    test_lines($test_code, {pre_code=>$pre_code});
}

main() unless caller;

1