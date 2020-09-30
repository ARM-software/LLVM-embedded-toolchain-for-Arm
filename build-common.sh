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

# This file contains common routines, shared amongst components build scripts.

error () {
  set +u
  echo "$0: error: $@" >&2
  set -u
  exit 1
}

warning () {
  set +u
  echo "$0: warning: $@" >&2
  set -u
}

checkPrograms () {
  for p in $@; do
    local prog=`which $p`
    if [ -z $prog ]; then
      error "'$p' is required to build the toolchain."
    fi
  done
}

moveMerge () {
  local SRC_DIR="$1"
  local DEST_DIR="$2"

  (cd "$SRC_DIR" && \
    find . -type d -exec mkdir -p "$DEST_DIR"/\{} \; && \
    find . -type f -exec mv \{} "$DEST_DIR"/\{} \; && \
    find . -type d -empty -delete)
}

# Clean DIR if it exists, or create an empty one, and pushd to it.
pushToCleanDir () {
  local DIR="$1"
  [ -d $DIR ] && rm -Rf $DIR
  mkdir -p $DIR

  pushd $DIR
}

# Build using either ninja or make
build () {
  if [ $USE_NINJA -ne 0 ]; then
    ninja "$@"
  else
    make -j$NPROC "$@"
  fi
}

# Install using either ninja or make
install () {
  if [ $USE_NINJA -ne 0 ]; then
    ninja install
  else
    make install
  fi
}

# Get the CMake generator to use
cmakeUseGenerator () {
  if [ $USE_NINJA -ne 0 ]; then
    echo "-G Ninja"
  fi
}

# Tell CMake to use ccache
cmakeUseCCache () {
  if [ $USE_CCACHE -ne 0 ]; then
    echo "-DCMAKE_C_COMPILER_LAUNCHER:STRING=ccache -DCMAKE_CXX_COMPILER_LAUNCHER:STRING=ccache"
  fi
}

# Return whether the first version is less than the second one. Comparison uses
# natural sort of version numbers. For instance, calling
# `versionLessThan 3.10.1 3.5.2` yields 0.
versionLessThan () {
  [ "$1" != "$2" ] && [ "$1" = "$(printf "$1\n$2\n" | sort -V |  head -n1)" ]
}

export -f error warning checkPrograms moveMerge pushToCleanDir build install \
  cmakeUseGenerator cmakeUseCCache versionLessThan
