#!/bin/bash
#
# gitbash and cygwin cannot use symbolic link reliablely. so we make hard copies
# this script is to be run when 'make' is not available, eg, in company cygwin or gitbash

prog=$(basename $0)

all_targets='bash bat'
# i didn't include taskbash and taskbat in all_targets because they are not used often.

usage() {
   msg=$1

   [ "X$msg" = "X" ] || echo >&2 "ERROR: $msg"

   cat >&2 <<END
usage:

   $prog bash|bat|taskbash|taskbat
   $prog all
   
   'all' covers: $all_targets.

   create a wrapper script for *_cfg.py, 
      bash - for bash on linux/cygwin/gitbash. 
            target will be launched from inside venv.
      bat - for batch on windows, 
            target will be launched from inside venv.
      taskbash - for bash on linux/cygwin/gitbash. 
            target will be launched from outside venv
      taskbat - for batch on windows, 
             target will be lauched from outside venv.

   ideally this can be done by a symbolic link but gitbash and cygwin cannot use 
   symbolic link reliablely. so we make hard copies

   -v          verbose mode

   -m pattern  only update scripts whose name matches the pattern

examples:

   $prog -m test_input taskbat
   C:\Users\william>sitebase\github\tpsup\python3\scripts\ptslnm_test_input_task.bat  s=henry

   $prog -m test_input taskbash

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
elif [ $target = bash -o $target = bat -o $target = taskbash -o $target = taskbat ]; then
   targets=$target
else
   usage "unsupport target='$target'"
fi

for t in $(echo $targets); do
   for f in *_cfg_*.py; do
      if [ "X$pattern" != "X" ]; then
         if ! echo $f | egrep -q "$pattern"; then
            continue
         fi
      fi

      # https://unix.stackexchange.com/questions/145402
      # sed -e would not work.
      # sed -E is extended regular expression, which is similar to perl's regex.
      target_type=$(echo $f | sed -E 's:^.*_cfg_(batch|trace).py:\1:')
      target_prefix=$(echo $f | sed -E 's:_cfg_(batch|trace).py::')
      [ $verbose = Y ] && echo "target_type=$target_type, target_prefix=$target_prefix"

      if [ $t = bat ]; then
         target_script="$target_prefix.bat"
      elif [ $t = bash ]; then
         target_script="$target_prefix"
      elif [ $t = taskbash ]; then
         target_script="${target_prefix}_task"
      elif [ $t = taskbat ]; then
         target_script="${target_prefix}_task.bat"
      else
         echo "FATAL: unknown target '$t'"
         exit 1
      fi

      if [ $t = bash -o $t = bat ]; then
         source_script="$TPSUP/python3/scripts/ptgeneric_py.$t"
      elif [ $t = taskbash ]; then
         source_script="$TPSUP/python3/scripts/pt${target_type}_generic_task.bash"
      elif [ $t = taskbat ]; then
         source_script="$TPSUP/python3/scripts/pt${target_type}_py_generic_task.bat"
      fi

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
