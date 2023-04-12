# Sample code for the LLVM Embedded Toolchain for Arm

This directory contains sample code which demonstrates how to use the LLVM
Embedded Toolchain for Arm.

## Directory structure

* `ldscripts` - Linker scripts used by the samples.
* `src` - Sample source code, Makefile and description, each sub-directory is a
  separate sample.

## Supported environments

The build scripts support four different environments:
* Linux
* macOS
* Windows
* Windows + [MSYS2](https://www.msys2.org/)

## Prerequisites

In order to compile the samples you will need the following tools:
* LLVM Embedded Toolchain for Arm
* GNU Make (Linux, macOS and MSYS2)

To run the samples you will need a QEMU emulator to be installed on your
machine. The samples rely on
the QEMU Arm System emulator. On Ubuntu Linux it can be installed as follows:

```
# apt-get install qemu-system-arm
```

On macOS the QEMU Arm System emulator can be installed via HomeBrew or
Mac Ports. Instructions can be found in
https://www.qemu.org/download/#macos

The Windows installer can be downloaded from
https://www.qemu.org/download/#windows.

To debug the samples you will need to install a debugger
that supports Arm targets, for example,
[LLDB](https://lldb.llvm.org/) version matching LLVM Embedded Toolchain for Arm.
Debugging is only supported on Linux and macOS.

## Specifying the location of the installed toolchain

The Makefiles of the code samples need the location of the installed LLVM
Embedded Toolchain for Arm.

If you are using Linux or MSYS2 and running the samples directly from the
installation directory the Makefiles will determine the correct location
automatically.

Otherwise you will need to set the environment variable ``BIN_PATH`` to point
to the ``bin`` directory of the toolchain.

## Compiling, running and debugging the samples

### Linux, macOS and MSYS2

Change to the directory of a specific sample (e.g. ``src/baremetal-uart``) and
use the following commands to build, run or debug the sample:
* ``$ make build`` to build the sample.
* ``$ make run`` to run the sample with QEMU emulator.
* ``$ make debug`` to run the sample with QEMU emulator with GDB server
  listening on the default port 1234. This option is supported only on
  Linux.

  To debug attach to QEMU with [LLDB](https://lldb.llvm.org/):

  ```
  $ lldb hello.elf
  (lldb) gdb-remote 1234
  ```
* ``$ make clean`` to delete the generated ``.elf`` and ``.hex`` files

### Windows

If you plan to run the compiled samples, ensure that the path of the directory
containing QEMU (specifically, the ``qemu-system-arm.exe`` file) is present in
the ``PATH`` environment variable.

Start a Command Prompt (``cmd.exe``), change to the directory of a specific
sample (e.g. ``src\baremetal-uart``) and use the following commands to build or
run the sample:
* ``> make.bat build`` to build the sample.
* ``> make.bat run`` to run the sample with QEMU emulator.
* ``> make.bat clean`` to delete the generated ``.elf`` and ``.hex`` files.
