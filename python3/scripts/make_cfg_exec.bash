#!/bin/bash
#
# gitbash and cygwin cannot use symbolic link reliablely. so we make hard copies
# this script is to be run when 'make' is not available, eg, in company cygwin or gitbash

prog=`basename $0`

usage () {
   msg = $1

   [ "X$msg" = "X" ] || echo >&2 "ERROR: $msg"

   cat >&2 <<END
usage:

   $prog bash|bat
   $prog all
    
   create a wrapper script for *_cfg.py, either bash for bash on linux/cygwin/gitbash, or bat for windows.
   ideally this can be done by a symbolic link but gitbash and cygwin cannot use symbolic link reliablely. 
   so we make hard copies

   -v      verbose mode

END
   exit 1
}

verbose=N

while getopts v o;
do
   case "$o" in
      v) verbose=Y;;
      #b) backward="$OPTARG";;
      *) echo "unknow switch '$o'"; usage;;
   esac
done

shift $((OPTIND-1))

if [ $# -ne 1 ]; then
   usage "wrong number of args" 
fi

target=$1

if [ $target = all ]; then
   targets='bash bat'
elif [ $target = bash -o $target = bat ]; then
   targets=$target
else
   usage "unsupport target='$target'"
fi

for t in `echo $targets`
do
   source_script="$TPSUP/python3/scripts/tpbatch_py_generic.$t"

   if [ ! -e "$source_script" ]; then
      echo "FATAL: missing source script '$source_script'"
      exit 1
   fi
   
   for f in *_cfg.py
   do
      target_script=`echo $f|sed -e 's:_cfg.py::'`; \
   
      if [ $t = bat ]; then
         target_script="$target_script.bat"
      fi
   
      if [ -e "$target_script" ]; then 
         if [ "$target_script" -nt "$source_script" ]; then
            echo "skipped $target_script as it is newer than $source_script";
            continue; 
         else
            rm -f "$target_script";
         fi; 
      fi; 
   
      echo "updating $target_script ..."; 
      cp -f "$source_script" "$target_script";
   done
done   
