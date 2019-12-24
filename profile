TPSUPMODE="$1"

unset TMOUT

# define chknfs ASAP so that in case of NFS hung, we can use it to troubleshoot
chknfs () {
   local paths p
   paths=$1

   if [ "X$paths" = "X" ]; then
      paths="$PATH"
   fi

   for p in `echo $paths|/bin/sed -e 's/:/ /g'`
   do
      echo $p
      \cd $p && \cd - >/dev/null
   done
}

if [ "X$BASH_SOURCE" != "X" ]; then
   ## the following sed command simplify the path, eg, /a/b/../c => /a/c
   #TPSUP=`dirname $BASH_SOURCE|sed -e 's:$:/:;s:[^/][^/]*//*[.][.]::;s://*$::'`
   #if ! echo "$TPSUP" | grep '^/' >/dev/null; then
   #   TPSUP=`pwd`/$TPSUP
   #fi
   TPSUP=$(cd `dirname $BASH_SOURCE`; pwd -P) || return
   export TPSUP
else
   if ! [[ $0 =~ bash ]]; then
      echo "Run bash first ... Env is not set !!!" >&2
      return
   else
      echo "You used wrong bash (check version). please exit and find a newer version instead !!!" >&2
      echo " Or you can export BASH_SOURCE=/home/tia/github/tpsup/profile or something similar" >&2
      return
   fi
fi

umask 022

kcd () {
   local old new cd
   old=$1
   new=$2
   cd=`pwd|sed -e "s:$old:$new:g"`
   cd $cd
}

delpath () {
   local OPTIND OPTARG o quiet usage pattern path new old flag

   quiet=N
   flag="-v"
   usage="  
delpath is a bash function defined in $BASH_SOURCE
usage:

   delpath [-q] pattern [env_var]

   env_var default to PATH, but can be anthing, eg, LD_LIBRARY_PATH,MANPATH,PERL5LIB,PYTHONPATH

   "

   while getopts q o;
   do
      case "$o" in
         q) quiet=Y; flag="";;
         *) echo "unknow switch. $usage">&2; return 1;;
      esac
   done

   shift $((OPTIND-1))

   pattern=$1
   if [ "X$pattern" = X ]; then
      echo "wrong number of args. $usage">&2; return 1
   fi

   if [ "X$2" = "X" ]; then
      path=PATH
   else
      path=$2
   fi

   if [ $quiet = N ]; then
      echo "searching pattern ($pattern) from \$$path" >&2
   fi

   old=`eval "echo \\\$$path"`

   new=`$TPSUP/scripts/delpath $flag $pattern $old`
   if [ $? -ne 0 ]; then
      echo "cmd=$TPSUP/scripts/delpath $flag $pattern $old failed, no change" >&2
      return 1
   fi
   eval "export $path=$new"
}

functions () {
   typeset -F
   echo 'use typeset -f to see detail'
}

if ! /usr/bin/perl -Mwarnings -e "print '';"; then
   # this happens on old Solaris host
   echo "/usr/bin/per1 is too old. find a newer version instead" >&2
   USE_NEWER_PERL=/usr/local/bin/per1
fi

PS1='$USER@$HOSTNAME:$PWD$ '
export PS1

HOSTNAME=`hostname`

UNAME=`uname -a`

# MINGW64_NT-10.0 LAPTOP-4DDGKLFF 2.11.2(0.329/5/3) 2018-11-10 14:38 x86_64 Msys
# CYGWIN_NT-10.0 LAPTOP-4DDGKLFF 3.0.4(0.338/5/3) 2019-03-16 09:50 x86_64 Cygwin
# Linux linux1 4.15.0-54-generic #58-Ubuntu SMP Mon Jun 24 10:55:24 UTC 2019 x86_64 x86_64 x86_64 GNU/Linux
   
if [[ $UNAME =~ Msys ]]; then
   # https://stackoverflow.com/questions/32597209/python-not-working-in-the-command-line-of-git-bash
   alias python2='winpty "/c/Program Files/Python27/python"'
   alias python3='winpty "/c/Program Files/Python37/python"'
elif [[ $UNAME =~ Cygwin ]]; then
   # https://stackoverflow.com/questions/3250749/using-windows-python-from-cygwin
   # to run interactive python from cygwin
   #    python -i
   # or
   #    cygstart python    # this bring up a new window
   alias wpython2="'/cygdrive/c/Program Files/Python27/python'"
   alias wpython3="'/cygdrive/c/Program Files/Python37/python'"
   # the above is to run windows's python from cygwin. we had installed python 
   # inside cygwin, they are /usr/bin/python2 (2.7) and /usr/bin/python3 (3.7)  

   # ssh in cygwin will get this error without the -tt
   #    Pseudo-terminal will not be allocated because stdin is not a terminal.
   alias ssh="ssh -tt"
elif [[ $UNAME =~ Linux ]]; then
   # linux has /usr/bin/python2 and /usr/bin/python3
   alias eclipse="/home/tian/eclipse/cpp-2019-06/eclipse/eclipse"
   alias pycharm="/snap/bin/pycharm-community"
else 
   echo "UNAME='$UNAME' is not supported"
fi

reduce () {
   local REDUCEPATHCMD=

   REDUCEPATHCMD=$TPSUP/scripts/reducepath
   
   if ! [ -f $REDUCEPATHCMD ]; then
      return
   fi 

   export  PATH=`$USE_NEWER_PERL $REDUCEPATHCMD -q "$PATH"`
   export  MANPATH=`$USE_NEWER_PERL $REDUCEPATHCMD -q "$MANPATH"`
   export  PERL5LIB=`$USE_NEWER_PERL $REDUCEPATHCMD -q "$PERL5LIB"`
   export  PYTHONPATH=`$USE_NEWER_PERL $REDUCEPATHCMD -q "$PYTHONPATH"`
   export  LD_LIBRARY_PATH=`$USE_NEWER_PERL $REDUCEPATHCMD -q "$LD_LIBRARY_PATH"`
   export  LD_LOAD_PATH=`$USE_NEWER_PERL $REDUCEPATHCMD -q "$LD_LOAD_PATH"`
}

# https://askubuntu.com/questions/98782/how-to-run-an-alias-in-a-shell-script
# Aliases are deprecated in favor of shell functions. From the bash manual page:
# For almost every purpose, aliases are superseded by shell functions.

alias perllib='cd $TPSUP/lib/perl/TPSUP'
alias rm='rm -i'
alias mv='mv -i'
alias cp='cp -i'
alias grep='grep -i'
alias ls='ls -a'

tpsup () {
  . $TPSUP/profile
}

tpscripts () {
   cd $TPSUP/scripts
}

kdbnotes () {
   cd $TPSUP/../kdb/notes
}

tpnotes () {
   cd $TPSUP/../notes
}

mycpp () {
   cd $TPSUP/../cpp/cookbook/src
}

if [ "X$TPSUPMODE" != "Xsafe" ]; then
   PERL5LIB=$TPSUP/lib/perl:$PERL5LIB
   PATH=$TPSUP/scripts:$PATH
else
   PERL5LIB=$PERL5LIB:$TPSUP/lib/perl
   PATH=$TPSUP/autopath:$PATH
fi

p2env () {
   python () {
      /usr/bin/python "$@"
   }

   pip () {
      /usr/bin/pip "$@"
   }

   export PYTHONPATH=$TPSUP/python2/lib:$PYTHONPATH
   export PATH=$TPSUP/python2/scripts:$PATH
   reduce

   # export the function
   set -a
}

p3env () {
   python () {
      /usr/bin/python3 "$@"
   }

   pip () {
      /usr/bin/pip3 "$@"
   }

   export PYTHONPATH=$TPSUP/python3/lib:$PYTHONPATH
   export PATH=$TPSUP/python3/scripts:$TPSUP/python3/examples:$PATH
   reduce

   # export the function
   set -a
}

tpproxy () {
   # to make wget/curl work behind firewall

   # export http_proxy=http://user:password@host:port
   # export https_proxy=http://user:password@host:port

   # for authencationless proxy
   # export http_proxy=http://host:port
   # export https_proxy=http://host:port

   echo "tpproxy is not implemented on yet" >&2
}

functions () {
   typeset -F
   echo "to see detail: typeset -f"
}

p3env  # default to python 3

alias p2c="python2 -m py_compile"
alias p3c="python3 -m py_compile"
alias p2scripts='cd $TPSUP/python2/scripts'
alias p2examples='cd $TPSUP/python2/examples'
alias p3scripts='cd $TPSUP/python3/scripts'
alias p3examples='cd $TPSUP/python3/examples'
alias p2lib='cd $TPSUP/python2/lib/tpsup'
alias p3lib='cd $TPSUP/python3/lib/tpsup'

wbar () {
   # window bar
   TERM=xterm
   export TERM
   if [ "X$TERM" == Xxterm ]; then
      PROMPT_COMMAND='echo -ne "\033]0;${USER}@${HOSTNAME}: ${PWD}\007"'
   fi
}

if [ "X$TERM" = Xxterm -o "X$TERM" = "Xvt100" ]; then
   PROMPT_COMMAND='echo -ne "\033]0;${USER}@${HOSTNAME}: ${PWD}\007"'
   export PROMPT_COMMAND

   vi () {
      local file
      file="$@"
      echo -ne "\033]0;${USER}@${HOSTNAME}: vi $@\007"
      /usr/bin/vi "$@"
   }

   less () {
      local file
      file="$@"
      echo -ne "\033]0;${USER}@${HOSTNAME}: less $@\007"
      /usr/bin/less "$@"
   }

   # unset -f func to unset a function.
fi

# https://stackoverflow.com/questions/6920402/in-a-bash-script-how-to-run-bash-functions-defined-outside
# export all functions
set -a

set -o vi
#  Control-V, Backspace
if !stty erase  2>/dev/null; then
   :
fi  

