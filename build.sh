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

. $(dirname $BASH_SOURCE[0])/config.sh
. $(dirname $BASH_SOURCE[0])/prepare-source.sh
for E in common clang newlib compiler-rt; do
  . $(dirname $BASH_SOURCE[0])/build-${E}.sh
done
. $(dirname $BASH_SOURCE[0])/configure-toolchain.sh
. $(dirname $BASH_SOURCE[0])/package-toolchain.sh

checkPrograms git cmake make ${HOST_LLVM_PATH}/clang ${HOST_LLVM_PATH}/clang++ find sort tar sed

# Ensure clang is recent enough.
CLANG_VERSION=$(${HOST_LLVM_PATH}/clang --version | grep 'clang version ' | cut -d ' ' -f3)
if versionLessThan "$CLANG_VERSION" "6.0.0"; then
  error "Your ${HOST_LLVM_PATH}/clang version ${CLANG_VERSION} is not recent enough. Please upgrade it to at least 6.0.0"
fi

# Ensure CMake is recent enough. LLVM now requires at least cmake version 3.13.4 to build.
CMAKE_VERSION=$(cmake --version | grep 'cmake version ' | sed -e's/.* //')
if versionLessThan "$CMAKE_VERSION" "3.13.4"; then
  error "Your cmake version ${CMAKE_VERSION} is not recent enough. Please upgrade it to at least 3.13.4."
fi

# If we use CCache, ensure it is recent enough. Older versions do weird things with clang.
if [ $USE_CCACHE -ne 0 ]; then
  CCACHE_VERSION=$(ccache --version | grep 'ccache version ' | sed -e's/.* //')
  if versionLessThan "$CCACHE_VERSION" "3.2.5"; then
    error "Your ccache version ${CCACHE_VERSION} is not recent enough. Please upgrade it to at least 3.2.5."
  fi
fi

# Define the default build steps if no argument is given
if [ "$#" -eq 0 ]; then
    set -- prepare clang newlib compilerrt configure package
fi

# Add examples, documentation, licensing info, ...
# build_misc

# Execute the build steps, one by one
while [ "$#" -gt 0 ]; do
  echo "# Executing step '$1'"
  case "$1" in
    clang|newlib|compilerrt)
      build_$1
      ;;
    configure)
      configure_toolchain
      ;;
    prepare)
      prepare_source
      ;;
    package)
      package_toolchain
      ;;
    *)
      echo "error: unknown step to execute '$1'" >&2
      exit 1
      ;;
  esac
  echo "# Done step '$1'"
  shift
done
