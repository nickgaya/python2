#! /bin/bash

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 PY2 PY3" >&2
    exit 2
fi 

py2=$1
py3=$2
shift 2

args=("$@")
if [ ${#args[@]} -eq 0 ]; then
    args=(tests/integration/)
fi

set -x

build/tox/"$py3"/bin/pytest --python2=build/tox/"$py2"/bin/python "${args[@]}"
