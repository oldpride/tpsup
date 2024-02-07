#!/bin/bash
#
# gitbash and cygwin cannot use symbolic link reliablely. so we make hard copies.
# this script is to be run when 'make' is not available, eg, in company cygwin or gitbash

prog=$(basename $0)

usage() {
   msg=$1

   [ "X$msg" = "X" ] || echo >&2 "ERROR: $msg"

   cat >&2 <<END
usage:

   $prog pattern
   $prog all
   
   'all' covers all *_linktool.cfg
   
   -v         verbose mode
   -n        dry run

   background: gitbash and cygwin cannot use symbolic link reliablely. so we make hard copies.
   if our program only runs on linux, we could have used symbolic link.

examples:

   $prog all

END
   exit 1
}

verbose=N
dryrun=N

while getopts vn o; do
   case "$o" in
   v) verbose=Y ;;
   n) dryrun=Y ;;
   # m) pattern="$OPTARG" ;;
   *)
      echo "unknow switch '$o'"
      usage
      ;;
   esac
done

shift $((OPTIND - 1))

if [ $# -ne 1 ]; then
   usage "wrong number of args"
fi

pattern=$1

if [ $pattern = all ]; then
   cfgs=`ls *_linktool.cfg`
else
   cfgs=`ls *_linktool.cfg | grep "$pattern"`
fi

for cfg in $(echo $cfgs); do
   link_source=`( . "$cfg"; echo "$link_source")`
   if ! [ -f "$link_source" ]; then
      echo "ERROR: $cfg, link_source=$link_source, not found"
      continue
   fi

   link_target=`echo $cfg |sed 's:_linktool.cfg::'`

   if [ $verbose = Y ]; then
      echo "link_source=$link_source, link_target=$link_target"
      /bin/ls -U -l "$link_source" "$link_target"
   fi

   if [ "$link_target" -nt "$link_source" ]; then
      echo "$link_target is newer than $link_source, no need to update"
      continue
   else
      echo "updating $link_target"
      if [ $dryrun = N ]; then
         (set -x; /bin/rm -f "$link_target"; /bin/cp -f "$link_source" "$link_target")
      else 
         echo "dryrun: /bin/rm -f $link_target; /bin/cp -f $link_source $link_target"
      fi 
   fi
done