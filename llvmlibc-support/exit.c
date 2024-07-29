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

#include <stddef.h>

#include "semihost.h"

void __llvm_libc_exit(int status) {

#if defined(__ARM_64BIT_STATE) && __ARM_64BIT_STATE
  size_t block[2];
  block[0] = ADP_Stopped_ApplicationExit;
  block[1] = status;
  semihosting_call(SYS_EXIT, block);
#else
  semihosting_call(SYS_EXIT, (const void *)ADP_Stopped_ApplicationExit);
#endif

  __builtin_unreachable(); /* semihosting call doesn't return */
}
