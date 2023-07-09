#!/bin/bash

usage () {
   cat >&2 <<EOF
usage:

   $prog check
   $prog make

   make or check local venv setup

   -v    verbose

EOF

   exit 1
}


verbose=N

while getopts v o;
do
   case "$o" in
      #d) depot_dir="$OPTARG";;
      v) verbose=Y;;
      *) echo "unknow switch '$o'"; usage;;
   esac
done

shift $((OPTIND-1))

if [ $# -ne 1 ]; then
   echo "wrong number of args" >&2
   usage
fi

action=$1

. $TPSUP/profile

if [ $action = check ]; then
   cd $SITEVENV
   pwd
elif [ $action = make ]; then
   python3 -m venv $SITEVENV
else 
   echo "unknown action='$action'" >&2
   usage
fi

