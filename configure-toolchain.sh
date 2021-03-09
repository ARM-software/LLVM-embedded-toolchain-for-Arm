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

configure_toolchain() {
  # LLD does not have a good bare-metal builtin linker script (yet)
  cp "$SOURCE_ROOT_DIR/ldscript/base.ld" "$TARGET_LLVM_PATH/lib/clang-runtimes/${TARGET}/base.ld"

  # write config files

  # no semihosting and no linker script
  cat > "$TARGET_LLVM_PATH/bin/${TARGET}_nosys.cfg" <<-EOF
	--target=$TARGET
	-fuse-ld=lld
	-L\$@/../lib/clang-runtimes/$TARGET/lib
	\$@/../lib/clang-runtimes/$TARGET/lib/crt0.o
	-lnosys
	EOF

  # semihosting and linker script provided
  cat > "$TARGET_LLVM_PATH/bin/${TARGET}_rdimon.cfg" <<-EOF
	--target=$TARGET
	-fuse-ld=lld
	-Wl,-T\$@/../lib/clang-runtimes/$TARGET/base.ld
	-L\$@/../lib/clang-runtimes/$TARGET/lib
	\$@/../lib/clang-runtimes/$TARGET/lib/rdimon-crt0.o
	-lrdimon
	EOF

  # semihosting, but no linker script, e.g. to use with QEMU Arm System emulator
  cat > "$TARGET_LLVM_PATH/bin/${TARGET}_rdimon_baremetal.cfg" <<-EOF
	--target=$TARGET
	-fuse-ld=lld
	-L\$@/../lib/clang-runtimes/$TARGET/lib
	\$@/../lib/clang-runtimes/$TARGET/lib/rdimon-crt0.o
	-lrdimon
	EOF
}

export -f configure_toolchain

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  . $(dirname $BASH_SOURCE[0])/config.sh
  . $(dirname $BASH_SOURCE[0])/build-common.sh
  configure_toolchain
fi
