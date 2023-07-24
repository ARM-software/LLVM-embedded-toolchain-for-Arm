# Migrating from Arm GNU Toolchain

## Overview

[Arm GNU Toolchain](https://developer.arm.com/Tools%20and%20Software/GNU%20Toolchain)
is the GNU Toolchain for the Arm Architecture released by Arm and traditionally
used for embedded development.

Generally the LLVM toolchain tries to be a drop in replacement for the GNU toolchain,
however there may be some missing features or small incompatibilities.

Some known differences and migration strategies are summarized below.

## Benefits

Using multiple toolchains to build a project benefits from different checks
and warnings present in different compilers to catch more issues,
particularly C and C++ standards compliance, during build time.

LLVM Embedded Toolchain for Arm provides support for multiple sanitizers
and memory safety features to also catch typical issues at runtime during testing,
see the [Clang documentation](https://clang.llvm.org/docs/index.html)
and [samples](https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/tree/main/samples/src).

LLVM Embedded Toolchain for Arm provides superior performance when targeting the
Armv8-M or later architecture, including the
[Arm Helium Technology](https://www.arm.com/technologies/helium)
(M-Profile Vector Extension, MVE).

## Key toolchain components

|Component|GNU toolchain (`arm-none-eabi-`)|LLVM toolchain|
|---------|-------------|--------------|
|C, C++ compiler​|`gcc`, `g++`|`clang`, `clang++`​|​
|Assembler​|`as`​|`clang` integrated assembler​|
|Linker​|`ld`​|`lld`​|
|Binutils​|`objdump`, `readelf`, ...|`llvm-objdump`, `llvm-readelf`, ...|
|Compiler runtime library​|`libgcc​`|`compiler-rt`​|
|Unwinder​|`libgcc`​|`libunwind`​|
|C standard library​|`newlib`, `newlib-nano`|`picolibc`|​
|C++ ABI library​|`libsupc++.a`|`libc++abi`​|​
|C++ standard library​|`libstdc++​`|`libc++`​|

## Toolchain identification

Toolchain version macros:

|Version number|GNU macro|LLVM macro|
|-------|---------|----------|
|Major|`__GNUC__`|`__clang_major__`|
|Minor|`__GNUC_MINOR__`|`__clang_minor__`|
|Patch level|`__GNUC_PATCHLEVEL__`|`__clang_patchlevel__`|

Note that `clang` defines GNU macros for compatibility too:
`__GNUC__` equal to `4`, `__GNUC_MINOR__` equal to `2`,
and `__GNUC_PATCHLEVEL__` equal to `1`.

## C and C++ language extensions

Clang supports the majority of GNU C and C++ extensions as described in
[Clang Language Extensions](https://clang.llvm.org/docs/LanguageExtensions.html).

The following feature checking macros can be used to test whether a particular
feature is supported:
* [`__has_builtin`](https://clang.llvm.org/docs/LanguageExtensions.html#has-builtin)
* [`__has_feature`](https://clang.llvm.org/docs/LanguageExtensions.html#has-feature-and-has-extension)
* [`__has_extension`](https://clang.llvm.org/docs/LanguageExtensions.html#has-feature-and-has-extension)
* [`__has_attribute`](https://clang.llvm.org/docs/LanguageExtensions.html#has-attribute)

## Assembly language

`clang` should be used instead of `arm-none-eabi-as` to compile assembly
(`.s` and `.S`) files.

There are minor differences in the assembly syntax between GNU and LLVM
compilers, however most of the time it is possible to write code that is
accepted by both.

For example, GNU and LLVM compilers differ in:
* Use of `.N` and `.W` suffixes for Thumb instructions.
* Use of `S` suffix for flag setting instructions.

## Multilib support

LLVM toolchain for Arm provides multilib support similar to the GNU toolchain,
see _Using the toolchain_ section in the [README](https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/blob/main/README.md#using-the-toolchain),
however uses different command line options to control selection of semihosting.

|Use case|GNU options|LLVM options|
|--------|-----------|------------|
|No semihosting|`--specs=nosys.specs`|`-lcrt0`|
|Semihosting|`--specs=rdimon.specs`|`-lcrt0-semihost -lsemihost`|
|Newlib-nano|`--specs=nano.specs`|Not available: `picolibc` is an equivalent of `newlib-nano`.

## Linker

`lld` is designed as a drop in replacement for GNU `ld`,
however there are some known differences to take into account, see:
* [Linker Script implementation notes and policy](https://lld.llvm.org/ELF/linker_script.html)
in the LLD documentation.
* The [LLD and GNU linker incompatibilities](https://maskray.me/blog/2020-12-19-lld-and-gnu-linker-incompatibilities)
blog post.

## Startup code

Refer to [Using Picolibc in Embedded Systems](https://github.com/picolibc/picolibc/blob/main/doc/using.md)
for the details of how `picolibc` handles initialization.

By default, `picolibc` provides an interrupt vector table. To replace it,
the application interrupt vector table should be placed into the `init`
[linker script](https://github.com/picolibc/picolibc/blob/main/doc/linking.md)
section and referenced by the `__interrupt_vector` symbol.

## Standard input and output

See [Picolibc and Operating Systems](https://github.com/picolibc/picolibc/blob/main/doc/os.md)
for the details on redirecting `stdin`, `stdout` and `stderr`.

The `baremetal-uart` [sample](https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/tree/main/samples/src/baremetal-uart)
provides a basic code example for redirecting `stdout`.
