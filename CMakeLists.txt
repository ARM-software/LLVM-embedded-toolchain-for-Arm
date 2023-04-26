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
#   git -C repos/llvm-project apply ../../patches/llvm-project.patch
#   git -C repos clone https://github.com/picolibc/picolibc.git
#   git -C repos/picolibc apply ../../patches/picolibc.patch
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
option(
    PREBUILT_TARGET_LIBRARIES
    "Target libraries are prebuilt so no need to build them"
)
set(TARGET_LIBRARIES_DIR
    "lib/clang-runtimes" CACHE STRING
    "Directory containing the target libraries."
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
set(LLVM_TOOLCHAIN_DISTRIBUTION_COMPONENTS
    llvm-toolchain-config-files
    llvm-toolchain-docs
    llvm-toolchain-libs
    llvm-toolchain-samples
    llvm-toolchain-third-party-licenses
    CACHE STRING "Components defined by this CMakeLists that should be
installed by the install-llvm-toolchain target"
)
set(LLVM_ENABLE_PROJECTS clang;lld CACHE STRING "")
set(LLVM_TARGETS_TO_BUILD AArch64;ARM CACHE STRING "")
set(LLVM_DEFAULT_TARGET_TRIPLE aarch64-linux-gnu CACHE STRING "")
set(LLVM_APPEND_VC_REV OFF CACHE BOOL "")
set(LLVM_ENABLE_TERMINFO OFF CACHE BOOL "")
set(CLANG_DEFAULT_LINKER lld CACHE STRING "")

# Default to a release build
# (CMAKE_BUILD_TYPE is a special CMake variable so if you want to set
# it then you have to FORCE it).
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE BOOL "" FORCE)
endif()

if(NOT CMAKE_C_COMPILER_LAUNCHER AND NOT CMAKE_CXX_COMPILER_LAUNCHER)
    # If ccache is available then use it by default.
    find_program(CCACHE_EXECUTABLE ccache)
    if(CCACHE_EXECUTABLE)
        set(CMAKE_C_COMPILER_LAUNCHER "${CCACHE_EXECUTABLE}" CACHE FILEPATH "" FORCE)
        set(CMAKE_CXX_COMPILER_LAUNCHER "${CCACHE_EXECUTABLE}" CACHE FILEPATH "" FORCE)
    endif()
endif()

# If lld is available then use it by default.
find_program(LLD_EXECUTABLE lld)
if(LLD_EXECUTABLE)
    set(LLVM_ENABLE_LLD ON CACHE BOOL "")
endif()

# A lot of files get installed which makes the install messages too
# noisy to be useful so default to disabling them.
set(CMAKE_INSTALL_MESSAGE NEVER CACHE STRING "")

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

# Read which revisions of the repos to use.
file(READ versions.json VERSIONS_JSON)
function(read_repo_version output_variable_prefix repo)
    string(JSON tag GET ${VERSIONS_JSON} "repos" "${repo}" "tag")
    string(JSON tagType GET ${VERSIONS_JSON} "repos" "${repo}" "tagType")
    if(tagType STREQUAL "commithash")
        # GIT_SHALLOW doesn't work with commit hashes.
        set(shallow OFF)
    elseif(tagType STREQUAL "branch")
        set(shallow ON)
        # CMake docs recommend that "branch names and tags should
        # generally be specified as remote names"
        set(tag "origin/${tag}")
    elseif(tagType STREQUAL "tag")
        set(shallow ON)
    else()
        message(FATAL_ERROR "Unrecognised tagType ${tagType}")
    endif()

    set(${output_variable_prefix}_TAG "${tag}" PARENT_SCOPE)
    set(${output_variable_prefix}_SHALLOW "${shallow}" PARENT_SCOPE)
endfunction()
read_repo_version(llvmproject llvm-project)
read_repo_version(picolibc picolibc)

FetchContent_Declare(llvmproject
    GIT_REPOSITORY https://github.com/llvm/llvm-project.git
    GIT_TAG "${llvmproject_TAG}"
    GIT_SHALLOW "${llvmproject_SHALLOW}"
    GIT_PROGRESS TRUE
    PATCH_COMMAND git reset --quiet --hard && git clean --quiet --force -dx && git apply ${CMAKE_CURRENT_SOURCE_DIR}/patches/llvm-project.patch
    # Add the llvm subdirectory later to ensure that
    # LLVMEmbeddedToolchainForArm is the first project declared.
    # Otherwise CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT
    # can't be used.
    SOURCE_SUBDIR do_not_add_llvm_subdir_yet
)

FetchContent_Declare(picolibc
    GIT_REPOSITORY https://github.com/picolibc/picolibc.git
    GIT_TAG "${picolibc_TAG}"
    GIT_SHALLOW "${picolibc_SHALLOW}"
    GIT_PROGRESS TRUE
    PATCH_COMMAND git reset --quiet --hard && git clean --quiet --force -dx && git apply ${CMAKE_CURRENT_SOURCE_DIR}/patches/picolibc.patch
    # We only want to download the content, not configure it at this
    # stage. picolibc will be built in many configurations using
    # ExternalProject_Add using the sources that are checked out here.
    SOURCE_SUBDIR do_not_add_picolibc_subdir
)

FetchContent_MakeAvailable(llvmproject)
FetchContent_MakeAvailable(picolibc)

function(get_llvm_version_numbers llvmproject_SOURCE_DIR)
    # Grab the version out of LLVM sources
    file(
        STRINGS ${llvmproject_SOURCE_DIR}/llvm/CMakeLists.txt version_strings
        REGEX [[set\(LLVM_VERSION_[A-Z]+ [0-9]+\)]]
    )
    string(REGEX MATCH [[MAJOR ([0-9]+)]] unused "${version_strings}")
    set(LLVM_VERSION_MAJOR ${CMAKE_MATCH_1} PARENT_SCOPE)
    string(REGEX MATCH [[MINOR ([0-9]+)]] unused "${version_strings}")
    set(LLVM_VERSION_MINOR ${CMAKE_MATCH_1} PARENT_SCOPE)
    string(REGEX MATCH [[PATCH ([0-9]+)]] unused "${version_strings}")
    set(LLVM_VERSION_PATCH ${CMAKE_MATCH_1} PARENT_SCOPE)
endfunction()
get_llvm_version_numbers(${llvmproject_SOURCE_DIR})

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
    set(CPACK_COMPONENTS_ALL ${LLVM_TOOLCHAIN_DISTRIBUTION_COMPONENTS} llvm-toolchain-mingw)
else()
    set(CPACK_COMPONENTS_ALL ${LLVM_TOOLCHAIN_DISTRIBUTION_COMPONENTS} ${LLVM_DISTRIBUTION_COMPONENTS})
endif()
# Enable limiting the installed components in TGZ and ZIP packages.
set(CPACK_ARCHIVE_COMPONENT_INSTALL TRUE)
# Don't create a separate archive for each component.
set(CPACK_COMPONENTS_GROUPING ALL_COMPONENTS_IN_ONE)
# When extracting the files put them in an ArmCompiler-.../ directory.
set(CPACK_COMPONENT_INCLUDE_TOPLEVEL_DIRECTORY TRUE)

if(CMAKE_OSX_ARCHITECTURES)
    # For universal binaries don't include architecture in the package name.
    set(CPACK_SYSTEM_NAME "${CMAKE_SYSTEM_NAME}")
else()
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
endif()

add_subdirectory(
    ${llvmproject_SOURCE_DIR}/llvm llvm
)

# Including CPack again after llvm CMakeLists.txt included it
# resets CPACK_PACKAGE_VERSION to the default MAJOR.MINOR.PATCH format.
include(CPack)

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
    -DLLVMEmbeddedToolchainForArm_SOURCE_DIR=${CMAKE_CURRENT_SOURCE_DIR}
    -Dllvmproject_SOURCE_DIR=${llvmproject_SOURCE_DIR}
    -Dpicolibc_SOURCE_DIR=${picolibc_SOURCE_DIR}
    -P ${CMAKE_CURRENT_SOURCE_DIR}/cmake/generate_version_txt.cmake
    BYPRODUCTS ${CMAKE_CURRENT_BINARY_DIR}/VERSION.txt
)
install(
    FILES
    ${CMAKE_CURRENT_BINARY_DIR}/VERSION.txt
    DESTINATION .
    COMPONENT llvm-toolchain-docs
)


# Groups all the targets that comprise the toolchain.
add_custom_target(llvm-toolchain ALL)

# Groups all the runtime targets
add_custom_target(llvm-toolchain-runtimes)

# Groups all C++ runtime libraries tests
add_custom_target(check-cxxabi)
add_custom_target(check-unwind)
add_custom_target(check-cxx)

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

set(picolibc_specific_runtimes_options
    -DLIBCXXABI_ENABLE_EXCEPTIONS=OFF
    -DLIBCXXABI_ENABLE_THREADS=OFF
    -DLIBCXX_TEST_CONFIG=${CMAKE_CURRENT_SOURCE_DIR}/test-support/llvm-libc++-picolibc.cfg.in
    -DLIBCXX_ENABLE_EXCEPTIONS=OFF
    -DLIBCXXABI_TEST_CONFIG=${CMAKE_CURRENT_SOURCE_DIR}/test-support/llvm-libc++abi-picolibc.cfg.in
    -DLIBCXX_ENABLE_MONOTONIC_CLOCK=OFF
    -DLIBCXX_ENABLE_RANDOM_DEVICE=OFF
    -DLIBCXX_ENABLE_RTTI=OFF
    -DLIBCXX_ENABLE_THREADS=OFF
    -DLIBCXX_ENABLE_WIDE_CHARACTERS=OFF
    -DLIBUNWIND_ENABLE_THREADS=OFF
    -DLIBUNWIND_TEST_CONFIG=${CMAKE_CURRENT_SOURCE_DIR}/test-support/llvm-libunwind-picolibc.cfg.in
)

add_custom_target(check-picolibc)

function(add_picolibc directory variant target_triple flags qemu_params variant_runtime_options_var)
    if(CMAKE_INSTALL_MESSAGE STREQUAL NEVER)
        set(MESON_INSTALL_QUIET "--quiet")
    endif()

    if(target_triple MATCHES "^aarch64")
        set(cpu_family aarch64)
    else()
        set(cpu_family arm)
    endif()

    ExternalProject_Add(
        picolibc_${variant}
        SOURCE_DIR ${picolibc_SOURCE_DIR}
        INSTALL_DIR "${LLVM_BINARY_DIR}/${directory}"
        PREFIX picolibc/${variant}
        DEPENDS clang lld llvm-ar llvm-config llvm-nm llvm-ranlib llvm-strip
        CONFIGURE_COMMAND ${MESON_EXECUTABLE} -Dincludedir=include -Dlibdir=lib -Dspecsdir=none --prefix <INSTALL_DIR> --cross-file <BINARY_DIR>/meson-cross-build.txt ${picolibc_SOURCE_DIR}
        BUILD_COMMAND ninja
        INSTALL_COMMAND ${MESON_EXECUTABLE} install ${MESON_INSTALL_QUIET}
        USES_TERMINAL_CONFIGURE TRUE
        USES_TERMINAL_BUILD TRUE
        USES_TERMINAL_TEST TRUE
        LIST_SEPARATOR ,
        # Always run the build command so that incremental builds are correct.
        BUILD_ALWAYS TRUE
        CONFIGURE_HANDLED_BY_BUILD TRUE
    )
    # Set meson_c_args to a comma-separated list of the clang path
    # and flags e.g. 'path/to/clang', '--target=armv6m-none-eabi',
    # '-march=armv6m'
    set(meson_c_args "${flags}")
    string(REPLACE " " "', '" meson_c_args "${meson_c_args}")
    set(meson_c_args "'${LLVM_BINARY_DIR}/bin/clang${CMAKE_EXECUTABLE_SUFFIX}', '${meson_c_args}'")
    ExternalProject_Get_Property(picolibc_${variant} BINARY_DIR)
    configure_file(${CMAKE_CURRENT_FUNCTION_LIST_DIR}/cmake/meson-cross-build.txt.in ${BINARY_DIR}/meson-cross-build.txt @ONLY)

    # picolibc tests
    string(REPLACE " " ";" qemu_params_list "${qemu_params}")
    add_custom_target(check-picolibc_${variant})
    set(qemu_command "qemu-system-${cpu_family}")
    # Full list of picolibc tests
    set(picolibc_tests
        abort
        atexit
        complex-funcs
        constructor
        constructor-skip
        fenv
        ffs
        hosted-exit
        long_double
        malloc
        malloc_stress
        math_errhandling
        math-funcs
        on_exit
        posix-io
        printf_scanf
        printf-tests
        rand
        regex
        setjmp
        stack-smash
        test-efcvt
        test-except
        test-fopen
        test-memset
        test-mktemp
        test-put
        test-strchr
        test-strtod
        timegm
        time-sprintf
        time-tests
        tls
        ungetc
    )
    # remove tests failing on a given platform
    if(variant STREQUAL "armv4t")
        list(REMOVE_ITEM picolibc_tests abort constructor-skip)
    endif()
    if(variant STREQUAL "armv5te")
        list(REMOVE_ITEM picolibc_tests abort constructor-skip test-except)
    endif()
    if(variant STREQUAL "armv6m_soft_nofp")
        list(REMOVE_ITEM picolibc_tests abort constructor-skip test-except)
    endif()
    if(variant STREQUAL "armv7m_soft_nofp")
        list(REMOVE_ITEM picolibc_tests abort constructor-skip test-except)
    endif()
    if(variant STREQUAL "armv7em_soft_nofp")
        list(REMOVE_ITEM picolibc_tests abort constructor-skip test-except)
    endif()
    if(variant STREQUAL "armv7em_hard_fpv4_sp_d16")
        list(REMOVE_ITEM picolibc_tests abort constructor-skip math_errhandling test-except)
    endif()
    if(variant STREQUAL "armv7em_hard_fpv5_d16")
        list(REMOVE_ITEM picolibc_tests abort constructor-skip math_errhandling test-except)
    endif()
    if(variant STREQUAL "armv8m.main_soft_nofp")
        list(REMOVE_ITEM picolibc_tests abort constructor-skip long_double math_errhandling malloc_stress test-except timegm)
    endif()
    if(variant STREQUAL "armv8m.main_hard_fp")
        list(REMOVE_ITEM picolibc_tests abort constructor-skip complex-funcs fenv long_double math_errhandling math-funcs malloc_stress printf_scanf rand test-efcvt test-except test-strtod timegm)
    endif()
    if(variant STREQUAL "armv8.1m.main_soft_nofp_nomve")
        list(REMOVE_ITEM picolibc_tests abort constructor-skip long_double math_errhandling malloc_stress test-except timegm)
    endif()
    if(variant STREQUAL "armv8.1m.main_hard_fp")
        list(REMOVE_ITEM picolibc_tests abort constructor-skip long_double math_errhandling malloc_stress test-except timegm)
    endif()
    if(variant STREQUAL "armv8.1m.main_hard_nofp_mve")
        list(REMOVE_ITEM picolibc_tests abort constructor-skip complex-funcs fenv ffs long_double math_errhandling math-funcs malloc_stress printf_scanf printf-tests rand regex test-efcvt test-except test-strtod timegm time-tests)
    endif()

    function(picolibc_test test)
        # -Oz parameter is added just like picolibc is doing, otherwise there is a build issue
        # ld.lld: error: undefined symbol: __issignalingl  while building math_errhandling test.
        add_custom_command(
                OUTPUT picolibc_tests_${variant}/check-picolibc_${variant}_build_${test}.out
                COMMAND ${LLVM_BINARY_DIR}/bin/clang${CMAKE_EXECUTABLE_SUFFIX} --config ${LLVM_BINARY_DIR}/bin/${variant}_semihost.cfg
                -T ${CMAKE_CURRENT_FUNCTION_LIST_DIR}/tests/ldscripts/picolibc_${variant}.ld
                -nostdlib -lc -lg -lm -lclang_rt.builtins -lsemihost -Oz
                ${picolibc_SOURCE_DIR}/test/${test}.c ${ARGN} -o picolibc_tests_${variant}/check-picolibc_${variant}_build_${test}.out
                COMMENT "Building: ${test} for ${variant}"
                DEPENDS ${picolibc_SOURCE_DIR}/test/${test}.c picolibc_${variant} compiler_rt_${variant}
        )
        add_custom_target(
                check-picolibc_${variant}-${test}
                ${qemu_command} ${qemu_params_list} -semihosting -nographic -kernel check-picolibc_${variant}_build_${test}.out
                DEPENDS picolibc_tests_${variant}/check-picolibc_${variant}_build_${test}.out
                WORKING_DIRECTORY picolibc_tests_${variant}
                COMMENT "TEST: ${variant} ${test}"
        )
        add_dependencies(check-picolibc_${variant} check-picolibc_${variant}-${test})
    endfunction()
    if(flags MATCHES "-march=armv8-a")
        message("Picolibc tests disabled for ${variant}")
    else()
        execute_process(COMMAND ${CMAKE_COMMAND} -E make_directory picolibc_tests_${variant})
        foreach(test IN LISTS picolibc_tests)
            picolibc_test(${test})
        endforeach()
        # Test disabled due to duplicated symbol name div in test file and in picolibc
        # picolibc_test(rounding-mode)
        # Test disabled due to fail on armv8.1m.main_hard_nofp_mve
        # picolibc_test(try-ilp32)
        add_dependencies(check-picolibc check-picolibc_${variant})

        # Use colon as a separator because comma and semicolon are used for
        # other purposes in CMake.
        string(REPLACE " " ":" qemu_params_colon "${qemu_params}")
        set(test_executor
            "${CMAKE_CURRENT_SOURCE_DIR}/test-support/lit-exec-qemu.py --qemu-command ${qemu_command} --qemu-params=${qemu_params_colon}")
        set(${variant_runtime_options_var}
            -DLIBC_LINKER_SCRIPT=${CMAKE_CURRENT_FUNCTION_LIST_DIR}/tests/ldscripts/picolibc_${variant}.ld
            -DLIBCXX_EXECUTOR=${test_executor}
            -DLIBCXXABI_EXECUTOR=${test_executor}
            -DLIBUNWIND_EXECUTOR=${test_executor}
            PARENT_SCOPE)
    endif()

    add_dependencies(
        llvm-toolchain-runtimes
        picolibc_${variant}
    )
endfunction()

function(get_runtimes_flags directory flags)
    set(runtimes_flags "${flags} -ffunction-sections -fdata-sections -fno-ident --sysroot ${LLVM_BINARY_DIR}/${directory}" PARENT_SCOPE)
endfunction()

function(add_compiler_rt directory variant target_triple flags libc_target)
    # We can't always put the exact target
    # architecture in the triple, because compiler-rt's cmake
    # system doesn't recognize every possible Arm architecture
    # version. So mostly we just say 'arm' and control the arch
    # version via -march=armv7m (or whatever).
    # Exceptions are architectures pre-armv7, which compiler-rt expects to
    # see in the triple because that's where it looks to decide whether to
    # use specific assembly sources.
    if(NOT target_triple MATCHES "^(aarch64-none-elf|arm-none-eabi|armv[4-6])")
        message(FATAL_ERROR "\
Target triple name \"${target_triple}\" not compatible with compiler-rt.
Use -march to specify the architecture.")
    endif()
    # Also, compiler-rt looks in the ABI component of the
    # triple to decide whether to use the hard float ABI.
    if(flags MATCHES "-mfloat-abi=hard" AND NOT target_triple MATCHES "-eabihf$")
        message(FATAL_ERROR "\
Hard-float library with target triple \"${target_triple}\" must end \"-eabihf\"")
    endif()

    get_runtimes_flags("${directory}" "${flags}")

    ExternalProject_Add(
        compiler_rt_${variant}
        SOURCE_DIR ${llvmproject_SOURCE_DIR}/compiler-rt
        PREFIX compiler-rt/${variant}
        INSTALL_DIR compiler-rt/${variant}/install
        DEPENDS clang lld llvm-ar llvm-config llvm-nm llvm-ranlib ${libc_target}
        CMAKE_ARGS
        -DCMAKE_AR=${LLVM_BINARY_DIR}/bin/llvm-ar${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_ASM_COMPILER_TARGET=${target_triple}
        -DCMAKE_ASM_FLAGS=${runtimes_flags}
        -DCMAKE_BUILD_TYPE=Release
        -DCMAKE_CXX_COMPILER=${LLVM_BINARY_DIR}/bin/clang++${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_CXX_COMPILER_TARGET=${target_triple}
        -DCMAKE_CXX_FLAGS=${runtimes_flags}
        -DCMAKE_C_COMPILER=${LLVM_BINARY_DIR}/bin/clang${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_C_COMPILER_TARGET=${target_triple}
        -DCMAKE_C_FLAGS=${runtimes_flags}
        -DCMAKE_INSTALL_MESSAGE=${CMAKE_INSTALL_MESSAGE}
        -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
        -DCMAKE_NM=${LLVM_BINARY_DIR}/bin/llvm-nm${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_RANLIB=${LLVM_BINARY_DIR}/bin/llvm-ranlib${CMAKE_EXECUTABLE_SUFFIX}
        # Let CMake know we're cross-compiling
        -DCMAKE_SYSTEM_NAME=Generic
        -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY
        -DCOMPILER_RT_BAREMETAL_BUILD=ON
        -DCOMPILER_RT_BUILD_LIBFUZZER=OFF
        -DCOMPILER_RT_BUILD_PROFILE=OFF
        -DCOMPILER_RT_BUILD_SANITIZERS=OFF
        -DCOMPILER_RT_BUILD_XRAY=OFF
        -DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON
        -DLLVM_LIT_ARGS=${LLVM_LIT_ARGS}
        -DLLVM_CCACHE_BUILD=${LLVM_CCACHE_BUILD}
        -DLLVM_CONFIG_PATH=${LLVM_BINARY_DIR}/bin/llvm-config${CMAKE_EXECUTABLE_SUFFIX}
        -DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=ON
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
    # Copy compiler-rt lib directory, moving libraries out of their
    # target-specific subdirectory.
    add_custom_command(
        TARGET compiler_rt_${variant}
        POST_BUILD
        COMMAND "${CMAKE_COMMAND}" -E copy_directory
            ${INSTALL_DIR}/lib/${target_triple} "${LLVM_BINARY_DIR}/${directory}/lib"
    )

    add_dependencies(
        llvm-toolchain-runtimes
        compiler_rt_${variant}
    )
endfunction()

function(add_libcxx_libcxxabi_libunwind directory variant target_triple flags libc_target extra_cmake_options)
    get_runtimes_flags("${directory}" "${flags}")

    ExternalProject_Add(
        libcxx_libcxxabi_libunwind_${variant}
        SOURCE_DIR ${llvmproject_SOURCE_DIR}/runtimes
        INSTALL_DIR "${LLVM_BINARY_DIR}/${directory}"
        PREFIX libcxx_libcxxabi_libunwind/${variant}
        DEPENDS clang compiler_rt_${variant} lld llvm-ar llvm-config llvm-nm llvm-ranlib ${libc_target}
        CMAKE_ARGS
        -DCMAKE_AR=${LLVM_BINARY_DIR}/bin/llvm-ar${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_ASM_FLAGS=${runtimes_flags}
        -DCMAKE_BUILD_TYPE=MinSizeRel
        -DCMAKE_CXX_COMPILER=${LLVM_BINARY_DIR}/bin/clang++${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_CXX_COMPILER_TARGET=${target_triple}
        -DCMAKE_CXX_FLAGS=${runtimes_flags}
        -DCMAKE_C_COMPILER=${LLVM_BINARY_DIR}/bin/clang${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_C_COMPILER_TARGET=${target_triple}
        -DCMAKE_C_FLAGS=${runtimes_flags}
        -DCMAKE_INSTALL_MESSAGE=${CMAKE_INSTALL_MESSAGE}
        -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
        -DCMAKE_NM=${LLVM_BINARY_DIR}/bin/llvm-nm${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_RANLIB=${LLVM_BINARY_DIR}/bin/llvm-ranlib${CMAKE_EXECUTABLE_SUFFIX}
        # Let CMake know we're cross-compiling
        -DCMAKE_SYSTEM_NAME=Generic
        -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY
        -DLIBCXXABI_BAREMETAL=ON
        -DLIBCXXABI_ENABLE_ASSERTIONS=OFF
        -DLIBCXXABI_ENABLE_SHARED=OFF
        -DLIBCXXABI_ENABLE_STATIC=ON
        -DLIBCXXABI_LIBCXX_INCLUDES="${LLVM_BINARY_DIR}/${directory}/include/c++/v1"
        -DLIBCXXABI_USE_COMPILER_RT=ON
        -DLIBCXXABI_USE_LLVM_UNWINDER=ON
        -DLIBCXX_CXX_ABI=libcxxabi
        -DLIBCXX_ENABLE_FILESYSTEM=OFF
        -DLIBCXX_ENABLE_SHARED=OFF
        -DLIBCXX_ENABLE_STATIC=ON
        -DLIBCXX_INCLUDE_BENCHMARKS=OFF
        -DLIBUNWIND_ENABLE_SHARED=OFF
        -DLIBUNWIND_ENABLE_STATIC=ON
        -DLIBUNWIND_IS_BAREMETAL=ON
        -DLIBUNWIND_REMEMBER_HEAP_ALLOC=ON
        -DLIBUNWIND_USE_COMPILER_RT=ON
        -DLLVM_LIT_ARGS=${LLVM_LIT_ARGS}
        -DLLVM_CCACHE_BUILD=${LLVM_CCACHE_BUILD}
        -DLLVM_ENABLE_RUNTIMES=libcxxabi,libcxx,libunwind
        -DRUNTIME_TEST_ARCH_FLAGS=${flags}
        ${extra_cmake_options}
        STEP_TARGETS build
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
        libcxx_libcxxabi_libunwind_${variant}
    )
endfunction()

function(add_libcxx_libcxxabi_libunwind_tests variant)
    foreach(check_target check-cxxabi check-unwind check-cxx)
        ExternalProject_Add_Step(
            libcxx_libcxxabi_libunwind_${variant}
            ${check_target}
            COMMAND "${CMAKE_COMMAND}" --build <BINARY_DIR> --target ${check_target}
            USES_TERMINAL TRUE
            EXCLUDE_FROM_MAIN TRUE
            ALWAYS TRUE
        )
        ExternalProject_Add_StepTargets(libcxx_libcxxabi_libunwind_${variant} ${check_target})
        ExternalProject_Add_StepDependencies(
            libcxx_libcxxabi_libunwind_${variant}
            ${check_target}
            libcxx_libcxxabi_libunwind_${variant}-build
        )
        add_dependencies(${check_target} libcxx_libcxxabi_libunwind_${variant}-${check_target})
    endforeach()
endfunction()

function(make_config_cfg directory variant flags)
    # Create clang configuration files
    # https://clang.llvm.org/docs/UsersManual.html#configuration-files
    set(crt0 "-lcrt0")
    set(extra_args "")
    configure_file(${CMAKE_CURRENT_FUNCTION_LIST_DIR}/cmake/config.cfg.in ${LLVM_BINARY_DIR}/bin/${variant}.cfg)
    set(crt0 "-lcrt0-semihost")
    set(extra_args "\n-lsemihost")
    configure_file(${CMAKE_CURRENT_FUNCTION_LIST_DIR}/cmake/config.cfg.in ${LLVM_BINARY_DIR}/bin/${variant}_semihost.cfg)
    install(FILES
        ${LLVM_BINARY_DIR}/bin/${variant}.cfg
        ${LLVM_BINARY_DIR}/bin/${variant}_semihost.cfg
        DESTINATION bin
        COMPONENT llvm-toolchain-config-files
    )
endfunction()

function(get_compiler_rt_target_triple target_arch)
    if(target_arch STREQUAL "aarch64")
        set(target_triple "aarch64-none-elf")
    else()
        # Choose the target triple so that compiler-rt will do the
        # right thing. We can't always put the exact target
        # architecture in the triple, because compiler-rt's cmake
        # system doesn't recognize every possible Arm architecture
        # version. So mostly we just say 'arm' and control the arch
        # version via -march=armv7m (or whatever).
        # Exceptions are architectures pre-armv7, which compiler-rt expects to
        # see in the triple because that's where it looks to decide whether to
        # use specific assembly sources.
        if(target_arch MATCHES "^armv[4-6]")
            set(target_triple "${target_arch}-none-eabi")
        else()
            set(target_triple "arm-none-eabi")
        endif()
        if(flags MATCHES "-mfloat-abi=hard")
            # Also, compiler-rt looks in the ABI component of the
            # triple to decide whether to use the hard float ABI.
            set(target_triple "${target_triple}hf")
        endif()
    endif()
    set(target_triple "${target_triple}" PARENT_SCOPE)
endfunction()

function(add_library_variants)
    set(variant_args "${ARGN}")
    while(variant_args)
        list(POP_FRONT variant_args target_arch variant_suffix flags qemu_params)

        if(variant_suffix)
            set(variant "${target_arch}_${variant_suffix}")
        else()
            set(variant "${target_arch}")
        endif()

        if(LLVM_TOOLCHAIN_LIBRARY_VARIANTS)
            if(NOT enable_${variant})
                message("Disabling library variant ${variant}")
                continue()
            else()
                message("Enabling library variant ${variant}")
            endif()
        endif()

        if(target_arch STREQUAL "aarch64")
            set(parent_dir_name aarch64-none-elf)
        else()
            set(parent_dir_name arm-none-eabi)
        endif()

        get_compiler_rt_target_triple(${target_arch})

        set(directory "${TARGET_LIBRARIES_DIR}/${parent_dir_name}/${variant}")
        set(flags "--target=${target_triple} ${flags}")
        make_config_cfg("${directory}" "${variant}" "${flags}")
        set(variant_options)
        if(NOT PREBUILT_TARGET_LIBRARIES)
            add_picolibc("${directory}" "${variant}" "${target_triple}" "${flags}" "${qemu_params}" variant_options)
            add_compiler_rt("${directory}" "${variant}" "${target_triple}" "${flags}" "picolibc_${variant}")
            list(APPEND variant_options ${picolibc_specific_runtimes_options})
            add_libcxx_libcxxabi_libunwind("${directory}" "${variant}" "${target_triple}" "${flags}" "picolibc_${variant}" "${variant_options}")
            if(flags MATCHES "-march=armv8")
                message("C++ runtime libraries tests disabled for ${variant}")
            else()
                add_libcxx_libcxxabi_libunwind_tests("${variant}")
            endif()
        endif()

        install(
            DIRECTORY "${LLVM_BINARY_DIR}/${directory}/"
            DESTINATION "${directory}"
            COMPONENT llvm-toolchain-libs
        )
    endwhile()
endfunction()

# Define which library variants to build and which flags to use.
# The order is <parent dir> <arch> <name suffix> <flags> <qemu params>
add_library_variants(
    aarch64         ""                  "-march=armv8-a"                                        "-M raspi3b"
    armv4t          ""                  "-march=armv4t"                                         "-M musicpal -cpu arm926"
    armv5te         ""                  "-march=armv5te"                                        "-M musicpal -cpu arm926"
    armv6m          soft_nofp           "-mfloat-abi=soft -march=armv6m"                        "-M mps2-an385"
    armv7m          soft_nofp           "-mfloat-abi=soft -march=armv7m+nofp"                   "-M mps2-an385 -cpu cortex-m3"
    armv7em         soft_nofp           "-mfloat-abi=soft -march=armv7em -mfpu=none"            "-M mps2-an386 -cpu cortex-m4"
    armv7em         hard_fpv4_sp_d16    "-mfloat-abi=hard -march=armv7em -mfpu=fpv4-sp-d16"     "-M mps2-an386 -cpu cortex-m4"
    armv7em         hard_fpv5_d16       "-mfloat-abi=hard -march=armv7em -mfpu=fpv5-d16"        "-M mps2-an500 -cpu cortex-m7"
    armv8m.main     soft_nofp           "-mfloat-abi=soft -march=armv8m.main+nofp"              "-M mps2-an505 -cpu cortex-m33"
    armv8m.main     hard_fp             "-mfloat-abi=hard -march=armv8m.main+fp"                "-M mps2-an505 -cpu cortex-m33"
    armv8.1m.main   soft_nofp_nomve     "-mfloat-abi=soft -march=armv8.1m.main+nofp+nomve"      "-M mps3-an547 -cpu cortex-m55"
    armv8.1m.main   hard_fp             "-mfloat-abi=hard -march=armv8.1m.main+fp"              "-M mps3-an547 -cpu cortex-m55"
    armv8.1m.main   hard_nofp_mve       "-mfloat-abi=hard -march=armv8.1m.main+nofp+mve"        "-M mps3-an547 -cpu cortex-m55"
)

install(
    FILES CHANGELOG.md LICENSE.txt README.md
    DESTINATION .
    COMPONENT llvm-toolchain-docs
)

install(
    DIRECTORY docs
    DESTINATION .
    COMPONENT llvm-toolchain-docs
)

if(LLVM_TOOLCHAIN_CROSS_BUILD_MINGW)
    set(mingw_runtime_dlls
        "\n - MinGW runtime DLLs: third-party-licenses/COPYING.MinGW-w64-runtime.txt, third-party-licenses/COPYING3.GCC, third-party-licenses/COPYING.RUNTIME"
    )
endif()
configure_file(cmake/THIRD-PARTY-LICENSES.txt.in THIRD-PARTY-LICENSES.txt)

install(
    FILES ${CMAKE_CURRENT_BINARY_DIR}/THIRD-PARTY-LICENSES.txt
    DESTINATION .
    COMPONENT llvm-toolchain-third-party-licenses
)

set(third_party_license_files
    ${llvmproject_SOURCE_DIR}/llvm/LICENSE.TXT          LLVM-LICENSE.txt
    ${llvmproject_SOURCE_DIR}/clang/LICENSE.TXT         CLANG-LICENSE.txt
    ${llvmproject_SOURCE_DIR}/lld/LICENSE.TXT           LLD-LICENSE.txt
    ${llvmproject_SOURCE_DIR}/compiler-rt/LICENSE.TXT   COMPILER-RT-LICENSE.txt
    ${llvmproject_SOURCE_DIR}/libcxx/LICENSE.TXT        LIBCXX-LICENSE.txt
    ${llvmproject_SOURCE_DIR}/libcxxabi/LICENSE.TXT     LIBCXXABI-LICENSE.txt
    ${llvmproject_SOURCE_DIR}/libunwind/LICENSE.TXT     LIBUNWIND-LICENSE.txt
    ${picolibc_SOURCE_DIR}/COPYING.NEWLIB               COPYING.NEWLIB
    ${picolibc_SOURCE_DIR}/COPYING.picolibc             COPYING.picolibc
)
while(third_party_license_files)
    list(POP_FRONT third_party_license_files source_file destination_name)
    install(
        FILES ${source_file}
        DESTINATION third-party-licenses
        COMPONENT llvm-toolchain-third-party-licenses
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
    COMPONENT llvm-toolchain-samples
    FILES_MATCHING REGEX "${sample_files_regex}"
)


# LLVM-style install
# To use it:
#   ninja install-llvm-toolchain
add_custom_target(
    install-llvm-toolchain
)
set(LLVM_TOOLCHAIN_DISTRIBUTION_COMPONENTS_ALL ${LLVM_TOOLCHAIN_DISTRIBUTION_COMPONENTS})
if(LLVM_TOOLCHAIN_CROSS_BUILD_MINGW)
    list(APPEND LLVM_TOOLCHAIN_DISTRIBUTION_COMPONENTS_ALL llvm-toolchain-mingw)
endif()
foreach(component ${LLVM_TOOLCHAIN_DISTRIBUTION_COMPONENTS})
    add_custom_target(
        install-${component}
        COMMAND
            "${CMAKE_COMMAND}"
            --install ${CMAKE_BINARY_DIR}
            --component ${component}
        USES_TERMINAL
    )
    add_dependencies(
        install-${component}
        llvm-toolchain
    )
    add_dependencies(
        install-llvm-toolchain
        install-${component}
    )
endforeach()
if(LLVM_TOOLCHAIN_CROSS_BUILD_MINGW)
    # No further action needed to install because the LLVM distributables
    # are copied as part of the llvm-toolchain-mingw component.
else()
    # Also run install-distribution to install the LLVM
    # binaries.
    add_dependencies(
        install-llvm-toolchain
        install-distribution
    )
endif()


# package-llvm-toolchain - target to create package
if(LLVM_TOOLCHAIN_CROSS_BUILD_MINGW OR WIN32)
    set(cpack_generator ZIP)
    set(package_filename_extension ".zip")
else()
    set(cpack_generator TGZ)
    set(package_filename_extension ".tar.gz")
endif()
# CPACK_PACKAGE_FILE_NAME may refer to the source package so use this variable instead.
set(binary_package_name ${CPACK_PACKAGE_NAME}-${CPACK_PACKAGE_VERSION}-${CPACK_SYSTEM_NAME})
set(package_filepath ${CMAKE_BINARY_DIR}/${binary_package_name}${package_filename_extension})
set(unpack_directory ${CMAKE_CURRENT_BINARY_DIR}/unpack/${binary_package_name})
add_custom_command(
    OUTPUT ${package_filepath}
    COMMAND "${CMAKE_COMMAND}" -E rm -f ${package_filepath}
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
add_dependencies(check-llvm-toolchain check-picolibc)

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
        COMMAND make run BIN_PATH=${LLVM_BINARY_DIR}/bin
        COMMAND make clean
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/tests/smoketests/${test}
    )
    add_dependencies(check-llvm-toolchain-smoketests-${test} llvm-toolchain)
    add_dependencies(check-llvm-toolchain check-llvm-toolchain-smoketests-${test})

    # Post-package tests
    add_custom_target(
        check-package-llvm-toolchain-smoketests-${test}
        COMMAND make clean
        COMMAND make run BIN_PATH=${unpack_directory}/bin
        COMMAND make clean
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/tests/smoketests/${test}
    )
    add_dependencies(check-package-llvm-toolchain-smoketests-${test} unpack-llvm-toolchain)
    add_dependencies(check-package-llvm-toolchain check-package-llvm-toolchain-smoketests-${test})
endforeach()

# Samples
# Don't run the baremetal-uart sample because it never terminates.
foreach(test
    baremetal-semihosting-aarch64
    baremetal-semihosting
    cpp-baremetal-semihosting
    cpp-baremetal-semihosting-cfi
    cpp-baremetal-semihosting-ubsan
)
    add_custom_target(
        check-llvm-toolchain-samples-${test}
        COMMAND make clean
        COMMAND make run BIN_PATH=${LLVM_BINARY_DIR}/bin
        COMMAND make clean
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/samples/src/${test}
    )
    add_dependencies(check-llvm-toolchain-samples-${test} llvm-toolchain)
    add_dependencies(check-llvm-toolchain check-llvm-toolchain-samples-${test})

    # Post-package tests
    add_custom_target(
        check-package-llvm-toolchain-samples-${test}
        COMMAND make clean
        COMMAND make run BIN_PATH=${unpack_directory}/bin
        COMMAND make clean
        WORKING_DIRECTORY ${unpack_directory}/samples/src/${test}
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
        -DCLANG_TABLEGEN=${LLVM_BINARY_DIR}/bin/clang-tblgen${CMAKE_EXECUTABLE_SUFFIX}
        -DLLVM_CCACHE_BUILD=${LLVM_CCACHE_BUILD}
        -DLLVM_CONFIG_PATH=${LLVM_BINARY_DIR}/bin/llvm-config${CMAKE_EXECUTABLE_SUFFIX}
        -DLLVM_DISTRIBUTION_COMPONENTS=${LLVM_DISTRIBUTION_COMPONENTS_comma}
        -DLLVM_ENABLE_PROJECTS=${LLVM_ENABLE_PROJECTS_comma}
        -DLLVM_TABLEGEN=${LLVM_BINARY_DIR}/bin/llvm-tblgen${CMAKE_EXECUTABLE_SUFFIX}
        -DLLVM_TARGETS_TO_BUILD=${LLVM_TARGETS_TO_BUILD_comma}
        BUILD_COMMAND "" # Let the install command build whatever it needs
        INSTALL_COMMAND "${CMAKE_COMMAND}" --build <BINARY_DIR> --target install-distribution
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
        COMPONENT llvm-toolchain-mingw
    )

    # Copy MinGW licenses
    install(
        DIRECTORY mingw-licenses/
        DESTINATION third-party-licenses
        COMPONENT llvm-toolchain-third-party-licenses
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
            COMPONENT llvm-toolchain-mingw
        )
    endforeach()

    add_dependencies(
        llvm-toolchain
        mingw-llvm
    )
endif()
