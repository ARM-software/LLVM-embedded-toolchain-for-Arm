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

# Default triple of the toolchain:
readonly TARGET=armv6m-none-eabi

#
# No modification should be necessary beyond this point.
#
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
readonly USE_PARALLEL=${USE_PARALLEL:-0}
readonly USE_NINJA=${USE_NINJA:-0}

export VERSION HOST_LLVM_PATH NPROC SOURCE_ROOT_DIR VERSION_STRING \
       VERSION_SUFFIX RELEASE_MODE INSTALL_ROOT_DIR PKG_VERSION_SUFFIX \
       BUILD_DIR REPOS_DIR TARGET_LLVM_PATH VENV_DIR USE_CCACHE \
       USE_PARALLEL USE_NINJA

umask 022

set -u
set -e
set -o pipefail
