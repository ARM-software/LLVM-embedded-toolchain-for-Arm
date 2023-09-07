// RUN: %clang --target=armv6m-none-eabi -mfloat-abi=soft -march=armv6m -mfpu=none -lcrt0-semihost -lsemihost -T %S/Inputs/microbit.ld %s -o %t.out
// RUN: qemu-system-arm -M microbit -semihosting -nographic -device loader,file=%t.out 2>&1 | FileCheck %s

#include <stdio.h>

int main(void) {
  printf("Hello World!\n"); // CHECK: Hello World!
  return 0;
}
