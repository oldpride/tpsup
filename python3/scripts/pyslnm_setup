#!/bin/bash

# this wrapper is to shorten command line, so that instead of
#    tpbatch.py pyslnm_test_cfg.py ...
# we can type
#    pyslnm_test ...
# to archive this
#    ln -s tpbatch_py_generic.bash pyslnm_test

# however: symbolic link doesn't work well on windows, cygwin or gitbash.
#          therefore, we had to use hard copy. see Makefile in this folder.


# set -x

# use double quotes to enclose path so that path like /c/Program Files/... will be protected
prog=`basename "$0"`
dir=`dirname "$0"`

UNAME=`uname -a`

if [[ "$UNAME" =~ Cygwin ]]; then
   cfg=`cygpath --windows "$dir/${prog}_cfg.py"`
   cmd=`which tpbatch.py`
   cmd=`cygpath --windows "$cmd"`
   python "$cmd" "$cfg" -c $prog "$@"
else
   cfg="$dir/${prog}_cfg.py"
   tpbatch.py "$cfg" -c $prog "$@"
fi


