#!/bin/bash

if [ ! -d ./venv ]; then
    echo "Please run ./setup.sh"
    exit 1
fi

. ./venv/bin/activate
pip3 -q install -r requirements-lint.txt

echo "Checking with CMakeLint"
cmakelint CMakeLists.txt
