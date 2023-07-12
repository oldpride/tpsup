#!/bin/bash

# this a wrapper set up env all the way to venv.
# it is used in cron job.

prog_task=$(basename "$0")
dir=$(dirname "$0")

prog=${prog_task%_task} # remove _task from prog_task

UNAME=$(uname -a)

# this didn't work
#    siteenv
# script cannot see the function inside the env that outside the script. unless
#    - set -a (before defining the function?)
#    - export -f funciton_name (after defining the function)

# so the first thing is to source the env
if [ "X$SITESPEC" = "X" ]; then
   echo "ERROR: env is not set. run 'siteenv' first."
   exit 1
fi

. $SITESPEC/profile
p3env
svenv

"$dir/$prog" "$@"

dvenv
