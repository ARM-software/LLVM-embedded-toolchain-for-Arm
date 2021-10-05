#!/bin/bash

if [ ! -d ./venv ]; then
    echo "Please run ./setup.sh"
    exit 1
fi

. ./venv/bin/activate
pip3 -q install -r requirements-lint.txt

echo "Checking with flake8"
flake8 scripts && echo 'No issues found'
echo "Checking with pylint"
pylint --rcfile=./scripts/.pylintrc --score=n scripts && echo 'No issues found'
echo "Checking with mypy"
mypy scripts
