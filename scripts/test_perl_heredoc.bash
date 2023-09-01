#!/bin/bash

export code="`cat $TPSUP/scripts/delpath`"

perl -e "$code" -- -v tpsup "$PATH"

exit 0;

# heredoc cannot take command arg
/usr/bin/perl <<END
$code
END
