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

prepare_source() {
  if [ ! -x $VENV_DIR/bin/repos.py ]; then
    error "Python virtualenv problem. Have you run setup.sh ?"
  fi

  if [ "$RELEASE_MODE" -eq 1 ]; then
    if [ -d $BUILD_DIR ] && [ ! -z "$(ls $BUILD_DIR)" ]; then
      error "Build directory '$BUILD_DIR' already exists and is not empty."
    fi

    if [ -d $TARGET_LLVM_PATH ] && [ ! -z "$(ls $TARGET_LLVM_PATH)" ]; then
      error "Install directory '$TARGET_LLVM_PATH' already exists and is not empty."
    fi

    if [ -d $TARGET_LLVM_PATH ]; then
      chmod 755 $TARGET_LLVM_PATH
    fi
  fi

  if [ -d $REPOS_DIR ]; then
    $VENV_DIR/bin/repos.py -r "$VERSION" --repositories "$REPOS_DIR" check || error "Cannot proceed with building because repositories check failed."
  else
    $VENV_DIR/bin/repos.py -r "$VERSION" --repositories "$REPOS_DIR" --patches "$PATCHES_DIR" clone
  fi
}

export -f prepare_source

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  . $(dirname $BASH_SOURCE[0])/config.sh
  . $(dirname $BASH_SOURCE[0])/build-common.sh
  prepare_source
fi
