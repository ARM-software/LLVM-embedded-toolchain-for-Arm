This sample shows how to use semihosting with [QEMU User space emulator](https://www.qemu.org/docs/master/user/main.html).

Usage:
* `VERSION=0.1 make build` to build the sample.
* `VERSION=0.1 make run` to run the the sample with QEMU User space emulator.
* `VERSION=0.1 make debug` to run the the sample with QEMU User space emulator with GDB server listening on the default port 1234.

    To debug attach to QEMU with GDB provided by the [GNU Arm Embedded Toolchain](https://developer.arm.com/tools-and-software/open-source-software/developer-tools/gnu-toolchain/gnu-rm/downloads):

    ```
    $ arm-none-eabi-gdb hello.elf
    (gdb) target remote :1234
    ```
