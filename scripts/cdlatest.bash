#!/bin/bash

# this script will be called by tpsup/profile

prog=`basename $0`

usage () {
   cat >&2 <<EOF
usage:

   $prog parent_dir

   try to cd to a latest folder under parent_dir, try to go as deep as possible
      - if there is only one subfolder, cd under it
      - if there are yyyymmdd* folders, cd under the latest one

   -m match_pattern    only nickname matching this pattern, egrep regex.
                       matching doesn't apply to dated subdirs.

   -x exclude_pattern  exclude nickname matching this pattern, egrep regex.
                       matching doesn't apply to dated subdirs.

   -d                  debug mode


example:

   $prog ~/backup

   # exact subdir matching
   $prog -m ^tpsup/ ~/backup

   # substring matching, mostly for exclusion
   $prog -x tpsup ~/backup

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
    subdir_count=`/bin/ls -1 -d */ 2>/dev/null|egrep "$match"|egrep -v "$exclude"|wc -l` 

    if [ $subdir_count = 1 ]; then
       subdir=`/bin/ls -1 -d */ 2>/dev/null|egrep "$match"|egrep -v "$exclude"` 
       cd $subdir
       continue
    fi

    # now we have either 0 subdirs or more than one.
    #
    # 0 subdirs may be caused by the matching criteria but we may have dated subdirs
    # which shouldn't be applied by the matchig criteria.
    #
    # now we are checking dated subdirs
    #
    # 20210524_release1
    # 2021-05-24_release2
    # 05-24
    # 0524
    # 05
    # 24
    latest_dated_dir=`/bin/ls -1 -d 20[0-9][0-9][0-9][0-9][0-9][0-9]*/ 20[0-9][0-9]-[0-9][0-9][0-9-][0-9]*/ [0-9][0-9][0-9][0-9]/ [0-9][0-9]-[0-9][0-9]/ [0-9][0-9]/ 2>/dev/null|tail -1`
    if [ "X$latest_dated_dir" != X ]; then
       cd $latest_dated_dir || exit 1
       continue
    else
       break
    fi
done

set +x

pwd
