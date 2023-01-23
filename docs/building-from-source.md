# Building from source

## Host platforms

The LLVM Embedded Toolchain for Arm has been built and tested on Linux/Ubuntu
18.04.5 LTS.

## Installing prerequisites

The build requires the following software to be installed, in addition
to the [LLVM requirements|https://llvm.org/docs/GettingStarted.html#software]:
* CMake 3.20 or above
* Meson
* Git
* Ninja
* Python

On a Ubuntu 18.04.5 LTS machine you can use the following commands to install
the software mentioned above:
```
$ apt-get install clang # If the Clang version installed by the package manager is older than 6.0.0, download a recent version from https://releases.llvm.org or build from source
$ apt-get install python3
$ apt-get install git
$ apt-get install make
$ apt-get install ninja-build
$ apt-get install cmake # If the CMake version installed by the package manager is too old, download a recent version from https://cmake.org/download and add it to PATH
$ pip install meson
```

## Building

The toolchain can be built directly with CMake.

```
mkdir build
cd build
cmake .. -GNinja -DFETCHCONTENT_QUIET=OFF
ninja llvm-toolchain
```

To make it easy to get started, the above command checks out and patches llvm-project & picolibc Git repos automatically.
If you prefer you can check out and patch the repos manually and use those:
```
mkdir repos
git -C repos clone https://github.com/llvm/llvm-project.git
git -C repos/llvm-project apply ../../patches/llvm-project.patch
git -C repos clone https://github.com/picolibc/picolibc.git
git -C repos/picolibc apply ../../patches/picolibc.patch
mkdir build
cd build
cmake .. -GNinja -DFETCHCONTENT_SOURCE_DIR_LLVMPROJECT=../repos/llvm-project -DFETCHCONTENT_SOURCE_DIR_PICOLIBC=../repos/picolibc
ninja llvm-toolchain
```

### Testing the toolchain

```
ninja check-llvm-toolchain
```

### Packaging the toolchain

After building, create a zip or tar.gz file as appropriate for the platform:
```
ninja package-llvm-toolchain
```

### Cross-compiling the toolchain for Windows

The LLVM Embedded Toolchain for Arm can be cross-compiled to run on Windows.
The compilation itself still happens on Linux. In addition to the prerequisites
mentioned in the [Installing prerequisites](#installing-prerequisites) section
you will also need a Mingw-w64 toolchain based on GCC 7.1.0 or above installed.
For example, to install it on Ubuntu Linux use the following command:
```
# apt-get install mingw-w64
```

The MinGW build includes GCC & MinGW libraries into the package.

The following three libraries are used:

Library             | Project   | Link
--------------------|-----------|---------------------
libstdc++-6.dll     | GCC       | https://gcc.gnu.org
libgcc_s_seh-1.dll  | GCC       | https://gcc.gnu.org
libwinpthread-1.dll | Mingw-w64 | http://mingw-w64.org

The libraries are distributed under their own licenses, this needs to
be taken into consideration if you decide to redistribute the built toolchain.

To enable the MinGW build, set the LLVM_TOOLCHAIN_CROSS_BUILD_MINGW option:
```
cmake . -DLLVM_TOOLCHAIN_CROSS_BUILD_MINGW=ON
ninja package-llvm-toolchain
```
The same build directory can be used for both native and MinGW toolchains.

## Known limitations
* Depending on the state of the sources, build errors may occur when
  the latest revisions of the llvm-project & picolibc repos are used.

## Divergences from upstream

### picolibc:
* Added a fix for building with -mthumb

### LLVM:
* Recognize $@ in a config file argument to mean the directory of the config
  file, allowing toolchain relative paths.
