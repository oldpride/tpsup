# https://tldp.org/LDP/abs/html/string-manipulation.html

# try using the bash build-in string manipulation instead of
# external commands like sed, awk, grep, expr, ...

stringZ=abcABC123ABCabc

echo "
----------------------------------------------------
String Length
These are the equivalent of strlen() in C.
"
echo "\$stringZ=$stringZ"
(
   set -x
   echo ${#stringZ}       # 15
   expr length $stringZ   # 15
   expr "$stringZ" : '.*' # 15
)

echo "
----------------------------------------------------
Length of Matching Substring at Beginning of String

expr match "\$string" regex

expr "\$string" : regex
"
echo "\$stringZ=$stringZ"
(
   set -x
   expr match "$stringZ" 'abc[A-Z]*.2' # 8
   # abc, followed by zero or more uppercase letters ([A-Z]*),
   # followed by any two characters (..),
   #   matches the beginning of $stringZ

   expr "$stringZ" : 'abc[A-Z]*.2' # 8
   # The same result as above, different notation.
)

echo "
----------------------------------------------------
Index

expr index \$string \$substring
Numerical position in \$string of first (any) character in \$substring 
that matches
note: the \$substring serves as a set of characters to match, 
      not a substring, nor a regex.
Length of Matching Substring at Beginning of String

"
echo "\$stringZ=$stringZ"
(
   set -x
   expr index "$stringZ" C12 # 6
   # C position.

   expr index "$stringZ" 1c # 3
   # 'c' (in #3 position) matches before '1'.
)

echo "
--------------------------------------------------------
Substring Extraction by position

\${string:position}
\${string:position:length}     0-based indexing, position starts at 0.

expr substr \$string \$position \$length
   1-based indexing, position starts at 1.
   Extracts \$length characters from \$string starting at \$position.
"
echo "\$stringZ=$stringZ"
(
   set -x
   echo "\${stringZ:0}=${stringZ:0}" # abcABC123ABCabc
   echo "\${stringZ:1}=${stringZ:1}" # bcABC123ABCabc
   echo "\${stringZ:7}=${stringZ:7}" # 23ABCabc

   echo "\${stringZ:7:3}=${stringZ:7:3}" # 23A
   # Three characters of substring.

   expr substr "$stringZ" 8 3 # 23A

   # Is it possible to index from the right end of the string?

   echo "\${stringZ:-4}=${stringZ:-4}" # abcABC123ABCabc
   # Defaults to full string, as in ${parameter:-default}.
   # However . . .

   echo "\${stringZ:(-4)}=${stringZ:(-4)}" # Cabc
   echo "\${stringZ: -4}=${stringZ: -4}"   # Cabc
   # Now, it works.
)

echo "
--------------------------------------------------------
substring extraction by regex

match from the beginning of the string
   expr match "\$string" '\(regex\)'
   expr "\$string" : '\(regex\)'

match from the end of the string
   expr match "\$string" '.*\(regex\)'
   expr "\$string" : '.*\(regex\)'

note:
   the \\(...\\) is to capture the substring.
   without the \\(...\\), the numeric position of the first character
   of the substring is returned.
"
echo "\$stringZ=$stringZ"
(
   set -x
   expr match "$stringZ" '\(.[b-c]*[A-Z]..[0-9]\)' # abcABC1
   expr "$stringZ" : '\(.[b-c]*[A-Z]..[0-9]\)'     # abcABC1
   expr "$stringZ" : '\(.......\)'                 # abcABC1
   # All of the above forms give an identical result.

   expr match "$stringZ" '.*\([A-C][A-C][A-C][a-c]*\)' # ABCabc
   expr "$stringZ" : '.*\(......\)'                    # ABCabc
)

echo "
--------------------------------------------------------
Substring Removal

\${string#regex}
   Remove from \$string the shortest part of \$regex that matches the front end of \$string. 
\${string##regex}
   Remove from \$string the longest part of \$regex that matches the front end of \$string.
\${string%regex}
   Remove from \$string the shortest part of \$regex that matches the back end of \$string.
\${string%%regex}
   Remove from \$string the longest part of \$regex that matches the back end of \$string.
"
echo "\$stringZ=$stringZ"
(
   echo "\${stringZ#a*C}=${stringZ#a*C}" # 123ABCabc
   # Strip out shortest match between 'a' and 'C', from front of $stringZ.

   echo "\${stringZ##a*C}=${stringZ##a*C}" # abc
   # Strip out longest match between 'a' and 'C', from front of $stringZ.

   echo "\${stringZ%b*c}=${stringZ%b*c}" # abcABC123ABCa
   # Strip out shortest match between 'b' and 'c', from back of $stringZ.

   echo "\${stringZ%%b*c}=${stringZ%%b*c}" # a
   # Strip out longest match between 'b' and 'c', from back of $stringZ.
)

echo "
--------------------------------------------------------
Substring Replacement using regex

note: bash regex wildcard is different from sed, awk, grep, expr, ...
      bash regex wildcard is similar to globbing, eg, ?, *, 
      bash regex wildcard is not similar to perl regex. eg, ., .*, .+

\${string/regex/replacement}
   Replace first match of \$regex with \$replacement.
\${string//regex/replacement}
   Replace all matches of \$regex with \$replacement.
\${string/#regex/replacement}
   If \$regex matches front end of \$string, substitute \$replacement for \$regex.
\${string/%regex/replacement}
   If \$regex matches back end of \$string, substitute \$replacement for \$regex.
"
echo "\$stringZ=$stringZ"
(
   echo "\${stringZ/[a-c]/X}=${stringZ/[a-c]/X}" # XbcABC123ABCabc
   # Replace first char in range [a-c] with 'X'.

   echo "\${stringZ//[a-c]/X}=${stringZ//[a-c]/X}" # XbXABC123ABCXbX
   # Replace all chars in range [a-c] with 'X'.

   echo "\${stringZ/#abc/XYZ}=${stringZ/#abc/XYZ}" # XYZABC123ABCabc
   # If $stringZ begins with 'abc', replace it with 'XYZ'.

   echo "\${stringZ/%abc/XYZ}=${stringZ/%abc/XYZ}" # abcABC123ABCXYZ
   # If $stringZ ends with 'abc', replace it with 'XYZ'.

   echo "\${stringZ/a?c/X}=${stringZ/a?c/X}" # XABC123ABCabc
   # Replace first match of 'a?c' (where ? can be any character) with 'X'.

   echo "\${stringZ//a*c/X}=${stringZ//a*c/X}" # X
   # Replace all matches of 'a*c' (where * can be any string) with 'X'.
)
