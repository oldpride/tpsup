#!/bin/bash

# this wrapper is to shorten command line, so that instead of
#    tptrace trace_myapp.cfg ...
# we can type
#    trace_myapp ...
# for this, do 
#    ln -s tptrace_generic trace_myapp


prog=`basename $0`
dir=`dirname $0`

tptrace $dir/$prog_trace.cfg -c $prog  "$@" 
