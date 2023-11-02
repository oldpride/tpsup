package TPSUP::TEST;

use strict;
use warnings;

use base qw( Exporter );
our @EXPORT_OK = qw(
    test_lines
);


sub get_function_source {
    my ($function) = @_;
    no strict 'refs';
    my $code_ref = \&{$function};
    use strict 'refs';
    my $filename = $INC{(caller)[1]};
    open my $fh, '<', $filename or die "Could not open $filename: $!";
    my @lines = <$fh>;
    close $fh;
    my ($start, $end) = ($code_ref =~ m/\{(.*)\}/s);
    my $line_number = (caller($code_ref))[2];
    my $source = join '', @lines[$line_number + $start - 1 .. $line_number + $end - 1];
    return $source;
}


