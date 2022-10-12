#
# Copyright (c) 2022, Arm Limited and affiliates.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


# How to use this file
#
# This file is used to build LLVM Embedded Toolchain for Arm.
# Recent versions of the following tools are pre-requisites:
# * A toolchain such as gcc & binutils
# * cmake
# * meson
# * ninja
# * python3
# * make and qemu to run tests
#
# Commands to build:
#   mkdir build
#   cd build
#   cmake .. -GNinja -DFETCHCONTENT_QUIET=OFF
#   ninja
#   ninja check-llvm-toolchain
#
# To make it easy to get started, the above command checks out
# llvm-project & picolibc Git repos automatically.
#
# If the repos are checked out automatically then cmake will fetch the
# latest changes and check them out every time it runs. To disable this
# behaviour run:
#   cmake . -DFETCHCONTENT_FULLY_DISCONNECTED=ON
#
# If you prefer you can check out and patch the repos manually and use those:
#   mkdir repos
#   git -C repos clone https://github.com/llvm/llvm-project.git
#   git -C repos/llvm-project apply ../../patches/llvm-HEAD.patch
#   git -C repos clone https://github.com/picolibc/picolibc.git
#   git -C repos/picolibc apply ../../patches/picolibc-HEAD.patch
#   mkdir build
#   cd build
#   cmake .. -GNinja -DFETCHCONTENT_SOURCE_DIR_LLVMPROJECT=../repos/llvm-project -DFETCHCONTENT_SOURCE_DIR_PICOLIBC=../repos/picolibc
#   ninja
#   ninja check-llvm-toolchain
#
# To install the toolchain run:
#   cmake . --install-prefix /absolute/path/to/install/directory
#   ninja install-llvm-toolchain
#
#
# This file is designed to be used in a way that will be familiar to
# LLVM developers. Targets like clang and check-all can be built as usual.
# In addition there are targets to build picolibc & runtimes variants.
#
#
# Cross-building from Linux to Windows MinGW is supported.
# Note that a build created this way includes GCC & MinGW DLLs which
# come under a different license. See building-from-source.md for
# details.
#
# To enable cross-building run:
#   cmake . -DLLVM_TOOLCHAIN_CROSS_BUILD_MINGW=ON -DCMAKE_INSTALL_PREFIX=$(pwd)/install-mingw
#
# If cross-building, there will be two toolchains built:
# 1. The "build" toolchain. This is used to build the libraries.
# 2. The "host" toolchain. This is the toolchain that will be packaged
#    up into "LLVM Embedded Toolchain for Arm".
# For "native" builds the "build" toolchain is also used as the "host"
# toolchain.
#
# The terminology can be pretty confusing when you've got
# toolchains building toolchains. There's a good explanation at
# https://docs.conan.io/en/latest/systems_cross_building/cross_building.html
#
# To build the "build" toolchain we add the llvm source as a
# subdirectory. This means you can build all its targets such
# as check-llvm directly.
# If cross-building, a "host" toolchain is built. It is built as a
# separate project.
#
# When libraries are built, they are always copied into the "build"
# toolchain. The primary reason for this is to minimise the number of
# if/else statements in the CMake code, but it has the nice side-effect
# that a cross-build is almost a superset of a native build.
# It is only at install time that one of either the "build" or "host"
# toolchain is copied to the install location.
# This makes it easy to switch back and forth between native and cross
# builds with:
#   cmake . -DLLVM_TOOLCHAIN_CROSS_BUILD_MINGW=<ON or OFF> --install-prefix=...
#
#
# When building the toolchain repeatedly, the most time-consuming part
# can be building the libraries since each one is configured separately.
# To work around this, the variants that get built can be limited using
# the LLVM_TOOLCHAIN_LIBRARY_VARIANTS option e.g.:
#   cmake . '-DLLVM_TOOLCHAIN_LIBRARY_VARIANTS=aarch64;armv6m_soft_nofp'


# CONFIGURE_HANDLED_BY_BUILD was introduced in CMake 3.20 and it
# greatly speeds up incremental builds.
cmake_minimum_required(VERSION 3.20)

option(
    LLVM_TOOLCHAIN_CROSS_BUILD_MINGW
    "Cross-build for Windows. Using this option implies that you accept the GCC & MinGW licenses."
)
set(LLVM_TOOLCHAIN_LIBRARY_VARIANTS
    "" CACHE STRING
    "Build only the specified library variants. If not specified then build all variants."
)

set(BUG_REPORT_URL "https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/issues" CACHE STRING "")
set(LLVM_DISTRIBUTION_COMPONENTS
    clang-format
    clang-resource-headers
    clang
    dsymutil
    lld
    llvm-ar
    llvm-config
    llvm-cov
    llvm-cxxfilt
    llvm-dwarfdump
    llvm-nm
    llvm-objcopy
    llvm-objdump
    llvm-profdata
    llvm-ranlib
    llvm-readelf
    llvm-readobj
    llvm-size
    llvm-strip
    llvm-symbolizer
    LTO
    CACHE STRING ""
)
set(LLVM_ENABLE_PROJECTS clang;lld CACHE STRING "")
set(LLVM_TARGETS_TO_BUILD AArch64;ARM CACHE STRING "")
set(LLVM_DEFAULT_TARGET_TRIPLE aarch64-none-elf CACHE STRING "")

# Default to a release build
# (CMAKE_BUILD_TYPE is a special CMake variable so if you want to set
# it then you have to FORCE it).
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE BOOL "" FORCE)
endif()

# If ccache is available then use it by default.
find_program(CCACHE_EXECUTABLE ccache)
if(CCACHE_EXECUTABLE)
    set(LLVM_CCACHE_BUILD ON CACHE BOOL "")
endif()


# Define which library variants to build and which flags to use
# The order is <arch> <name suffix> <flags>
set(library_variants
    aarch64         ""                  "-march=armv8-a"
    armv6m          _soft_nofp          "-mfloat-abi=soft -march=armv6m"
    armv7em         _hard_fpv4_sp_d16   "-mfloat-abi=hard -march=armv7em -mfpu=fpv4-sp-d16"
    armv7em         _hard_fpv5_d16      "-mfloat-abi=hard -march=armv7em -mfpu=fpv5-d16"
    armv7em         _soft_nofp          "-mfloat-abi=soft -march=armv7em -mfpu=none"
    armv7m          _soft_nofp          "-mfloat-abi=soft -march=armv7m+nofp"
    armv8m.main     _hard_fp            "-mfloat-abi=hard -march=armv8m.main+fp"
    armv8m.main     _soft_nofp          "-mfloat-abi=soft -march=armv8m.main+nofp"
    armv8.1m.main   _hard_fp            "-mfloat-abi=hard -march=armv8.1m.main+fp"
    armv8.1m.main   _hard_nofp_mve      "-mfloat-abi=hard -march=armv8.1m.main+nofp+mve"
    armv8.1m.main   _soft_nofp_nomve    "-mfloat-abi=soft -march=armv8.1m.main+nofp+nomve"
)


include(ExternalProject)
include(FetchContent)

# Check out and patch llvm-project and picolibc.
#
# If you'd rather check out and patch manually then run cmake with
# -DFETCHCONTENT_SOURCE_DIR_LLVMPROJECT=/path/to/llvm-project
# -DFETCHCONTENT_SOURCE_DIR_PICOLIBC=/path/to/picolibc
#
# By default check out will be silent but this can be changed by running
# cmake with -DFETCHCONTENT_QUIET=OFF
#
# If you want to stop cmake updating the repos then run
# cmake . -DFETCHCONTENT_FULLY_DISCONNECTED=ON

FetchContent_Declare(llvmproject
    GIT_REPOSITORY https://github.com/llvm/llvm-project.git
    GIT_TAG origin/main
    GIT_SHALLOW TRUE
    GIT_PROGRESS TRUE
    PATCH_COMMAND git reset --quiet --hard && git clean --quiet --force -dx && git apply ${CMAKE_CURRENT_SOURCE_DIR}/patches/llvm-HEAD.patch
    # Add the llvm subdirectory later to ensure that
    # LLVMEmbeddedToolchainForArm is the first project declared.
    # Otherwise CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT
    # can't be used.
    SOURCE_SUBDIR do_not_add_llvm_subdir_yet
)

FetchContent_Declare(picolibc
    GIT_REPOSITORY https://github.com/picolibc/picolibc.git
    GIT_TAG origin/main
    GIT_SHALLOW TRUE
    GIT_PROGRESS TRUE
    PATCH_COMMAND git reset --quiet --hard && git clean --quiet --force -dx && git apply ${CMAKE_CURRENT_SOURCE_DIR}/patches/picolibc-HEAD.patch
    # We only want to download the content, not configure it at this
    # stage. picolibc will be built in many configurations using
    # ExternalProject_Add using the sources that are checked out here.
    SOURCE_SUBDIR do_not_add_picolibc_subdir
)

FetchContent_MakeAvailable(llvmproject)
FetchContent_MakeAvailable(picolibc)


# Grab the version out of LLVM sources
file(
    STRINGS ${llvmproject_SOURCE_DIR}/llvm/CMakeLists.txt version_strings
    REGEX [[set\(LLVM_VERSION_[A-Z]+ [0-9]+\)]]
)
string(REGEX MATCH [[MAJOR ([0-9]+)]] unused "${version_strings}")
set(LLVM_VERSION_MAJOR ${CMAKE_MATCH_1})
string(REGEX MATCH [[MINOR ([0-9]+)]] unused "${version_strings}")
set(LLVM_VERSION_MINOR ${CMAKE_MATCH_1})
string(REGEX MATCH [[PATCH ([0-9]+)]] unused "${version_strings}")
set(LLVM_VERSION_PATCH ${CMAKE_MATCH_1})


project(
    LLVMEmbeddedToolchainForArm
    VERSION ${LLVM_VERSION_MAJOR}.${LLVM_VERSION_MINOR}.${LLVM_VERSION_PATCH}
    DESCRIPTION "LLVM Embedded Toolchain for Arm"
    HOMEPAGE_URL "https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm"
)

# We generally want to install to a local directory to see what the
# output will look like rather than install into the system, so change
# the default accordingly.
# See https://cmake.org/cmake/help/latest/variable/CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT.html
# Note that this code only works after the first call to project so it
# can't be moved after the add_subdirectory command below.
if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
    set(CMAKE_INSTALL_PREFIX
        "${CMAKE_BINARY_DIR}/install"
        CACHE PATH "" FORCE
    )
endif()

# These must be set before include(CPack) which the llvm CMakeLists.txt does.
# Restrict which LLVM components are installed.
if(LLVM_TOOLCHAIN_CROSS_BUILD_MINGW)
    set(CPACK_COMPONENTS_ALL llvm-toolchain)
else()
    set(CPACK_COMPONENTS_ALL ${LLVM_DISTRIBUTION_COMPONENTS} llvm-toolchain)
endif()
# Enable limiting the installed components in TGZ and ZIP packages.
set(CPACK_ARCHIVE_COMPONENT_INSTALL TRUE)
# Don't create a separate archive for each component.
set(CPACK_COMPONENTS_GROUPING ALL_COMPONENTS_IN_ONE)
# Strip debug info from files before packaging them
set(CPACK_STRIP_FILES TRUE)

string(TOLOWER ${CMAKE_SYSTEM_PROCESSOR} processor_name)
string(REGEX MATCH "amd64|x64|x86" x86_match ${processor_name})
if(x86_match)
    set(processor_name "x86_64")
else()
    set(processor_name "AArch64")
endif()
if(LLVM_TOOLCHAIN_CROSS_BUILD_MINGW)
    set(CPACK_SYSTEM_NAME "Windows-${processor_name}")
else()
    set(CPACK_SYSTEM_NAME "${CMAKE_SYSTEM_NAME}-${processor_name}")
endif()

add_subdirectory(
    ${llvmproject_SOURCE_DIR}/llvm llvm
)

# Including CPack again after llvm CMakeLists.txt included it
# resets CPACK_PACKAGE_VERSION to the default MAJOR.MINOR.PATCH format.
include(CPack)

set(llvm_bin ${LLVM_BINARY_DIR}/bin)

# Ensure LLVM tool symlinks are installed.
list(APPEND CMAKE_MODULE_PATH ${llvmproject_SOURCE_DIR}/llvm/cmake/modules)
llvm_install_symlink(LLVM llvm-ranlib llvm-ar ALWAYS_GENERATE)
llvm_install_symlink(LLVM llvm-readelf llvm-readobj ALWAYS_GENERATE)
llvm_install_symlink(LLVM llvm-strip llvm-objcopy ALWAYS_GENERATE)

# For building picolibc use Meson.
# Although picolibc has support for building with CMake, the Meson code
# is more mature and works better with LLVM.
find_program(MESON_EXECUTABLE meson REQUIRED)


# Generate VERSION.txt
# Use add_custom_target instead of add_custom_command so that the target
# is always considered out-of-date, ensuring that VERSION.txt will be
# updated when the git revision changes.
add_custom_target(
    version_txt
    COMMAND
    "${CMAKE_COMMAND}"
    -DLLVMEmbeddedToolchainForArm_VERSION=${LLVMEmbeddedToolchainForArm_VERSION}
    -Dllvmproject_SOURCE_DIR=${llvmproject_SOURCE_DIR}
    -Dpicolibc_SOURCE_DIR=${picolibc_SOURCE_DIR}
    -P ${CMAKE_CURRENT_SOURCE_DIR}/cmake/generate_version_txt.cmake
    BYPRODUCTS ${CMAKE_CURRENT_BINARY_DIR}/VERSION.txt
)
install(
    FILES
    ${CMAKE_CURRENT_BINARY_DIR}/VERSION.txt
    DESTINATION .
    COMPONENT llvm-toolchain
)


# Groups all the targets that comprise the toolchain.
add_custom_target(llvm-toolchain ALL)

# Groups all the runtime targets
add_custom_target(llvm-toolchain-runtimes)

if(NOT LLVM_TOOLCHAIN_CROSS_BUILD_MINGW)
    add_dependencies(
        llvm-toolchain
        ${LLVM_DISTRIBUTION_COMPONENTS}
    )
endif()

add_dependencies(
    llvm-toolchain
    llvm-toolchain-runtimes
    version_txt
)

foreach(variant ${LLVM_TOOLCHAIN_LIBRARY_VARIANTS})
    set(enable_${variant} TRUE)
endforeach()

# Destructively iterate over the 3-tuples defining the variants.
while(library_variants)
    list(POP_FRONT library_variants target_arch variant_suffix flags)

    if(target_arch STREQUAL "aarch64")
        set(target "aarch64-none-elf")
        set(cpu_family aarch64)
    else()
        set(target "${target_arch}-none-eabi")
        set(cpu_family arm)
    endif()
    set(variant "${target_arch}${variant_suffix}")
    set(common_flags "--target=${target} ${flags}")

    if(LLVM_TOOLCHAIN_LIBRARY_VARIANTS)
        if(NOT enable_${variant})
            message("Disabling library variant ${variant}")
            continue()
        else()
            message("Enabling library variant ${variant}")
        endif()
    endif()

    # Create clang configuration files
    # https://clang.llvm.org/docs/UsersManual.html#configuration-files
    set(crt0 "crt0.o")
    set(extra_args "")
    configure_file(cmake/config.cfg.in ${llvm_bin}/${variant}.cfg)
    set(crt0 "crt0-semihost.o")
    set(extra_args "\n-lsemihost")
    configure_file(cmake/config.cfg.in ${llvm_bin}/${variant}_semihost.cfg)
    install(FILES
        ${llvm_bin}/${variant}.cfg
        ${llvm_bin}/${variant}_semihost.cfg
        DESTINATION bin
        COMPONENT llvm-toolchain
    )

    set(sysroot ${LLVM_BINARY_DIR}/lib/clang-runtimes/${variant})

    # picolibc
    ExternalProject_Add(
        picolibc_${variant}
        SOURCE_DIR ${picolibc_SOURCE_DIR}
        INSTALL_DIR ${sysroot}
        PREFIX picolibc/${variant}
        DEPENDS clang lld llvm-ar llvm-config llvm-nm llvm-ranlib llvm-strip
        CONFIGURE_COMMAND ${MESON_EXECUTABLE} -Dincludedir=include -Dlibdir=lib --prefix <INSTALL_DIR> --cross-file <BINARY_DIR>/meson-cross-build.txt ${picolibc_SOURCE_DIR}
        BUILD_COMMAND ninja
        INSTALL_COMMAND ninja install
        USES_TERMINAL_CONFIGURE TRUE
        USES_TERMINAL_BUILD TRUE
        USES_TERMINAL_TEST TRUE
        LIST_SEPARATOR ,
        # Always run the build command so that incremental builds are correct.
        BUILD_ALWAYS TRUE
        CONFIGURE_HANDLED_BY_BUILD TRUE
    )
    # Set meson_c_args to a comma-separated list of the clang path and flags e.g.
    # 'path/to/clang', '--target=armv6m-none-eabi', '-march=armv6m'
    set(meson_c_args "${common_flags}")
    string(REPLACE " " "', '" meson_c_args "${meson_c_args}")
    set(meson_c_args "'${llvm_bin}/clang', '${meson_c_args}'")
    ExternalProject_Get_Property(picolibc_${variant} BINARY_DIR)
    configure_file(cmake/meson-cross-build.txt.in ${BINARY_DIR}/meson-cross-build.txt @ONLY)

    # compiler-rt

    # Defining _DEFAULT_SOURCE means that extensions like posix_memalign
    # can be used by the C++ runtimes. This is required to implement
    # C++17's aligned new & delete operators.
    set(runtimes_flags "${common_flags} -ffunction-sections -fdata-sections -fno-ident --sysroot ${sysroot} -D_DEFAULT_SOURCE")

    ExternalProject_Add(
        compiler_rt_${variant}
        SOURCE_DIR ${llvmproject_SOURCE_DIR}/compiler-rt
        PREFIX compiler-rt/${variant}
        INSTALL_DIR compiler-rt/${variant}/install
        DEPENDS clang lld llvm-ar llvm-config llvm-nm llvm-ranlib picolibc_${variant}
        CMAKE_ARGS
        -DCMAKE_AR=${llvm_bin}/llvm-ar
        -DCMAKE_ASM_COMPILER_TARGET=${target}
        -DCMAKE_ASM_FLAGS=${runtimes_flags}
        -DCMAKE_BUILD_TYPE=Release
        -DCMAKE_CXX_COMPILER=${llvm_bin}/clang++
        -DCMAKE_CXX_COMPILER_TARGET=${target}
        -DCMAKE_CXX_FLAGS=${runtimes_flags}
        -DCMAKE_C_COMPILER=${llvm_bin}/clang
        -DCMAKE_C_COMPILER_TARGET=${target}
        -DCMAKE_C_FLAGS=${runtimes_flags}
        -DCMAKE_EXE_LINKER_FLAGS=-fuse-ld=lld
        -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
        -DCMAKE_NM=${llvm_bin}/llvm-nm
        -DCMAKE_RANLIB=${llvm_bin}/llvm-ranlib
        # Set the cmake system name to Generic so that no host system
        # include files are searched. At least on OSX this problem
        # occurs.
        -DCMAKE_SYSTEM_NAME=Generic
        -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY
        -DCOMPILER_RT_BAREMETAL_BUILD=ON
        -DCOMPILER_RT_BUILD_LIBFUZZER=OFF
        -DCOMPILER_RT_BUILD_PROFILE=OFF
        -DCOMPILER_RT_BUILD_SANITIZERS=OFF
        -DCOMPILER_RT_BUILD_XRAY=OFF
        -DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON
        -DLLVM_CCACHE_BUILD=${LLVM_CCACHE_BUILD}
        -DLLVM_CONFIG_PATH=${llvm_bin}/llvm-config
        USES_TERMINAL_CONFIGURE TRUE
        USES_TERMINAL_BUILD TRUE
        USES_TERMINAL_INSTALL TRUE
        USES_TERMINAL_TEST TRUE
        LIST_SEPARATOR ,
        # Always run the build command so that incremental builds are correct.
        BUILD_ALWAYS TRUE
        CONFIGURE_HANDLED_BY_BUILD TRUE
    )
    ExternalProject_Get_Property(compiler_rt_${variant} INSTALL_DIR)
    # Copy compiler-rt install into sysroot, moving
    # generic/libclang_rt.builtins-<arch>.a out of its subdirectory.
    add_custom_command(
        TARGET compiler_rt_${variant}
        POST_BUILD
        COMMAND "${CMAKE_COMMAND}" -E copy_directory ${INSTALL_DIR} ${sysroot}
        COMMAND "${CMAKE_COMMAND}" -E copy_directory ${sysroot}/lib/generic ${sysroot}/lib
        COMMAND "${CMAKE_COMMAND}" -E rm -rf ${sysroot}/lib/generic
    )

    # Other LLVM runtimes

    ExternalProject_Add(
        runtimes_${variant}
        SOURCE_DIR ${llvmproject_SOURCE_DIR}/runtimes
        INSTALL_DIR ${sysroot}
        PREFIX runtimes/${variant}
        DEPENDS clang compiler_rt_${variant} lld llvm-ar llvm-config llvm-nm llvm-ranlib picolibc_${variant}
        CMAKE_ARGS
        -DCMAKE_AR=${llvm_bin}/llvm-ar
        -DCMAKE_ASM_FLAGS=${runtimes_flags}
        -DCMAKE_BUILD_TYPE=MinSizeRel
        -DCMAKE_CXX_COMPILER=${llvm_bin}/clang++
        -DCMAKE_CXX_COMPILER_TARGET=${target}
        -DCMAKE_CXX_FLAGS=${runtimes_flags}
        -DCMAKE_C_COMPILER=${llvm_bin}/clang
        -DCMAKE_C_COMPILER_TARGET=${target}
        -DCMAKE_C_FLAGS=${runtimes_flags}
        -DCMAKE_EXE_LINKER_FLAGS=-fuse-ld=lld
        -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
        -DCMAKE_NM=${llvm_bin}/llvm-nm
        -DCMAKE_RANLIB=${llvm_bin}/llvm-ranlib
        -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY
        -DLIBCXXABI_BAREMETAL=ON
        -DLIBCXXABI_ENABLE_ASSERTIONS=OFF
        -DLIBCXXABI_ENABLE_EXCEPTIONS=OFF
        -DLIBCXXABI_ENABLE_PIC=OFF
        -DLIBCXXABI_ENABLE_SHARED=OFF
        -DLIBCXXABI_ENABLE_STATIC=ON
        -DLIBCXXABI_ENABLE_THREADS=OFF
        -DLIBCXXABI_LIBCXX_INCLUDES=${sysroot}/include/c++/v1
        -DLIBCXXABI_USE_COMPILER_RT=ON
        -DLIBCXXABI_USE_LLVM_UNWINDER=ON
        -DLIBCXX_CXX_ABI=libcxxabi
        -DLIBCXX_ENABLE_DEBUG_MODE_SUPPORT=OFF
        -DLIBCXX_ENABLE_EXCEPTIONS=OFF
        -DLIBCXX_ENABLE_EXPERIMENTAL_LIBRARY=OFF
        -DLIBCXX_ENABLE_FILESYSTEM=OFF
        -DLIBCXX_ENABLE_LOCALIZATION=OFF
        -DLIBCXX_ENABLE_MONOTONIC_CLOCK=OFF
        -DLIBCXX_ENABLE_PARALLEL_ALGORITHMS=OFF
        -DLIBCXX_ENABLE_RANDOM_DEVICE=OFF
        -DLIBCXX_ENABLE_RTTI=OFF
        -DLIBCXX_ENABLE_SHARED=OFF
        -DLIBCXX_ENABLE_STATIC=ON
        -DLIBCXX_ENABLE_THREADS=OFF
        -DLIBCXX_ENABLE_WIDE_CHARACTERS=OFF
        -DLIBCXX_INCLUDE_BENCHMARKS=OFF
        # libc++ CMake files incorrectly detect that the "-GR-" flag
        # (the clang-cl analog of -fno-rtti) is supported. Manually mark it
        # as unsupported to avoid warnings.
        -DLIBCXX_SUPPORTS_GR_FLAG=OFF
        -DLIBUNWIND_ENABLE_SHARED=OFF
        -DLIBUNWIND_ENABLE_STATIC=ON
        -DLIBUNWIND_ENABLE_THREADS=OFF
        -DLIBUNWIND_IS_BAREMETAL=ON
        -DLIBUNWIND_REMEMBER_HEAP_ALLOC=ON
        -DLIBUNWIND_USE_COMPILER_RT=ON
        -DLLVM_CCACHE_BUILD=${LLVM_CCACHE_BUILD}
        -DLLVM_ENABLE_RUNTIMES=libcxxabi,libcxx,libunwind
        USES_TERMINAL_CONFIGURE TRUE
        USES_TERMINAL_BUILD TRUE
        USES_TERMINAL_INSTALL TRUE
        USES_TERMINAL_TEST TRUE
        LIST_SEPARATOR ,
        # Always run the build command so that incremental builds are correct.
        BUILD_ALWAYS TRUE
        CONFIGURE_HANDLED_BY_BUILD TRUE
    )

    add_dependencies(
        llvm-toolchain-runtimes
        compiler_rt_${variant}
        picolibc_${variant}
        runtimes_${variant}
    )

    install(
        DIRECTORY ${sysroot}
        DESTINATION lib/clang-runtimes
        COMPONENT llvm-toolchain
    )
endwhile()

install(
    DIRECTORY docs
    DESTINATION .
    COMPONENT llvm-toolchain
)

if(LLVM_TOOLCHAIN_CROSS_BUILD_MINGW)
    set(mingw_runtime_dlls
        "\n - MinGW runtime DLLs: third-party-licenses/COPYING.MinGW-w64-runtime.txt, third-party-licenses/COPYING3.GCC, third-party-licenses/COPYING.RUNTIME"
    )
endif()
configure_file(cmake/THIRD-PARTY-LICENSES.txt.in THIRD-PARTY-LICENSES.txt)

install(
    FILES CHANGELOG.md LICENSE.txt README.md ${CMAKE_CURRENT_BINARY_DIR}/THIRD-PARTY-LICENSES.txt
    DESTINATION .
    COMPONENT llvm-toolchain
)

set(third_party_license_files
    ${llvmproject_SOURCE_DIR}/llvm/LICENSE.TXT          LLVM-LICENSE.txt
    ${llvmproject_SOURCE_DIR}/clang/LICENSE.TXT         CLANG-LICENSE.txt
    ${llvmproject_SOURCE_DIR}/lld/LICENSE.TXT           LLD-LICENSE.txt
    ${llvmproject_SOURCE_DIR}/compiler-rt/LICENSE.TXT   COMPILER-RT-LICENSE.txt
    ${llvmproject_SOURCE_DIR}/libcxx/LICENSE.TXT        LIBCXX-LICENSE.txt
    ${llvmproject_SOURCE_DIR}/libcxxabi/LICENSE.TXT     LIBCXXABI-LICENSE.txt
    ${picolibc_SOURCE_DIR}/COPYING.NEWLIB               COPYING.NEWLIB
    ${picolibc_SOURCE_DIR}/COPYING.picolibc             COPYING.picolibc
)
while(third_party_license_files)
    list(POP_FRONT third_party_license_files source_file destination_name)
    install(
        FILES ${source_file}
        DESTINATION third-party-licenses
        COMPONENT llvm-toolchain
        RENAME ${destination_name}
    )
endwhile()

# Install samples
if(WIN32 OR LLVM_TOOLCHAIN_CROSS_BUILD_MINGW)
    set(sample_files_regex "Makefile|.*\\.(c|conf|cpp|ld|md|bat)")
else()
    set(sample_files_regex "Makefile|.*\\.(c|conf|cpp|ld|md)")
endif()
install(
    DIRECTORY samples
    DESTINATION .
    COMPONENT llvm-toolchain
    FILES_MATCHING REGEX "${sample_files_regex}"
)


# LLVM-style install
# To use it:
#   ninja install-llvm-toolchain
add_custom_target(
    install-llvm-toolchain
    COMMAND
        "${CMAKE_COMMAND}"
        --install ${CMAKE_BINARY_DIR}
        --strip
        --component llvm-toolchain
    USES_TERMINAL
)
if(LLVM_TOOLCHAIN_CROSS_BUILD_MINGW)
    # No further action needed to install because the MinGW binaries
    # are declared to be part of the llvm-toolchain
    # install component.
else()
    # Also run install-distribution-stripped to install the LLVM
    # binaries.
    add_dependencies(
        install-llvm-toolchain
        install-distribution-stripped
    )
endif()
add_dependencies(
    install-llvm-toolchain
    llvm-toolchain
)


# package-llvm-toolchain - target to create package
if(LLVM_TOOLCHAIN_CROSS_BUILD_MINGW OR WIN32)
    set(cpack_generator ZIP)
    set(package_filename_extension ".zip")
else()
    set(cpack_generator TGZ)
    set(package_filename_extension ".tar.gz")
endif()
set(package_filepath ${CMAKE_BINARY_DIR}/${CPACK_PACKAGE_NAME}-${CPACK_PACKAGE_VERSION}-${CPACK_SYSTEM_NAME}${package_filename_extension})
add_custom_command(
    OUTPUT ${package_filepath}
    COMMAND cpack -G ${cpack_generator}
    DEPENDS llvm-toolchain
    USES_TERMINAL
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
)
add_custom_target(
    package-llvm-toolchain
    DEPENDS ${package_filepath}
)
add_custom_target(
    clear-unpack-directory
    COMMAND "${CMAKE_COMMAND}" -E rm -rf unpack
    COMMAND "${CMAKE_COMMAND}" -E make_directory unpack
)
add_custom_target(
    unpack-llvm-toolchain
    COMMAND "${CMAKE_COMMAND}" -E tar x ${package_filepath}
    DEPENDS ${package_filepath}
    USES_TERMINAL
    WORKING_DIRECTORY unpack
)
add_dependencies(
    unpack-llvm-toolchain
    clear-unpack-directory
)



# Smoke tests

# Run tests on the built toolchain.
add_custom_target(check-llvm-toolchain)

# Run tests on the packaged and unpacked toolchain.
add_custom_target(check-package-llvm-toolchain)

# Smoke tests
foreach(test
    basic-semihosting
    cpp-basic-semihosting
)
    add_custom_target(
        check-llvm-toolchain-smoketests-${test}
        COMMAND make clean
        COMMAND make run BIN_PATH=${llvm_bin}
        COMMAND make clean
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/tests/smoketests/${test}
    )
    add_dependencies(check-llvm-toolchain-smoketests-${test} llvm-toolchain)
    add_dependencies(check-llvm-toolchain check-llvm-toolchain-smoketests-${test})

    # Post-package tests
    add_custom_target(
        check-package-llvm-toolchain-smoketests-${test}
        COMMAND make clean
        COMMAND make run BIN_PATH=${CMAKE_CURRENT_BINARY_DIR}/unpack/bin
        COMMAND make clean
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/tests/smoketests/${test}
    )
    add_dependencies(check-package-llvm-toolchain-smoketests-${test} unpack-llvm-toolchain)
    add_dependencies(check-package-llvm-toolchain check-package-llvm-toolchain-smoketests-${test})
endforeach()

# Samples
# Don't run the baremetal-uart sample because it never terminates.
foreach(test
    baremetal-semihosting
    cpp-baremetal-semihosting
)
    add_custom_target(
        check-llvm-toolchain-samples-${test}
        COMMAND make clean
        COMMAND make run BIN_PATH=${llvm_bin}
        COMMAND make clean
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/samples/src/${test}
    )
    add_dependencies(check-llvm-toolchain-samples-${test} llvm-toolchain)
    add_dependencies(check-llvm-toolchain check-llvm-toolchain-samples-${test})

    # Post-package tests
    add_custom_target(
        check-package-llvm-toolchain-samples-${test}
        COMMAND make clean
        COMMAND make run BIN_PATH=${CMAKE_CURRENT_BINARY_DIR}/unpack/bin
        COMMAND make clean
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/unpack/samples/src/${test}
    )
    add_dependencies(check-package-llvm-toolchain-samples-${test} unpack-llvm-toolchain)
    add_dependencies(check-package-llvm-toolchain check-package-llvm-toolchain-samples-${test})
endforeach()

if(LLVM_TOOLCHAIN_CROSS_BUILD_MINGW)
    find_program(MINGW_C_EXECUTABLE x86_64-w64-mingw32-gcc-posix REQUIRED)
    find_program(MINGW_CXX_EXECUTABLE x86_64-w64-mingw32-g++-posix REQUIRED)
    cmake_path(SET MINGW_SYSROOT NORMALIZE "${MINGW_C_EXECUTABLE}/../../x86_64-w64-mingw32")

    string(REPLACE ";" "," LLVM_ENABLE_PROJECTS_comma "${LLVM_ENABLE_PROJECTS}")
    string(REPLACE ";" "," LLVM_DISTRIBUTION_COMPONENTS_comma "${LLVM_DISTRIBUTION_COMPONENTS}")
    string(REPLACE ";" "," LLVM_TARGETS_TO_BUILD_comma "${LLVM_TARGETS_TO_BUILD}")
    ExternalProject_Add(
        mingw-llvm
        SOURCE_DIR ${llvmproject_SOURCE_DIR}/llvm
        PREFIX mingw-llvm
        INSTALL_DIR mingw-llvm/install
        DEPENDS clang-tblgen llvm-config llvm-tblgen
        CMAKE_ARGS
        -DBUG_REPORT_URL=${BUG_REPORT_URL}
        -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}
        -DCMAKE_CROSSCOMPILING=ON
        -DCMAKE_C_COMPILER=${MINGW_C_EXECUTABLE}
        -DCMAKE_CXX_COMPILER=${MINGW_CXX_EXECUTABLE}
        -DCMAKE_FIND_ROOT_PATH=${MINGW_SYSROOT}
        -DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=NEVER
        -DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=ONLY
        -DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=ONLY
        -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
        -DCMAKE_SYSTEM_NAME=Windows
        -DCLANG_TABLEGEN=${llvm_bin}/clang-tblgen
        -DLLVM_CCACHE_BUILD=${LLVM_CCACHE_BUILD}
        -DLLVM_CONFIG_PATH=${llvm_bin}/llvm-config
        -DLLVM_DISTRIBUTION_COMPONENTS=${LLVM_DISTRIBUTION_COMPONENTS_comma}
        -DLLVM_ENABLE_PROJECTS=${LLVM_ENABLE_PROJECTS_comma}
        -DLLVM_TABLEGEN=${llvm_bin}/llvm-tblgen
        -DLLVM_TARGETS_TO_BUILD=${LLVM_TARGETS_TO_BUILD_comma}
        BUILD_COMMAND "" # Let the install command build whatever it needs
        INSTALL_COMMAND "${CMAKE_COMMAND}" --build <BINARY_DIR> --target install-distribution-stripped
        USES_TERMINAL_CONFIGURE TRUE
        USES_TERMINAL_BUILD TRUE
        USES_TERMINAL_INSTALL TRUE
        LIST_SEPARATOR ,
        # Always run the build command so that incremental builds are correct.
        BUILD_ALWAYS TRUE
        CONFIGURE_HANDLED_BY_BUILD TRUE
    )
    ExternalProject_Get_Property(mingw-llvm INSTALL_DIR)
    # Handle symlinks such as clang++.
    # CPack supports putting symlinks in zip files but to Windows they
    # just look like a file containing text like "clang".
    # Convert the required symlinks to regular files and remove the
    # remaining ones.
    add_custom_command(
        TARGET mingw-llvm
        POST_BUILD
        COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/cmake/handle-windows-symlinks.sh
        WORKING_DIRECTORY ${INSTALL_DIR}
    )

    install(
        DIRECTORY ${INSTALL_DIR}/
        DESTINATION .
        COMPONENT llvm-toolchain
    )

    # Copy MinGW licenses
    install(
        DIRECTORY mingw-licenses/
        DESTINATION third-party-licenses
        COMPONENT llvm-toolchain
    )

    # Copy MinGW runtime DLLs
    foreach(mingw_runtime_dll
        libwinpthread-1.dll # POSIX thread API implementation
        libgcc_s_seh-1.dll  # GCC runtime
        libstdc++-6.dll     # C++ Standard Library
    )
        execute_process(
            COMMAND ${MINGW_C_EXECUTABLE} -print-file-name=${mingw_runtime_dll}
            OUTPUT_VARIABLE mingw_runtime_dll
            OUTPUT_STRIP_TRAILING_WHITESPACE
            COMMAND_ERROR_IS_FATAL ANY
        )
        install(
            FILES ${mingw_runtime_dll}
            TYPE BIN
            COMPONENT llvm-toolchain
        )
    endforeach()

    add_dependencies(
        llvm-toolchain
        mingw-llvm
    )
endif()
