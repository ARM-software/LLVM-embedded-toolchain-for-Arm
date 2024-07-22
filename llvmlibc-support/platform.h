//
// Copyright (c) 2022, Arm Limited and affiliates.
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//

// This header file defines the interface between libcrt0.a, which defines
// the program entry point, and libsemihost.a, which implements the
// LLVM-libc porting functions in terms of semihosting. If you replace
// libsemihost.a with something else, this header file shows how to make
// that work with libcrt0.a.

#ifndef LLVMET_LLVMLIBC_SUPPORT_PLATFORM_H
#define LLVMET_LLVMLIBC_SUPPORT_PLATFORM_H

// libcrt0.a will call this function after the stack pointer is
// initialized. If any setup specific to the libc porting layer is
// needed, this is where to do it. For example, in semihosting, the
// standard I/O handles must be opened via the SYS_OPEN operation, and
// this function is where libsemihost.a does it.
void _platform_init(void);

#endif // LLVMET_LLVMLIBC_SUPPORT_PLATFORM_H
