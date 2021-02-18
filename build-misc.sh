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

build_misc () {
  [ "$#" -ne 0 ] && error "misc does not support variants."

  for D in ReleaseNotes UserGuide UserGuideBareMetal InstallGuide ABINotes; do
    rst2pdf -o $TARGET_LLVM_PATH/$D.pdf doc/$D.rst
  done

  cat >$TARGET_LLVM_PATH/LICENSES.txt <<EOF
Use of this package is subject to the terms of your written agreement with Arm.

This product embeds and uses the following pieces of software which have
additional or alternate licenses:
 - LLVM: thirdpartylicences/LLVM-LICENSE.txt
 - Clang: thirdpartylicences/CLANG-LICENSE.txt
 - lldb: thirdpartylicences/LLDB-LICENSE.txt
 - lld: thirdpartylicences/LLD-LICENSE.txt
 - libc++: thirdpartylicences/LIBCXX-LICENSE.txt
 - libc++abi: thirdpartylicences/LIBCXXABI-LICENSE.txt
 - libunwind: thirdpartylicences/LIBUNWIND-LICENSE.txt
 - libclc: thirdpartylicences/LIBCLC-LICENSE.TXT
 - llgo: thirdpartylicences/LLGO-LICENSE.TXT
 - openmp: thirdpartylicences/OPENMP-LICENSE.TXT
 - parallel-libs: thirdpartylicences/PARALLEL-LIBS-ACXXEL-LICENSE.TXT
 - polly: thirdpartylicences/POLLY-LICENSE.TXT
 - pstl: thirdpartylicences/PSTL-LICENSE.TXT
 - clang-tools-extra: thirdpartylicences/CLANG-TOOLS-EXTRA-LICENSE.TXT
 - compiler-rt: thirdpartylicences/COMPILER-RT-LICENSE.txt
 - newlib: thirdpartylicences/COPYING.NEWLIB
 - libgloss: thirdpartylicences/COPYING.LIBGLOSS
EOF

  [ -e $TARGET_LLVM_PATH/thirdpartylicences ] && rm -Rf $TARGET_LLVM_PATH/thirdpartylicences
  mkdir $TARGET_LLVM_PATH/thirdpartylicences
  cp $REPOS_DIR/llvm.git/llvm/LICENSE.TXT $TARGET_LLVM_PATH/thirdpartylicences/LLVM-LICENSE.TXT
  cp $REPOS_DIR/llvm.git/clang/LICENSE.TXT $TARGET_LLVM_PATH/thirdpartylicences/CLANG-LICENSE.TXT
  cp $REPOS_DIR/llvm.git/lldb/LICENSE.TXT $TARGET_LLVM_PATH/thirdpartylicences/LLDB-LICENSE.TXT
  cp $REPOS_DIR/llvm.git/lld/LICENSE.TXT $TARGET_LLVM_PATH/thirdpartylicences/LLD-LICENSE.TXT
  cp $REPOS_DIR/llvm.git/libcxx/LICENSE.TXT $TARGET_LLVM_PATH/thirdpartylicences/LIBCXX-LICENSE.TXT
  cp $REPOS_DIR/llvm.git/libcxxabi/LICENSE.TXT $TARGET_LLVM_PATH/thirdpartylicences/LIBCXXABI-LICENSE.TXT
  cp $REPOS_DIR/llvm.git/libunwind/LICENSE.TXT $TARGET_LLVM_PATH/thirdpartylicences/LIBUNWIND-LICENSE.TXT
  cp $REPOS_DIR/llvm.git/compiler-rt/LICENSE.TXT $TARGET_LLVM_PATH/thirdpartylicences/COMPILER-RT-LICENSE.TXT
  cp $REPOS_DIR/llvm.git/libclc/LICENSE.TXT $TARGET_LLVM_PATH/thirdpartylicences/LIBCLC-LICENSE.TXT
  cp $REPOS_DIR/llvm.git/llgo/LICENSE.TXT $TARGET_LLVM_PATH/thirdpartylicences/LLGO-LICENSE.TXT
  cp $REPOS_DIR/llvm.git/openmp/LICENSE.txt $TARGET_LLVM_PATH/thirdpartylicences/OPENMP-LICENSE.TXT
  cp $REPOS_DIR/llvm.git/parallel-libs/acxxel/LICENSE.TXT $TARGET_LLVM_PATH/thirdpartylicences/PARALLEL-LIBS-ACXXEL-LICENSE.TXT
  cp $REPOS_DIR/llvm.git/polly/LICENSE.txt $TARGET_LLVM_PATH/thirdpartylicences/POLLY-LICENSE.TXT
  cp $REPOS_DIR/llvm.git/pstl/LICENSE.txt $TARGET_LLVM_PATH/thirdpartylicences/PSTL-LICENSE.TXT
  cp $REPOS_DIR/llvm.git/clang-tools-extra/LICENSE.TXT $TARGET_LLVM_PATH/thirdpartylicences/CLANG-TOOLS-EXTRA-LICENSE.TXT
  cp $REPOS_DIR/newlib.git/COPYING.NEWLIB $TARGET_LLVM_PATH/thirdpartylicences/COPYING.NEWLIB
  cp $REPOS_DIR/newlib.git/COPYING.LIBGLOSS $TARGET_LLVM_PATH/thirdpartylicences/COPYING.LIBGLOSS

  # Install examples
  mkdir -p $TARGET_LLVM_PATH/examples
  cp examples/{*.txt,*.c,*.cpp,*.s} $TARGET_LLVM_PATH/examples
  sed -e "s!@TARGET_LLVM_PATH@!$TARGET_LLVM_PATH!" examples/Makefile.in > $TARGET_LLVM_PATH/examples/Makefile
  chmod 644 $TARGET_LLVM_PATH/examples/*
}

export -f build_misc

# If this script is executed (and not sourced):
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  . $(dirname $BASH_SOURCE[0])/config.sh
  . $(dirname $BASH_SOURCE[0])/build-common.sh
  build_misc
fi
