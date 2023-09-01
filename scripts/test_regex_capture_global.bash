#!/bin/bash

# https://unix.stackexchange.com/questions/251013
# bash regex doesn't support global (repeating) match;
# the following is a workaround for global (repeating) match

global_rematch() {
   local s=$1 regex=$2

   while [[ $s =~ $regex ]]; do
      # ${BASH_REMATCH[0]} is the entire matched string.
      # ${BASH_REMATCH[1]} is the first captured group.
      echo "${BASH_REMATCH[1]}"

      # bash string manipulation
      # https://tldp.org/LDP/abs/html/string-manipulation.html
      # ${var#Pattern} substring removal
      #     Remove from $var the shortest part of $Pattern that
      #     matches the front end of $var.}}
      # note:
      #    below * is a wildcard.
      #    double quotes is to prevent globbing and word splitting.
      s=${s#*"${BASH_REMATCH[1]}"}
   done

   echo "final s=$s"

}

mystring1='<link rel="self" href="/api/clouds/1/instances/1AAAAA"/> dsf <link rel="self" href="/api/clouds/1/instances/2BBBBB"/>'

regex='/instances/([A-Z0-9]+)'

global_rematch "$mystring1" "$regex"

mapfile -t myArray < <(global_rematch "$mystring1" "$regex")
# <(...)              is command output as a file name
# mapfile myArray     mapfile is a bash build-in, assigning the stdin to myArray.
# -t                  trim trailing delimiters, ie, newline

echo "\${myArray[@]} = ${myArray[@]}"
echo "\${myArray[0]} = ${myArray[0]}"
