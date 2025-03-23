#!/bin/bash

# this wrapper is to shorten command line, so that instead of
#    ptbatch.py ptslnm_test_cfg_batch.py ...
# we can type
#    ptslnm_test ...
# to archive this
#    ln -s ptbatch_py_generic.bash ptslnm_test

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

# check whether it is running in versbose. we will pass it to ptbatch
verbose=""
if [ "X$1" = "X-v" ]; then
   verbose="-v"
fi

if [[ "$UNAME" =~ Cygwin ]]; then
   cfg=$(cygpath --windows "$dir/${prog}_cfg_${type}.py")
   cmd=$(which pt${type}.py)
   cmd=$(cygpath --windows "$cmd")
   python "$cmd" $verbose "$cfg" -c $prog "$@"
else
   cfg="$dir/${prog}_cfg_${type}.py"
   pt${type}.py $verbose "$cfg" -c $prog "$@"
fi
