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

## Components

The LLVM Embedded Toolchain for Arm relies on the following upstream components

Component  | Link
---------- | ------------------------------------
LLVM       | https://github.com/llvm/llvm-project
newlib     | https://sourceware.org/newlib

## C++ support

C++ is partially supported with the use of libc++ and libc++abi from LLVM. Features
that are not supported include:
 - Exceptions
 - RTTI
 - Multithreading
 - Locales and input/output streams
 - C++17's aligned operator new

## License

Content of this repository is licensed under Apache-2.0. See ``LICENSE.txt``.

The resulting binaries are covered under their respective open source licenses,
see component links above.

In addition, if the toolchain is cross-compiled to run on Windows (see
[Cross-compiling the toolchain for Windows](#cross-compiling-the-toolchain-for-windows)
for details) several Mingw-w64 runtime libraries residing on your machine
may be copied to the ``bin`` directory of the toolchain and included in the
generated ``.tar.gz`` archive if you choose to do so.

The following three libraries are used:

Library             | Project   | Link
--------------------|-----------|---------------------
libstdc++-6.dll     | GCC       | https://gcc.gnu.org
libgcc_s_seh-1.dll  | GCC       | https://gcc.gnu.org
libwinpthread-1.dll | Mingw-w64 | http://mingw-w64.org

The libraries are covered under their respective open source licenses.

## Contributions and Pull Requests

Contributions are accepted under Apache-2.0. Only submit contributions where
you have authored all of the code.

### Coding style

The project uses the [PEP 8](https://www.python.org/dev/peps/pep-0008) style
guide for all Python scripts. The scripts also must pass pylint and flake8
checks as well as type-checking with mypy.

Use the following commands to check the scripts before submitting a pull
request:

```
$ ./setup.sh
$ ./run-precommit-checks.sh
```

## How to provide feedback/report an issue

Please raise an issue via
https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/issues

## Host platforms

The LLVM Embedded Toolchain for Arm has been built and tested on Linux/Ubuntu
18.04.5 LTS.

## Getting started

### Build the toolchain

Build requirements
* a suitable compiler toolchain:
  * Clang 6.0.0 or above, or
  * GCC 5.1.0 or above
* CMake 3.13.4 or above
* Python version 3.6 or above and python3-venv
* Git
* GNU Make

0. Install typically missing packages. There might be others depending on your
   setup.
```
# apt-get install clang # If the Clang version installed by the package manager is older than 6.0.0, download a recent version from https://releases.llvm.org or build from source
# apt-get install python3
# apt-get install python3-venv
# apt-get install git
# apt-get install make
# apt-get install cmake # If the CMake version installed by the package manager is older than 3.13.4, download a recent version from https://cmake.org/download and add it to PATH
```

1. Install the build scripts in a python virtual env (in directory ``venv``):
```
$ ./setup.sh
```
2. Activate the virtual environment:
```
$ . ./venv/bin/activate
```
3. Build the toolchain with:
```
$ build.py
```
The script supports various command line options. To get a description of all
options run:
```
$ build.py -h
```
Some notable options include:
* ``--revision`` the LLVM Embedded Toolchain for Arm version. Default version
  is ``0.1``. The available toolchain versions can be listed with:
```
$ repos.py list
0.1
HEAD
```
* ``--host-toolchain`` the toolchain type. The supported values are:
  * ``clang`` Clang (the default)
  * ``gcc`` GCC
  * ``mingw`` Mingw-w64 (used for cross-compilation, see
    [Cross-compiling the toolchain for Windows](#cross-compiling-the-toolchain-for-windows))
* ``--host-toolchain-dir`` the directory from Step 0 that the toolchain resides
  in. Default is ``/usr/bin``.
* ``--install-dir`` the LLVM Embedded Toolchain for Arm installation directory.
  Default is ``./install-<revision>``.

The build script can optionally take advantage of some tools to speed up the
build. Currently, these tools are ``ccache``, and ``ninja``.
```
$ build.py --use-ccache --use-ninja
```
4. By now, you should have a working toolchain in directory
   ``<install-dir>/LLVMEmbeddedToolchainForArm-<revision>``

### Use the toolchain

Once built, you can use the generated config files to configure the compiler
correctly. The available config files can be listed with
`ls <install-dir>/LLVMEmbeddedToolchainForArm-<revision>/bin/*.cfg`

```
$ PATH=<install-dir>/LLVMEmbeddedToolchainForArm-<revision>/bin:$PATH
$ clang --config armv6m_soft_nofp_rdimon -o example example.c
```

Note that configurations under the `nosys` or `rdimon_baremetal` categories
require the linker script to be specified with `-T`:

```
$ PATH=<install-dir>/LLVMEmbeddedToolchainForArm-<revision>/bin:$PATH
$ clang --config armv6m_soft_nofp_nosys -T device.ld -o example example.c
```

### Test the toolchain

Once the toolchain is built, you can build smoke tests:

```
$ build.py test
```

If QEMU is installed and present in your system path, these tests will also be
run.

Furthermore, see the `samples` folder for sample code and instructions on
building, running and debugging.

## Cross-compiling the toolchain for Windows

The LLVM Embedded Toolchain for Arm can be cross-compiled to run on Windows.
The compilation itself still happens on Linux. In addition to the prerequisites
mentioned in the [Build the toolchain](#build-the-toolchain) section you will
also need a Mingw-w64 toolchain based on GCC 5.1.0 or above installed. For
example, to install it on Ubuntu Linux use the following command:

```
# apt-get install mingw-w64
```

Then use ``build.py`` to build the toolchain:

```
$ build.py --host-toolchain mingw
```

Cross-compilation still requires a native toolchain, i.e. a compiler toolchain
that  produces binaries that run on the build machine. The native toolchain can
be specified using the following options:
* ``--native-toolchain`` the toolchain type. Either ``clang`` or ``gcc``.
  Default is ``clang``.
* ``--native-toolchain-dir`` the directory that the toolchain resides in.
  Default is ``/usr/bin``.

For example:
```
$ build.py --host-toolchain mingw \
           --native-toolchain gcc \
           --native-toolchain-dir /opt/gcc-latest/bin
```

The script will prompt you whether it should copy the Mingw-w64 runtime
libraries from your local machine to the toolchain ``bin`` directory. The
libraries are distributed under their own [licenses](#license), this needs to
be taken into consideration if you decide to redistribute the built toolchain.

To avoid an interactive prompt use the ``--copy-runtime-dlls`` command line
option, for example:
```
$ build.py --host-toolchain mingw --copy-runtime-dlls no
```

## Known limitations
* Depending on the state of the components, build errors may occur when
  ``--revision HEAD`` is used.

## Divergences from upstream

### newlib:
* Clang does not support the ``naked`` attribute on C functions, breaking the
  Linux startup (out of scope).
* Target triple ending with eabi is not considered an ELF target.
* Revision 0.1 only: set the correct floating-point endianness when building
  with Clang.

### LLVM:
* Recognize $@ in a config file argument to mean the directory of the config
  file, allowing toolchain relative paths.
