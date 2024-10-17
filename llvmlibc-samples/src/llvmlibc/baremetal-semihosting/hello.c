// Copyright (c) 2024, Arm Limited and affiliates.
// SPDX-License-Identifier: Apache-2.0

// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at

//    http://www.apache.org/licenses/LICENSE-2.0

// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

// Implementation of errno
int *__llvm_libc_errno() {
  static int internal_err;
  return &internal_err;
}

// Example that uses heap, string and math library.

int main(void) {
  const char *hello_s = "hello ";
  const char *world_s = "world";
  const size_t hello_s_len = strlen(hello_s);
  const size_t world_s_len = strlen(world_s);
  const size_t out_s_len = hello_s_len + world_s_len + 1;
  char *out_s = (char*) malloc(out_s_len);
  assert(out_s_len >= hello_s_len + 1);
  strncpy(out_s, hello_s, hello_s_len + 1);
  assert(out_s_len >= strlen(out_s) + world_s_len + 1);
  strncat(out_s, world_s, world_s_len + 1);
  // 2024-10-17 Embedded printf implementation does not currently
  // support printing floating point numbers.
  printf("%s %li\n", out_s, lround(400000 * atanf(1.0f)));
  free(out_s);
  return 0;
}
