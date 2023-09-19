#!/bin/bash

# this wrapper is to shorten command line, so that instead of
#    ptbatch.py pyslnm_test_cfg_batch.py ...
# we can type
#    pyslnm_test ...
# to archive this
#    ln -s ptbatch_py_generic.bash pyslnm_test

# however: symbolic link doesn't work well on windows, cygwin or gitbash.
#          therefore, we had to use hard copy. see Makefile in this folder.

# set -x

# use double quotes to enclose path so that path like /c/Program Files/... will be protected
prog=$(basename "$0")
dir=$(dirname "$0")

UNAME=$(uname -a)

types="batch trace"
for type in $types; do
   if [ -f "$dir/${prog}_cfg_${type}.py" ]; then
      if [ "X$seen_type" != "X" ]; then
         echo "ERROR: found multiple cfg files for $prog: $seen_type and $type"
         exit 1
      else
         seen_type=$type
      fi
   fi
done

type=$seen_type

if [[ "$UNAME" =~ Cygwin ]]; then
   cfg=$(cygpath --windows "$dir/${prog}_cfg_${type}.py")
   cmd=$(which pt${type}.py)
   cmd=$(cygpath --windows "$cmd")
   python "$cmd" "$cfg" -c $prog "$@"
else
   cfg="$dir/${prog}_cfg_${type}.py"
   pt${type}.py "$cfg" -c $prog "$@"
fi
