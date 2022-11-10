#!/bin/bash

usage () {
   cat >&2 <<EOF
usage:

   $0 ref_yyyymmdd +day
   $0 ref_yyyymmdd -day

example:

   $0 20201231 +1
   $0 20201231 +0
   $0 20201231 -1

EOF

   exit 1
}

if [ $# -ne 2 ]; then
   echo "wrong number of args" >&2
   usage
fi

date -d "$1 $2 day" "+%Y%m%d"
