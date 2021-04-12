# LLVM Embedded Toolchain for Arm

This repository contains build scripts and auxiliary material for building a bare-metal LLVM based toolchain targeting Arm based on:
* clang + llvm
* lld
* lldb
* compiler-rt
* newlib

Currently, only Armv6-M can be targeted, and only one library variant is provided targeting the Armv6-M architecture without any optional features.

## Goal

The goal is to provide a LLVM based bare-metal toolchain that can target the Arm architecture family from Armv6-M and newer. The toolchain follows the ABI for the Arm Architectue and attempts to provide typical features needed for embedded and realtime operating systems.

## Components

The LLVM Embedded Toolchain for Arm relies on the following upstream components

Component  | Link
---------- | ------------------------------------
LLVM       | https://github.com/llvm/llvm-project
newlib     | https://sourceware.org/newlib

## License

Content of this repository is licensed under Apache-2.0. See ``LICENSE.txt``.

The resulting binaries are covered under their respective open source licenses, see component links above.

## Contributions and Pull Requests

Contributions are accepted under Apache-2.0. Only submit contributions where you have authored all of the code.

### Coding style

The project uses the [PEP 8](https://www.python.org/dev/peps/pep-0008) style
guide for all Python scripts. The scripts also must pass pylint checks. Use the
following command to check the scripts before submitting a pull request
(assuming that pylint is installed):

```
pylint --rcfile=scripts/.pylintrc scripts
```

## How to provide feedback/report an issue

Please raise an issue via  https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/issues

## Host platforms

The LLVM Embedded Toolchain for Arm has been built and tested on Linux/Ubuntu 18.04.5 LTS.

## Getting started

### Build the toolchain

Build requirements
* clang 6.0.0 or above
* cmake 3.13.4 or above
* python version 3.6 or above and python3-venv
* git
* make

0. Install typically missing packages. There might be others depending on your setup.
```
sudo apt-get install clang # If the clang version installed by the package manager is older than 6.0.0, download a recent version from https://releases.llvm.org or build from source
sudo apt-get install python3
sudo apt-get install python3-venv
sudo apt-get install git
sudo apt-get install make
sudo apt-get install cmake # If the cmake version installed by the package manager is older than 3.13.4, download a recent version from https://cmake.org/download and add it to PATH
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
The script supports various command line options. To get a description of all options run:
```
$ build.py -h
```
Some notable options include:
* ``--revision`` the LLVM Embedded Toolchain for Arm version. Default version is ``0.1``. The available toolchain versions can be listed with:
```
$ repos.py list
0.1
HEAD
```
* ``--host-toolchain-dir`` the directory from Step 0 that ``clang`` resides in. Default is ``/usr/bin``.
* ``--install-dir`` the LLVM Embedded Toolchain for Arm installation directory. Default is the current directory.

The build script can optionally take advantage of some tools to speed up the
build. Currently these tools are ``ccache``, and ``ninja``.
```
$ build.py --use-ccache --use-ninja
```
4. By now, you should have a working toolchain in directory
* ``<install-dir>/LLVMEmbeddedToolchainForArm-<revision>`` if you were building a release (e.g ``--revision 0.1``) or in
* ``<install-dir>/LLVMEmbeddedToolchainForArm`` if you were building using latest component source (``--revision HEAD``).

### Use the toolchain

Once built, you can use the generated config files to configure the compiler correctly. The available config files can be listed with `ls <install-dir>/LLVMEmbeddedToolchainForArm-<revision>/bin/*.cfg`

```
PATH=<install-dir>/LLVMEmbeddedToolchainForArm-<revision>/bin:$PATH
clang --config armv6m-none-eabi_rdimon -o example example.c
```

Note that `armv6m-none-eabi_nosys` and `armv6m-none-eabi_rdimon_baremetal` require the linker script to be specifed with `-T`:

```
PATH=<install-dir>/LLVMEmbeddedToolchainForArm-<revision>/bin:$PATH
clang --config armv6m-none-eabi_nosys -T device.ld -o example example.c
```

### Test the toolchain

See the `samples` folder for sample code and instructions on building, running and debugging.

## Known limitations
* Depending on the state of the components, build errors may occur when ``--revision HEAD`` is used.

## Divergences from upstream

### newlib:
* clang does not support naked attribute on a C function, breaking the linux startup (out of scope).
* Target triple ending with eabi is not considered an ELF target.

### LLVM:
* Recognize $@ in a config file argument to mean the directory of the config file, allowing toolchain relative paths.
