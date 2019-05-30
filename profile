set -o vi

UNAME=`uname -a`

# MINGW64_NT-10.0 LAPTOP-4DDGKLFF 2.11.2(0.329/5/3) 2018-11-10 14:38 x86_64 Msys
# CYGWIN_NT-10.0 LAPTOP-4DDGKLFF 3.0.4(0.338/5/3) 2019-03-16 09:50 x86_64 Cygwin

if [[ $UNAME =~ Msys ]]; then
   alias perllib='cd /c/Users/william/github/tpsup/lib/perl5/TPSUP'
   alias tpscripts='cd /c/Users/william/github/tpsup/scripts'
   export PERL5LIB=/c/Users/william/github/tpsup/lib/perl5/TPSUP
   export PATH="$PATH:/c/Users/william/github/tpsup/scripts"
elif [[ $UNAME =~ Cygwin ]]; then
   alias perllib='cd /cygdrive/c/Users/william/github/tpsup/lib/perl5/TPSUP'
   alias tpscripts='cd /cygdrive/c/Users/william/github/tpsup/scripts'
   export PERL5LIB=/cygdrive/c/Users/william/github/tpsup/lib/perl5
   export PATH="$PATH:/cygdrive/c/Users/william/github/tpsup/scripts"
else 
   echo "UNAME='$UNAME' is not supported"
fi

