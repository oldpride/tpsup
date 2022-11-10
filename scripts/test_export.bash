#!/bin/bash

# testreduce() is a function in site-spec/profile, it calls reduce() function.
# there used to be a problem when we call testreduce() from a script, we got error
#    reduce: command not found
# i already had "set -ab" to both site-spec/profile and tpsup/profile, but still
# got the error sometimes. Haven't found a root cause yet. 2021/02/05

testreduce;


# quick solution: run tpsup or siteenv.
