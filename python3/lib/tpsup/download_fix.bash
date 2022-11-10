#!/bin/bash

p3env

for version in `cat fix_supported_versions.txt`
do
	(set -x; download_fix.py $version ~/data/fix/$version)
done
