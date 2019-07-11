TPSUPMODE="$1"

umask 022

unset TMOUT

kcd () {
   old=$1
   new=$2
   cd=`pwd|sed -e "s:$old:$new:g"`
   cd $cd
}

delpath () {
   pattern=$1
   if [ "X$pattern" = X ]; then
      echo "usage: delpath pattern"
      return 1
   fi

   if [ "X$2" = "X" ]; then
      path=PATH
   else
     path=$2
   fi

   echo "deleting pattern ($pattern) from \$$path" >&2
   old=`eval "echo \\\$$path"`

   new=`$TPSUP/scripts/delpath $pattern $old`
   if [ $? -ne 0 ]; then
      echo "cmd=$TPSUP/scripts/delpath $pattern $old failed, no change" >&2
      return 1
   fi
   eval "export $path=$new"
}

chknfs () {
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

# save original PATH, add more reliable PATH to the front, so that
# user ENV (eg, a hanging mount point) won't scroll up the critial part (delpath) of
# this profile. We will later restore the original PATH
SAVED_PATH="$PATH"
export PATH=/usr/bin:/bin:/sbin:$SAVED_PATH

HOSTNAME=`hostname`
export HOSTNAME

if [ "X$BASH_SOURCE" != "X" ]; then
   # the following sed command simplify the path, eg, /a/b/../c => /a/c
   TPSUP=`dirname $BASH_SOURCE|sed -e 's:$:/:;s:[^/][^/]*//*[.][.]::;s://*$::'`

   if ! echo "$TPSUP" | grep '^/' >/dev/null; then
      TPSUP=`pwd`/$TPSUP
   fi
else
   if ! echo $0 |grep bash >/dev/null; then
      echo "Run bash first ... Env is not set !!!" >&2
      return
   else
      echo "You used wrong bash (check version). please exit and find a newer version instead !!!" >&2
      echo " Or you can export BASH_SOURCE=/home/tia/github/tpsup/profile or something similar" >&2
      return
   fi
fi

# restore original PATH
export PATH="$SAVED_PATH"

if ! /usr/bin/perl -Mwarnings -e "print '';"; then
   # this happens on old Solaris host
   echo "/usr/bin/per1 is too old. find a newer version instead" >&2
   USE_NEWER_PERL=/usr/local/bin/per1
fi

if [ -f $TPSUP/scripts/trimpath ]; then
   TPSUP=`$USE_NEWER_PERL $TPSUP/scripts/trimpath $TPSUP`
fi

export TPSUP
export TPSUPMODE

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
   alias python2="/cygdrive/c/Program Files/Python27/python"
   alias python3="/cygdrive/c/Program Files/Python37/python"
elif [[ $UNAME =~ Linux ]]; then
   alias python2="/usr/bin/python2.7"
   alias python3="/usr/bin/python3"
   :
else 
   echo "UNAME='$UNAME' is not supported"
fi

alias perllib='cd $TPSUP/lib/perl/TPSUP'
alias tpscripts='cd $TPSUP/scripts'
alias tpnotes='cd $TPSUP/notes'
alias kdbnotes='cd $TPSUP/../kdb/notes'
alias tpsup='. $TPSUP/profile'

if [ "X$TPSUPMODE" != "Xsafe" ]; then
   PERL5LIB=$TPSUP/lib/perl:$PERL5LIB
   PATH=$TPSUP/scripts:$PATH
else
   PERL5LIB=$PERL5LIB:$TPSUP/lib/perl
   PATH=$TPSUP/autopath:$PATH
fi

py2env () {
   alias python=python2
   PYTHONPATH=$TPSUP/python2/lib:$PYTHONPATH
   export PYTHONPATH
   PATH=$PATH:$TPSUP/python2/scripts
}

py3env () {
   alias python=python3
   PYTHONPATH=$TPSUP/python3/lib:$PYTHONPATH
   export PYTHONPATH
   PATH=$PATH:$TPSUP/python3/scripts
}

py3env  # default to python 3

alias pyc="python -m py_compile"
alias py2c="python2 -m py_compile"
alias py3c="python3 -m py_compile"
alias py2scripts='cd $TPSUP/python2/scripts'
alias py3scripts='cd $TPSUP/python3/scripts'
alias py2lib='cd $TPSUP/python2/lib/tpsup'
alias py3lib='cd $TPSUP/python3/lib/tpsup'

if [ "X$PATH" != "X" ]; then
   PATH=`$USE_DB_PERL $TPSUP/scripts/reducepath -q "$PATH"`
   export PATH
fi

if [ "X$PERL5LIB" != "X" ]; then
   PERL5LIB="$USE_DB_PERL $TPSUP/scripts/reducepath -q "$PERL5LIB""
   export PERL5LIB
fi

if [ "X$LD_LIBRARY_PATH" != "X" ]; then
   LD_LIBRARY_PATH=`$USE_DB_PERL $TPSUP/scripts/reducepath -q "$LD_LIBRARY_PATH"`
   export LD_LIBRARY_PATH
fi

if [ "X$LD_LOAD_PATH" != "X" ]; then
   LD_LOAD_PATH=`$USE_DB_PERL $TPSUP/scripts/reducepath -q "$LD_LOAD_PATH"`
   export LD_LOAD_PATH
fi

if [ -f ~/local.profle ]; then
   . ~/local.profile
fi

window_bar () {
   TERM=xterm
   export TERM
   if [ "X$TERM" == Xxterm ]; then
      PROMPT_COMMAND='echo -ne "\033]0;${USER}@${HOSTNAME}: ${PWD}\007"'
   fi
}

alias wbar=window_bar

if [ "X$TERM" = Xxterm -o "X$TERM" = "Xvt100" ]; then
   PROMPT_COMMAND='echo -ne "\033]0;${USER}@${HOSTNAME}: ${PWD}\007"'
   export PROMPT_COMMAND

   vi () {
      file="$@"
      echo -ne "\033]0;${USER}@${HOSTNAME}: vi $@\007"
      /usr/bin/vi "$@"
   }

   less () {
      file="$@"
      echo -ne "\033]0;${USER}@${HOSTNAME}: less $@\007"
      /usr/bin/less "$@"
   }

   # unset -f func to unset a function.
fi

set -o vi
#  Control-V, Backspace
if !stty erase  2>/dev/null; then
   :
fi  

