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

Building on macOS is functional but experimental. Currently it is only lightly tested on
a Macbook Pro with M1 on macOS 12.3.1.

[Binary packages](https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/releases)
are provided for major LLVM releases for Linux and Windows.

## Getting started

Download a release of the toolchain for your platform from [Github
releases](https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/releases)
and extract the archive into an arbitrary directory.

### Using the toolchain

To use the toolchain, on the command line you need to provide:
* A [configuration file](
  https://clang.llvm.org/docs/UsersManual.html#configuration-files) specified
  with `--config`, or a suitable set of command line options including the
  `crt0` library to use - see [experimental multilib](#experimental-multilib).
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

### Experimental multilib

The clang provided by LLVM Embedded Toolchain for Arm 16 can automatically
select an appropriate set of libraries based on your compile flags, without
needing either an explicit `--sysroot` option or a `--config` option.
For example the following will automatically use libraries from the
`lib/clang-runtimes/arm-none-eabi/armv6m_soft_nofp` directory:

```
$ clang \
--target=armv6m-none-eabi \
-fno-exceptions \
-fno-rtti \
-lcrt0-semihost \
-lsemihost \
-T picolibc.ld \
-o example example.c
```

The config files are still present and you can still use them.

It's possible that the multilib system will choose a set of libraries that are
not the ones you want to use. In this case you can bypass the multilib system
by providing a `--sysroot` option specifying the directory containing the
`include` and `lib` directories of the libraries you want to use. For example:

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
