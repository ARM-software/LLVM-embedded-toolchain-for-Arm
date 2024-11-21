# Building from source

## Host platforms

LLVM Embedded Toolchain for Arm is built and tested on Ubuntu 18.04 LTS.

The Windows version of LLVM tools is built on Windows Server 2019
and lightly tested on Windows 10. Windows package provides runtime libraries
built on Linux, because of their limited Windows support.

Building and testing on macOS is functional but experimental.

## Installing prerequisites

The build requires the following software to be installed, in addition
to the [LLVM requirements](https://llvm.org/docs/GettingStarted.html#software):
* CMake 3.20 or above
* Meson
* Git
* Ninja
* Python
* QEMU (for running the test suite, so optional)

On a Ubuntu 18.04.5 LTS machine you can use the following commands to install
the software mentioned above:
```
$ apt-get install python3 git make ninja-build qemu
$ apt-get install clang # If the Clang version installed by the package manager is older than 6.0.0, download a recent version from https://releases.llvm.org or build from source
$ apt-get install cmake # If the CMake version installed by the package manager is too old, download a recent version from https://cmake.org/download and add it to PATH
$ pip install meson
```

On macOS, you can use homebrew:
```
$ brew install llvm python3 git make ninja qemu cmake
$ pip install meson
```

Some recent targets are not supported by QEMU, for these the Arm FVP models are
used instead. These models are available free-of-change but are not
open-source, and come with their own licenses.

These models can be downloaded and installed (into the source tree) with the
`fvp/get_fvps.sh` script. This is currently only available for Linux. By
default, `get_fvps.sh` will run the installers for packages which have them,
which will prompt you to agree to their licenses. Some of the packages do not
have installers, instead they place their license file into the
`fvp/license_terms` directory, which you should read before continuing.

For non-interactive use (for example in CI systems), `get_fvps.sh` can be run
with the `--non-interactive` option, which causes it to implcitly accept all of
the EULAs. If you have previously downloaded and installed the FVPs outside of
the source tree, you can set the `-DFVP_INSTALL_DIR=...` cmake option to set
the path to them.

If the FVPs are not installed, tests which need them will be skipped, but QEMU
tests will still be run, and all library variants will still be built.

## Customizing

To build additional library variants, edit the `CMakeLists.txt` by adding
calls to the `add_library_variant` CMake function using existing library
variant definitions as a template.

To build additional LLVM tools, edit the `CMakeLists.txt` by adding required
tools to the `LLVM_DISTRIBUTION_COMPONENTS` CMake list.

## Building

The toolchain can be built directly with CMake.

```
export CC=clang
export CXX=clang++
mkdir build
cd build
cmake .. -GNinja -DFETCHCONTENT_QUIET=OFF
ninja llvm-toolchain
```

To make it easy to get started, the above command checks out and patches llvm-project & picolibc Git repos automatically.
If you prefer you can check out and patch the repos manually and use those.
If you check out repos manually then it is your responsibility to ensure that the correct revisions are checked out - see `versions.json` to identify these.

```
export CC=clang
export CXX=clang++
mkdir repos
git -C repos clone https://github.com/llvm/llvm-project.git
git -C repos/llvm-project am -k "$PWD"/patches/llvm-project/*.patch
git -C repos clone https://github.com/picolibc/picolibc.git
git -C repos/picolibc am -k "$PWD"/patches/picolibc/*.patch
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

After building, create a zip or tar.xz file as appropriate for the platform:
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

See [patches](https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/tree/main/patches)
directory for the current set of differences from upstream.

The patches for llvm-project are split between two folders, llvm-project and
llvm-project-perf. The former are generally required for building and
successfully running all tests. The patches in llvm-project-perf are optional,
and designed to improve performance in certain circumstances.

To reduce divergence from upstream and potential patch conflicts, the
performance patches are not applied by default, but can be enabled for an
automatic checkout with the APPLY_LLVM_PERFORMANCE_PATCHES option.

## Building individual library variants

When working on library code, it may be useful to build a library variant
without having to rebuild the entire toolchain.

Each variant is built using the `arm-runtimes` sub-project, and can be
configured and built directly if you provide a path to a LLVM build or install.

The default CMake arguments to build a particular variant are stored in a JSON
format in the arm-multilib/json/variants folder, which can be loaded at
configuration with the `-DVARIANT_JSON` setting. Any additional options
provided on the command line will override values from he JSON. `-DC_LIBRARY`
will be required to set which library to build, and `-DLLVM_BINARY_DIR` should
point to the top-level directory of a build or install of LLVM.

(The actual binaries, such as `clang`, are expected to be in
`$LLVM_BINARY_DIR/bin`, not `$LLVM_BINARY_DIR` itself. For example, if you're
using the results of a full build of this toolchain itself in another
directory, then you should set `LLVM_BINARY_DIR` to point at the `llvm`
subdirectory of the previous build tree, not the `llvm/bin` subdirectory.)

For example, to build the `armv7a_soft_nofp` variant using `picolibc`, using
an existing LLVM build and source checkouts:

```
cd LLVM-embedded-toolchain-for-Arm
mkdir build-lib
cd build-lib
cmake ../arm-runtimes -G Ninja \
  -DVARIANT_JSON=../arm-multilib/json/variants/armv7a_soft_nofp.json \
  -DC_LIBRARY=picolibc \
  -DLLVM_BINARY_DIR=/path/to/llvm \
  -DFETCHCONTENT_SOURCE_DIR_LLVMPROJECT=/path/to/llvm-project \
  -DFETCHCONTENT_SOURCE_DIR_PICOLIBC=/path/to/picolibc
ninja
```

If enabled and the required test executor available, tests can be run with
using specific test targets:
`ninja check-picolibc`
`ninja check-compiler-rt`
`ninja check-cxx`
`ninja check-cxxabi`
`ninja check-unwind`

Alternatively, `ninja check-all` runs all enabled tests. 

## Building sets of libraries

As well as individual libraries, it is also possible to build a set of
libraries without rebuilding the entire toolchain. The `arm-multilib`
sub-project builds and collects multiple libraries, and generates a
`multilib.yaml` file to map compile flags to variants.

The `arm-multilib/multilib.json` file defines which variants are built and
their order in the mapping. This can be used to configure the project directly

For example, building the picolibc variants using an existing LLVM build and
source checkouts:
```
cd LLVM-embedded-toolchain-for-Arm
mkdir build-multilib
cd build-multilib
cmake ../arm-multilib -G Ninja \
  -DMULTILIB_JSON=../arm-multilib/json/multilib.json \
  -DC_LIBRARY=picolibc \
  -DLLVM_BINARY_DIR=/path/to/llvm \
  -DFETCHCONTENT_SOURCE_DIR_LLVMPROJECT=/path/to/llvm-project \
  -DFETCHCONTENT_SOURCE_DIR_PICOLIBC=/path/to/picolibc
ninja
```
To only build a subset of the variants defined in the JSON file,
the `-DENABLE_VARIANTS` option controls which variants to build.
E.g, `-DENABLE_VARIANTS="aarch64a;armv7a_soft_nofp"` only builds the two 
variants of `aarch64a` and `armv7a_soft_nofp`.

If enabled and the required test executor available, tests can be run with
using specific test targets:

`ninja check-picolibc`
`ninja check-compiler-rt`
`ninja check-cxx`
`ninja check-cxxabi`
`ninja check-unwind`

Alternatively, `ninja check-all` runs all enabled tests.
`ninja check-<VARAINT_NAME>` runs all the tests for that specific variant.
