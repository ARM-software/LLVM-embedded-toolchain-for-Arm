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

# This file contains useful environment variables to control
# the building of the LLVM baremetal toolchain for Arm

readonly VERSION="${VERSION:-0.1}" # Use 'HEAD' for developement

# Path to the clang to use for building the LLVM baremetal toolchain for Arm:
readonly HOST_LLVM_PATH="${HOST_LLVM_PATH:-/usr/bin}"

# How many CPUs to use for building the LLVM baremetal toolchain for Arm:
readonly NPROC="${NPROC:-$(getconf _NPROCESSORS_ONLN)}"

# The Arm sub-arch we want to use:
readonly ARCH=${ARCH:-"armv6m"}

# Architecture options:
# (good overview: https://gcc.gnu.org/onlinedocs/gcc/ARM-Options.html)
readonly ARCH_OPTIONS=${ARCH_OPTIONS:-""}

# Float ABI
readonly FLOAT_ABI=${FLOAT_ABI:-"soft"}

#
# No modification should be necessary beyond this point.
#
# Default triple of the toolchain:
NEWLIB_FP_SUPPORT=false
if [ $FLOAT_ABI != "soft" ]; then
    NEWLIB_FP_SUPPORT=true
fi

readonly TARGET=$ARCH-none-eabi

# CFLAGS/ASM_FLAGS
readonly FLAGS="-mfloat-abi=${FLOAT_ABI} -march=${ARCH}${ARCH_OPTIONS}"

readonly SOURCE_ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Install directory of the LLVM baremetal toolchain for Arm:
readonly INSTALL_ROOT_DIR=${INSTALL_ROOT_DIR:-$SOURCE_ROOT_DIR}

if [ "$VERSION" == 'HEAD' ]; then
  readonly VERSION_STRING=$(date "+%F-%T")
  readonly VERSION_SUFFIX=''
  readonly RELEASE_MODE=0
else
  readonly VERSION_STRING="${VERSION}"
  readonly VERSION_SUFFIX="-${VERSION_STRING}"
  readonly RELEASE_MODE=1
fi

readonly PKG_VERSION_SUFFIX="-${VERSION_STRING}"
readonly TARGET_LLVM_PATH=$INSTALL_ROOT_DIR/LLVMEmbeddedToolchainForArm$VERSION_SUFFIX
readonly BUILD_DIR=$SOURCE_ROOT_DIR/build$VERSION_SUFFIX
readonly REPOS_DIR=$SOURCE_ROOT_DIR/repos$VERSION_SUFFIX
readonly PATCHES_DIR=$SOURCE_ROOT_DIR/patches
readonly VENV_DIR=$SOURCE_ROOT_DIR/venv

readonly USE_CCACHE=${USE_CCACHE:-0}
readonly USE_NINJA=${USE_NINJA:-0}

export VERSION HOST_LLVM_PATH NPROC SOURCE_ROOT_DIR VERSION_STRING \
       VERSION_SUFFIX RELEASE_MODE INSTALL_ROOT_DIR PKG_VERSION_SUFFIX \
       BUILD_DIR REPOS_DIR TARGET_LLVM_PATH VENV_DIR USE_CCACHE \
       USE_NINJA

umask 022

set -u
set -e
set -o pipefail
