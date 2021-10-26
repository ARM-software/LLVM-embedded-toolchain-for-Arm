# Sample code for the LLVM Embedded Toolchain for Arm

This directory contains sample code which demonstrates how to use the LLVM
Embedded Toolchain for Arm.

## Directory structure

* `ldscripts` - Linker scripts used by the samples.
* `startup` - Startup code used by the samples.
* `src` - Sample source code, Makefile and description, each sub-directory is a
  separate sample.

## Supported environments

The build scripts support three different environments:
* Linux
* Windows
* Windows + [MSYS2](https://www.msys2.org/)

## Prerequisites

In order to compile the samples you will need the following tools:
* LLVM Embedded Toolchain for Arm
* GNU Make (Linux and MSYS2)

To run the samples you will need a QEMU emulator to be installed on your
machine. The ``basic-semihosting`` sample uses the QEMU User space emulator,
on Ubuntu Linux it can be installed using the following command:

```
# apt-get install qemu-user
```

The User space emulator is only available for Linux.

The other two samples (``baremetal-semihosting`` and ``baremetal-uart``) rely on
the QEMU Arm System emulator. On Ubuntu Linux it can be installed as follows:

```
# apt-get install qemu-system-arm
```

The Windows installer can be downloaded from
https://www.qemu.org/download/#windows.

To debug the samples you will need to install GDB provided by the
[GNU Arm Embedded Toolchain](https://developer.arm.com/tools-and-software/open-source-software/developer-tools/gnu-toolchain/gnu-rm/downloads).
Debugging is only supported on Linux.

## Specifying the location of the installed toolchain

The Makefiles of the code samples need the location of the installed LLVM
Embedded Toolchain for Arm.

If you are using Linux or MSYS2 and running the samples directly from the
installation directory the Makefiles will determine the correct location
automatically.

Otherwise you will need to set the environment variable ``BIN_PATH`` to point
to the ``bin`` directory of the toolchain.

## Compiling, running and debugging the samples

### Linux and MSYS2

Change to the directory of a specific sample (e.g. ``src/baremetal-uart``) and
use the following commands to build, run or debug the sample:
* ``$ make build`` to build the sample.
* ``$ make run`` to run the sample with QEMU emulator.
* ``$ make debug`` to run the sample with QEMU emulator with GDB server
  listening on the default port 1234 (Note: ``debug`` is supported only on
  Linux).

  To debug attach to QEMU with
  [GNU Arm Embedded Toolchain](https://developer.arm.com/tools-and-software/open-source-software/developer-tools/gnu-toolchain/gnu-rm/downloads)
  GDB:

  ```
  $ arm-none-eabi-gdb hello.elf
  (gdb) target remote :1234
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
