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

ssize_t __llvm_libc_stdio_read(struct __llvm_libc_stdio_cookie *cookie,
                               const char *buf, size_t size) {
  size_t args[4];
  args[0] = (size_t)cookie->handle;
  args[1] = (size_t)buf;
  args[2] = (size_t)size;
  args[3] = 0;
  ssize_t retval = semihosting_call(SYS_READ, args);
  if (retval >= 0)
    retval = size - retval;
  return retval;
}
