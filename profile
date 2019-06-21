set -o vi

UNAME=`uname -a`

# MINGW64_NT-10.0 LAPTOP-4DDGKLFF 2.11.2(0.329/5/3) 2018-11-10 14:38 x86_64 Msys
# CYGWIN_NT-10.0 LAPTOP-4DDGKLFF 3.0.4(0.338/5/3) 2019-03-16 09:50 x86_64 Cygwin

if [[ $UNAME =~ Msys ]]; then
   export TPSUP=~/github/tpsup
   alias perllib='cd /c/Users/william/github/tpsup/lib/perl/TPSUP'
   alias tpscripts='cd /c/Users/william/github/tpsup/scripts'
   alias tpsup='. ~/github/tpsup/profile'
   export PERL5LIB=/c/Users/william/github/tpsup/lib/perl/TPSUP
   export PYTHONPATH=/c/Users/william/github/tpsup/python2/lib
   export PATH="$PATH:/c/Users/william/github/tpsup/scripts"
elif [[ $UNAME =~ Cygwin ]]; then
   export TPSUP=/cygdrive/c/Users/william/github/tpsup
   alias perllib='cd /cygdrive/c/Users/william/github/tpsup/lib/perl/TPSUP'
   alias tpscripts='cd /cygdrive/c/Users/william/github/tpsup/scripts'
   alias tpsup='. /cygdrive/c/Users/william/github/tpsup/profile'
   export PERL5LIB=/cygdrive/c/Users/william/github/tpsup/lib/perl
   export PYTHONPATH=/cygdrive/c/Users/william/github/tpsup/python2/lib
   export PATH="$PATH:/cygdrive/c/Users/william/github/tpsup/scripts"
elif [[ $UNAME =~ Linux ]]; then
   export TPSUP=~/github/tpsup
   alias perllib='cd ~/github/tpsup/lib/perl/TPSUP'
   alias tpscripts='cd ~/github/tpsup/scripts'
   alias tpsup='. ~/github/tpsup/profile'
   export PERL5LIB=$HOME/github/tpsup/lib/perl
   export PYTHONPATH=$HOME/github/tpsup/python2/lib
   export PATH="$PATH:$HOME/github/tpsup/scripts"
else 
   echo "UNAME='$UNAME' is not supported"
fi

set -o vi


