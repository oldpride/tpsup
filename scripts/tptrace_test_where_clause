#!/bin/bash

# this wrapper is to shorten command line, so that instead of
#    tpbatch tpslnm_test_batch.cfg ...
# we can type
#    tpslnm_test ...
# to archive this
#    ln -s tpbatch_generic.bash tpslnm_test

# however: symbolic link doesn't work well on windows, cygwin or gitbash.
#          therefore, we had to use hard copy.

# set -x

# use double quotes to enclose path so that path like /c/Program Files/... will be protected
prog=$(basename "$0")
dir=$(dirname "$0")

UNAME=$(uname -a)

types="batch trace"
for type in $types; do
   if [ -f "$dir/${prog}_${type}.cfg" ]; then
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
   cfg=$(cygpath --windows "$dir/${prog}_${type}.cfg")
   cmd=$(which tp${type})
   cmd=$(cygpath --windows "$cmd")
   perl "$cmd" "$cfg" -c $prog "$@"
else
   cfg="$dir/${prog}_${type}.cfg"
   tp${type} "$cfg" -c $prog "$@"
fi
