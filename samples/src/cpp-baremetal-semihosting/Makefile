#
# Copyright (c) 2021, Arm Limited and affiliates.
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

include ../../Makefile.conf

build: hello.elf

hello.elf: *.cpp
	$(BIN_PATH)/clang++ --config armv6m_soft_nofp_rdimon_baremetal -g -T ../../ldscripts/microbit.ld -o hello.elf ../../startup/startup_ARMCM0.S $^

%.hex: %.elf
	$(BIN_PATH)/llvm-objcopy -O ihex $< $@

# -m option is a workaround to ensure correct initialization of semihosting
run: hello.hex
	qemu-system-arm -M microbit -semihosting -nographic -device loader,file=$< -m 1073741824k

debug: hello.hex
	qemu-system-arm -M microbit -semihosting -nographic -device loader,file=$< -m 1073741824k -s -S

clean:
	rm -f *.elf *.hex

.PHONY: clean run debug
