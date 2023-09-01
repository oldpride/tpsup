#!/bin/bash

echo "to confirm this is bash. BASH_VERSION=$BASH_VERSION"

set -a    # export all variables
# set +a   to turn off

FROMINSIDE=1
export FROMINSIDEEXPORT=2


env |egrep ^FROMINSIDE

