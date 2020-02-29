#!/bin/bash -i

# https://unix.stackexchange.com/questions/1496/why-doesnt-my-bash-script-recognize-aliases
# Aliases are not expanded when the shell is not interactive, unless the expand_aliases shell option is set using shopt (see the description of shopt under SHELL BUILTIN COMMANDS below).

# Therefore, add -i, to make the back interactive
# BUT NOTE: all the aliases printed are not from parent shell, they are from .bashrc !!!!

echo "from bash"
echo ---------------------------------------------------------
alias

echo
echo

# perl doesn't need to run with "perl -i"
echo "from perl"
echo ---------------------------------------------------------
perl -e 'system("bash -i -c alias")'

