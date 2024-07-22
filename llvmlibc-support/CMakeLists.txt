#
# Copyright (c) 2022, Arm Limited and affiliates.
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

# This directory builds two additional library files to go with llvm-libc:
#
# libcrt0.a contains an implementation of the _start() default entry point,
# which sets up the stack and does any necessary initialization before
# calling main().
#
# libsemihost.a implements llvm-libc's porting function API such as
# __llvm_libc_stdio_write, in terms of the Arm semihosting system.
#
# To use LLVM libc in a semihosting context, include both of these
# libraries. To use it in a different context, you will need to
# reimplement the same functions that libsemihost.a provides, but
# libcrt0.a might still be useful.

cmake_minimum_required(VERSION 3.20.0)
project(llvmlibc-support LANGUAGES C ASM)

add_library(semihost STATIC
  init.c
  exit.c
  stdio_read.c
  stdio_write.c
)

add_library(crt0 STATIC
  crt0.c
)

install(TARGETS semihost crt0)
