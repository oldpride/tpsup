#!/bin/bash

usage () {
   cat >&2 <<EOF
usage:

   $0 yyyymmdd
 
find day of week of a particular day

example:

   $0 20201231
EOF

   exit 1
}

if [ $# -ne 1 ]; then
   echo "wrong number of args" >&2
   usage
fi

date -d "$1" "+%A"
