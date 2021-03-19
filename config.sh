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


LIBRARY_SPEC="${LIBRARY_SPEC:-armv6m_soft_nofp}"

case $LIBRARY_SPEC in
    "armv8.1m.main_hard_fp")
        ARCH="armv8.1m.main"
        ARCH_OPTIONS="+fp"
        FLOAT_ABI="hard"
        ;;
    "armv8.1m.main_hard_nofp_mve")
        ARCH="armv8.1m.main"
        ARCH_OPTIONS="+nofp+mve"
        FLOAT_ABI="hard"
        NEWLIB_FP_SUPPORT=false
        ;;
    "armv8.1m.main_soft_nofp_nomve")
        ARCH="armv8.1m.main"
        ARCH_OPTIONS="+nofp+nomve"
        FLOAT_ABI="soft"
        ;;
    "armv8m.main_hard_fp")
        ARCH="armv8m.main"
        ARCH_OPTIONS="+fp"
        FLOAT_ABI="hard"
        ;;
    "armv8m.main_soft_nofp")
        ARCH="armv8m.main"
        ARCH_OPTIONS="+nofp"
        FLOAT_ABI="soft"
        ;;
    "armv7em_hard_fpv4_sp_d16")
        ARCH="armv7em"
        ARCH_OPTIONS=""
        OTHER_FLAGS="-mfpu=fpv4-sp-d16"
        FLOAT_ABI="hard"
        ;;
    "armv7em_hard_fpv5_d16")
        ARCH="armv7em"
        ARCH_OPTIONS=""
        OTHER_FLAGS="-mfpu=fpv5-d16"
        FLOAT_ABI="hard"
        ;;
    "armv7em_soft_nofp")
        ARCH="armv7em"
        ARCH_OPTIONS=""
        OTHER_FLAGS="-mfpu=none"
        FLOAT_ABI="soft"
        ;;
    "armv7m_soft_nofp")
        ARCH="armv7m"
        ARCH_OPTIONS="+nofp"
        FLOAT_ABI="soft"
        ;;
    "armv6m_soft_nofp")
        ARCH="armv6m"
        ARCH_OPTIONS=""
        FLOAT_ABI="soft"
        ;;
    *)
        echo "LIBRARY_SPEC option not recognized: `$LIBRARY_SPEC`!!"
        exit 1
        ;;
esac

#
# No modification should be necessary beyond this point.
#
# set to true if we need to compile the newlib fp maths variants
if [ $FLOAT_ABI != "soft" ]; then
    NEWLIB_FP_SUPPORT=${NEWLIB_FP_SUPPORT:-true}
else
    NEWLIB_FP_SUPPORT=false
fi

# Default triple of the toolchain
readonly TARGET=$ARCH-none-eabi

OTHER_FLAGS=${OTHER_FLAGS:-""}

# CFLAGS/ASM_FLAGS
readonly FLAGS="-mfloat-abi=${FLOAT_ABI} -march=${ARCH}${ARCH_OPTIONS} ${OTHER_FLAGS}"

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
