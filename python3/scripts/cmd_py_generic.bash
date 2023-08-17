#!/bin/bash

# this wrapper is to shorten command line, so that instead of
#    python grep_cmd.py ...
# we can type
#    grep ...
# to archive this, we could have used symbolic link
# however: symbolic link doesn't work well on windows, cygwin or gitbash.
#          therefore, we had to use hard copy. see Makefile in this folder.

# set -x

# use double quotes to enclose path so that path like /c/Program Files/... will be protected
prog=$(basename "$0")
dir=$(dirname "$0")

UNAME=$(uname -a)

pyfile="$dir/${prog}_cmd.py"

if [[ "$UNAME" =~ Cygwin ]]; then
   pyfile=$(cygpath --windows "$pyfile")
   python "$pyfile" "$@"
else
   "$pyfile" "$@"
fi
