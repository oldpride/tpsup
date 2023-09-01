#!/bin/bash

check_only=N

prog=`basename $0`

usage () {
   cat <<EOF
usage:

   $prog  url

   -v     verbose

example:

   $prog "https://fundresearch.fidelity.com/mutual-funds/fees-and-prices/316343201"

EOF

   exit 1
}

verbose=N

while getopts v o;
do
   case "$o" in
      v) verbose=Y;;
      *) echo "unknow switch '$o'"; usage;;
   esac
done

shift $((OPTIND-1))

if [ $# -ne 1 ]; then
   echo "wrong number of args"
   usage
fi

url=$1

set -x
perl -MIO::Socket::SSL=debug4 -MWWW::Mechanize -e "WWW::Mechanize->new()->get('$url')"


