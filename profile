perllib='cd "$TPSUP/lib/perl/TPSUP"'
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

mytp () {
   # for compatibility with corp settings
   cd "$TPSUP/scripts"
}

myperllib () {
   # for compatibility with corp settings
   cd "$TPSUP/lib/perl/TPSUP"
}

kdbnotes () {
   cd "$TPSUP/../kdb/notes"
}

mynotes () {
   cd "$TPSUP/../notes"
}

mycpp () {
   cd "$TPSUP/../cpp/cookbook/src"
}

myjoomla () {
   cd "$TPSUP/../joomla"
}

mykivy () {
   cd "$TPSUP/../kivy"
}

function myjava  {
   if [[ $UNAME =~ Msys ]]; then
      cd /c/users/$USER/eclipse-workspace
   elif [[ $UNAME =~ Cygwin ]]; then
      cd /cygdrive/c/users/$USER/eclipse-workspace
   elif [[ $UNAME =~ Linux ]]; then
      cd ~/eclipse-workspace
   else 
      echo "UNAME='$UNAME' is not supported"
   fi
}

if [ "X$TPSUPMODE" != "Xsafe" ]; then
   PERL5LIB="$TPSUP/lib/perl:$PERL5LIB"
   PATH="$TPSUP/scripts:$PATH"
else
   PERL5LIB="$PERL5LIB:$TPSUP/lib/perl"
   PATH="$TPSUP/autopath:$PATH"
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
   if ! [ -e /usr/bin/python3 ]; then
      return
   fi

   python () {
      /usr/bin/python3 "$@"
   }

   pip () {
      /usr/bin/pip3 "$@"
   }

   export PYTHONPATH="$TPSUP/python3/lib:$PYTHONPATH"
   export       PATH="$TPSUP/python3/scripts:$TPSUP/python3/examples:$PATH"
   reduce

   # export the function
   set -a
}

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

tpproxy () {
   local usage
   usage="
usage:
   tpproxy is a bash function.
   tpproxy check
   tpproxy set
"

   if [ "X$1" = "Xcheck" ]; then
      echo "http_proxy=$http_proxy"
      echo "https_proxy=$https_proxy"
   elif [ "X$1" = "Xset" ]; then
      #export http_proxy=$http_proxy
      #export https_proxy=$https_proxy
      echo "tpproxy is not implemented on yet" >&2
   else
      echo "http_proxy=$http_proxy" >&2
      echo "https_proxy=$https_proxy" >&2
      echo "$usage" >&2
   fi

   # to make wget/curl work behind firewall

   # export http_proxy=http://user:password@host:port
   # export https_proxy=http://user:password@host:port

   # for authencationless proxy
   # export http_proxy=http://host:port
   # export https_proxy=http://host:port
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

p3env  # default to python 3

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

