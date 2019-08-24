#!/bin/bash

p3env

for version in `cat fix_supported_versions.txt`
do
	output=fix.$version.py

	if [ -f $output ]; then
		echo "$output already exists, skipped."
		continue
	fi
	(set -x; parse_fix_download.py ~/data/fix/$version $output)
done
