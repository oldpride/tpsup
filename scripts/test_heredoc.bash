#!/bin/bash

a=1
cmd="echo hello"

test_cat_with_quotes=$(cat <<'END'
a=$a
$($cmd)
END
)

test_cat_no_quotes=$(cat <<END
a=$a
$($cmd)
END
)

echo "$test_cat_with_quotes"
echo "$test_cat_no_quotes"
