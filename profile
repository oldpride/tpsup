TPSUPMODE="$1"

unset TMOUT

# define chknfs ASAP so that in case of NFS hung, we can use it to troubleshoot
chknfs () {
   local paths p
   paths=$1

   if [ "X$paths" = "X" ]; then
      paths="$PATH"
   fi

   # this cannot handle space char in PATH (in windows)
   #for p i `echo "$paths"|/bin/sed -e 's/:/ /g'`
   echo "$paths"|/bin/sed -e "s/:/\n/g" | while read p
   do
      echo "checking '$p'"
      \cd "$p" && \cd - >/dev/null
   done
   echo All Done
}

if [ "X$BASH_SOURCE" != "X" ]; then
   ## the following sed command simplify the path, eg, /a/b/../c => /a/c
   #TPSUP=`dirname $BASH_SOURCE|sed -e 's:$:/:;s:[^/][^/]*//*[.][.]::;s://*$::'`
   #if ! echo "$TPSUP" | grep '^/' >/dev/null; then
   #   TPSUP=`pwd`/$TPSUP
   #fi

   # for windows, wrap around in order to handle space chars, eg C:\Program Files\...
   TPSUP=$(cd "`dirname \"$BASH_SOURCE\"`"; pwd -P) || return
   export TPSUP
else
   if ! [[ "$0" =~ bash ]]; then
      echo "Run bash first ... Env is not set !!!" >&2
      return
   else
      echo "You used wrong bash (check version). please exit and find a newer version instead !!!" >&2
      echo " Or you can export BASH_SOURCE=/home/tian/sitedir/github/tpsup/profile or something similar" >&2
      return
   fi
fi

umask 022

kcd () {
   local old new cd
   old=$1
   new=$2
   cd=`pwd|sed -e "s!$old!$new!g"`
   cd "$cd"
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

   # wrap around for windows PATH
   # windows always need perl to launch perl script
   new=`perl "$TPSUP/scripts/delpath" $flag "$pattern" "$old"`
   if [ $? -ne 0 ]; then
      echo "cmd=perl \"$TPSUP/scripts/delpath\" $flag \"$pattern\" \"$old\" failed, no change" >&2
      return 1
   fi
   eval "export $path=\"$new\""
}

functions () {
   typeset -F
   echo 'use typeset -f to see detail'
}

export PERL_BINARY=perl

PS1='$USER@$HOSTNAME:$PWD$ '
export PS1

HOSTNAME=`hostname`

UNAME=`uname -a`

# MINGW64_NT-10.0 LAPTOP-4DDGKLFF 2.11.2(0.329/5/3) 2018-11-10 14:38 x86_64 Msys
# CYGWIN_NT-10.0 LAPTOP-4DDGKLFF 3.0.4(0.338/5/3) 2019-03-16 09:50 x86_64 Cygwin
# Linux linux1 4.15.0-54-generic #58-Ubuntu SMP Mon Jun 24 10:55:24 UTC 2019 x86_64 x86_64 x86_64 GNU/Linux
   
if [[ $UNAME =~ Msys ]]; then
   # Git Bash has USERNAME preset instead of USER
   export USER=$USERNAME

   alias     ework='cd /c/users/$USER/eclipse-workspace'
   alias     mygit='cd /c/users/$USER/github'
   alias downloads='cd /c/users/$USER/downloads'

   # https://stackoverflow.com/questions/32597209/python-not-working-in-the-command-line-of-git-bash
   alias python2='winpty "/c/Program Files/Python27/python"'
   alias python3='winpty "/c/Program Files/Python37/python"'
elif [[ $UNAME =~ Cygwin ]]; then
   alias     ework='cd /cygdrive/c/users/$USER/eclipse-workspace'
   alias     mygit='cd /cygdrive/c/users/$USER/github'
   alias downloads='cd /cygdrive/c/users/$USER/downloads'

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
   if ! /usr/bin/perl -Mwarnings -e "print '';"; then
      # this happens on old Solaris host
      echo "/usr/bin/per1 is too old. find a newer version instead" >&2
      export PERL_BINARY=/usr/local/bin/per1
   fi

   # linux has /usr/bin/python2 and /usr/bin/python3

   alias eclipse="/home/tian/eclipse/cpp-2019-06/eclipse/eclipse"
   alias pycharm="/snap/bin/pycharm-community"

   alias     ework='cd ~/eclipse-workspace'
   alias     mygit='cd ~/github'
   alias downloads='cd ~/Downloads'
else 
   echo "UNAME='$UNAME' is not supported"
fi

reduce () {
   # this function takes about 2 seconds

   local REDUCEPATHCMD

   REDUCEPATHCMD="$TPSUP/scripts/reducepath"
   
   if ! [ -f "$REDUCEPATHCMD" ]; then
      return
   fi 

   export             PATH=`$PERL_BINARY "$REDUCEPATHCMD" -q "$PATH"`
   export          MANPATH=`$PERL_BINARY "$REDUCEPATHCMD" -q "$MANPATH"`
   export         PERL5LIB=`$PERL_BINARY "$REDUCEPATHCMD" -q "$PERL5LIB"`
   export     LD_LOAD_PATH=`$PERL_BINARY "$REDUCEPATHCMD" -q "$LD_LOAD_PATH"`
   export  LD_LIBRARY_PATH=`$PERL_BINARY "$REDUCEPATHCMD" -q "$LD_LIBRARY_PATH"`

   if [[ $UNAME =~ Cygwin ]]; then
      export PYTHONPATH=`$PERL_BINARY "$REDUCEPATHCMD" -q -d ";" "$PYTHONPATH"`
   else   
      export PYTHONPATH=`$PERL_BINARY "$REDUCEPATHCMD" -q        "$PYTHONPATH"`
   fi
}

# https://askubuntu.com/questions/98782/how-to-run-an-alias-in-a-shell-script
# Aliases are deprecated in favor of shell functions. From the bash manual page:
# For almost every purpose, aliases are superseded by shell functions.

alias perllib='cd "$TPSUP/lib/perl/TPSUP"'
alias rm='rm -i'
alias mv='mv -i'
alias cp='cp -i'
alias grep='grep -i'
alias ls='ls -a'

tpsup () {
  . "$TPSUP/profile"
}

tpscripts () {
   cd "$TPSUP/scripts"
}

winhome () {
   # for cygwin, which home is not C:/USERS/$USERNAME
   cd "C:/USERS/$USERNAME"
}

if [ "X$TPSUPMODE" != "Xsafe" ]; then
   PERL5LIB="$TPSUP/lib/perl:$PERL5LIB"
   PATH="$TPSUP/scripts:$PATH"
else
   PERL5LIB="$PERL5LIB:$TPSUP/lib/perl"
   PATH="$TPSUP/autopath:$PATH"
fi

itrs () {
   local usage args yyyymmdd yyyy mm dd
   usage="
convert ITRS path from
   /apps/log/<today %Y%m%d>.log
to
   /apps/log/20200226.log

usage:    itrs command args

          itrs -r
          >> command args

example:  itrs less '/apps/log/<today %Y%m%d>.log'

          itrs -r
          >> less /apps/log/<today %Y%m%d>.log
   
"
   if [ $# -eq 0 ]; then
      echo "$usage"
      return
   fi

   yyyymmdd=`date +%Y%m%d`
   yyyy=`echo $yyyymmdd|cut -c1-4`
     mm=`echo $yyyymmdd|cut -c5-6`
     dd=`echo $yyyymmdd|cut -c7-8`

   if [ "$1" = "-r" ]; then
      echo -n ">> "
      read args
   else
      args="$@"
   fi

   args=`echo "$args"|sed -e 's:%Y:$yyyy:g; s:%m:$mm:g; s:%d:$dd:g; s:<today[ ]*::; s:>::'`

   eval "$args"
}

diffalias () {
   local usage
   usage="
usage:
   Compare alias change.
   
   Snap the current alias
      diffalias snap
  
   Compare with the current alias with the previous snap
      diffalias diff

example:

   unalias a>/dev/null; diffalias snap; alias a=b; diffalias diff

   "

   if [ $# -ne 1 ]; then
      echo "$usage"
      return
   fi

   dir="/tmp/snap_dir_$USER"
   [ -d $dir ] || mkdir -p $dir || return 

   if   [ $1 = snap ]; then
      alias >$dir/alias.txt
   elif [ $1 = diff ]; then
      alias >$dir/alias.txt.new
      diff $dir/alias.txt $dir/alias.txt.new
   else
      echo "$usage"
      return
   fi
}

functions () {
   typeset -F
   echo "to see detail: typeset -f"
}

# p3env -q # default to python 3

alias p2c="python2 -m py_compile"
alias p3c="python3 -m py_compile"
alias p2scripts='cd "$TPSUP/python2/scripts"'
alias p2examples='cd "$TPSUP/python2/examples"'
alias p3scripts='cd "$TPSUP/python3/scripts"'
alias p3examples='cd "$TPSUP/python3/examples"'
alias p2lib='cd "$TPSUP/python2/lib/tpsup"'
alias p3lib='cd "$TPSUP/python3/lib/tpsup"'

wbar () {
   # window bar
   TERM=xterm
   export TERM
   if [[ $TERM =~ ^xterm|^vt ]]; then
      PROMPT_COMMAND='echo -ne "\033]0;${USER}@${HOSTNAME}: ${PWD}\007"'
   fi
}

if [[ $TERM =~ ^xterm|^vt ]]; then
   # we use PROMPT_COMMAND to manage title bar, it will not replace PS1.

   # on GitBash/Cygwin or home linux host, we normally don't ssh. therefore, no need for 
   # ${USER}@${HOSTNAME}

   if [[ $UNAME =~ Msys|Cygwin || ${HOSTNAME} = linux1 ]]; then
      PROMPT_COMMAND='echo -ne "\033]0;${PWD}\007"'
   else 
      PROMPT_COMMAND='echo -ne "\033]0;${USER}@${HOSTNAME}: ${PWD}\007"'
   fi 

   export PROMPT_COMMAND

   for cmd in vi vim less su
   do
      # eval'ed command looks like this
      #    vi () { echo -ne "\033]0;${USER}@${HOSTNAME}: vi $@\007"; /usr/bin/vi "$@"; }

      # set -x
      if [[ $UNAME =~ Msys|Cygwin || ${HOSTNAME} = linux1 ]]; then
         eval "$cmd () { echo -ne \"\\033]0;\"               \"$cmd \$@\\007\"; /usr/bin/$cmd \"\$@\"; }"
      else
         eval "$cmd () { echo -ne \"\\033]0;\$USER@\$HOSTNAME: $cmd \$@\\007\"; /usr/bin/$cmd \"\$@\"; }"
      fi
      # set +x
   done
fi

# https://stackoverflow.com/questions/6920402/in-a-bash-script-how-to-run-bash-functions-defined-outside
# export all functions
set -a

set -o vi
#  Control-V, Backspace
if !stty erase  2>/dev/null; then
   :
fi  

# when sync to customized site, exclude *.site files
export PROFILE_SITE=$TPSUP/profile.site

if [ -f $PROFILE_SITE ]; then
   . $PROFILE_SITE
fi

