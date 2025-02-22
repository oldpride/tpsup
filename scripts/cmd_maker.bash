#!/bin/bash
#
# wrap python/js/ts scripts with bash or batch so that we can run them in any environment
# 

prog=$(basename $0)

all_targets='bash bat'

usage() {
   msg = $1

   [ "X$msg" = "X" ] || echo >&2 "ERROR: $msg"

   cat >&2 <<END
usage:

   $prog bash|bat|taskbash|taskbat
   $prog all
   
   'all' covers: $all_targets.

   create a wrapper script for *_cmd.py, *_cmd.js, *_cmd.js
      bash - for bash on linux/cygwin/gitbash. 
            target will be launched from inside venv.
      bat - for batch on windows, 
            target will be launched from inside venv.

   ideally this can be done by a symbolic link but gitbash and cygwin cannot use 
   symbolic link reliablely. so we make hard copies

   -v          verbose mode

   -m pattern  only update scripts whose name matches the pattern

examples:

   $prog all
   $prog -m grep_cmd all
   $prog -m grep_cmd bat

END
   exit 1
}

verbose=N

while getopts vm: o; do
   case "$o" in
   v) verbose=Y ;;
   m) pattern="$OPTARG" ;;
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

target=$1

if [ $target = all ]; then
   targets=$all_targets
elif [ $target = bash -o $target = bat ]; then
   targets=$target
else
   usage "unsupport target='$target'"
fi

for t in $(echo $targets); do
   for f in `/bin/ls -1 *_cmd.py *_cmd.js *_cmd.ts 2>/dev/null`; do
      if [ "X$pattern" != "X" ]; then
         if ! echo $f | egrep -q "$pattern"; then
            continue
         fi
      fi

      # https://unix.stackexchange.com/questions/145402
      # sed -e would not work.
      # sed -E is extended regular expression, which is similar to perl's regex.
      target_prefix=$(echo $f | sed -E 's:_cmd.(py|js|ts)::')
      [ $verbose = Y ] && echo "target_prefix=$target_prefix"

      if [ $t = bat ]; then
         target_script="$target_prefix.bat"
      elif [ $t = bash ]; then
         target_script="$target_prefix"
      else
         echo "FATAL: unknown target '$t'"
         exit 1
      fi

      source_script="$TPSUP/scripts/cmd_generic.$t"

      if [ ! -e "$source_script" ]; then
         echo "FATAL: missing source script '$source_script'"
         exit 1
      fi

      if [ -e "$target_script" ]; then
         if [ "$target_script" -nt "$source_script" ]; then
            echo "skipped $target_script as it is newer than $source_script"
            continue
         else
            rm -f "$target_script"
         fi
      fi

      echo "updating $target_script ..."
      cp -f "$source_script" "$target_script"
   done

done
