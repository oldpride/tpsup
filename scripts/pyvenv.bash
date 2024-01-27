#!/bin/bash

prog=`basename $0`

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

. "$TPSUP/profile"
#p3env

uname=`uname -a`
if [[ $uname =~ ^(Linux|Darwin) ]]; then
   # Linux linux1 5.15.0-76-generic #83-Ubuntu SMP Thu Jun 15 19:16:32 UTC 
   # 2023 x86_64 x86_64 x86_64 GNU/Linux
   OS=${BASH_REMATCH[1]}
   PREFIX=${BASH_REMATCH[1]}
   VERSION=`echo $uname|cut -d' ' -f3|cut -d. -f1-2`
elif [[ $uname =~ _NT ]]; then
   # Git bash
   # MINGW64_NT-10.0-19045 tianpc2 3.3.3-341.x86_64 2022-01-17 11:45 UTC x86_64 Msys
   # cygwin
   # CYGWIN_NT-10.0 tianpc2 3.3.4(0.341/5/3) 2022-01-31 19:35 x86_64 Cygwin
   OS=Windows
   PREFIX=win
   VERSION=`echo $uname|sed -e 's:^.*_NT[_-]\([0-9][0-9]*\)[.].*:\1:'`
else 
   echo "unsupported OS=$uname" >&2
   exit 1
fi

# $ python --version
# Python 3.10.6

pythons="python python3"
# WSL only has python3 at /usr/bin/python3

for p in `echo $pythons`
do
   if which "$p"; then
      python="$p"
      break
   fi
done

if [ "X$python" = "X" ] ;then
   echo "ERROR: neither '$pythons' is in PATH"
   exit 1
fi

python_version=`"$python" --version|cut -d' ' -f2|cut -d. -f1-2`
expected_sitevenv="$SITEBASE/python3/venv/$OS/${PREFIX}${VERSION}-python$python_version"

if [ $action = check ]; then
   echo "   expected: $expected_sitevenv"
   echo "     actual: $SITEVENV"
   if ! [ "$SITEVENV" = "$expected_sitevenv" ]; then
      echo "ERROR: SITEVENV is not expected" >&2
   else
      echo "OK:    SITEVENV matched expected"
   fi
   set -x
   cd "$SITEVENV"
   pwd
elif [ $action = make ]; then
   echo "this may take a minute ..."
   set -x
   "$python" -m venv "$SITEVENV"
else 
   echo "unknown action='$action'" >&2
   usage
fi

