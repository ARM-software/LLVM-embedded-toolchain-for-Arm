#
# Copyright (c) 2023, Arm Limited and affiliates.
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
build-trap: hello-trap.elf

hello.elf: *.cpp		# build with minimal runtime mode
	$(BIN_PATH)/clang++ $(MICROBIT_TARGET) $(CRT_SEMIHOST) $(CPP_FLAGS) --std=c++17 -fsanitize=undefined -fsanitize-minimal-runtime -g -T ../../ldscripts/microbit.ld -o hello.elf $^

hello-trap.elf: *.cpp 	# build with trap mode
	$(BIN_PATH)/clang++ $(MICROBIT_TARGET) $(CRT_SEMIHOST) $(CPP_FLAGS) --std=c++17 -fsanitize=undefined -fsanitize-trap=all -g -T ../../ldscripts/microbit.ld -o hello.elf $^

%.hex: %.elf
	$(BIN_PATH)/llvm-objcopy -O ihex $< $@

run: hello.hex
	qemu-system-arm -M microbit -semihosting -nographic -device loader,file=$<

debug: hello.hex
	qemu-system-arm -M microbit -semihosting -nographic -device loader,file=$< -s -S

clean:
	rm -f *.elf *.hex

.PHONY: clean run debug
