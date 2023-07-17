#
# Copyright (c) 2020-2023, Arm Limited and affiliates.
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

hello.elf: *.c
	$(BIN_PATH)/clang $(AARCH64_TARGET) $(CRT_SEMIHOST) -g -T ../../ldscripts/raspi3b.ld -o hello.elf $^

%.img: %.elf
	$(BIN_PATH)/llvm-objcopy -O binary $< $@

run: hello.img
	qemu-system-aarch64 -M raspi3b -semihosting -nographic -kernel $<

debug: hello.img
	qemu-system-aarch64 -M raspi3b -semihosting -nographic -kernel $< -s -S

clean:
	rm -f *.elf *.img

.PHONY: clean run debug
