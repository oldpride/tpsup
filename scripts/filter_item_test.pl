#!/usr/bin/env perl

use TPSUP::FIX qw(get_fixname_by_tag);
$pass_item = sub {
    my ($item) = @_;
    return get_fixname_by_tag($item);
};

