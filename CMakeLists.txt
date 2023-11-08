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
#   git -C repos/llvm-project am ../../patches/llvm-project/*.patch
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
option(
    LIBS_DEPEND_ON_TOOLS
    "Automatically ensure tools like clang are up to date before building libraries.
    Set this to OFF if you're working on the libraries and want to avoid rebuilding
    the tools every time you update llvm-project."
    ON
)

set(LLVM_TOOLCHAIN_C_LIBRARY
    "picolibc" CACHE STRING
    "Which C library to use."
)
set_property(CACHE LLVM_TOOLCHAIN_C_LIBRARY
    PROPERTY STRINGS picolibc newlib)
option(LLVM_TOOLCHAIN_NEWLIB_OVERLAY_INSTALL
    "Make cpack build an overlay package that can be unpacked over the main toolchain to install a secondary set of libraries based on newlib.")

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

find_package(Python3 REQUIRED COMPONENTS Interpreter)

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
    set(LLVM_USE_LINKER lld CACHE STRING "")
endif()

# A lot of files get installed which makes the install messages too
# noisy to be useful so default to disabling them.
set(CMAKE_INSTALL_MESSAGE NEVER CACHE STRING "")

include(ExternalProject)
include(FetchContent)
include(ProcessorCount)

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
read_repo_version(${LLVM_TOOLCHAIN_C_LIBRARY} ${LLVM_TOOLCHAIN_C_LIBRARY})

set(
    llvm_project_patches
    ${CMAKE_CURRENT_SOURCE_DIR}/patches/llvm-project/0001-Fix-llvm-test-CodeGen-ARM-build-attributes.ll-test.patch
    ${CMAKE_CURRENT_SOURCE_DIR}/patches/llvm-project/0002-Add-check-for-building-with-picolibc.patch
    ${CMAKE_CURRENT_SOURCE_DIR}/patches/llvm-project/0003-Run-picolibc-tests-with-qemu.patch
    ${CMAKE_CURRENT_SOURCE_DIR}/patches/llvm-project/0004-xfail-two-remaining-libcxx-with-picolibc-tests.patch)
FetchContent_Declare(llvmproject
    GIT_REPOSITORY https://github.com/llvm/llvm-project.git
    GIT_TAG "${llvmproject_TAG}"
    GIT_SHALLOW "${llvmproject_SHALLOW}"
    GIT_PROGRESS TRUE
    PATCH_COMMAND git reset --quiet --hard && git clean --quiet --force -dx && git am --ignore-whitespace --3way ${llvm_project_patches}
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

FetchContent_Declare(newlib
    GIT_REPOSITORY https://sourceware.org/git/newlib-cygwin.git
    GIT_TAG "${newlib_TAG}"
    GIT_SHALLOW "${newlib_SHALLOW}"
    GIT_PROGRESS TRUE
    PATCH_COMMAND git reset --quiet --hard && git clean --quiet --force -dx && git apply ${CMAKE_CURRENT_SOURCE_DIR}/patches/newlib.patch
    # Similarly to picolibc, we don't do the configuration here.
    SOURCE_SUBDIR do_not_add_newlib_subdir
)

FetchContent_MakeAvailable(llvmproject)
FetchContent_MakeAvailable(${LLVM_TOOLCHAIN_C_LIBRARY})

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

if(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL newlib)
    install(
        FILES
        ${CMAKE_CURRENT_SOURCE_DIR}/newlib.cfg
        DESTINATION bin
        COMPONENT llvm-toolchain-newlib-configs
    )
endif()

# These must be set before include(CPack) which the llvm CMakeLists.txt does.
# Restrict which LLVM components are installed.
if(LLVM_TOOLCHAIN_NEWLIB_OVERLAY_INSTALL)
    set(CPACK_COMPONENTS_ALL
        llvm-toolchain-libs
        llvm-toolchain-newlib-configs
        llvm-toolchain-third-party-licenses)
elseif(LLVM_TOOLCHAIN_CROSS_BUILD_MINGW)
    set(CPACK_COMPONENTS_ALL ${LLVM_TOOLCHAIN_DISTRIBUTION_COMPONENTS} llvm-toolchain-mingw)
else()
    set(CPACK_COMPONENTS_ALL ${LLVM_TOOLCHAIN_DISTRIBUTION_COMPONENTS} ${LLVM_DISTRIBUTION_COMPONENTS})
endif()
# Enable limiting the installed components in TGZ and ZIP packages.
set(CPACK_ARCHIVE_COMPONENT_INSTALL TRUE)
# Don't create a separate archive for each component.
set(CPACK_COMPONENTS_GROUPING ALL_COMPONENTS_IN_ONE)
# When extracting the files put them in an ArmCompiler-.../ directory.
# Exception: the newlib overlay package does not do this, because it has
# to be able to unpack over the top of an existing installation on all
# platforms, and each platform has a different top-level directory name.
if(LLVM_TOOLCHAIN_NEWLIB_OVERLAY_INSTALL)
    set(CPACK_COMPONENT_INCLUDE_TOPLEVEL_DIRECTORY FALSE)
else()
    set(CPACK_COMPONENT_INCLUDE_TOPLEVEL_DIRECTORY TRUE)
endif()
# Compress package in parallel.
set(CPACK_THREADS 0 CACHE STRING "")

# set processor_name
string(TOLOWER ${CMAKE_SYSTEM_PROCESSOR} processor_name)
if(${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
    # If we're compiling on OSX we need to understand what targets we're
    #  building for.
    string(FIND "${CMAKE_OSX_ARCHITECTURES}" "x86_64" x86_result)
    string(FIND "${CMAKE_OSX_ARCHITECTURES}" "arm64" arm64_result)

    if((NOT ${x86_result} EQUAL -1) AND (NOT ${arm64_result} EQUAL -1))
        set(processor_name "universal")
    elseif(NOT ${x86_result} EQUAL -1)
        set(processor_name "x86_64")
    elseif(NOT ${arm64_result} EQUAL -1)
        set(processor_name "arm64")
    # CMAKE_OSX_ARCHITECTURES wasn't set or malformed
    # if it was malformed, we'll catch that later in the process
    # otherwise processor_name is already the system processor name
    endif()
else()
    string(REGEX MATCH "amd64|x64|x86" x86_match ${processor_name})
    if(x86_match)
        set(processor_name "x86_64")
    else()
        set(processor_name "AArch64")
    endif()
endif()

if(LLVM_TOOLCHAIN_CROSS_BUILD_MINGW)
    set(CPACK_SYSTEM_NAME "Windows-${processor_name}")
else()
    set(CPACK_SYSTEM_NAME "${CMAKE_SYSTEM_NAME}-${processor_name}")
endif()

add_subdirectory(
    ${llvmproject_SOURCE_DIR}/llvm llvm
)

if(LLVM_TOOLCHAIN_NEWLIB_OVERLAY_INSTALL)
    set(CPACK_PACKAGE_FILE_NAME ${CMAKE_PROJECT_NAME}-newlib-overlay-${CMAKE_PROJECT_VERSION})
endif()

# Including CPack again after llvm CMakeLists.txt included it
# resets CPACK_PACKAGE_VERSION to the default MAJOR.MINOR.PATCH format.
include(CPack)

# Ensure LLVM tool symlinks are installed.
list(APPEND CMAKE_MODULE_PATH ${llvmproject_SOURCE_DIR}/llvm/cmake/modules)
llvm_install_symlink(LLVM llvm-ranlib llvm-ar ALWAYS_GENERATE)
llvm_install_symlink(LLVM llvm-readelf llvm-readobj ALWAYS_GENERATE)
llvm_install_symlink(LLVM llvm-strip llvm-objcopy ALWAYS_GENERATE)

if(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL picolibc)
    # For building picolibc use Meson.
    # Although picolibc has support for building with CMake, the Meson code
    # is more mature and works better with LLVM.
    find_program(MESON_EXECUTABLE meson REQUIRED)
endif()

include(cmake/to_meson_list.cmake)

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
    # only one of picolibc and newlib source dirs is needed, but easiest to
    # specify both definitions
    -Dpicolibc_SOURCE_DIR=${picolibc_SOURCE_DIR}
    -Dnewlib_SOURCE_DIR=${newlib_SOURCE_DIR}
    # but we do tell the script which library we're actually using
    -DLLVM_TOOLCHAIN_C_LIBRARY=${LLVM_TOOLCHAIN_C_LIBRARY}
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
add_custom_target(check-llvm-toolchain-runtimes)
add_custom_target(check-compiler-rt)
add_custom_target(check-cxxabi)
add_custom_target(check-unwind)
add_custom_target(check-cxx)

add_dependencies(
    check-llvm-toolchain-runtimes
    check-compiler-rt
    check-cxxabi
    check-unwind
    check-cxx
)

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

if(LIBS_DEPEND_ON_TOOLS)
    set(lib_tool_dependencies
        clang
        lld
        llvm-ar
        llvm-config
        llvm-nm
        llvm-ranlib
        llvm-strip
    )
endif()

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

set(newlib_specific_runtimes_options
    -DLIBCXXABI_ENABLE_EXCEPTIONS=OFF
    -DLIBCXXABI_ENABLE_THREADS=OFF
    -DLIBCXX_ENABLE_EXCEPTIONS=OFF
    -DLIBCXX_ENABLE_THREADS=OFF
    -DLIBCXX_ENABLE_RTTI=OFF
    -DLIBCXX_ENABLE_MONOTONIC_CLOCK=OFF
    -DLIBCXX_ENABLE_RANDOM_DEVICE=OFF
    -DLIBCXX_ENABLE_WIDE_CHARACTERS=ON
    -DLIBCXX_ENABLE_LOCALIZATION=OFF
    -DLIBUNWIND_ENABLE_THREADS=OFF
)

if(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL newlib AND
        LLVM_TOOLCHAIN_NEWLIB_OVERLAY_INSTALL)
    # If we're building newlib with the intention of installing it as
    # an overlay on the main package archive, then all of newlib's
    # includes, libraries and multilib.yaml go in a subdirectory of
    # lib/clang-runtimes. Configuration files in the bin directory
    # will make it easy to reset the sysroot to point at that subdir.
    set(library_subdir "/newlib")
else()
    set(library_subdir "")
endif()

add_custom_target(check-picolibc)
# Set LLVM_DEFAULT_EXTERNAL_LIT to the directory of clang
# which was build in previous step. This path is not exported
# by add_subdirectory of llvm project
set(LLVM_DEFAULT_EXTERNAL_LIT "${LLVM_BINARY_DIR}/bin/llvm-lit")

add_custom_target(check-newlib) # FIXME: put things in this

function(get_test_executor_params target_triple qemu_machine qemu_cpu qemu_params)
    if(target_triple MATCHES "^aarch64")
        set(qemu_command "qemu-system-aarch64")
    else()
        set(qemu_command "qemu-system-arm")
    endif()

    # Use colon as a separator because comma and semicolon are used for
    # other purposes in CMake.
    string(REPLACE " " ":" qemu_params_list "${qemu_params}")

    set(
        test_executor_params
        --qemu-command ${qemu_command}
        --qemu-machine ${qemu_machine})
    if(qemu_cpu)
        list(APPEND test_executor_params --qemu-cpu ${qemu_cpu})
    endif()
    if(qemu_params_list)
        list(APPEND test_executor_params "--qemu-params=${qemu_params_list}")
    endif()
    set(test_executor_params "${test_executor_params}" PARENT_SCOPE)
endfunction()

function(
    add_picolibc
    directory
    variant
    target_triple
    flags
    test_executor_params
    default_boot_flash_addr
    default_boot_flash_size
    default_flash_addr
    default_flash_size
    default_ram_addr
    default_ram_size
    default_stack_size
)
    if(CMAKE_INSTALL_MESSAGE STREQUAL NEVER)
        set(MESON_INSTALL_QUIET "--quiet")
    endif()

    if(target_triple MATCHES "^aarch64")
        set(cpu_family aarch64)
        set(enable_long_double_test false)
    else()
        set(cpu_family arm)
        set(enable_long_double_test true)
    endif()

    ExternalProject_Add(
        picolibc_${variant}
        SOURCE_DIR ${picolibc_SOURCE_DIR}
        INSTALL_DIR "${LLVM_BINARY_DIR}/${directory}"
        PREFIX picolibc/${variant}
        DEPENDS ${lib_tool_dependencies}
        CONFIGURE_COMMAND
            ${MESON_EXECUTABLE}
            setup
            -Dincludedir=include
            -Dlibdir=lib
            -Dspecsdir=none
            -Dmultilib=false
            -Dtests-enable-stack-protector=false
            -Dtest-long-double=${enable_long_double_test}
            --prefix <INSTALL_DIR>
            --cross-file <BINARY_DIR>/meson-cross-build.txt
            <SOURCE_DIR>
        BUILD_COMMAND ${MESON_EXECUTABLE} configure -Dtests=false
        COMMAND ${MESON_EXECUTABLE} compile
        INSTALL_COMMAND ${MESON_EXECUTABLE} install ${MESON_INSTALL_QUIET}
        TEST_COMMAND ${MESON_EXECUTABLE} configure -Dtests=true
        # meson<0.64.0 does not properly apply new configuration after
        # "meson configure -Dtests=false"
        # use "meson setup --reconfigure" as a workaround
        COMMAND ${MESON_EXECUTABLE} setup . <SOURCE_DIR> -Dtests=true --reconfigure
        COMMAND ${MESON_EXECUTABLE} test
        COMMAND ${MESON_EXECUTABLE} configure -Dtests=false
        USES_TERMINAL_CONFIGURE FALSE
        USES_TERMINAL_BUILD TRUE
        USES_TERMINAL_TEST TRUE
        LIST_SEPARATOR ,
        # Always run the build command so that incremental builds are correct.
        BUILD_ALWAYS TRUE
        CONFIGURE_HANDLED_BY_BUILD TRUE
        TEST_EXCLUDE_FROM_MAIN TRUE
        STEP_TARGETS install test
    )

    # Set meson_c_args to a comma-separated list of the clang path
    # and flags e.g. 'path/to/clang', '--target=armv6m-none-eabi',
    # '-march=armv6m'
    separate_arguments(flags)
    list(PREPEND flags "${LLVM_BINARY_DIR}/bin/clang${CMAKE_EXECUTABLE_SUFFIX}")
    list(APPEND flags --sysroot "${LLVM_BINARY_DIR}/${directory}")
    to_meson_list("${flags}" meson_c_args)

    set(test_executor_bin ${CMAKE_CURRENT_SOURCE_DIR}/test-support/picolibc-test-wrapper.py)
    to_meson_list("${test_executor_params}" test_executor_params)

    ExternalProject_Get_Property(picolibc_${variant} BINARY_DIR)
    configure_file(${CMAKE_CURRENT_FUNCTION_LIST_DIR}/cmake/meson-cross-build.txt.in ${BINARY_DIR}/meson-cross-build.txt @ONLY)

    # Building picolibc tests requires compiler_rt to be installed.
    # Building compiler_rt tests requires picolibc to be installed.
    # To solve this compiler_rt relies on picolibc to be just installed, not on
    # the full target, which would include tests. Picolibc tests, are enabled
    # only in tests step, otherwise, they would be built before install.
    ExternalProject_Add_StepDependencies(picolibc_${variant} test compiler_rt_${variant}-install)

    add_dependencies(check-picolibc picolibc_${variant}-test)
    add_dependencies(
        llvm-toolchain-runtimes
        picolibc_${variant}
    )
endfunction()

function(
    add_newlib
    directory
    variant
    target_triple
    flags
    test_executor_params
    default_boot_flash_addr
    default_boot_flash_size
    default_flash_addr
    default_flash_size
    default_ram_addr
    default_ram_size
    default_stack_size
)
    if(target_triple MATCHES "^aarch64")
        set(cpu_family aarch64)
    else()
        set(cpu_family arm)
    endif()

    set(sysroot "${LLVM_BINARY_DIR}/${directory}")

    set(build_env
      "CC_FOR_TARGET=${LLVM_BINARY_DIR}/bin/clang -target ${target_triple} -ffreestanding"
      "CXX_FOR_TARGET=${LLVM_BINARY_DIR}/bin/clang++ -target ${target_triple} -ffreestanding"
      "AR_FOR_TARGET=${LLVM_BINARY_DIR}/bin/llvm-ar"
      "AS_FOR_TARGET=${LLVM_BINARY_DIR}/bin/llvm-as"
      "NM_FOR_TARGET=${LLVM_BINARY_DIR}/bin/llvm-nm"
      "OBJDUMP_FOR_TARGET=${LLVM_BINARY_DIR}/bin/llvm-objdump"
      "RANLIB_FOR_TARGET=${LLVM_BINARY_DIR}/bin/llvm-ranlib"
      "READELF_FOR_TARGET=${LLVM_BINARY_DIR}/bin/llvm-readelf"
      "STRIP_FOR_TARGET=${LLVM_BINARY_DIR}/bin/llvm-strip"
      "CFLAGS_FOR_TARGET=${flags} -Wno-error=implicit-function-declaration -D__USES_INITFINI__ -UHAVE_INIT_FINI__ -U_HAVE_INIT_FINI__ -UHAVE_INIT_FINI --sysroot ${sysroot}"
      "CCASFLAGS=${flags} -Wno-error=implicit-function-declaration -D__USES_INITFINI__ -UHAVE_INIT_FINI__ -U_HAVE_INIT_FINI__ -UHAVE_INIT_FINI --sysroot ${sysroot}"
    )

    set(make_flags)
    ProcessorCount(nproc)
    if(NOT nproc EQUAL 0)
        set(make_flags -j${nproc})
    endif()

    ExternalProject_Add(
        newlib_${variant}
        SOURCE_DIR ${newlib_SOURCE_DIR}
        INSTALL_DIR "${LLVM_BINARY_DIR}/${directory}"
        PREFIX newlib/${variant}
        DEPENDS ${lib_tool_dependencies}
        CONFIGURE_COMMAND
            ${CMAKE_COMMAND} -E env ${build_env}
            <SOURCE_DIR>/configure
            --target=${target_triple}
            --prefix "${sysroot}"
            --exec_prefix <BINARY_DIR>/tmpinstall
            --enable-newlib-io-long-long
            --enable-newlib-register-fini
            --disable-newlib-supplied-syscalls
            --enable-newlib-io-c99-formats
            --disable-nls
            --enable-lite-exit
            --disable-multilib
        BUILD_COMMAND
            ${CMAKE_COMMAND} -E env ${build_env}
            make ${make_flags}
            &&
            "${LLVM_BINARY_DIR}/bin/llvm-ar" rcs
            <BINARY_DIR>/${target_triple}/libgloss/${cpu_family}/libcrt0-rdimon.a
            <BINARY_DIR>/${target_triple}/libgloss/${cpu_family}/rdimon-crt0.o
            &&
            "${LLVM_BINARY_DIR}/bin/llvm-ar" rcs
            <BINARY_DIR>/${target_triple}/libgloss/${cpu_family}/libcrt0-nosys.a
            <BINARY_DIR>/${target_triple}/libgloss/${cpu_family}/crt0.o
        INSTALL_COMMAND
            make install
            &&
            ${CMAKE_COMMAND} -E copy_directory
            <BINARY_DIR>/tmpinstall/${target_triple}
            ${sysroot}
            &&
            ${CMAKE_COMMAND} -E copy
            <BINARY_DIR>/${target_triple}/libgloss/${cpu_family}/libcrt0-rdimon.a
            ${sysroot}/lib
            &&
            ${CMAKE_COMMAND} -E copy
            <BINARY_DIR>/${target_triple}/libgloss/${cpu_family}/libcrt0-nosys.a
            ${sysroot}/lib
        # FIXME: TEST_COMMAND?
        USES_TERMINAL_CONFIGURE FALSE
        USES_TERMINAL_BUILD TRUE
        # Always run the build command so that incremental builds are correct.
        BUILD_ALWAYS TRUE
        CONFIGURE_HANDLED_BY_BUILD TRUE
        TEST_EXCLUDE_FROM_MAIN TRUE
        STEP_TARGETS install # FIXME: test?
    )

    add_dependencies(
        llvm-toolchain-runtimes
        newlib_${variant}
    )
endfunction()

macro(
    add_libc
    directory
    variant
    target_triple
    flags
    test_executor_params
    default_boot_flash_addr
    default_boot_flash_size
    default_flash_addr
    default_flash_size
    default_ram_addr
    default_ram_size
    default_stack_size
)
    # It would be nice to just pass ${ARGN} to both the underlying functions,
    # but that has the side effect of expanding any list arguments (e.g.
    # test_executor_params) into lots of separate words - the same bug that
    # $* has in POSIX sh. We want the analogue of "$@" here, but I don't know
    # of one for cmake.
    if(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL picolibc)
        add_picolibc(
            "${directory}"
            "${variant}"
            "${target_triple}"
            "${flags}"
            "${test_executor_params}"
            "${default_boot_flash_addr}"
            "${default_boot_flash_size}"
            "${default_flash_addr}"
            "${default_flash_size}"
            "${default_ram_addr}"
            "${default_ram_size}"
            "${default_stack_size}"
        )
    elseif(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL newlib)
        add_newlib(
            "${directory}"
            "${variant}"
            "${target_triple}"
            "${flags}"
            "${test_executor_params}"
            "${default_boot_flash_addr}"
            "${default_boot_flash_size}"
            "${default_flash_addr}"
            "${default_flash_size}"
            "${default_ram_addr}"
            "${default_ram_size}"
            "${default_stack_size}"
        )
    endif()
endmacro()

function(get_runtimes_flags directory flags)
    set(runtimes_flags "${flags} -ffunction-sections -fdata-sections -fno-ident --sysroot ${LLVM_BINARY_DIR}/${directory}" PARENT_SCOPE)
endfunction()

function(
    add_compiler_rt
    directory
    variant
    target_triple
    flags
    test_executor
    libc_target
)
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

    set(compiler_rt_test_flags "${runtimes_flags} -fno-exceptions -fno-rtti -lcrt0-semihost -lsemihost -T picolibcpp.ld")
    if(variant STREQUAL "armv6m_soft_nofp")
        set(compiler_rt_test_flags "${compiler_rt_test_flags} -fomit-frame-pointer")
    endif()

    ExternalProject_Add(
        compiler_rt_${variant}
        SOURCE_DIR ${llvmproject_SOURCE_DIR}/compiler-rt
        PREFIX compiler-rt/${variant}
        INSTALL_DIR compiler-rt/${variant}/install
        DEPENDS ${lib_tool_dependencies} ${libc_target}
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
        -DCOMPILER_RT_INCLUDE_TESTS=ON
        -DCOMPILER_RT_EMULATOR=${test_executor}
        -DCOMPILER_RT_TEST_COMPILER=${LLVM_BINARY_DIR}/bin/clang
        -DCOMPILER_RT_TEST_COMPILER_CFLAGS=${compiler_rt_test_flags}
        -DLLVM_LIT_ARGS=${LLVM_LIT_ARGS}
        -DLLVM_CMAKE_DIR=${LLVM_BINARY_DIR}/lib/cmake/llvm
        -DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=ON
        STEP_TARGETS build install
        USES_TERMINAL_CONFIGURE FALSE
        USES_TERMINAL_BUILD TRUE
        USES_TERMINAL_INSTALL TRUE
        USES_TERMINAL_TEST TRUE
        LIST_SEPARATOR ,
        # Always run the build command so that incremental builds are correct.
        BUILD_ALWAYS TRUE
        CONFIGURE_HANDLED_BY_BUILD TRUE
        INSTALL_COMMAND ${CMAKE_COMMAND} --install .
        # Copy compiler-rt lib directory, moving libraries out of their
        # target-specific subdirectory.
        COMMAND
            ${CMAKE_COMMAND}
            -E copy_directory
            <INSTALL_DIR>/lib/${target_triple}
            "${LLVM_BINARY_DIR}/${directory}/lib"
    )

    add_dependencies(
        llvm-toolchain-runtimes
        compiler_rt_${variant}
    )
endfunction()

function(
    extend_with_exception_and_rtti
    extended_name
    base_name
    enable_exceptions_and_rtti
)
    if(${enable_exceptions_and_rtti})
        set(base_name ${base_name}_exceptions_rtti)
    endif()
    set(${extended_name} ${base_name} PARENT_SCOPE)
endfunction()

function(
    add_libcxx_libcxxabi_libunwind
    directory
    variant
    target_triple
    flags
    test_executor
    libc_target
    extra_cmake_options
    enable_exceptions_and_rtti
)
    get_runtimes_flags("${directory}" "${flags}")
    extend_with_exception_and_rtti(target_name "libcxx_libcxxabi_libunwind_${variant}" ${enable_exceptions_and_rtti})
    extend_with_exception_and_rtti(prefix "libcxx_libcxxabi_libunwind/${variant}" ${enable_exceptions_and_rtti})
    extend_with_exception_and_rtti(instal_dir "${LLVM_BINARY_DIR}/${directory}" ${enable_exceptions_and_rtti})
    if(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL picolibc)
        list(APPEND extra_cmake_options -DLIBCXXABI_ENABLE_EXCEPTIONS=${enable_exceptions_and_rtti} -DLIBCXX_ENABLE_EXCEPTIONS=${enable_exceptions_and_rtti} -DLIBCXX_ENABLE_RTTI=${enable_exceptions_and_rtti} -DLIBCXXABI_ENABLE_STATIC_UNWINDER=${enable_exceptions_and_rtti})
    endif()

    ExternalProject_Add(
        ${target_name}
        SOURCE_DIR ${llvmproject_SOURCE_DIR}/runtimes
        INSTALL_DIR ${instal_dir}
        PREFIX ${prefix}
        DEPENDS ${lib_tool_dependencies} compiler_rt_${variant} ${libc_target}
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
        -DCMAKE_INSTALL_PREFIX=${instal_dir}
        -DCMAKE_NM=${LLVM_BINARY_DIR}/bin/llvm-nm${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_RANLIB=${LLVM_BINARY_DIR}/bin/llvm-ranlib${CMAKE_EXECUTABLE_SUFFIX}
        # Let CMake know we're cross-compiling
        -DCMAKE_SYSTEM_NAME=Generic
        -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY
        -DLIBC_LINKER_SCRIPT=picolibcpp.ld
        -DLIBCXXABI_BAREMETAL=ON
        -DLIBCXXABI_ENABLE_ASSERTIONS=OFF
        -DLIBCXXABI_ENABLE_SHARED=OFF
        -DLIBCXXABI_ENABLE_STATIC=ON
        -DLIBCXXABI_LIBCXX_INCLUDES="${LLVM_BINARY_DIR}/${directory}/include/c++/v1"
        -DLIBCXXABI_USE_COMPILER_RT=ON
        -DLIBCXXABI_USE_LLVM_UNWINDER=ON
        -DLIBCXXABI_EXECUTOR=${test_executor}
        -DLIBCXX_ABI_UNSTABLE=ON
        -DLIBCXX_CXX_ABI=libcxxabi
        -DLIBCXX_ENABLE_FILESYSTEM=OFF
        -DLIBCXX_ENABLE_SHARED=OFF
        -DLIBCXX_ENABLE_STATIC=ON
        -DLIBCXX_INCLUDE_BENCHMARKS=OFF
        -DLIBCXX_EXECUTOR=${test_executor}
        -DLIBUNWIND_ENABLE_SHARED=OFF
        -DLIBUNWIND_ENABLE_STATIC=ON
        -DLIBUNWIND_IS_BAREMETAL=ON
        -DLIBUNWIND_REMEMBER_HEAP_ALLOC=ON
        -DLIBUNWIND_USE_COMPILER_RT=ON
        -DLIBUNWIND_EXECUTOR=${test_executor}
        -DLLVM_LIT_ARGS=${LLVM_LIT_ARGS}
        -DLLVM_ENABLE_RUNTIMES=libcxxabi,libcxx,libunwind
        -DRUNTIME_TEST_ARCH_FLAGS=${flags}
        -DRUNTIME_VARIANT_NAME=${variant}
        ${extra_cmake_options}
        STEP_TARGETS build
        USES_TERMINAL_CONFIGURE FALSE
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
        ${target_name}
    )
endfunction()

function(add_compiler_rt_tests variant)
    ExternalProject_Add_Step(
        compiler_rt_${variant}
        check-compiler-rt
        COMMAND "${CMAKE_COMMAND}" --build <BINARY_DIR> --target check-compiler-rt
        USES_TERMINAL TRUE
        EXCLUDE_FROM_MAIN TRUE
        ALWAYS TRUE
    )
    ExternalProject_Add_StepTargets(compiler_rt_${variant} check-compiler-rt)
    ExternalProject_Add_StepDependencies(
        compiler_rt_${variant}
        check-compiler-rt
        compiler_rt_${variant}-build
    )
    add_custom_target(check-compiler-rt-${variant})
    add_dependencies(check-compiler-rt-${variant} compiler_rt_${variant}-check-compiler-rt)
    add_dependencies(check-compiler-rt check-compiler-rt-${variant})
    add_dependencies(check-llvm-toolchain-runtimes-${variant} check-compiler-rt-${variant})
endfunction()

function(add_libcxx_libcxxabi_libunwind_tests variant enable_exceptions_and_rtti)
    extend_with_exception_and_rtti(target_name "libcxx_libcxxabi_libunwind_${variant}" ${enable_exceptions_and_rtti})
    extend_with_exception_and_rtti(variant_with_extensions "${variant}" ${enable_exceptions_and_rtti})
    foreach(check_target check-cxxabi check-unwind check-cxx)
        ExternalProject_Add_Step(
            ${target_name}
            ${check_target}
            COMMAND "${CMAKE_COMMAND}" --build <BINARY_DIR> --target ${check_target}
            USES_TERMINAL TRUE
            EXCLUDE_FROM_MAIN TRUE
            ALWAYS TRUE
        )
        ExternalProject_Add_StepTargets(${target_name} ${check_target})
        ExternalProject_Add_StepDependencies(
            ${target_name}
            ${check_target}
            ${target_name}-build
        )
        add_custom_target(${check_target}-${variant_with_extensions})
        add_dependencies(${check_target}-${variant_with_extensions} ${target_name}-${check_target})
        add_dependencies(${check_target} ${target_name}-${check_target})
        add_dependencies(check-llvm-toolchain-runtimes-${variant} ${check_target}-${variant_with_extensions})
    endforeach()
endfunction()

function(get_compiler_rt_target_triple target_arch flags)
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

function(add_library_variant target_arch)
    set(
        one_value_args
        SUFFIX
        COMPILE_FLAGS
        MULTILIB_FLAGS
        QEMU_MACHINE
        QEMU_CPU
        QEMU_PARAMS
        BOOT_FLASH_ADDRESS
        BOOT_FLASH_SIZE
        FLASH_ADDRESS
        FLASH_SIZE
        RAM_ADDRESS
        RAM_SIZE
        STACK_SIZE
    )
    cmake_parse_arguments(VARIANT "" "${one_value_args}" "" ${ARGN})

    if(VARIANT_SUFFIX)
        set(variant "${target_arch}_${VARIANT_SUFFIX}")
    else()
        set(variant "${target_arch}")
    endif()

    if(LLVM_TOOLCHAIN_LIBRARY_VARIANTS)
        if(NOT enable_${variant})
            message("Disabling library variant ${variant}")
            return()
        else()
            message("Enabling library variant ${variant}")
        endif()
    endif()

    if(target_arch STREQUAL "aarch64")
        set(parent_dir_name aarch64-none-elf)
    else()
        set(parent_dir_name arm-none-eabi)
    endif()

    get_compiler_rt_target_triple("${target_arch}" "${VARIANT_COMPILE_FLAGS}")

    set(directory "${TARGET_LIBRARIES_DIR}${library_subdir}/${parent_dir_name}/${variant}")
    set(VARIANT_COMPILE_FLAGS "--target=${target_triple} ${VARIANT_COMPILE_FLAGS}")
    get_test_executor_params(
        "${target_triple}"
        "${VARIANT_QEMU_MACHINE}"
        "${VARIANT_QEMU_CPU}"
        "${VARIANT_QEMU_PARAMS}"
    )
    set(
        lit_test_executor
        ${CMAKE_CURRENT_SOURCE_DIR}/test-support/lit-exec-qemu.py
        ${test_executor_params}
    )
    list(JOIN lit_test_executor " " lit_test_executor)
    if(NOT PREBUILT_TARGET_LIBRARIES)
        add_libc(
            "${directory}"
            "${variant}"
            "${target_triple}"
            "${VARIANT_COMPILE_FLAGS}"
            "${test_executor_params}"
            "${VARIANT_BOOT_FLASH_ADDRESS}"
            "${VARIANT_BOOT_FLASH_SIZE}"
            "${VARIANT_FLASH_ADDRESS}"
            "${VARIANT_FLASH_SIZE}"
            "${VARIANT_RAM_ADDRESS}"
            "${VARIANT_RAM_SIZE}"
            "${VARIANT_STACK_SIZE}"
        )
        add_compiler_rt(
            "${directory}"
            "${variant}"
            "${target_triple}"
            "${VARIANT_COMPILE_FLAGS}"
            "${lit_test_executor}"
            "${LLVM_TOOLCHAIN_C_LIBRARY}_${variant}-install"
        )
        add_libcxx_libcxxabi_libunwind(
            "${directory}"
            "${variant}"
            "${target_triple}"
            "${VARIANT_COMPILE_FLAGS}"
            "${lit_test_executor}"
            "${LLVM_TOOLCHAIN_C_LIBRARY}_${variant}-install"
            "${${LLVM_TOOLCHAIN_C_LIBRARY}_specific_runtimes_options}"
            OFF
        )
        if(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL picolibc)
            add_libcxx_libcxxabi_libunwind(
                "${directory}"
                "${variant}"
                "${target_triple}"
                "${VARIANT_COMPILE_FLAGS}"
                "${lit_test_executor}"
                "${LLVM_TOOLCHAIN_C_LIBRARY}_${variant}-install"
                "${${LLVM_TOOLCHAIN_C_LIBRARY}_specific_runtimes_options}"
                ON
            )
        endif()
        if(VARIANT_COMPILE_FLAGS MATCHES "-march=armv8")
            message("C++ runtime libraries tests disabled for ${variant}")
        else()
            add_custom_target(check-llvm-toolchain-runtimes-${variant})
            add_dependencies(check-llvm-toolchain-runtimes check-llvm-toolchain-runtimes-${variant})
            add_compiler_rt_tests("${variant}")
            add_libcxx_libcxxabi_libunwind_tests("${variant}" OFF)
            if(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL picolibc)
                add_libcxx_libcxxabi_libunwind_tests("${variant}" ON)
            endif()
        endif()
    endif()

    string(APPEND multilib_yaml_content "- Dir: ${parent_dir_name}/${variant}\n")

    string(APPEND multilib_yaml_content "  Flags:\n")
    string(REPLACE " " ";" multilib_flags_list ${VARIANT_MULTILIB_FLAGS})
    foreach(flag ${multilib_flags_list})
        string(APPEND multilib_yaml_content "  - ${flag}\n")
    endforeach()
    string(APPEND multilib_yaml_content "  ExclusiveGroup: stdlibs\n")

    install(
        DIRECTORY "${LLVM_BINARY_DIR}/${directory}/"
        DESTINATION "${directory}"
        COMPONENT llvm-toolchain-libs
    )
    if(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL picolibc)
        string(APPEND multilib_yaml_content "- Dir: ${parent_dir_name}/${variant}_exceptions_rtti\n")
        string(APPEND multilib_yaml_content "  Flags:\n")
        string(REPLACE " " ";" multilib_flags_list ${VARIANT_MULTILIB_FLAGS})
        foreach(flag ${multilib_flags_list})
            string(APPEND multilib_yaml_content "  - ${flag}\n")
        endforeach()
        string(APPEND multilib_yaml_content "  ExclusiveGroup: stdlibs\n")

        install(
        DIRECTORY "${LLVM_BINARY_DIR}/${directory}_exceptions_rtti/"
        DESTINATION "${directory}_exceptions_rtti/"
        COMPONENT llvm-toolchain-libs
        )
    endif()
    set(multilib_yaml_content "${multilib_yaml_content}" PARENT_SCOPE)
endfunction()

set(multilib_yaml_content "")

# Define which library variants to build and which flags to use.
# For most variants, the "flash" memory is placed in address range, where
# simulated boards have RAM. This is because code for some tests does not fit
# the real flash.
add_library_variant(
    aarch64
    COMPILE_FLAGS "-march=armv8-a"
    MULTILIB_FLAGS "--target=aarch64-none-unknown-elf"
    QEMU_MACHINE "virt"
    QEMU_CPU "cortex-a57"
    BOOT_FLASH_ADDRESS 0x40000000
    BOOT_FLASH_SIZE 0x1000
    FLASH_ADDRESS 0x40001000
    FLASH_SIZE 0xfff000
    RAM_ADDRESS 0x41000000
    RAM_SIZE 0x1000000
    STACK_SIZE 8K
)
# For AArch32, clang uses different defaults for FPU selection than GCC, both
# when "+fp" or "+fp.dp" are used and when no FPU specifier is provided in
# "-march=". Using "-mfpu=" explicitly.
add_library_variant(
    armv4t
    COMPILE_FLAGS "-march=armv4t -mfpu=none"
    MULTILIB_FLAGS "--target=armv4t-none-unknown-eabi -mfpu=none"
    QEMU_MACHINE "none"
    QEMU_CPU "ti925t"
    QEMU_PARAMS "-m 1G"
    BOOT_FLASH_ADDRESS 0x00000000
    BOOT_FLASH_SIZE 0x1000
    FLASH_ADDRESS 0x20000000
    FLASH_SIZE 0x1000000
    RAM_ADDRESS 0x21000000
    RAM_SIZE 0x1000000
    STACK_SIZE 4K
)
add_library_variant(
    armv5te
    COMPILE_FLAGS "-march=armv5te -mfpu=none"
    MULTILIB_FLAGS "--target=armv5e-none-unknown-eabi -mfpu=none"
    QEMU_MACHINE "none"
    QEMU_CPU "arm926"
    QEMU_PARAMS "-m 1G"
    BOOT_FLASH_ADDRESS 0x00000000
    BOOT_FLASH_SIZE 0x1000
    FLASH_ADDRESS 0x20000000
    FLASH_SIZE 0x1000000
    RAM_ADDRESS 0x21000000
    RAM_SIZE 0x1000000
    STACK_SIZE 4K
)
add_library_variant(
    armv6m
    SUFFIX soft_nofp
    COMPILE_FLAGS "-mfloat-abi=soft -march=armv6m -mfpu=none"
    MULTILIB_FLAGS "--target=thumbv6m-none-unknown-eabi -mfpu=none"
    QEMU_MACHINE "mps2-an385"
    BOOT_FLASH_ADDRESS 0x00000000
    BOOT_FLASH_SIZE 0x1000
    FLASH_ADDRESS 0x21000000
    FLASH_SIZE 0x600000
    RAM_ADDRESS 0x21600000
    RAM_SIZE 0xa00000
    STACK_SIZE 4K
)
add_library_variant(
    armv7a
    SUFFIX soft_nofp
    COMPILE_FLAGS "-mfloat-abi=soft -march=armv7a -mfpu=none"
    MULTILIB_FLAGS "--target=armv7-none-unknown-eabi -mfpu=none"
    QEMU_MACHINE "none"
    QEMU_CPU "cortex-a7"
    QEMU_PARAMS "-m 1G"
    BOOT_FLASH_ADDRESS 0x00000000
    BOOT_FLASH_SIZE 0x1000
    FLASH_ADDRESS 0x20000000
    FLASH_SIZE 0x1000000
    RAM_ADDRESS 0x21000000
    RAM_SIZE 0x1000000
    STACK_SIZE 4K
)
add_library_variant(
    armv7a
    SUFFIX hard_vfpv3_d16
    COMPILE_FLAGS "-mfloat-abi=hard -march=armv7a -mfpu=vfpv3-d16"
    MULTILIB_FLAGS "--target=armv7-none-unknown-eabihf -mfpu=vfpv3-d16"
    QEMU_MACHINE "none"
    QEMU_CPU "cortex-a8"
    QEMU_PARAMS "-m 1G"
    BOOT_FLASH_ADDRESS 0x00000000
    BOOT_FLASH_SIZE 0x1000
    FLASH_ADDRESS 0x20000000
    FLASH_SIZE 0x1000000
    RAM_ADDRESS 0x21000000
    RAM_SIZE 0x1000000
    STACK_SIZE 4K
)
add_library_variant(
    armv7r
    SUFFIX soft_nofp
    COMPILE_FLAGS "-mfloat-abi=soft -march=armv7r -mfpu=none"
    MULTILIB_FLAGS "--target=armv7r-none-unknown-eabi -mfpu=none"
    QEMU_MACHINE "none"
    QEMU_CPU "cortex-r5f"
    QEMU_PARAMS "-m 1G"
    BOOT_FLASH_ADDRESS 0x00000000
    BOOT_FLASH_SIZE 0x1000
    FLASH_ADDRESS 0x20000000
    FLASH_SIZE 0x1000000
    RAM_ADDRESS 0x21000000
    RAM_SIZE 0x1000000
    STACK_SIZE 4K
)
add_library_variant(
    armv7r
    SUFFIX hard_vfpv3_d16
    COMPILE_FLAGS "-mfloat-abi=hard -march=armv7r -mfpu=vfpv3-d16"
    MULTILIB_FLAGS "--target=armv7r-none-unknown-eabihf -mfpu=vfpv3-d16"
    QEMU_MACHINE "none"
    QEMU_CPU "cortex-r5f"
    QEMU_PARAMS "-m 1G"
    BOOT_FLASH_ADDRESS 0x00000000
    BOOT_FLASH_SIZE 0x1000
    FLASH_ADDRESS 0x20000000
    FLASH_SIZE 0x1000000
    RAM_ADDRESS 0x21000000
    RAM_SIZE 0x1000000
    STACK_SIZE 4K
)
add_library_variant(
    armv7m
    SUFFIX soft_fpv4_sp_d16
    COMPILE_FLAGS "-mfloat-abi=softfp -march=armv7m -mfpu=fpv4-sp-d16"
    MULTILIB_FLAGS "--target=thumbv7m-none-unknown-eabi -mfpu=fpv4-sp-d16"
    QEMU_MACHINE "mps2-an386"
    QEMU_CPU "cortex-m4"
    BOOT_FLASH_ADDRESS 0x00000000
    BOOT_FLASH_SIZE 0x1000
    FLASH_ADDRESS 0x21000000
    FLASH_SIZE 0x600000
    RAM_ADDRESS 0x21600000
    RAM_SIZE 0xa00000
    STACK_SIZE 4K
)
# When no -mfpu=none is specified, the compiler internally adds all other
# possible fpu settings before searching for matching variants. So for the
# no-fpu variant to win, it has to be in multilab.yaml after all other
# fpu variants. The order of variants in multilab.yaml depends on the order
# of the add_library_variant calls. So the add_library_variant that adds
# the soft_nofp for armv7m is placed after all other armv7m variants.
add_library_variant(
    armv7m
    SUFFIX soft_nofp
    COMPILE_FLAGS "-mfloat-abi=soft -march=armv7m -mfpu=none"
    MULTILIB_FLAGS "--target=thumbv7m-none-unknown-eabi -mfpu=none"
    QEMU_MACHINE "mps2-an385"
    QEMU_CPU "cortex-m3"
    BOOT_FLASH_ADDRESS 0x00000000
    BOOT_FLASH_SIZE 0x1000
    FLASH_ADDRESS 0x21000000
    FLASH_SIZE 0x600000
    RAM_ADDRESS 0x21600000
    RAM_SIZE 0xa00000
    STACK_SIZE 4K
)
add_library_variant(
    armv7em
    SUFFIX hard_fpv4_sp_d16
    COMPILE_FLAGS "-mfloat-abi=hard -march=armv7em -mfpu=fpv4-sp-d16"
    MULTILIB_FLAGS "--target=thumbv7em-none-unknown-eabihf -mfpu=fpv4-sp-d16"
    QEMU_MACHINE "mps2-an386"
    QEMU_CPU "cortex-m4"
    BOOT_FLASH_ADDRESS 0x00000000
    BOOT_FLASH_SIZE 0x1000
    FLASH_ADDRESS 0x21000000
    FLASH_SIZE 0x600000
    RAM_ADDRESS 0x21600000
    RAM_SIZE 0xa00000
    STACK_SIZE 4K
)
add_library_variant(
    armv7em
    SUFFIX hard_fpv5_d16
    COMPILE_FLAGS "-mfloat-abi=hard -march=armv7em -mfpu=fpv5-d16"
    MULTILIB_FLAGS "--target=thumbv7em-none-unknown-eabihf -mfpu=fpv5-d16"
    QEMU_MACHINE "mps2-an500"
    QEMU_CPU "cortex-m7"
    BOOT_FLASH_ADDRESS 0x00000000
    BOOT_FLASH_SIZE 0x1000
    FLASH_ADDRESS 0x60000000
    FLASH_SIZE 0x600000
    RAM_ADDRESS 0x60600000
    RAM_SIZE 0xa00000
    STACK_SIZE 4K
)
# When no -mfpu=none is specified, the compiler internally adds all other
# possible fpu settings before searching for matching variants. So for the
# no-fpu variant to win, it has to be in multilab.yaml after all other
# fpu variants. The order of variants in multilab.yaml depends on the order
# of the add_library_variant calls. So the add_library_variant that adds
# the soft_nofp for armv7em is placed after all other armv7em variants.
add_library_variant(
    armv7em
    SUFFIX soft_nofp
    COMPILE_FLAGS "-mfloat-abi=soft -march=armv7em -mfpu=none"
    MULTILIB_FLAGS "--target=thumbv7em-none-unknown-eabi -mfpu=none"
    QEMU_MACHINE "mps2-an386"
    QEMU_CPU "cortex-m4"
    BOOT_FLASH_ADDRESS 0x00000000
    BOOT_FLASH_SIZE 0x1000
    FLASH_ADDRESS 0x21000000
    FLASH_SIZE 0x600000
    RAM_ADDRESS 0x21600000
    RAM_SIZE 0xa00000
    STACK_SIZE 4K
)
add_library_variant(
    armv8m.main
    SUFFIX soft_nofp
    COMPILE_FLAGS "-mfloat-abi=soft -march=armv8m.main -mfpu=none"
    MULTILIB_FLAGS "--target=thumbv8m.main-none-unknown-eabi -mfpu=none"
    QEMU_MACHINE "mps2-an505"
    QEMU_CPU "cortex-m33"
    BOOT_FLASH_ADDRESS 0x10000000
    BOOT_FLASH_SIZE 0x1000
    FLASH_ADDRESS 0x80000000
    FLASH_SIZE 0x600000
    RAM_ADDRESS 0x80600000
    RAM_SIZE 0xa00000
    STACK_SIZE 4K
)
add_library_variant(
    armv8m.main
    SUFFIX hard_fp
    COMPILE_FLAGS "-mfloat-abi=hard -march=armv8m.main -mfpu=fpv5-sp-d16"
    MULTILIB_FLAGS "--target=thumbv8m.main-none-unknown-eabihf -mfpu=fpv5-sp-d16"
    QEMU_MACHINE "mps2-an505"
    QEMU_CPU "cortex-m33"
    BOOT_FLASH_ADDRESS 0x10000000
    BOOT_FLASH_SIZE 0x1000
    FLASH_ADDRESS 0x80000000
    FLASH_SIZE 0x600000
    RAM_ADDRESS 0x80600000
    RAM_SIZE 0xa00000
    STACK_SIZE 4K
)
add_library_variant(
    armv8.1m.main
    SUFFIX soft_nofp_nomve
    COMPILE_FLAGS "-mfloat-abi=soft -march=armv8.1m.main+nomve -mfpu=none"
    MULTILIB_FLAGS "--target=thumbv8.1m.main-none-unknown-eabi -mfpu=none"
    QEMU_MACHINE "mps3-an547"
    QEMU_CPU "cortex-m55"
    BOOT_FLASH_ADDRESS 0x00000000
    BOOT_FLASH_SIZE 512K
    FLASH_ADDRESS 0x60000000
    FLASH_SIZE 0x1000000
    RAM_ADDRESS 0x61000000
    RAM_SIZE 0x1000000
    STACK_SIZE 4K
)
add_library_variant(
    armv8.1m.main
    SUFFIX hard_fp_nomve
    COMPILE_FLAGS "-mfloat-abi=hard -march=armv8.1m.main+nomve -mfpu=fp-armv8-fullfp16-sp-d16"
    MULTILIB_FLAGS "--target=thumbv8.1m.main-none-unknown-eabihf -march=thumbv8.1m.main+fp16 -mfpu=fp-armv8-fullfp16-sp-d16"
    QEMU_MACHINE "mps3-an547"
    QEMU_CPU "cortex-m55"
    BOOT_FLASH_ADDRESS 0x00000000
    BOOT_FLASH_SIZE 512K
    FLASH_ADDRESS 0x60000000
    FLASH_SIZE 0x1000000
    RAM_ADDRESS 0x61000000
    RAM_SIZE 0x1000000
    STACK_SIZE 4K
)
add_library_variant(
    armv8.1m.main
    SUFFIX hard_fpdp_nomve
    COMPILE_FLAGS "-mfloat-abi=hard -march=armv8.1m.main+nomve -mfpu=fp-armv8-fullfp16-d16"
    MULTILIB_FLAGS "--target=thumbv8.1m.main-none-unknown-eabihf -march=thumbv8.1m.main+fp16 -mfpu=fp-armv8-fullfp16-d16"
    QEMU_MACHINE "mps3-an547"
    QEMU_CPU "cortex-m55"
    BOOT_FLASH_ADDRESS 0x00000000
    BOOT_FLASH_SIZE 512K
    FLASH_ADDRESS 0x60000000
    FLASH_SIZE 0x1000000
    RAM_ADDRESS 0x61000000
    RAM_SIZE 0x1000000
    STACK_SIZE 4K
)
add_library_variant(
    armv8.1m.main
    SUFFIX hard_nofp_mve
    COMPILE_FLAGS "-mfloat-abi=hard -march=armv8.1m.main+mve -mfpu=none"
    MULTILIB_FLAGS "--target=thumbv8.1m.main-none-unknown-eabihf -march=thumbv8.1m.main+dsp+mve -mfpu=none"
    QEMU_MACHINE "mps3-an547"
    QEMU_CPU "cortex-m55"
    BOOT_FLASH_ADDRESS 0x00000000
    BOOT_FLASH_SIZE 512K
    FLASH_ADDRESS 0x60000000
    FLASH_SIZE 0x1000000
    RAM_ADDRESS 0x61000000
    RAM_SIZE 0x1000000
    STACK_SIZE 4K
)

configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/cmake/multilib.yaml.in
    ${CMAKE_CURRENT_BINARY_DIR}/multilib-without-fpus.yaml
    @ONLY
)

set(multilib_yaml_depends
    "${CMAKE_CURRENT_SOURCE_DIR}/multilib-fpus.py"
    "${CMAKE_CURRENT_BINARY_DIR}/multilib-without-fpus.yaml"
)
if(LIBS_DEPEND_ON_TOOLS)
    list(APPEND multilib_yaml_depends clang)
endif()

add_custom_command(
  OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/llvm/${TARGET_LIBRARIES_DIR}${library_subdir}/multilib.yaml
  COMMAND ${CMAKE_COMMAND} -E copy
    ${CMAKE_CURRENT_BINARY_DIR}/multilib-without-fpus.yaml
    ${CMAKE_CURRENT_BINARY_DIR}/llvm/${TARGET_LIBRARIES_DIR}${library_subdir}/multilib.yaml
  COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/multilib-fpus.py"
    "--clang=${LLVM_BINARY_DIR}/bin/clang${CMAKE_EXECUTABLE_SUFFIX}"
    "--llvm-source=${llvmproject_SOURCE_DIR}"
    >> "${CMAKE_CURRENT_BINARY_DIR}/llvm/${TARGET_LIBRARIES_DIR}${library_subdir}/multilib.yaml"
  DEPENDS ${multilib_yaml_depends}
)
add_custom_target(multilib_yaml ALL DEPENDS
  ${CMAKE_CURRENT_BINARY_DIR}/llvm/${TARGET_LIBRARIES_DIR}${library_subdir}/multilib.yaml)
add_dependencies(llvm-toolchain-runtimes multilib_yaml)

install(
    FILES ${CMAKE_CURRENT_BINARY_DIR}/llvm/${TARGET_LIBRARIES_DIR}${library_subdir}/multilib.yaml
    DESTINATION ${TARGET_LIBRARIES_DIR}${library_subdir}
    COMPONENT llvm-toolchain-libs
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

if(NOT LLVM_TOOLCHAIN_NEWLIB_OVERLAY_INSTALL)
    set(third_party_license_summary_install_dir .)
    set(third_party_license_files_install_dir third-party-licenses)
else()
    # If we're building an overlay archive, put all the license files
    # one level down in third-party-licenses/newlib, so that
    # COPYING.NEWLIB doesn't collide with the file of the same name
    # from picolibc, and the LLVM license files are also duplicated
    # (in case the overlay archive is used with a non-matching version
    # of the main toolchain).
    set(third_party_license_summary_install_dir third-party-licenses/newlib)
    set(third_party_license_files_install_dir third-party-licenses/newlib)
endif()

install(
    FILES ${CMAKE_CURRENT_BINARY_DIR}/THIRD-PARTY-LICENSES.txt
    DESTINATION ${third_party_license_summary_install_dir}
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
)
if(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL picolibc)
    list(APPEND third_party_license_files
        ${picolibc_SOURCE_DIR}/COPYING.NEWLIB           COPYING.NEWLIB
        ${picolibc_SOURCE_DIR}/COPYING.picolibc         COPYING.picolibc
    )
endif()
if(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL newlib)
    list(APPEND third_party_license_files
        ${newlib_SOURCE_DIR}/COPYING.NEWLIB             COPYING.NEWLIB
        ${newlib_SOURCE_DIR}/COPYING.LIBGLOSS           COPYING.LIBGLOSS
    )
endif()

while(third_party_license_files)
    list(POP_FRONT third_party_license_files source_file destination_name)
    install(
        FILES ${source_file}
        DESTINATION ${third_party_license_files_install_dir}
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
elseif(${CMAKE_SYSTEM_NAME} MATCHES "Darwin"
        AND NOT LLVM_TOOLCHAIN_NEWLIB_OVERLAY_INSTALL)
    set(cpack_generator DragNDrop)
    set(package_filename_extension ".dmg")
else()
    set(cpack_generator TXZ)
    set(package_filename_extension ".tar.xz")
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


add_custom_target(check-llvm-toolchain)
add_dependencies(check-llvm-toolchain check-${LLVM_TOOLCHAIN_C_LIBRARY})
add_dependencies(check-llvm-toolchain check-compiler-rt)
add_subdirectory(test)
add_dependencies(check-llvm-toolchain check-llvm-toolchain-lit)
add_subdirectory(packagetest)

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
        -DLLVM_CMAKE_DIR=${LLVM_BINARY_DIR}/lib/cmake/llvm
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
