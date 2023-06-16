// RUN: %clang --config armv6m_soft_nofp_semihost.cfg -T %S/Inputs/microbit.ld %s -o %t.out
// RUN: qemu-system-arm -M microbit -semihosting -nographic -device loader,file=%t.out 2>&1 | FileCheck %s

#include <stdio.h>

int main(void) {
  printf("Hello World!\n"); // CHECK: Hello World!
  return 0;
}
