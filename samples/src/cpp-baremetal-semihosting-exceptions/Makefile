#
# Copyright (c) 2024, Arm Limited and affiliates.
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

build: hello.hex hello-exn.hex

hello.hex: hello.cpp
	$(BIN_PATH)/clang++ $(MICROBIT_TARGET) $(CRT_SEMIHOST) $(CPP_FLAGS) -print-multi-directory -g -T ../../ldscripts/microbit.ld -o hello.elf $^ | grep -v "_exn_"
	$(BIN_PATH)/clang++ $(MICROBIT_TARGET) $(CRT_SEMIHOST) $(CPP_FLAGS) -g -T ../../ldscripts/microbit.ld -o hello.elf $^
	$(BIN_PATH)/llvm-objcopy -O ihex hello.elf hello.hex

hello-exn.hex: hello-exn.cpp
	$(BIN_PATH)/clang++ $(MICROBIT_TARGET) $(CRT_SEMIHOST) -print-multi-directory -g -T ../../ldscripts/microbit.ld -o hello-exn.elf $^ | grep "_exn_"
	$(BIN_PATH)/clang++ $(MICROBIT_TARGET) $(CRT_SEMIHOST) -g -T ../../ldscripts/microbit.ld -o hello-exn.elf $^
	$(BIN_PATH)/llvm-objcopy -O ihex hello-exn.elf hello-exn.hex

run: hello.hex hello-exn.hex
	qemu-system-arm -M microbit -semihosting -nographic -device loader,file=hello.hex
	qemu-system-arm -M microbit -semihosting -nographic -device loader,file=hello-exn.hex 2>&1 | grep "caught"

clean:
	rm -f *.elf *.hex

.PHONY: clean run
