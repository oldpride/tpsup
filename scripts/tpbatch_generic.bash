#!/bin/bash

# this wrapper is to shorten command line, so that instead of
#    tpbatch tpslnm_test.cfg ...
# we can type
#    tpslnm_test ...
# to archive this
#    ln -s tpbatch_generic.bash tpslnm_test

prog=`basename $0`
dir=`dirname $0`

tpbatch $dir/$prog.cfg -c $prog "$@" 
