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
#   git -C repos/llvm-project am -k $PWD/patches/llvm-project/*.patch
#   git -C repos clone https://github.com/picolibc/picolibc.git
#   git -C repos/picolibc am -k $PWD/patches/picolibc/*.patch
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
set(LLVM_TOOLCHAIN_MULTILIB_JSON
    "${CMAKE_CURRENT_SOURCE_DIR}/arm-multilib/json/multilib.json" CACHE STRING
    "JSON file defining the multilib."
)
set(LLVM_TOOLCHAIN_LIBRARY_VARIANTS
    "all" CACHE STRING
    "Build only the specified library variants, or \"all\"."
)
option(
    LIBS_DEPEND_ON_TOOLS
    "Automatically ensure tools like clang are up to date before building libraries.
    Set this to OFF if you're working on the libraries and want to avoid rebuilding
    the tools every time you update llvm-project."
    ON
)
option(
    LIBS_USE_COMPILER_LAUNCHER
    "Pass CMAKE_C_COMPILER_LAUNCHER and CMAKE_CXX_COMPILER_LAUNCHER
    down to the library builds, so that programs such as ccache can
    be used to speed up repeated builds. This is not done by default,
    as it can also make the inital build slower due to the cold cache."
)
option(
    APPLY_LLVM_PERFORMANCE_PATCHES
    "During checkout, apply optional downstream patches to
    llvm-project to improve performance."
)
option(
    ENABLE_QEMU_TESTING
    "Enable tests that use QEMU. This option is ON by default."
    ON
)
option(
    ENABLE_FVP_TESTING
    "Enable tests that use FVPs. This option is OFF by default."
)
set(
    FVP_INSTALL_DIR
    "${CMAKE_CURRENT_SOURCE_DIR}/fvp/install" CACHE STRING
    "The directory in which the FVP models are installed. These are not
    included in this repository, but can be downloaded by the script
    fvp/get_fvps.sh"
)
set(FVP_CONFIG_DIR "${CMAKE_CURRENT_SOURCE_DIR}/fvp/config")
set(LLVM_TOOLCHAIN_C_LIBRARY
    "picolibc" CACHE STRING
    "Which C library to use."
)
set_property(CACHE LLVM_TOOLCHAIN_C_LIBRARY
    PROPERTY STRINGS picolibc newlib llvmlibc)

# Previously, the LLVM_TOOLCHAIN_LIBRARY_OVERLAY_INSTALL option was
# called LLVM_TOOLCHAIN_NEWLIB_OVERLAY_INSTALL. Detect a setting of
# that name, in case it's in an existing CMakeCache.txt or command
# line, and use it to set the default for the more general option
# name.
if(LLVM_TOOLCHAIN_NEWLIB_OVERLAY_INSTALL)
  set(overlay_install_default ON)
else()
  set(overlay_install_default OFF)
endif()
option(LLVM_TOOLCHAIN_LIBRARY_OVERLAY_INSTALL
    "Make cpack build an overlay package that can be unpacked over the main toolchain to install a secondary set of libraries based on newlib or llvm-libc."
    ${overlay_install_default})
if(LLVM_TOOLCHAIN_LIBRARY_OVERLAY_INSTALL)
  if(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL "picolibc")
    message(FATAL_ERROR "LLVM_TOOLCHAIN_LIBRARY_OVERLAY_INSTALL is only permitted for C libraries other than the default picolibc")
  endif()
endif()

set(BUG_REPORT_URL "https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/issues" CACHE STRING "")
set(LLVM_DISTRIBUTION_COMPONENTS
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
    llvm-strings
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
include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/fetch_llvm.cmake)
if(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL picolibc)
    include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/fetch_picolibc.cmake)
endif()
if(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL newlib)
    include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/fetch_newlib.cmake)
endif()

##################################################################################################
# We set all project properties later, this call is just to enable the
# CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT check
project(LLVMEmbeddedToolchainForArm)
# We generally want to install to a local directory to see what the
# output will look like rather than install into the system, so change
# the default accordingly.
# See https://cmake.org/cmake/help/latest/variable/CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT.html
# Note that THIS CODE ONLY WORKS AFTER THE FIRST CALL TO PROJECT so it
# can't be moved after the add_subdirectory(<llvm>) command below as it will be too late -
# the llvm project will set it to the default system install directory.
if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
    set(CMAKE_INSTALL_PREFIX
        "${CMAKE_BINARY_DIR}/install"
        CACHE PATH "" FORCE
    )
endif()
##################################################################################################

if(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL newlib)
    install(
        FILES
        ${CMAKE_CURRENT_SOURCE_DIR}/newlib.cfg
        DESTINATION bin
        COMPONENT llvm-toolchain-newlib-configs
    )
endif()

install(
    FILES
    ${CMAKE_CURRENT_SOURCE_DIR}/Omax.cfg
    ${CMAKE_CURRENT_SOURCE_DIR}/OmaxLTO.cfg
    DESTINATION bin
    COMPONENT llvm-toolchain-config-files
)

if(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL llvmlibc)
    install(
        FILES
        ${CMAKE_CURRENT_SOURCE_DIR}/llvmlibc.cfg
        DESTINATION bin
        COMPONENT llvm-toolchain-llvmlibc-configs
    )

    install(
      DIRECTORY
      ${CMAKE_CURRENT_SOURCE_DIR}/llvmlibc-samples/src
      DESTINATION samples
      COMPONENT llvm-toolchain-llvmlibc-configs
    )

    # We need to build libc-hdrgen
    ExternalProject_Add(
        libc_hdrgen
        SOURCE_DIR ${llvmproject_SOURCE_DIR}/llvm
        DEPENDS ${lib_tool_dependencies}
        CMAKE_ARGS
            -DLLVM_ENABLE_RUNTIMES=libc
            -DLLVM_LIBC_FULL_BUILD=ON
            -DCMAKE_BUILD_TYPE=Debug
        STEP_TARGETS build install
        BUILD_COMMAND ${CMAKE_COMMAND} --build . --target libc-hdrgen
        INSTALL_COMMAND ${CMAKE_COMMAND} -E true
        # Always run the build command so that incremental builds are correct.
        BUILD_ALWAYS TRUE
        CONFIGURE_HANDLED_BY_BUILD TRUE
    )
    ExternalProject_Get_property(libc_hdrgen BINARY_DIR)
    set(LIBC_HDRGEN ${BINARY_DIR}/bin/libc-hdrgen${CMAKE_EXECUTABLE_SUFFIX})

    # LLVM libc lacks a configuration for AArch64, but the AArch32 one works
    # fine. However, setting the configuration for both architectures to the
    # arm config directory means the baremetal config.json is never loaded,
    # as it resides in the directory above. To ensure both are used, copy
    # them to the same location and point libc to that.
    set(LIBC_CFG_DIR ${CMAKE_BINARY_DIR}/llvmlibc-config)
    file(COPY
        ${llvmproject_SOURCE_DIR}/libc/config/baremetal/config.json
        ${llvmproject_SOURCE_DIR}/libc/config/baremetal/arm/.
        DESTINATION
        ${LIBC_CFG_DIR}
    )
endif()

add_subdirectory(
    ${llvmproject_SOURCE_DIR}/llvm llvm
)

get_directory_property(LLVM_VERSION_MAJOR DIRECTORY ${llvmproject_SOURCE_DIR}/llvm DEFINITION LLVM_VERSION_MAJOR)
get_directory_property(LLVM_VERSION_MINOR DIRECTORY ${llvmproject_SOURCE_DIR}/llvm DEFINITION LLVM_VERSION_MINOR)
get_directory_property(LLVM_VERSION_PATCH DIRECTORY ${llvmproject_SOURCE_DIR}/llvm DEFINITION LLVM_VERSION_PATCH)

project(
    LLVMEmbeddedToolchainForArm
    VERSION ${LLVM_VERSION_MAJOR}.${LLVM_VERSION_MINOR}.${LLVM_VERSION_PATCH}
    DESCRIPTION "LLVM Embedded Toolchain for Arm"
    HOMEPAGE_URL "https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm"
)

# Set package name for shorter archive file name
set(SHORT_PACKAGE_NAME "LLVM-ET-Arm")

# Set package name and version.
if(DEFINED LLVM_TOOLCHAIN_PACKAGE_NAME)
    set(PACKAGE_NAME ${LLVM_TOOLCHAIN_PACKAGE_NAME})
else()
    set(PACKAGE_NAME ${SHORT_PACKAGE_NAME})
endif()
set(CPACK_PACKAGE_NAME ${PACKAGE_NAME})
set(PACKAGE_VERSION "${LLVM_VERSION_MAJOR}.${LLVM_VERSION_MINOR}.${LLVM_VERSION_PATCH}")
if(DEFINED LLVM_TOOLCHAIN_VERSION_SUFFIX)
    set(PACKAGE_VERSION "${PACKAGE_VERSION}-${LLVM_TOOLCHAIN_VERSION_SUFFIX}")
endif()

# Restrict which LLVM components are installed.
if(LLVM_TOOLCHAIN_LIBRARY_OVERLAY_INSTALL)
    set(CPACK_COMPONENTS_ALL
        llvm-toolchain-libs
        llvm-toolchain-${LLVM_TOOLCHAIN_C_LIBRARY}-configs
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
# Exception: the overlay packages do not do this, because they have
# to be able to unpack over the top of an existing installation on all
# platforms, and each platform has a different top-level directory name.
if(LLVM_TOOLCHAIN_LIBRARY_OVERLAY_INSTALL)
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

set(CPACK_PACKAGE_VERSION ${PACKAGE_VERSION})

if(LLVM_TOOLCHAIN_LIBRARY_OVERLAY_INSTALL)
    set(PACKAGE_FILE_NAME ${PACKAGE_NAME}-${LLVM_TOOLCHAIN_C_LIBRARY}-overlay-${PACKAGE_VERSION})
else()
    set(PACKAGE_FILE_NAME ${PACKAGE_NAME}-${PACKAGE_VERSION}-${CPACK_SYSTEM_NAME})
endif()
set(CPACK_PACKAGE_FILE_NAME ${PACKAGE_FILE_NAME})

# Including CPack again after llvm CMakeLists.txt included it
# resets CPACK_PACKAGE_VERSION to the default MAJOR.MINOR.PATCH format.
include(CPack)

# Ensure LLVM tool symlinks are installed.
list(APPEND CMAKE_MODULE_PATH ${llvmproject_SOURCE_DIR}/llvm/cmake/modules)
llvm_install_symlink(LLVM llvm-ranlib llvm-ar ALWAYS_GENERATE)
llvm_install_symlink(LLVM llvm-readelf llvm-readobj ALWAYS_GENERATE)
llvm_install_symlink(LLVM llvm-strip llvm-objcopy ALWAYS_GENERATE)

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
    # at most one of picolibc and newlib source dirs is needed, but easiest to
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

# Set LLVM_DEFAULT_EXTERNAL_LIT to the directory of clang
# which was build in previous step. This path is not exported
# by add_subdirectory of llvm project
set(LLVM_DEFAULT_EXTERNAL_LIT "${LLVM_BINARY_DIR}/bin/llvm-lit")

add_custom_target(check-llvm-toolchain-runtimes)
add_custom_target(check-${LLVM_TOOLCHAIN_C_LIBRARY})
add_custom_target(check-compiler-rt)
add_custom_target(check-cxx)
add_custom_target(check-cxxabi)
add_custom_target(check-unwind)

if(NOT PREBUILT_TARGET_LIBRARIES)
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


    add_dependencies(
        check-llvm-toolchain-runtimes
        check-${LLVM_TOOLCHAIN_C_LIBRARY}
        check-compiler-rt
        check-cxx
        check-cxxabi
        check-unwind
    )

    if(LLVM_TOOLCHAIN_LIBRARY_OVERLAY_INSTALL)
        # If we're building a non-default libc with the intention of
        # installing it as an overlay on the main package archive, then
        # all of its includes, libraries and multilib.yaml go in a
        # subdirectory of lib/clang-runtimes. Configuration files in the
        # bin directory will make it easy to reset the sysroot to point at
        # that subdir.
        set(library_subdir "/${LLVM_TOOLCHAIN_C_LIBRARY}")
    else()
        set(library_subdir "")
    endif()

    if(LIBS_USE_COMPILER_LAUNCHER)
        if(CMAKE_C_COMPILER_LAUNCHER)
            list(APPEND compiler_launcher_cmake_args "-DCMAKE_C_COMPILER_LAUNCHER=${CMAKE_C_COMPILER_LAUNCHER}")
        endif()
        if(CMAKE_CXX_COMPILER_LAUNCHER)
            list(APPEND compiler_launcher_cmake_args "-DCMAKE_CXX_COMPILER_LAUNCHER=${CMAKE_CXX_COMPILER_LAUNCHER}")
        endif()
    endif()

    # ENABLE_VARIANTS expects a semi-colon separated list.
    # To prevent CMake expanding it automatically while passing it
    # down, switch to comma separated. Enabling the ExternalProject
    # LIST_SEPARATOR option will handle switching it back.
    string(REPLACE ";" "," ENABLE_VARIANTS_PASSTHROUGH "${LLVM_TOOLCHAIN_LIBRARY_VARIANTS}")

    ExternalProject_Add(
        multilib-${LLVM_TOOLCHAIN_C_LIBRARY}
        PREFIX ${CMAKE_BINARY_DIR}/multilib-builds
        SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/arm-multilib
        INSTALL_DIR ${CMAKE_CURRENT_BINARY_DIR}/llvm/${TARGET_LIBRARIES_DIR}${library_subdir}
        DEPENDS ${lib_tool_dependencies}
        CMAKE_ARGS
        ${compiler_launcher_cmake_args}
        -DC_LIBRARY=${LLVM_TOOLCHAIN_C_LIBRARY}
        -DLLVM_BINARY_DIR=${CMAKE_CURRENT_BINARY_DIR}/llvm
        -DMULTILIB_JSON=${LLVM_TOOLCHAIN_MULTILIB_JSON}
        -DENABLE_VARIANTS=${ENABLE_VARIANTS_PASSTHROUGH}
        -DLIBC_HDRGEN=${LIBC_HDRGEN}
        -DFVP_INSTALL_DIR=${FVP_INSTALL_DIR}
        -DENABLE_QEMU_TESTING=${ENABLE_QEMU_TESTING}
        -DENABLE_FVP_TESTING=${ENABLE_FVP_TESTING}
        -DFVP_CONFIG_DIR=${CMAKE_CURRENT_SOURCE_DIR}/fvp/config
        -DFETCHCONTENT_SOURCE_DIR_LLVMPROJECT=${FETCHCONTENT_SOURCE_DIR_LLVMPROJECT}
        -DFETCHCONTENT_SOURCE_DIR_PICOLIBC=${FETCHCONTENT_SOURCE_DIR_PICOLIBC}
        -DFETCHCONTENT_SOURCE_DIR_NEWLIB=${FETCHCONTENT_SOURCE_DIR_NEWLIB}
        -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
        USES_TERMINAL_CONFIGURE FALSE
        USES_TERMINAL_BUILD TRUE
        USES_TERMINAL_TEST TRUE
        LIST_SEPARATOR ,
        CONFIGURE_HANDLED_BY_BUILD TRUE
        TEST_EXCLUDE_FROM_MAIN TRUE
        STEP_TARGETS build install
    )

    add_dependencies(
        llvm-toolchain-runtimes
        multilib-${LLVM_TOOLCHAIN_C_LIBRARY}-install
    )

    foreach(check_target check-${LLVM_TOOLCHAIN_C_LIBRARY} check-compiler-rt check-cxx check-cxxabi check-unwind)
        ExternalProject_Add_Step(
            multilib-${LLVM_TOOLCHAIN_C_LIBRARY}
            ${check_target}
            COMMAND "${CMAKE_COMMAND}" --build <BINARY_DIR> --target ${check_target}
            USES_TERMINAL TRUE
            EXCLUDE_FROM_MAIN TRUE
            ALWAYS TRUE
        )
        ExternalProject_Add_StepTargets(multilib-${LLVM_TOOLCHAIN_C_LIBRARY} ${check_target})
        ExternalProject_Add_StepDependencies(
            multilib-${LLVM_TOOLCHAIN_C_LIBRARY}
            ${check_target}
            multilib-${LLVM_TOOLCHAIN_C_LIBRARY}-install
        )
        add_dependencies(${check_target} multilib-${LLVM_TOOLCHAIN_C_LIBRARY}-${check_target})
    endforeach()

    # Read the json to generate variant specific target names for convenience.
    file(READ ${LLVM_TOOLCHAIN_MULTILIB_JSON} multilib_json_str)
    string(JSON multilib_defs GET ${multilib_json_str} "libs")

    string(JSON lib_count LENGTH ${multilib_defs})
    math(EXPR lib_count_dec "${lib_count} - 1")

    foreach(lib_idx RANGE ${lib_count_dec})
        string(JSON lib_def GET ${multilib_defs} ${lib_idx})
        string(JSON variant GET ${lib_def} "variant")
        foreach(check_target check-${LLVM_TOOLCHAIN_C_LIBRARY} check-compiler-rt check-cxx check-cxxabi check-unwind)
            ExternalProject_Add_Step(
                multilib-${LLVM_TOOLCHAIN_C_LIBRARY}
                ${check_target}-${variant}
                COMMAND "${CMAKE_COMMAND}" --build <BINARY_DIR> --target ${check_target}-${variant}
                USES_TERMINAL TRUE
                EXCLUDE_FROM_MAIN TRUE
                ALWAYS TRUE
            )
            ExternalProject_Add_StepTargets(multilib-${LLVM_TOOLCHAIN_C_LIBRARY} ${check_target}-${variant})
            ExternalProject_Add_StepDependencies(
                multilib-${LLVM_TOOLCHAIN_C_LIBRARY}
                ${check_target}-${variant}
                multilib-${LLVM_TOOLCHAIN_C_LIBRARY}-install
            )
            add_custom_target(${check_target}-${variant})
            add_dependencies(${check_target}-${variant} multilib-${LLVM_TOOLCHAIN_C_LIBRARY}-${check_target}-${variant})
        endforeach()
    endforeach()
endif()

install(
    DIRECTORY ${LLVM_BINARY_DIR}/${TARGET_LIBRARIES_DIR}/.
    DESTINATION ${TARGET_LIBRARIES_DIR}
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

if(NOT LLVM_TOOLCHAIN_LIBRARY_OVERLAY_INSTALL)
    set(third_party_license_summary_install_dir .)
    set(third_party_license_files_install_dir third-party-licenses)
else()
    # If we're building an overlay archive, put all the license files
    # one level down in third-party-licenses/<library type>, so that
    # COPYING.NEWLIB doesn't collide with the file of the same name
    # from picolibc, and the LLVM license files are also duplicated
    # (in case the overlay archive is used with a non-matching version
    # of the main toolchain).
    set(third_party_license_summary_install_dir third-party-licenses/${LLVM_TOOLCHAIN_C_LIBRARY})
    set(third_party_license_files_install_dir third-party-licenses/${LLVM_TOOLCHAIN_C_LIBRARY})
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
if(LLVM_TOOLCHAIN_C_LIBRARY STREQUAL llvmlibc)
    list(APPEND third_party_license_files
        ${llvmproject_SOURCE_DIR}/libc/LICENSE.TXT      LIBC-LICENSE.TXT
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
if(LLVM_TOOLCHAIN_CROSS_BUILD_MINGW)
    list(APPEND LLVM_TOOLCHAIN_DISTRIBUTION_COMPONENTS llvm-toolchain-mingw)
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
        AND NOT LLVM_TOOLCHAIN_LIBRARY_OVERLAY_INSTALL)
    set(cpack_generator DragNDrop)
    set(package_filename_extension ".dmg")
else()
    set(cpack_generator TXZ)
    set(package_filename_extension ".tar.xz")
endif()
set(package_filepath ${CMAKE_BINARY_DIR}/${PACKAGE_FILE_NAME}${package_filename_extension})
set(unpack_directory ${CMAKE_CURRENT_BINARY_DIR}/unpack/${PACKAGE_FILE_NAME})
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

add_custom_target(check-all-llvm-toolchain)

add_dependencies(
    check-all-llvm-toolchain
    check-all
    check-llvm-toolchain
    check-llvm-toolchain-runtimes
)
