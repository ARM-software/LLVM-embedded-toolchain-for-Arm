This sample shows how to use semihosting with
[QEMU Arm System emulator](https://www.qemu.org/docs/master/system/target-arm.html)
targeting the
[micro:bit board model](https://www.qemu.org/2019/05/22/microbit/).

It uses the startup code and the linker script file from the GNU Arm Embedded
Toolchain samples.

Usage:
* `VERSION=0.1 make build` to build the sample.
* `VERSION=0.1 make run` to run the sample with QEMU Arm System emulator.
* `VERSION=0.1 make debug` to run the sample with QEMU Arm System emulator with
  GDB server listening on the default port 1234.

  To debug attach to QEMU with GDB provided by the
  [GNU Arm Embedded Toolchain](https://developer.arm.com/tools-and-software/open-source-software/developer-tools/gnu-toolchain/gnu-rm/downloads):

  ```
  $ arm-none-eabi-gdb hello.elf
  (gdb) target remote :1234
  ```
