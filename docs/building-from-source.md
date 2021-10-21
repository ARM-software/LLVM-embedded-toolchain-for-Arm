# Building from source

## Host platforms

The LLVM Embedded Toolchain for Arm has been built and tested on Linux/Ubuntu
18.04.5 LTS.

## Installing prerequisites

The build requires the following software to be installed:
* a suitable compiler toolchain:
  * Clang 6.0.0 or above, or
  * GCC 5.1.0 or above
* CMake 3.13.4 or above
* Python version 3.6 or above and python3-venv
* Git
* GNU Make

On a Ubuntu 18.04.5 LTS machine you can use the following commands to install
the software mentioned above:
```
# apt-get install clang # If the Clang version installed by the package manager is older than 6.0.0, download a recent version from https://releases.llvm.org or build from source
# apt-get install python3
# apt-get install python3-venv
# apt-get install git
# apt-get install make
# apt-get install cmake # If the CMake version installed by the package manager is older than 3.13.4, download a recent version from https://cmake.org/download and add it to PATH
```

## Preparing the environment

The build scripts are written in Python and require a Python virtual environment
to run. Use the following steps to create the environment.

1. Install the build scripts in a Python virtual env (in directory ``venv``):
```
$ ./setup.sh
```
2. Activate the virtual environment:
```
$ . ./venv/bin/activate
```

## Using the `build.py` script

The simplest way to build the toolchain is to invoke
```
$ build.py
```
in the Python. virtual environment.

The build script supports various command line options. To get a description of
all options run:
```
$ build.py -h
```
Some notable options include:
* ``--revision`` the LLVM Embedded Toolchain for Arm version. Default version
  is ``13.0.0``. The available versions are:
  * ``13.0.0`` - based on LLVM 13.0.0 and newlib 4.1.0
  * ``branch-13`` - based on the tip of the LLVM 13 branch and newlib 4.1.0
  * ``HEAD`` - based on the latest commits in the LLVM and newlib repositories
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

## Testing the toolchain

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
mentioned in the [Installing prerequisites](#installing-prerequisites) section
you will also need a Mingw-w64 toolchain based on GCC 5.1.0 or above installed.
For example, to install it on Ubuntu Linux use the following command:

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
libraries from your local machine to the toolchain ``bin`` directory. 

The following three libraries are used:

Library             | Project   | Link
--------------------|-----------|---------------------
libstdc++-6.dll     | GCC       | https://gcc.gnu.org
libgcc_s_seh-1.dll  | GCC       | https://gcc.gnu.org
libwinpthread-1.dll | Mingw-w64 | http://mingw-w64.org

The libraries are distributed under their own licenses, this needs to
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

### LLVM:
* Recognize $@ in a config file argument to mean the directory of the config
  file, allowing toolchain relative paths.
