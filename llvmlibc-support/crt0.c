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
#include <stdlib.h>

#include "platform.h"

int main(int, char **);

__attribute__((used)) static void c_startup(void) {
  _platform_init();
  _Exit(main(0, NULL));
}

extern long __stack[];
__attribute__((naked)) void _start(void) {
  __asm__("mov sp, %0" : : "r"(__stack));
  __asm__("b c_startup");
}
