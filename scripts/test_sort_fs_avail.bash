#!/bin/bash

# this is learned from JR of Bloomberg Ticker Plant Engineering Team

set -x

df -lk |grep -v avail|sort -rn +3
