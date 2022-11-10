#!/bin/bash

# bash hash array, ie, bash associated array

declare -A a1
a1[aa]=AA
a1[bb]=BB

echo "a1[aa]=${a1[aa]}"


declare -A b1=( [HDD]=Samsung [Monitor]=Dell [Keyboard]=A4Tech )
echo "b1[HDD]=${b1[HDD]}"

echo "keys=${!b1[@]}"
echo "values=${b1[@]}"

for key in ${!b1[@]}
do
   echo $key=$key
done

echo "added more data"
b1+=([Mouse]=Logitech)
echo "values=${b1[@]}"

echo "delete data"
unset b1[Monitor]
echo "b1[Monitor] = ${b1[Monitor]}"

echo "check key existence"
if [ ${b1[Monitor]+_} ]; then echo "Found"; else echo "Not found"; fi

echo "remove whole array"
unset b1
echo "b1=${b1[@]}"
