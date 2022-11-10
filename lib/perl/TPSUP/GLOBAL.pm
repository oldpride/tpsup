package TPSUP::GLOBAL;

# provide a name space for global vars for complicated calling between modules

use base qw( Exporter );
our @EXPORT_OK = qw($we_return);

use strict;
use warnings;

# 'return' in eval will only return to eval, not to the caller sub.
# in order to return the caller sub, we use the following var, which
# can be modified by eval.
our $we_return;

1
