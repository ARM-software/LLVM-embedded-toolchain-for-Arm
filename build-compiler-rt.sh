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

build_compilerrt () {
  pushToCleanDir $BUILD_DIR/compiler-rt

  cmake \
    $(cmakeUseGenerator) \
    $REPOS_DIR/llvm.git/compiler-rt \
    -DCMAKE_BUILD_TYPE=Release \
    -DCOMPILER_RT_BUILD_SANITIZERS:BOOL=OFF \
    -DCOMPILER_RT_BUILD_XRAY:BOOL=OFF \
    -DCOMPILER_RT_BUILD_LIBFUZZER:BOOL=OFF \
    -DCOMPILER_RT_BUILD_PROFILE:BOOL=OFF \
    -DCOMPILER_RT_BAREMETAL_BUILD:BOOL=ON \
    -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY \
    -DCMAKE_C_COMPILER_TARGET="$TARGET" \
    -DCMAKE_ASM_COMPILER_TARGET="$TARGET" \
    -DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON \
    -DLLVM_CONFIG_PATH="$BUILD_DIR/llvm/bin/llvm-config" \
    -DCMAKE_C_COMPILER="$TARGET_LLVM_PATH/bin/clang" \
    -DCMAKE_AR="$TARGET_LLVM_PATH/bin/llvm-ar" \
    -DCMAKE_NM="$TARGET_LLVM_PATH/bin/llvm-nm" \
    -DCMAKE_RANLIB="$TARGET_LLVM_PATH/bin/llvm-ranlib" \
    -DCMAKE_EXE_LINKER_FLAGS="-fuse-ld=lld" \
    -DCMAKE_INSTALL_PREFIX="$TARGET_LLVM_PATH/lib/clang-runtimes/$TARGET"

  build

  install

  # Cleanup the no longer necessary installed dir
  mv "$TARGET_LLVM_PATH/lib/clang-runtimes/$TARGET/lib/linux/"* "$TARGET_LLVM_PATH/lib/clang-runtimes/$TARGET/lib/"
  rmdir "$TARGET_LLVM_PATH/lib/clang-runtimes/$TARGET/lib/linux"

  popd
}

export -f build_compilerrt

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  . $(dirname $BASH_SOURCE[0])/config.sh
  . $(dirname $BASH_SOURCE[0])/build-common.sh
  build_compilerrt
fi
