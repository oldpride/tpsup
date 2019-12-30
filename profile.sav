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

