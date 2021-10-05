#!/bin/bash

#
# Copyright (c) 2020, Arm Limited and affiliates.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
set -e

# If your python3 is not just "python3" edit this
PYTHON3=python3

python_err="Error: Python 3.6 or newer is required."
if command -v "$PYTHON3" --version &> /dev/null
then
  pyv=$("$PYTHON3" -c 'from sys import version_info; print("".join(map(str, (version_info.major, version_info.minor))))')
  if [ "$pyv" -lt 36 ]
  then
    echo "$python_err" && exit 1
  fi
else
  echo "$python_err" && exit 1
fi

"$PYTHON3" -m venv venv

. venv/bin/activate

cd "$(dirname "$0")"

pip install --upgrade pip
pip install --upgrade wheel
pip install --upgrade setuptools
pip install -r requirements.txt
pip install -e scripts
