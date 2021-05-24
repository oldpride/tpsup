#!/bin/bash

prog=`basename $0`

usage () {
   cat >&2 <<EOF
usage:

   $prog parent_dir

   try to cd to a latest folder under parent_dir, try to go as deep as possible
      - if there is only one subfolder, cd under it
      - if there are yyyymmdd* folders, cd under the latest one

   -m match_pattern    only nickname matching this pattern, egrep regex
   -x exclude_pattern  exclude nickname matching this pattern, egrep regex
   -d                  debug mode


example:

   $prog /media/sdcard/LCA

EOF

   exit 1
}

debug=N
match="."
exclude="__NO_PATTERN__"

while getopts c:m:t:dx: o;
do
   case "$o" in
      m) match="$OPTARG";;
      x) exclude="$OPTARG";;
      d) debug=Y;;
      *) echo "unknow switch '$o'"; usage;;
   esac
done

shift $((OPTIND-1))

if [ $# -ne 1 ]; then
   echo "wrong number of args" >&2
   usage
fi

parent_dir=$1

[ $debug = Y ] && set -x

cd $parent_dir || exit 1

while :
do
    subdirs=`/bin/ls -1 -d */ 2>/dev/null|egrep "$match"|egrep -v "$exclude"` 
    subdir_count=`echo -n "$subdirs" |wc -l`

    if [ $subdir_count = 0 ]; then 
       break
    fi

    if [ $subdir_count = 1 ]; then
       cd $subdirs
       continue
    fi

    latest_dated_dir=`/bin/ls -1 -d 20[0-9][0-9][0-9][0-9][0-9][0-9]*/ 2>/dev/null|egrep "$match"|egrep -v "$exclude"|tail -1`
    if [ "X$latest_dated_dir" != X ]; then
       cd $latest_dated_dir || exit 1
       continue
    else
       break
    fi
done

set +x

pwd
