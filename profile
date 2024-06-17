TPSUPMODE="$1"

unset TMOUT

# define chknfs ASAP so that in case of NFS hung, we can use it to troubleshoot
chknfs() {
   local paths p
   paths=$1

   if [ "X$paths" = "X" ]; then
      paths="$PATH"
   fi

   # this cannot handle space char in PATH (in windows)
   #for p i `echo "$paths"|/bin/sed -e 's/:/ /g'`
   echo "$paths" | /bin/sed -e "s/:/\n/g" | while read p; do
      echo "checking '$p'"
      \cd "$p" && \cd - >/dev/null
   done
   echo All Done
}

get_bash_source() {
   TP_BASH_SOURCE_FOUND=N
   unset TP_BASH_SOURCE_DIR
   unset TP_BASH_SOURCE_FILE

   if [ "X$BASH_SOURCE" != "X" ]; then
      TP_BASH_SOURCE_DIR=$(dirname "$BASH_SOURCE")
      TP_BASH_SOURCE_FILE=$(basename "$BASH_SOURCE")

      TP_BASH_SOURCE_DIR=$(
         cd "$TP_BASH_SOURCE_DIR"
         pwd -P
      )
      TP_BASH_SOURCE_FOUND=Y

      return 0
   else
      if ! [[ "$0" =~ bash ]]; then
         echo "Run bash first ... Env is not set !!!" >&2
      else
         echo "You used wrong bash (check version). please exit and find a newer version instead !!!" >&2
         echo " Or you can export BASH_SOURCE=this_file" >&2
      fi
      return 1
   fi
}

get_bash_source || return $?
# [ $TP_BASH_SOURCE_FOUND = Y ] || return $?
export TPSUP=$(
   cd "$TP_BASH_SOURCE_DIR"
   pwd -P
) || return

umask 022

export HOSTNAME=$(hostname | cut -d. -f1)

export UNAME=$(uname -a)
# cygwin
#    CYGWIN_NT-10.0 tianpc 3.1.7(0.340/5/3) 2020-08-22 17:48 x86_64 Cygwin
# gitbash
#    MINGW64_NT-10.0-19044 tianpc 3.1.6-340.x86_64 2020-07-09 14:33 UTC x86_64 Msys
# linux
#    Linux linux1 4.15.0-112-generic #113-Ubuntu SMP Thu Jul 9 23:41:39 UTC 2020 x86_64 x86_64 x86_64 GNU/Linux
# Windows cmd.exe, 'ver' command
#    Microsoft Windows [Version 10.0.19044.1889]

kcd() {
   local old new cd
   old=$1
   new=$2
   cd=$(pwd | sed -e "s!$old!$new!g")
   cd "$cd"
}

# delpath
#    remove a component from env var, eg, PATH, LD_LIBRARY_PATH, PERL5LIB, PYTHONPATH.
#    default to PATH.
#    very useful during NFS outage, assuming we had the shell started before the outage.
# design consideration
#    - use a separate script $TPSUP/scripts/delpath, for easy testing
#    - load code into profile, so that it won't hung during NFS outage
#    - commands can only be
#        - bash built-in, eg, echo, eval,
#        - full path, eg, /usr/bin/perl
delpath_code=$(cat "$TPSUP/scripts/delpath")

delpath() {
   local OPTIND OPTARG o quiet dryrun usage pattern path new old flag

   quiet=N
   dryrun=N
   flag="-v"
   usage="  
delpath is a bash function defined in $BASH_SOURCE
usage:

   delpath [-q] pattern [env_var]

   env_var default to PATH, but can be anthing, eg, LD_LIBRARY_PATH,MANPATH,PERL5LIB,PYTHONPATH

   -n     dry run

example:

   delpath /nfs/
   delpath /nfs/ LD_LIBRARY_PATH
   delpath /nfs/ PERL5LIB
   "
   # don't forget to localize OPTIND OPTARG
   while getopts qn o; do
      case "$o" in
      q)
         quiet=Y
         flag=""
         ;;
      n) dryrun=Y ;;
      *)
         echo "unknow switch. $usage" >&2
         return 1
         ;;
      esac
   done

   shift $((OPTIND - 1))

   pattern=$1
   if [ "X$pattern" = X ]; then
      echo "wrong number of args. $usage" >&2
      return 1
   fi

   if [ "X$2" = "X" ]; then
      path=PATH
   else
      path=$2
   fi

   if [ $quiet = N ]; then
      echo "searching pattern ($pattern) from \$$path" >&2
   fi

   old=$(eval "echo \$$path")

   # remove NFS dependency as this function is heavily used during NFS outage.
   #    LD_LIBRARY_PATH='' LD_RUN_PATH='' PERL5LIB=''
   # wrap around for windows PATH
   #    windows always need perl to launch perl script
   # to reduce NFS dependency, we don't call script like below
   #    new=`perl "$TPSUP/scripts/delpath" $flag "$pattern" "$old"`
   # instead, we do
   new=$(LD_LIBRARY_PATH='' LD_RUN_PATH='' PERL5LIB='' /usr/bin/perl -e "$delpath_code" -- $flag "$pattern" "$old")
   if [ $? -ne 0 ]; then
      echo "delpath failed, no change. test cmd=\"$TPSUP/scripts/delpath\" $flag \"$pattern\" \"$old\"" >&2
      return 1
   fi

   if [ $dryrun = N ]; then
      eval "export $path=\"$new\""
   else
      echo "dry run delpath. nothing changed"
   fi
}

findpath() {
   # making findpath as function instead of a script is to make it usable when NFS hang.
   local pattern path usage o case_insensitive OPTIND OPTARG

   usage="
usage: 

   findpath pattern [path]

   'path' can be any env var, default to PATH

   if 'pattern' is 'all', just print every component

   -i      case-insensitive

example:

   findpath /usr
   findpath -i roaming 
   findpath all LD_LIBRARY_PATH
"

   if [ $# -eq 0 -o $# -gt 2 ]; then
      echo "ERROR: wrong number of args" >&2
      echo "$usage" >&2
      return 1
   fi

   case_insensitive=N

   # don't forget to localize OPTIND OPTARG
   while getopts i o; do
      case "$o" in
      i) case_insensitive=Y ;;
      *)
         echo "unknow switch. $usage" >&2
         return 1
         ;;
      esac
   done

   shift $((OPTIND - 1))

   pattern=$1
   path=$2

   if [ "X$path" = "X" ]; then
      path=PATH
   fi

   resolved=$(eval "echo \$$path")

   echo "$resolved" | /bin/sed -e "s/:/\n/g" | while read line; do
      if [[ ${pattern,,} = all ]]; then
         echo "$line"
      elif [ $case_insensitive = N ]; then
         if [[ $line =~ $pattern ]]; then
            echo "$line"
         fi
      else
         # use ${var,,} syntax to convert to lower case
         if [[ ${line,,} =~ ${pattern,,} ]]; then
            echo "$line"
         fi

      fi
   done
}

listpath() {
   local pattern path usage o case_insensitive OPTIND OPTARG

   usage="
usage: 

   findpath path

   'path' can be any env var, default to PATH

example:

   listpath PATH
   findpath LD_LIBRARY_PATH
"

   if [ $# -ne 1 ]; then
      echo "ERROR: wrong number of args" >&2
      echo "$usage" >&2
      return 1
   fi

   path=$1

   findpath all $path
}

get_native_path() {
   local p
   p="$1"

   unset TP_RET
   if [[ $UNAME =~ Msys || $UNAME =~ Cygwin ]]; then
      TP_RET=$(cygpath -w "$p")
      return $?
   else
      TP_RET="$p"
      return 0
   fi
}

functions() {
   typeset -F
   cat <<EOF
to list functions:
   typeset -F

to see function definition
   typeset -f func_name

to delete a function
   unset -f func_name
   
EOF
}

export PERL_BINARY=perl

PS1='$USER@$HOSTNAME:$PWD$ '
export PS1

# MINGW64_NT-10.0 LAPTOP-4DDGKLFF 2.11.2(0.329/5/3) 2018-11-10 14:38 x86_64 Msys
# CYGWIN_NT-10.0 LAPTOP-4DDGKLFF 3.0.4(0.338/5/3) 2019-03-16 09:50 x86_64 Cygwin
# Linux linux1 4.15.0-54-generic #58-Ubuntu SMP Mon Jun 24 10:55:24 UTC 2019 x86_64 x86_64 x86_64 GNU/Linux

if [[ $UNAME =~ Msys ]]; then
   # Git Bash has USERNAME preset instead of USER
   export USER=$USERNAME

   export WINHOME=$(
      cd $USERPROFILE
      pwd -P
   )
   export CHOME=$(
      cd "C:/Users/$USER"
      pwd -P
   )

   alias ework='cd /c/users/$USER/eclipse-workspace'
   alias downloads='cd /c/users/$USER/downloads'

   # https://stackoverflow.com/questions/32597209/python-not-working-in-the-command-line-of-git-bash
   alias wpython2='winpty "/c/Program Files/Python27/python"'
   alias wpython3='winpty "/c/Program Files/Python310/python"'

   export OS_TYPE=Windows
   export OS_MAJOR=$(echo $UNAME | cut -d- -f2 | cut -d' ' -f1 | cut -d. -f1)
   export OS_MINOR=$(echo $UNAME | cut -d- -f2 | cut -d' ' -f1 | cut -d. -f2)

   export PATH="$PATH:$TPSUP/bat"
elif [[ $UNAME =~ Cygwin ]]; then
   export WINHOME=$(
      cd $USERPROFILE
      pwd -P
   )
   export CHOME=$(
      cd "C:/Users/$USER"
      pwd -P
   )

   alias ework='cd /cygdrive/c/users/$USER/eclipse-workspace'
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

   export OS_TYPE=Windows
   export OS_MAJOR=$(echo $UNAME | cut -d- -f2 | cut -d' ' -f1 | cut -d. -f1)
   export OS_MINOR=$(echo $UNAME | cut -d- -f2 | cut -d' ' -f1 | cut -d. -f2)

   export PATH="$PATH:$TPSUP/bat"
elif [[ $UNAME =~ Linux|Darwin ]]; then
   export Linux=$(uname -a | cut -d" " -f3 | cut -d. -f1,2)
   # Linux linux1 4.15.0-112-generic #113-Ubuntu SMP Thu Jul 9 23:41:39 UTC 2020 x86_64 x86_64 x86_64 GNU/Linux
   # Linux should be set to 4.15

   if ! /usr/bin/perl -Mwarnings -e "print '';"; then
      # this happens on old Solaris host
      echo "/usr/bin/per1 is too old. find a newer version instead" >&2
      export PERL_BINARY=/usr/local/bin/per1
   fi

   # linux has /usr/bin/python2 and /usr/bin/python3

   alias eclipse="/home/tian/eclipse/cpp-2019-06/eclipse/eclipse"
   alias pycharm="/snap/bin/pycharm-community"

   alias ework='cd ~/eclipse-workspace'
   alias mygit='cd ~/github'
   alias downloads='cd ~/Downloads'

   export OS_TYPE=Linux
   export OS_MAJOR=$(echo $UNAME | cut -d' ' -f3 | cut -d. -f1)
   export OS_MINOR=$(echo $UNAME | cut -d' ' -f3 | cut -d. -f2)
else
   echo "UNAME='$UNAME' is not supported"
fi

freshenv() {
   local VAR
   for VAR in MANPATH PERL5LIB LD_LOAD_PATH LD_LIBRARY_PATH PYTHONPATH; do
      unset $VAR
   done
   export PATH=/bin:/usr/bin:/usr/sbin
   echo "PATH=$PATH"
}

reduce() {
   local REDUCEPATHCMD
   local VARS NEW_EXPORT
   local NOW INTERVAL DEBUG FLAG
   local OPTIND OPTARG USAGE

   FLAG="-q" # default to quiet mode, ie, no debug

   if [ "X$TP_REDUCE_DEBUG" = "XY" ]; then
      DEBUG=Y
   else
      DEBUG=N
   fi

   USAGE="

usage:
   reduce all
   reduce VAR1 VAR2 ...
 
   reduce is a function defined in tpsup profile.

   -d             debug mode. 

   we can also set TP_REDUCE_DEBUG. this is basicaly a trace mode. eg, 
      export TP_REDUCE_DEBUG=Y
      unset  TP_REDUCE_DEBUG

   set TP_REDUCE_THRESHOLD (number of seconds) to detect over-frequent calling.
      export TP_REDUCE_THRESHOLD=4     #  enable the detection
      unset  TP_REDUCE_THRESHOLD       # disable the detection

"
   # don't forget to localize OPTIND OPTARG
   while getopts d o; do
      case "$o" in
      d)
         DEBUG=Y
         FLAG=""
         ;;
      *)
         echo "unknow switch. ${FUNCNAME[1]}. $USAGE" >&2
         return 1
         ;;
      esac
   done

   shift $((OPTIND - 1))

   if [ $# -eq 0 ]; then
      echo "reduce: wrong number of args. called from ${FUNCNAME[1]}. $USAGE" >&2
      return 1
   fi

   if [ $1 = "all" ]; then
      VARS="PATH MANPATH PERL5LIB LD_LOAD_PATH LD_LIBRARY_PATH PYTHONPATH"
   else
      VARS="$@"
   fi

   # this function takes about 2 seconds

   [ $DEBUG = Y ] && (
      echo ""
      echo "reduce() is called by '${FUNCNAME[1]}'"
   )

   if [ "X$TP_REDUCE_DISABLE" = "XY" ]; then
      # reduce() is called from many functions.
      # reduce() takes a lot of time, therefore, we should miminalize the callings.
      # At the beginning of the site profile, we   set TP_REDUCE_DISABLE=Y flag.
      # At the end       of the site profile, we unset TP_REDUCE_DISABLE and run it once.
      [ $DEBUG = Y ] && (
         echo ""
         echo "skipped reduce() because TP_REDUCE_DISABLE=$TP_REDUCE_DISABLE"
      )
      return
   fi

   NOW=$(date +%s)
   if [ "X$TP_REDUCE_TIME" != "X" ]; then
      if [ "X$TP_REDUCE_THRESHOLD" != "X" ]; then
         INTERVAL=$((NOW - TP_REDUCE_TIME))
         if [ $INTERVAL -lt $TP_REDUCE_THRESHOLD ]; then
            cat >&2 <<END
WARN: two reduce() called in $INTERVAL seconds, within $TP_REDUCE_THRESHOLD seconds
      previous caller: $TP_REDUCE_CALLER
       current caller: ${FUNCNAME[1]}
END
         fi
      fi
   fi
   export TP_REDUCE_TIME=$NOW
   export TP_REDUCE_CALLER=${FUNCNAME[1]}

   REDUCEPATHCMD="$TPSUP/scripts/reducepath"

   if ! [ -f "$REDUCEPATHCMD" ]; then
      echo "$REDUCEPATHCMD is not found"
      return
   fi

   NEW_EXPORT=$($PERL_BINARY "$REDUCEPATHCMD" -e $FLAG $VARS)

   if [ "X$NEW_EXPORT" = "X" ]; then
      [ $DEBUG = Y ] && (
         echo ""
         echo "no change."
      )
      return
   fi

   eval "$NEW_EXPORT"
}
# https://askubuntu.com/questions/98782/how-to-run-an-alias-in-a-shell-script
# Aliases are deprecated in favor of shell functions. From the bash manual page:
# For almost every purpose, aliases are superseded by shell functions.

alias rm='rm -i'
alias mv='mv -i'
alias cp='cp -i'
alias grep='grep -i'
alias ls='ls -a'

tpsup() { . "$TPSUP/profile"; }

winhome() {
   # this works in cygwin and gitbash
   #
   # cygwin's home dir may not always be the same as cmd.exe's home dir = windows home dir
   # "C:/USERS/$USERNAME" is not always windows' home dir
   #
   # "$HOMEDRIVE/$HOMEPATH" is always the windows home dir
   #
   # test from cygwin
   #
   # $ echo "$HOMEDRIVE/$HOMEPATH"
   # H:/
   #
   # $ cd "$HOMEDRIVE/$HOMEPATH"
   # $ pwd
   # /cygdrive/h
   #
   cd "$HOMEDRIVE/$HOMEPATH"
}

chome() {
   # this works in cygwin and gitbash
   #
   # "C:/USERS/$USERNAME" is $USERPROFILE not always windows' home dir, but is the most active folder
   #
   # test from gitbash
   #
   # $ echo "$USERPROFILE"
   # C:\Users\william
   #
   # $ cd "$USERPROFILE"
   #
   # $ pwd
   # /c/Users/william
   #
   cd "$USERPROFILE"
}

if [ "X$TPSUPMODE" != "Xsafe" ]; then
   export PERL5LIB="$TPSUP/lib/perl:$PERL5LIB"
   PATH="$TPSUP/scripts:$PATH"
else
   export PERL5LIB="$PERL5LIB:$TPSUP/lib/perl"
   PATH="$TPSUP/autopath:$PATH"
fi

itrs() {
   local usage args yyyymmdd yyyy mm dd
   usage="
convert ITRS path from
   /apps/log/<today %Y%m%d>.log
to
   /apps/log/20200226.log

usage:    itrs command args

          itrs -r
          >> command args

example:  itrs ls '/apps/log/<today %Y%m%d>.log'

          itrs -r
          >> ls /apps/log/<today %Y%m%d>.log
   
"
   if [ $# -eq 0 ]; then
      echo "$usage"
      return
   fi

   yyyymmdd=$(date +%Y%m%d)
   yyyy=$(echo $yyyymmdd | cut -c1-4)
   mm=$(echo $yyyymmdd | cut -c5-6)
   dd=$(echo $yyyymmdd | cut -c7-8)

   if [ "$1" = "-r" ]; then
      echo -n ">> "
      read args
   else
      args="$@"
   fi

   args=$(echo "$args" | sed -e 's:%Y:$yyyy:g; s:%m:$mm:g; s:%d:$dd:g; s:<today[ ]*::g; s:>::g')

   eval "$args"
}

diffalias() {
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

   if [ $1 = snap ]; then
      alias >$dir/alias.txt
   elif [ $1 = diff ]; then
      alias >$dir/alias.txt.new
      diff $dir/alias.txt $dir/alias.txt.new
   else
      echo "$usage"
      return
   fi
}

myappdata() {
   local p
   p="C:\\Users\\$USERNAME\\AppData\\Roaming"
   p=$(convertpath "$p")
   cd "$p"
}

wintmp() {
   # go to user tmp dir
   if [[ $UNAME =~ Msys ]]; then
      USER_TMP=/c/users/$USERNAME/AppData/Local/Temp
   elif [[ $UNAME =~ Cygwin ]]; then
      USER_TMP=/cygdrive/c/users/$USERNAME/AppData/Local/Temp
   else
      echo "wintmp() on unsupported OS: $UNAME"
      return
   fi

   DAILY_TMP=$USER_TMP/daily/$(date +%Y%m%d)

   if [ -d $DALIY_TMP ]; then
      cd $DAILY_TMP
      return
   fi

   cd $USER_TMP
}

mytmp() {
   if [[ $UNAME =~ Msys ]]; then
      USER_TMP=/tmp/tmp_$USERNAME
   elif [[ $UNAME =~ Cygwin ]]; then
      USER_TMP=/tmp/tmp_$USERNAME
   elif [[ $UNAME =~ Linux ]]; then
      USER_TMP=/var/tmp/tmp_$USERNAME
   else
      echo "wintmp() on unsupported OS: $UNAME"
      return
   fi

   DAILY_TMP=$USER_TMP/$(date +%Y%m%d)

   if [ -d $DALIY_TMP ]; then
      cd $DAILY_TMP
      return
   fi

   cd $USER_TMP
}

functions() {
   typeset -F
   echo "to see detail: typeset -f"
}

cd "$TPSUP"/profile.d/
for f in *; do
   if [[ $f =~ [.~] ]]; then # regex
      # skip .sav, .deco, .yyyymmdd
      continue
   fi

   eval "function $f { . '$TPSUP/profile.d/$f'; }"
done
cd - >/dev/null

wbar() {
   # window bar
   TERM=xterm
   export TERM
   if [[ $TERM =~ ^xterm|^vt ]]; then
      PROMPT_COMMAND='echo -ne "\033]0;${USER}@${HOSTNAME}: ${PWD}\007"'
   fi
}

p2env() {
   pythonenv $@ 2
}

p3env() {
   pythonenv $@ 3
}

cdlatest() {
   latest_dir=$($TPSUP/scripts/cdlatest.bash "$@")

   if [ "X$latest_dir" != "X" ]; then
      cd $latest_dir
   fi
}

# p3env -q # default to python 3

if [[ $TERM =~ ^xterm|^vt ]]; then
   # we use PROMPT_COMMAND to manage title bar, it will not replace PS1.

   # on GitBash/Cygwin or home linux host, we normally don't ssh. therefore, no need for
   # ${USER}@${HOSTNAME}

   if [[ $UNAME =~ Msys|Cygwin || ${HOSTNAME} =~ linux1 ]]; then
      # bash head string ${MYVAR::3}
      # bas tail string  ${MYVAR: -3} # must have a space !!!
      # PROMPT_COMMAND only controls the terminal frame title.
      # we shorten the PWD part so that we can see the important part in task bar.
      if [[ $(sfc 2>&1 | tr -d '\0') =~ SCANNOW ]]; then
         PROMPT_COMMAND='echo -ne "\033]0;admin:${PWD: -15}\007"'
      else
         PROMPT_COMMAND='echo -ne "\033]0;${PWD: -15}\007"'
      fi
   else
      PROMPT_COMMAND='echo -ne "\033]0;${USER}@${HOSTNAME::10}:${PWD: -15}\007"'
   fi

   export PROMPT_COMMAND

   for cmd in vi vim less su; do
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
# -a export all functions and variables
set -a

# -b report background process immediately without waiting for the next prompt
set -b

set -o vi
#  Control-V, Backspace
if !stty erase  2>/dev/null; then
   :
fi

p3examples() { cd "$TPSUP/python3/examples"; }
sitebase() { cd "$SITEBASE"; }
export SPECNAME=$(basename "$SITESPEC")

tp() { cd "$TPSUP/scripts"; }
tpcmd() { cd "$TPSUP/bat"; }
tpps1() { cd "$TPSUP/ps1"; }
tplib() { cd "$TPSUP/lib/perl/TPSUP"; }
tpp3() { cd "$TPSUP/python3/scripts"; }
tpp3lib() { cd "$TPSUP/python3/lib/tpsup"; }

site() { cd "$SITESPEC/scripts"; }
sitecmd() { cd "$SITESPEC/bat"; }
siteps1() { cd "$SITESPEC/ps1"; }
sitelib() { cd "$SITESPEC/lib/perl/${SPECNAME^^}"; } # ${x,,} lower case, ${x^^} upper case
sitep3() { cd "$SITESPEC/python3/scripts"; }
sitep3lib() { cd "$SITESPEC/python3/lib/tpsup"; }

if [ "X$MYBASE" = "X" ]; then
   # inside company,
   #    we use $MYBASE to modify files and then rsync to $SITEBASE
   #    $MYBASE is for each developer, owned by each dev, and should run git here
   #    $SITEBASE should be owned by production id
   #
   # at home
   #    $MYBASE and $SITEBASE are the same, because they owned by the same id
   MYBASE=$SITEBASE
fi

mytp() { cd "$MYBASE/github/tpsup/scripts"; }
mytpcmd() { cd "$MYBASE/github/tpsup/bat"; }
mytpps1() { cd "$MYBASE/github/tpsup/ps1"; }
mytplib() { cd "$MYBASE/github/tpsup/lib/perl/TPSUP"; }
mytpp3() { cd "$MYBASE/github/tpsup/python3"; }
mytpp3lib() { cd "$MYBASE/github/tpsup/python3/lib/tpsup"; }

mycmd() { cd "$MYBASE/github/tpsup/bat"; }
myps1() { cd "$MYBASE/github/tpsup/ps1"; }
mylib() { cd "$MYBASE/github/tpsup/lib/perl/TPSUP"; }
myp3() { cd "$MYBASE/github/tpsup/python3"; }
myp3lib() { cd "$MYBASE/github/tpsup/python3/lib/tpsup"; }

mysite() { cd "$MYBASE/github/$SPECNAME/scripts"; }
mysitecmd() { cd "$MYBASE/github/$SPECNAME/bat"; }
mysiteps1() { cd "$MYBASE/github/$SPECNAME/ps1"; }
mysitelib() { cd "$MYBASE/github/$SPECNAME/lib/perl/${SPECNAME^^}"; } # ${x,,} lc, ${x^^} uc
mysitep3() { cd "$MYBASE/github/$SPECNAME/python3/scripts"; }
mysitep3lib() { cd "$MYBASE/github/$SPECNAME/python3/lib/tpsup"; }

myandroid() {
   echo "ANDROID_HOME=$ANDROID_HOME"
   [ "X$ANDROID_HOME" = "X" ] || cd "$ANDROID_HOME"
}

clear() {
   # https://superuser.com/questions/555554
   /usr/bin/clear
   printf "\033[03J" # this is needed for putty

   if [[ $UNAME =~ MINGW ]]; then
      # this gitbash
      if [ "X$TERM_PROGRAM" = "Xvscode" ]; then
         echo "click control+k to clear"
      fi
   fi
}

if ! [ "X$SSH_CLIENT" = "X" ]; then
   # $ env |grep SSH
   # SSH_CONNECTION=192.168.1.62 50334 192.168.1.191 22
   # SSH_CLIENT=192.168.1.62 50334 22
   # SSH_TTY=/dev/pts/4

   putty_client=$(echo $SSH_CLIENT | cut -d" " -f1)
   putty_client_file=~/.tpsup/putty_client.txt
   # echo "putty_client=$putty_client"
   # echo "putty_client_file=$putty_client_file"

   if [ -f "$putty_client_file" ]; then
      # putty_client_file format is
      # ip min_pos max_pos
      # 192.168.1.62 0 2
      line=$(egrep "^$putty_client\\s" $putty_client_file)
      if ! [ "X$line" = "X" ]; then
         min_pos=$(echo $line | awk '{print $2}')
         max_pos=$(echo $line | awk '{print $3}')
         # echo "puttypos $min_pos $max_pos"
         puttypos $min_pos $max_pos
      fi
   fi
fi
