#!/bin/bash

# this is learned from JR of Bloomberg Ticker Plant Engineering Team

sum=0; while read A B C; do ((sum += B)); done <sum_one_line_test.txt; echo $sum
