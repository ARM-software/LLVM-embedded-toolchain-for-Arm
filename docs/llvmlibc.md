# Experimental LLVM libc support

LLVM Embedded Toolchain for Arm uses
[`picolibc`](https://github.com/picolibc/picolibc) as the standard C
library. For experimental and evaluation purposes, you can instead
choose to use the LLVM project's own C library.

> **NOTE:** `llvmlibc` support in LLVM Embedded Toolchain for Arm is
> an experimental technology preview, with significant limitations.

## Building the toolchain with LLVM libc

> **NOTE:** Building the LLVM libc package is only supported on Linux
> and macOS.

Configure the toolchain with the CMake setting
`-DLLVM_TOOLCHAIN_C_LIBRARY=llvmlibc` to build a version of the
toolchain based on LLVM libc.

If you also add `-DLLVM_TOOLCHAIN_LIBRARY_OVERLAY_INSTALL=on` then the
`package-llvm-toolchain` CMake target will generate an overlay package
similar to the [newlib overlay
package](https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/blob/main/docs/newlib.md).
If you unpack this over an existing installation of the toolchain,
then you can switch to LLVM libc by adding `--config=llvmlibc.cfg` on
the command line.

## Using LLVM libc

To compile a program with this LLVM libc, you must provide the
following command line options, in addition to `--target`, `-march` or
`-mcpu`, and the input and output files:

* `--config=llvmlibc.cfg` if you are using LLVM libc as an overlay
  package (but you do not need this if you have built the whole
  toolchain with only LLVM libc)

* `-lcrt0` to include a library defining the `_start` symbol (or else
  provide that symbol yourself)

* `-lsemihost` to include a library that implements porting functions
  in LLVM's libc in terms of the Arm semihosting API (or else provide
  an alternative implementation of those functions yourself)

* `-Wl,--defsym=__stack=0x`_nnnnnn_ to define the starting value of
  your stack pointer. Alternatively, use a linker script that defines
  the symbol `__stack` in addition to whatever other memory layout you
  want.

For example:

```
clang --config=llvmlibc.cfg --target=arm-none-eabi -march=armv7m -o hello hello.c -lsemihost -lcrt0 -Wl,--defsym=__stack=0x200000
```

## Limitations of LLVM libc in LLVM Embedded Toolchain for Arm

At present, this toolchain only builds LLVM libc for AArch32, not for
AArch64.

At present, this toolchain does not build any C++ libraries to go with
LLVM libc.

At the time of writing this (2024-07), LLVM libc is a work in
progress. It is incomplete: not all standard C library functionality
is provided.
