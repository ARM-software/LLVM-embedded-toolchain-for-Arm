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
- Armv4T (experimental)
- Armv5TE (experimental)
- Armv6 (experimental, using the Armv5TE library variant)
- AArch64 armv8.0 (experimental)

## C++ support

C++ is partially supported with the use of libc++ and libc++abi from LLVM. Features
that are not supported include:
 - Exceptions
 - RTTI
 - Multithreading

## Components

The LLVM Embedded Toolchain for Arm relies on the following upstream components

Component  | Link
---------- | ------------------------------------
LLVM       | https://github.com/llvm/llvm-project
picolibc   | https://github.com/picolibc/picolibc

## License

Content of this repository is licensed under Apache-2.0. See
[LICENSE.txt](LICENSE.txt).

The resulting binaries are covered under their respective open source licenses,
see component links above.

## Host platforms

LLVM Embedded Toolchain for Arm is built and tested on Ubuntu 18.04 LTS.

The Windows version is built on Windows Server 2019 and lightly tested on Windows 10.

Building on macOS is functional for x86_64 and Apple Silicon.

[Binary packages](https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/releases)
are provided for major LLVM releases for Linux and Windows.

## Getting started

Download a release of the toolchain for your platform from [Github
releases](https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/releases)
and extract the archive into an arbitrary directory.

On Ubuntu 20.04 and later `libtinfo5` is required: `apt install libtinfo5`.

On macOS the toolchain binaries are quarantined by com.apple.quarantine. To
run the executables change directory to bin and run the following command to
remove the com.apple.quarantine:

```
find . -type f -perm +0111 | xargs xattr -d com.apple.quarantine
```

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

> *Note:* If you are using the toolchain in a shared environment with untrusted input,
> make sure it is sufficiently sandboxed.

### Using the toolchain without config files

Instead of using a config file you can provide a `--sysroot` option specifying
the directory containing the`include` and `lib` directories of the libraries
you want to use, in addition to various other required options:
* The target triple
* Disabling exceptions and RTTI
* The `crt0` library - either `crt0` or `crt0-semihost`
* The semihosting library, if desired.
 For example:

```
$ clang \
--sysroot=<install-dir>/LLVMEmbeddedToolchainForArm-<revision>/lib/clang-runtimes/arm-none-eabi/armv6m_soft_nofp \
--target=armv6m-none-eabi \
-fno-exceptions \
-fno-rtti \
-lcrt0-semihost \
-lsemihost \
-T picolibc.ld \
-o example example.c
```

## Building from source

LLVM Embedded Toolchain for Arm is an open source project and thus can be built
from source. Please see the [Building from source](docs/building-from-source.md)
guide for detailed instructions.

## Providing feedback and reporting issues

Please raise an issue via [Github issues](https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/issues).

## Contributions and Pull Requests

Please see the [Contribution Guide](docs/contributing.md) for details.
