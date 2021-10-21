# LLVM Embedded Toolchain for Arm

This repository contains build scripts and auxiliary material for building a
bare-metal LLVM based toolchain targeting Arm based on:
* clang + llvm
* lld
* libc++abi
* libc++
* compiler-rt
* newlib

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
newlib     | https://sourceware.org/newlib

## License

Content of this repository is licensed under Apache-2.0. See
[LICENSE.txt](LICENSE.txt).

The resulting binaries are covered under their respective open source licenses,
see component links above.

## Host platforms

The LLVM Embedded Toolchain for Arm has been built and tested on Linux/Ubuntu
18.04.5 LTS.

## Getting started

Download a release of the toolchain for you platform using [Github
releases](/ARM-software/LLVM-embedded-toolchain-for-Arm/releases) and extract
the archive into an arbitrary directory.

### Downloading runtime libraries (Windows only)

We currently don't ship several Windows DLLs that are part of the GCC and
Mingw-w64 projects due to licensing considerations.

In order to use the toolchain on Windows you will need to provide the following
three libraries manually.

Library             | Project   | Link
--------------------|-----------|---------------------
libstdc++-6.dll     | GCC       | https://gcc.gnu.org
libgcc_s_seh-1.dll  | GCC       | https://gcc.gnu.org
libwinpthread-1.dll | Mingw-w64 | http://mingw-w64.org

1. Download the [MinGW-W64 GCC-7.3.0 x86_64-posix-seh](https://sourceforge.net/projects/mingw-w64/files/Toolchains%20targetting%20Win64/Personal%20Builds/mingw-builds/7.3.0/threads-posix/seh/x86_64-7.3.0-release-posix-seh-rt_v5-rev0.7z) release from SourceForge
2. Extract the archive and copy the three DLLs mentioned above from the
   `mingw64/bin` directory to the `LLVMEmbeddedToolchainForArm-<revision>/bin`
   directory

### Using the toolchain

To use the toolchain you need to provide a compiler configuration file on the
command line, for example:

```
$ PATH=<install-dir>/LLVMEmbeddedToolchainForArm-<revision>/bin:$PATH
$ clang --config armv6m_soft_nofp_rdimon -o example example.c
```

The available configuration files can be listed using:
```
$ ls <install-dir>/LLVMEmbeddedToolchainForArm-<revision>/bin/*.cfg
```

Note that configurations under the `nosys` or `rdimon_baremetal` categories
require the linker script to be specified with `-T`:

```
$ PATH=<install-dir>/LLVMEmbeddedToolchainForArm-<revision>/bin:$PATH
$ clang --config armv6m_soft_nofp_nosys -T device.ld -o example example.c
```

## Building from source

LLVM Embedded Toolchain for Arm is an open source project and thus can be built
from source. Please see the [Building from source](docs/building-from-source.md)
guide for detailed instructions.

## Providing feedback and reporting issues

Please raise an issue via [Github issues](https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/issues).

## Contributions and Pull Requests

Please see the [Contribution Guide](docs/contributing.md) for details.
