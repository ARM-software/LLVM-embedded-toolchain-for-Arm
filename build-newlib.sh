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

build_newlib () {
  pushToCleanDir $BUILD_DIR/newlib

  CC_FOR_TARGET="$TARGET_LLVM_PATH/bin/clang -target $TARGET -ffreestanding" \
  CXX_FOR_TARGET="$TARGET_LLVM_PATH/bin/clang++ -target $TARGET -ffreestanding" \
  AR_FOR_TARGET="$TARGET_LLVM_PATH/bin/llvm-ar" \
  NM_FOR_TARGET="$TARGET_LLVM_PATH/bin/llvm-nm" \
  AS_FOR_TARGET="$TARGET_LLVM_PATH/bin/llvm-as" \
  RANLIB_FOR_TARGET="$TARGET_LLVM_PATH/bin/llvm-ranlib" \
  STRIP_FOR_TARGET="$TARGET_LLVM_PATH/bin/llvm-strip" \
  READELF_FOR_TARGET="$TARGET_LLVM_PATH/bin/llvm-readelf" \
  OBJDUMP_FOR_TARGET="$TARGET_LLVM_PATH/bin/llvm-objdump" \
  $REPOS_DIR/newlib.git/configure --target=$TARGET \
    --prefix=$TARGET_LLVM_PATH \
    --exec-prefix="$TARGET_LLVM_PATH/targets" \
    --enable-newlib-io-long-long \
    --enable-newlib-register-fini \
    --disable-newlib-supplied-syscalls \
    --enable-newlib-io-c99-formats \
    --disable-nls \
    --enable-lite-exit

  make -j$NPROC
  make install

  popd
}

export -f build_newlib

# If this script is executed (and not sourced):
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  . $(dirname $BASH_SOURCE[0])/config.sh
  . $(dirname $BASH_SOURCE[0])/build-common.sh
  build_newlib
fi
