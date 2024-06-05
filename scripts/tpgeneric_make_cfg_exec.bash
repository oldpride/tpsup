#!/bin/bash
#
# gitbash and cygwin cannot use symbolic link reliablely. so we make hard copies
# this script is to be run when 'make' is not available, eg, in company cygwin or gitbash

prog=$(basename $0)

all_targets='bash' # exclude 'bat' from default because it is not used often.
# i didn't include taskbash and taskbat in all_targets because they are not used often.

usage() {
   msg=$1

   [ "X$msg" = "X" ] || echo >&2 "ERROR: $msg"

   cat >&2 <<END
usage:

   $prog bash|bat
   $prog all
   
   'all' covers: $all_targets.

   create a wrapper script for _cfg_(batch|trace).pl files.
      bash - for bash on linux/cygwin/gitbash. 
            target will be launched from inside venv.
      bat - for batch on windows, 
            target will be launched from inside venv.

   ideally this can be done by a symbolic link but gitbash and cygwin cannot use 
   symbolic link reliablely. so we make hard copies

   -v          verbose mode
   -n          dry run

   -m pattern  only update scripts whose name matches the pattern

examples:

   $prog -m tptrace_test bat
   C:\Users\william>sitebase\github\tpsup\scripts\tptrace_test.bat any


END
   exit 1
}

verbose=N
dryrun=N

while getopts vnm: o; do
   case "$o" in
   v) verbose=Y ;;
   n) dryrun=Y ;;
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
   # for f in *_cfg_batch.pl *_cfg_trace.pl; do
   for f in `\ls *_cfg_batch.pl *_cfg_trace.pl 2>/dev/null`; do 
      # because glob will return the original pattern if no file is found, we use ls instead.
      # use \ls to avoid alias
      if [ "X$pattern" != "X" ]; then
         if ! echo $f | egrep -q "$pattern"; then
            continue
         fi
      fi

      # https://unix.stackexchange.com/questions/145402
      # sed -e would not work.
      # sed -E is extended regular expression, which is similar to perl's regex.
      target_type=$(echo $f | sed -E 's:^.*_cfg_(batch|trace).pl:\1:')
      target_prefix=$(echo $f | sed -E 's:_cfg_(batch|trace).pl::')
      [ $verbose = Y ] && echo "target_type=$target_type, target_prefix=$target_prefix"

      if [ $t = bat ]; then
         target_script="$target_prefix.bat"
      elif [ $t = bash ]; then
         target_script="$target_prefix"
      # elif [ $t = taskbash ]; then
      #    target_script="${target_prefix}_task"
      # elif [ $t = taskbat ]; then
      #    target_script="${target_prefix}_task.bat"
      else
         echo "FATAL: unknown target '$t'"
         exit 1
      fi

      if [ $t = bash -o $t = bat ]; then
         source_script="$TPSUP/scripts/tpgeneric.$t"
      fi

      if [ ! -e "$source_script" ]; then
         echo "FATAL: missing source script '$source_script'"
         exit 1
      fi

      if [ -e "$target_script" ]; then
         if [ -h "$target_script" ]; then
            if [ $dryrun = N ]; then
               echo "$target_script is a old-style sym link. removed. will use file copy"
               rm -f "$target_script"
            else
               echo "dryrun: rm -f $target_script"
            fi
         elif [ "$target_script" -nt "$source_script" ]; then
            echo "$target_script skipped as it is newer than $source_script"
            continue
         else
            if [ $dryrun = N ]; then
               echo "$target_script exists. removed. will use file copy"
               rm -f "$target_script"
            else
               echo "dryrun: rm -f $target_script"
            fi
         fi
      fi

      if [ $dryrun = N ]; then
         echo "$target_script updated"
         cp -f "$source_script" "$target_script"
      else
         echo "dryrun: cp -f $source_script $target_script"
      fi
   done

done
