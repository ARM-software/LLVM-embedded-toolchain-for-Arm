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

#!/bin/bash

build_clang () {
  mkdir -p $BUILD_DIR/llvm

  pushd $BUILD_DIR/llvm

  Projs=(
    "clang"
    "lld"
    "lldb"
  )
  llvmProjs=$(IFS=\; ; echo "${Projs[*]}")

  DistComps=(
    "clang-format"
    "clang-resource-headers"
    "clang"
    "dsymutil"
    "lld"
    "llvm-ar"
    "llvm-config"
    "llvm-cov"
    "llvm-cxxfilt"
    "llvm-dwarfdump"
    "llvm-nm"
    "llvm-objdump"
    "llvm-profdata"
    "llvm-ranlib"
    "llvm-readelf"
    "llvm-readobj"
    "llvm-size"
    "llvm-strip"
    "llvm-symbolizer"
    "LTO"
  )
  llvmDistComps=$(IFS=\; ; echo "${DistComps[*]}")

  CC=${HOST_LLVM_PATH}/clang \
  CXX=${HOST_LLVM_PATH}/clang++ \
  cmake \
    -DLLVM_TARGETS_TO_BUILD:STRING="ARM" \
    -DLLVM_DEFAULT_TARGET_TRIPLE:STRING="$TARGET" \
    -DCMAKE_BUILD_TYPE:STRING=Release \
    -DCMAKE_INSTALL_PREFIX:STRING=$TARGET_LLVM_PATH \
    -DLLVM_ENABLE_PROJECTS:STRING="$llvmProjs" \
    -DLLVM_DISTRIBUTION_COMPONENTS:STRING="$llvmDistComps" \
    $(cmakeUseCCache) \
    $(cmakeUseGenerator) \
    $REPOS_DIR/llvm.git/llvm

  build install-distribution-stripped

  popd

  if [ "$RELEASE_MODE" -eq 1 ]; then
    # Record the list of files and links installed by clang
    (cd $(dirname $TARGET_LLVM_PATH) && find $(basename $TARGET_LLVM_PATH) -type f -o -type l | sort > $BUILD_DIR/llvm-index.txt)
  fi
}

export -f build_clang

# If this script is executed (and not sourced):
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  . $(dirname $BASH_SOURCE[0])/config.sh
  . $(dirname $BASH_SOURCE[0])/build-common.sh
  build_clang
fi
