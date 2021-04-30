# Sample code for the LLVM Embedded Toolchain for Arm

This directory contains sample code which demonstrates how to use the LLVM
Embedded Toolchain for Arm.

## Directory structure

* `ldscripts` - Linker scripts used by the samples.
* `startup` - Startup code used by the samples.
* `src` - Sample source code, Makefile and description, each sub-directory is a
  separate sample.

## Prerequisites

In order to compile the samples you will need the following tools:
* LLVM Embedded Toolchain for Arm
* GNU Make

To run the samples you will need a QEMU emulator to be installed on your
machine. The ``basic-semihosting`` sample uses the QEMU User space emulator,
on Ubuntu Linux it can be installed using the following command:

```
# apt-get install qemu-user
```

The other two samples (``baremetal-semihosting`` and ``baremetal-uart``) rely on
the QEMU Arm System emulator. On Ubuntu Linux it can be installed as follows:

```
# apt-get install qemu-system-arm
```

To debug the samples you will need to install GDB provided by the
[GNU Arm Embedded Toolchain](https://developer.arm.com/tools-and-software/open-source-software/developer-tools/gnu-toolchain/gnu-rm/downloads).

## Using the samples

### Specifying the location of the installed toolchain

The Makefiles of the code samples need the location of the installed LLVM
Embedded Toolchain for Arm. There are several ways to specify the location:
* Set the environment variable ``BIN_PATH`` to point to the ``bin`` directory
  of the toolchain, or
* Set the environment variable ``VERSION`` to the revision of the built
  toolchain (e.g. ``0.1`` or ``HEAD``). The sample Makefiles will assume that
  the toolchain is installed in the default directory used by the
  ``build.py`` script (i.e.
  ``install-<revision>/LLVMEmbeddedToolchainForArm-<revision>``
  in the root of the ``LLVM-embedded-toolchain-for-Arm`` repository
  checkout), or
* Don't set any of the above variables. This will have the same effect as
  setting ``VERSION=0.1``

### Compiling, running and debugging the samples

Change to the directory of a specific sample (e.g. ``src/baremetal-uart``) and
use the following commands to build, run or debug the sample:
* ``$ make build`` to build the sample.
* ``$ make run`` to run the sample with QEMU emulator.
* ``$ make debug`` to run the sample with QEMU emulator with GDB server
  listening on the default port 1234.

  To debug attach to QEMU with
  [GNU Arm Embedded Toolchain](https://developer.arm.com/tools-and-software/open-source-software/developer-tools/gnu-toolchain/gnu-rm/downloads)
  GDB:

  ```
  $ arm-none-eabi-gdb hello.elf
  (gdb) target remote :1234
  ```
* ``$ make clean`` to delete the generated ``.elf`` and ``.hex`` files

Note: you can set an environment variable for a command using the following
syntax:
```
$ VERSION=HEAD make run
```
