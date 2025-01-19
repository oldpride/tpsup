#!/bin/bash

line="echo cmd"
for i in {0..29}; do
   line+=" arg$i"
done
echo "$line"
