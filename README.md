# LLVM Embedded Toolchain for Arm

This repository contains build scripts and auxiliary material for building a
bare-metal LLVM based toolchain targeting Arm based on:
* clang + llvm
* lld
* libc++abi
* libc++
* compiler-rt
* picolibc (newlib in versions 14 and earlier)

## Goal

The goal is to provide an LLVM based bare-metal toolchain that can target the
Arm architecture family from Armv6-M and newer. The toolchain follows the ABI
for the Arm Architecture and attempts to provide typical features needed for
embedded and realtime operating systems.

## Supported architectures

- Armv6-M
- Armv7-M
- Armv7E-M
- Armv8-M Mainline
- Armv8.1-M Mainline
- AArch64 armv8.0 (experimental)

## C++ support

C++ is partially supported with the use of libc++ and libc++abi from LLVM. Features
that are not supported include:
 - Exceptions
 - RTTI
 - Multithreading
 - Locales and input/output streams
 - C++17's aligned operator new

## Components

The LLVM Embedded Toolchain for Arm relies on the following upstream components

Component  | Link
---------- | ------------------------------------
LLVM       | https://github.com/llvm/llvm-project
picolibc   | https://github.com/picolibc/picolibc

### Windows runtime DLLs

On Windows the toolchain also uses several DLLs that are part of the Mingw-w64
project (based on GCC):

Library             | Project   | Link
--------------------|-----------|---------------------
libstdc++-6.dll     | GCC       | https://gcc.gnu.org
libgcc_s_seh-1.dll  | GCC       | https://gcc.gnu.org
libwinpthread-1.dll | Mingw-w64 | http://mingw-w64.org

## License

Content of this repository is licensed under Apache-2.0. See
[LICENSE.txt](LICENSE.txt).

The resulting binaries are covered under their respective open source licenses,
see component links above.

## Host platforms

The LLVM Embedded Toolchain for Arm has been built and tested on Linux/Ubuntu
18.04.5 LTS.

## Getting started

Download a release of the toolchain for your platform from [Github
releases](https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/releases)
and extract the archive into an arbitrary directory.

### Using the toolchain

To use the toolchain, on the command line you need to provide:
* A [configuration file](
  https://clang.llvm.org/docs/UsersManual.html#configuration-files) specified
  with `--config`.
* A [linker script](
  https://sourceware.org/binutils/docs/ld/Scripts.html) specified with `-T`.
  Default `picolibcpp.ld` & `picolibc.ld` scripts are provided and can be used
  directly or included from a [custom linker script](
  https://github.com/picolibc/picolibc/blob/main/doc/linking.md#using-picolibcld).

For example:

```
$ PATH=<install-dir>/LLVMEmbeddedToolchainForArm-<revision>/bin:$PATH
$ clang --config armv6m_soft_nofp_semihost.cfg -T picolibc.ld -o example example.c
```

The available configuration files can be listed using:
```
$ ls <install-dir>/LLVMEmbeddedToolchainForArm-<revision>/bin/*.cfg
```

## Building from source

LLVM Embedded Toolchain for Arm is an open source project and thus can be built
from source. Please see the [Building from source](docs/building-from-source.md)
guide for detailed instructions.

## Providing feedback and reporting issues

Please raise an issue via [Github issues](https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/issues).

## Contributions and Pull Requests

Please see the [Contribution Guide](docs/contributing.md) for details.
