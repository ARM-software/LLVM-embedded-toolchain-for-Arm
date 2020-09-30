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

package_toolchain() {
  echo "$VERSION_STRING" > $TARGET_LLVM_PATH/VERSION.txt

  if [ "$RELEASE_MODE" -eq 1 ]; then
    (cd $(dirname $TARGET_LLVM_PATH) && tar --create --file=$SOURCE_ROOT_DIR/LLVMEmbeddedToolchainForArm${PKG_VERSION_SUFFIX}.tar.gz -a --owner=root --group=root $(basename $TARGET_LLVM_PATH))
    (cd $REPOS_DIR && tar --create --file=$SOURCE_ROOT_DIR/LLVMEmbeddedToolchainForArm${PKG_VERSION_SUFFIX}-src.tar.gz -a --owner=root --group=root --transform="flags=rSh;s,^\.,LLVMEmbeddedToolchainForArm${PKG_VERSION_SUFFIX}," --exclude-vcs .)
  fi
}

export -f package_toolchain

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  . $(dirname $BASH_SOURCE[0])/config.sh
  . $(dirname $BASH_SOURCE[0])/build-common.sh
  package_toolchain
fi
