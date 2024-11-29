# Experimental newlib support

LLVM Embedded Toolchain for Arm uses [`picolibc`](https://github.com/picolibc/picolibc)
as the standard C library. For compatibility with existing projects using
[`newlib`](https://sourceware.org/newlib/), a separate package of `newlib`-based
library variants is provided.

> **NOTE:**  `newlib` support in LLVM Embedded Toolchain for Arm is experimental
> and may change in following releases.

## Using pre-built `newlib` library package

1. Install LLVM Embedded Toolchain for Arm
1. Download corresponding `LLVM-ET-Arm-newlib-overlay` package
and extract it on top of the main toolchain folder.

    * Note: The overlay package copies all the `newlib` library variants into the
    `lib/clang-runtimes/newlib` subdirectory, so that they do not collide with
    the `picolibc` variants in `lib/clang-runtimes`.
    It also adds the `newlib.cfg` into the `bin` directory,
    which switches the `--sysroot` to the `newlib` subdirectory above. 

1. Add the `newlib.cfg` config file to the command line to use `newlib`
library variants instead of `picolibc`.
1. Add `-lrdimon` and `-lcrt0-rdimon` to the command line to use semihosting
or `-lnosys` and `-lcrt0-nosys` otherwise.
1. You may use the provided default linker script by adding `-T redboot.ld`
to the command line.

Example:
```
$ clang --config=newlib.cfg --target=arm-none-eabi -march=armv7m -T redboot.ld -lrdimon -lcrt0-rdimon -o hello hello.c
```

## Building `newlib` library package

> **NOTE:**  Building `newlib` package is only supported on Linux and macOS.

Configure the toolchain with the CMake setting
`-DLLVM_TOOLCHAIN_C_LIBRARY=newlib` to build a newlib-based version of
the toolchain.

If you also add `-DLLVM_TOOLCHAIN_LIBRARY_OVERLAY_INSTALL=on` then the
`package-llvm-toolchain` CMake target will generate the `newlib`
overlay package.

Note that the `-DLLVM_TOOLCHAIN_LIBRARY_OVERLAY_INSTALL=on` option
only generates the `newlib` package, but does not install it as part
of the `install` CMake target.