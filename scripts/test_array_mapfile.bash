#!/bin/bash

# mapfile is a bash build-in
# $ man bash
# mapfile [-d delim] [-n count] [-O origin] [-s count] [-t] [-u fd] [-C  callback]  [-c
#      quantum] [array]
#      readarray [-d delim] [-n count] [-O origin] [-s count] [-t] [-u fd] [-C callback] [-c
#      quantum] [array]
#             Read lines from the standard input into the indexed array variable  array,  or
#             from file descriptor fd if the -u option is supplied.  The variable MAPFILE is
#             the default array.  Options, if supplied, have the following meanings:
#             -d     The first character of delim is used  to  terminate  each  input  line,
#                    rather than newline.  If delim is the empty string, mapfile will termi‐
#                    nate a line when it reads a NUL character.
#             -n     Copy at most count lines.  If count is 0, all lines are copied.
#             -O     Begin assigning to array at index origin.  The default index is 0.
#             -s     Discard the first count lines read.
#             -t     Remove a trailing delim (default newline) from each line read.
#             -u     Read lines from file descriptor fd instead of the standard input.
#             -C     Evaluate callback each time quantum lines  are  read.   The  -c  option
#                    specifies quantum.
#             -c     Specify the number of lines read between each call to callback.
#
#             If  -C is specified without -c, the default quantum is 5000.  When callback is
#             evaluated, it is supplied the index of the next array element to  be  assigned
#             and the line to be assigned to that element as additional arguments.  callback
#             is evaluated after the line is read but before the array element is assigned.
#
#             If not supplied with an explicit origin, mapfile will clear array  before  as‐
#             signing to it.
#
#             mapfile  returns  successfully  unless an invalid option or option argument is
#             supplied, array is invalid or unassignable, or if array is not an indexed  ar‐
#             ray.

mapfile -t myArray < <(echo a; echo b; echo c;)
# <(...) is command output

for e in ${myArray[@]}; do
  echo $e
done

echo "\${myArray[@]} = ${myArray[@]}"
echo "\${myArray[0]} = ${myArray[0]}"

myArray=("d", "e", "f")
echo "\${myArray[@]} = ${myArray[@]}"



