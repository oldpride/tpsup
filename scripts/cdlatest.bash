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

   -d                  debug mode.

   -b number           search backward for this number of dir, or as backward as possible.
                       default number is 0, ie, the latest one.
                       NOTE: this only works on the yyyymmdd* subdirs.


example:

   # set up test dirs
   cdlatest_setup_test.bash

   # test default, should see /home/tian/testcd/20210203_test
   $prog ~/testcd

   # test matching, should see /home/tian/testcd/20210203_app1
   $prog -m app1 ~/testcd

   # test excluding, should see /home/tian/testcd/20210203_app1
   $prog -x test ~/testcd

   # looking backward (or older) 1, should see /home/tian/testcd/20210202_app1
   $prog -m app1 -b 1 ~/testcd

   # test yyyy/mm/dd structure, should see /home/tian/testcd/app1/2021/02/06
   $prog ~/testcd/app1

   # test backward (or older) 2, should still see /home/tian/testcd/app1/2021/02/06
   # because backward doesn't work for yyyy/mm/dd structure
   $prog -b 2 ~/testcd/app1

EOF

   exit 1
}

debug=N
match="."
exclude="__NO_PATTERN__"
backward=0

while getopts b:c:m:t:dx: o;
do
   case "$o" in
      b) backward="$OPTARG";;
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

tailcount=`expr 1 + $backward`

parent_dir=$1

[ $debug = Y ] && set -x

cd $parent_dir || exit 1

while :
do
    # yyyymmdd+proj-style dir has highest precedence
    # eg, 20210806_app1
    #     2021-08-06-app1
    subdir=`/bin/ls -1 -d [12][09][0-9][0-9][01][0-9][0-3][0-9]*/ [12][09][0-9][0-9]-[01][0-9]-[0-3][0-9]*/ 2>/dev/null |egrep "$match"|egrep -v "$exclude" | tail -$tailcount | head -n 1`
    if [ "X$subdir" != "X" ]; then
       cd $subdir
       continue
    fi

    # next is yyyymmdd. we can still apply backward search. 
    # They are numeric, therefore we cannot apply match patterns
    subdir=`/bin/ls -1 -d [12][09][0-9][0-9][01][0-9][0-3][0-9]/ [12][09][0-9][0-9]-[01][0-9]-[0-3][0-9]/ 2>/dev/null |tail -$tailcount | head -n 1`
    if [ "X$subdir" != "X" ]; then
       cd $subdir
       continue
    fi

    # next is yyyy/mm/dd structure. Because they are multiple levels, there is no good way
    # to search backward. Therefore, search-backward feature is gone here.
    subdir=`/bin/ls -1 -d [12][09][0-9][0-9]/ [01][0-9]-[0-3][0-9]/ [0-3][0-9]/ 2>/dev/null|tail -1`
    if [ "X$subdir" != "X" ]; then
       cd $subdir
       continue
    fi

    # for non-dated dir, if there is only one subdir after filtering, we choose it
    subdirs=`/bin/ls -1 -d */ 2>/dev/null|egrep "$match"|egrep -v "$exclude"` 
    subdir_count=`echo "$subdirs"|wc -l` 

    if [ "X$subdirs" = "X" ]; then
       # [ $subdir_count -eq 0 ] will never be true because `echo ""|wc -l` is actually 1, not 0.
       # therefore, we use the above test
       break
    elif [ $subdir_count -eq 1 ]; then
       cd $subdirs
       continue
    elif [ $subdir_count -gt 1 ]; then
       # more than one subdirs, and none are dated, we don't know which to choose
       break
    fi
done

set +x

pwd
