#
# Copyright (c) 2024, Arm Limited and affiliates.
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

# CMake build for a multilib layout of library variants, with each
# variant in a subdirectory and a multilib.yaml file to map flags to
# a variant.

cmake_minimum_required(VERSION 3.20)

project(arm-multilib)

# Root directory of the repo.
set(TOOLCHAIN_SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/..)

# Cache variables to be set by user
set(MULTILIB_JSON "" CACHE STRING "JSON file to load library definitions from.")
set(ENABLE_VARIANTS "all" CACHE STRING "Semicolon separated list of variants to build, or \"all\". Must match entries in the json.")
set(C_LIBRARY "picolibc" CACHE STRING "Which C library to use.")
set_property(CACHE C_LIBRARY PROPERTY STRINGS picolibc newlib llvmlibc)
set(LLVM_BINARY_DIR "" CACHE PATH "Path to LLVM toolchain build or install root.")
set(LIBC_HDRGEN "" CACHE PATH "Path to prebuilt lbc-hdrgen if not included in LLVM binaries set by LLVM_BINARY_DIR")
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
    "" CACHE STRING
    "The directory in which the FVP models are installed. These are not
    included in this repository, but can be downloaded by the script
    fvp/get_fvps.sh"
)
set(FVP_CONFIG_DIR "${TOOLCHAIN_SOURCE_DIR}/fvp/config" CACHE STRING "The directory in which the FVP models are installed.")
option(
    ENABLE_PARALLEL_LIB_CONFIG
    "Run the library variant configuration steps in parallel."
    ON
)
option(
    ENABLE_PARALLEL_LIB_BUILD
    "Run the library variant build steps in parallel."
    OFF
)
set(PARALLEL_LIB_BUILD_LEVELS
    "1" CACHE STRING
    "If ENABLE_PARALLEL_LIB_BUILD is ON, this number of processes will be assigned to each variant built."
)
if(NOT CMAKE_GENERATOR MATCHES "Ninja")
    if (ENABLE_PARALLEL_LIB_CONFIG OR ENABLE_PARALLEL_LIB_BUILD)
        message(WARNING "Library build parallelization should only be enabled with the Ninja generator.")
    endif()
endif()

# If a compiler launcher such as ccache has been set, it should be
# passed down to each subproject build.
set(compiler_launcher_cmake_args "")
if(CMAKE_C_COMPILER_LAUNCHER)
    list(APPEND compiler_launcher_cmake_args "-DCMAKE_C_COMPILER_LAUNCHER=${CMAKE_C_COMPILER_LAUNCHER}")
endif()
if(CMAKE_CXX_COMPILER_LAUNCHER)
    list(APPEND compiler_launcher_cmake_args "-DCMAKE_CXX_COMPILER_LAUNCHER=${CMAKE_CXX_COMPILER_LAUNCHER}")
endif()

# Arguments to pass down to the library projects.
foreach(arg
    LLVM_BINARY_DIR
    LIBC_HDRGEN
    FVP_INSTALL_DIR
    FVP_CONFIG_DIR
)
    if(${arg})
        list(APPEND passthrough_dirs "-D${arg}=${${arg}}")
    endif()
endforeach()

find_package(Python3 REQUIRED COMPONENTS Interpreter) # needed by fetch_*.cmake

include(ExternalProject)
include(${TOOLCHAIN_SOURCE_DIR}/cmake/fetch_llvm.cmake)
list(APPEND passthrough_dirs "-DFETCHCONTENT_SOURCE_DIR_LLVMPROJECT=${FETCHCONTENT_SOURCE_DIR_LLVMPROJECT}")
if(C_LIBRARY STREQUAL picolibc)
    include(${TOOLCHAIN_SOURCE_DIR}/cmake/fetch_picolibc.cmake)
    list(APPEND passthrough_dirs "-DFETCHCONTENT_SOURCE_DIR_PICOLIBC=${FETCHCONTENT_SOURCE_DIR_PICOLIBC}")
elseif(C_LIBRARY STREQUAL newlib)
    include(${TOOLCHAIN_SOURCE_DIR}/cmake/fetch_newlib.cmake)
    list(APPEND passthrough_dirs "-DFETCHCONTENT_SOURCE_DIR_NEWLIB=${FETCHCONTENT_SOURCE_DIR_NEWLIB}")
endif()

# Target for any dependencies to build the runtimes project.
add_custom_target(runtimes-depends)

# If building llvm-libc, ensure libc-hdrgen is available.
if(C_LIBRARY STREQUAL llvmlibc)
    if(NOT LIBC_HDRGEN)
        if(EXISTS ${LLVM_BINARY_DIR}/bin/libc-hdrgen${CMAKE_EXECUTABLE_SUFFIX})
            set(LIBC_HDRGEN ${LLVM_BINARY_DIR}/bin/libc-hdrgen${CMAKE_EXECUTABLE_SUFFIX})
        else()
            ExternalProject_Add(
                libc_hdrgen
                SOURCE_DIR ${llvmproject_SOURCE_DIR}/llvm
                CMAKE_ARGS
                    -DLLVM_ENABLE_RUNTIMES=libc
                    -DLLVM_LIBC_FULL_BUILD=ON
                    -DCMAKE_BUILD_TYPE=Debug
                BUILD_COMMAND ${CMAKE_COMMAND} --build . --target libc-hdrgen
                INSTALL_COMMAND ${CMAKE_COMMAND} -E true
                CONFIGURE_HANDLED_BY_BUILD TRUE
            )
            ExternalProject_Get_property(libc_hdrgen BINARY_DIR)
            set(LIBC_HDRGEN ${BINARY_DIR}/bin/libc-hdrgen${CMAKE_EXECUTABLE_SUFFIX})
            add_dependencies(runtimes-depends libc_hdrgen)
        endif()
    endif()
    list(APPEND passthrough_dirs "-DLIBC_HDRGEN=${LIBC_HDRGEN}")
endif()

# Create one target to run all the tests.
add_custom_target(check-${C_LIBRARY})
add_custom_target(check-compiler-rt)
add_custom_target(check-cxx)
add_custom_target(check-cxxabi)
add_custom_target(check-unwind)

add_custom_target(check-all)
add_dependencies(
    check-all
    check-${C_LIBRARY}
    check-compiler-rt
    check-cxx
    check-cxxabi
    check-unwind
)

if(ENABLE_PARALLEL_LIB_CONFIG OR ENABLE_PARALLEL_LIB_BUILD)
    # Additional targets to build the variant subprojects in parallel.
    # The build steps can use multible jobs to compile in parallel, but
    # the configuration steps are largely single threaded. This creates a
    # bottleneck if each variant is built in series.
    # It is significantly faster to run all the subproject configuration
    # steps in parallel, run the build steps, then run the next set of
    # configuration steps in parallel, etc.
    set(
        subtargets
        compiler_rt-configure
        compiler_rt-build
        clib-configure
        clib-build
        cxxlibs-configure
        cxxlibs-build
    )
    set(subtarget_deps none ${subtargets})
    list(REMOVE_AT subtarget_deps 6)

    foreach(subtarget subtarget_dep IN ZIP_LISTS subtargets subtarget_deps)
        add_custom_target(${subtarget}-all)
        if(NOT subtarget_dep STREQUAL "none")
            add_dependencies(${subtarget}-all ${subtarget_dep}-all)
        endif()
    endforeach()
endif()

# Read the JSON file to load a multilib configuration.
file(READ ${MULTILIB_JSON} multilib_json_str)
string(JSON multilib_defs GET ${multilib_json_str} "libs")

string(JSON lib_count LENGTH ${multilib_defs})
math(EXPR lib_count_dec "${lib_count} - 1")

foreach(lib_idx RANGE ${lib_count_dec})
    string(JSON lib_def GET ${multilib_defs} ${lib_idx})
    string(JSON variant GET ${lib_def} "variant")
    set(additional_cmake_args "")

    # If a variant doesn't support all possible C library
    # options, check if it should be skipped.
    string(JSON variant_support ERROR_VARIABLE json_error GET ${lib_def} "libraries_supported")
    if(NOT variant_support STREQUAL "libraries_supported-NOTFOUND")
        # Replace colons with semi-colons so CMake comprehends the list.
        string(REPLACE "," ";" variant_support ${variant_support})
        if(NOT C_LIBRARY IN_LIST variant_support)
            continue()
        endif()
    endif()

    if(variant IN_LIST ENABLE_VARIANTS OR ENABLE_VARIANTS STREQUAL "all")
        string(JSON variant_multilib_flags GET ${lib_def} "flags")
        # Placeholder libraries won't have a json, so store the error in
        # a variable so a fatal error isn't generated.
        string(JSON variant_json ERROR_VARIABLE json_error GET ${lib_def} "json")

        if(NOT variant_json STREQUAL "json-NOTFOUND")
            # Sort by target triple
            if(variant MATCHES "^aarch64")
                set(parent_dir_name aarch64-none-elf)
            else()
                set(parent_dir_name arm-none-eabi)
            endif()
            set(destination_directory "${CMAKE_CURRENT_BINARY_DIR}/multilib/${parent_dir_name}/${variant}")
            install(
                DIRECTORY ${destination_directory}
                DESTINATION ${parent_dir_name}
            )
            set(variant_json_file ${CMAKE_CURRENT_SOURCE_DIR}/json/variants/${variant_json})

            # Read info from the variant specific json.
            file(READ ${variant_json_file} variant_json_str)
            string(JSON test_executor GET ${variant_json_str} "args" "common" "TEST_EXECUTOR")

            # The multilib project can be configured to disable QEMU and/or FVP
            # testing, which will need to override the settings from the json.
            if((test_executor STREQUAL "qemu" AND NOT ${ENABLE_QEMU_TESTING}) OR (test_executor STREQUAL "fvp" AND NOT ${ENABLE_FVP_TESTING}))
                list(APPEND additional_cmake_args "-DENABLE_LIBC_TESTS=OFF" "-DENABLE_COMPILER_RT_TESTS=OFF" "-DENABLE_LIBCXX_TESTS=OFF")
                set(read_ENABLE_LIBC_TESTS "OFF")
                set(read_ENABLE_COMPILER_RT_TESTS "OFF")
                set(read_ENABLE_LIBCXX_TESTS "OFF")
            else()
                # From the json, check which tests are enabled.
                foreach(test_enable_var
                    ENABLE_LIBC_TESTS
                    ENABLE_COMPILER_RT_TESTS
                    ENABLE_LIBCXX_TESTS
                )
                    string(JSON read_${test_enable_var} ERROR_VARIABLE json_error GET ${variant_json_str} "args" ${C_LIBRARY} ${test_enable_var})
                    if(read_${test_enable_var} STREQUAL "json-NOTFOUND")
                        string(JSON read_${test_enable_var} ERROR_VARIABLE json_error GET ${variant_json_str} "args" "common" ${test_enable_var})
                        if(read_${test_enable_var} STREQUAL "json-NOTFOUND")
                            set(read_${test_enable_var} "OFF")
                        endif()
                    endif()
                endforeach()
            endif()

            ExternalProject_Add(
                runtimes-${variant}
                PREFIX ${CMAKE_BINARY_DIR}/lib-builds
                SOURCE_DIR ${TOOLCHAIN_SOURCE_DIR}/arm-runtimes
                INSTALL_DIR ${destination_directory}
                DEPENDS runtimes-depends
                CMAKE_ARGS
                ${compiler_launcher_cmake_args}
                ${passthrough_dirs}
                ${additional_cmake_args}
                -DVARIANT_JSON=${variant_json_file}
                -DC_LIBRARY=${C_LIBRARY}
                -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
                STEP_TARGETS build install
                USES_TERMINAL_CONFIGURE FALSE
                USES_TERMINAL_BUILD TRUE
                LIST_SEPARATOR ,
                CONFIGURE_HANDLED_BY_BUILD TRUE
                TEST_EXCLUDE_FROM_MAIN TRUE
            )

            if(ENABLE_PARALLEL_LIB_CONFIG OR ENABLE_PARALLEL_LIB_BUILD)
                # Create additional steps to configure/build the subprojects.
                # These are collected to be run together, so that all the
                # configuration steps can be run in parallel.
                # Each step should depend on the previous, with the first depending on the pre-defined
                # 'configure' step, and the pre-defined 'build' step depending on the last.
                set(subtarget_deps configure ${subtargets} build)
                list(SUBLIST subtarget_deps 0 6 subtarget_dependees)
                list(SUBLIST subtarget_deps 2 6 subtarget_dependers)

                # First loop to add the steps and targets.
                foreach(subtarget subtarget_dependee IN ZIP_LISTS subtargets subtarget_dependees)
                    # Enabling USES_TERMINAL puts the step in Ninja's "console" job pool, which
                    # prevents the steps from being run in parallel since each must be given
                    # exclusive access to the terminal. When disabled, the console won't be updated
                    # with any output from the step until it completes.
                    set(step_uses_terminal ON)
                    set(step_extra_env "")
                    if(${subtarget} MATCHES "-configure$" AND ENABLE_PARALLEL_LIB_CONFIG)
                        set(step_uses_terminal OFF)
                    elseif(${subtarget} MATCHES "-build$" AND ENABLE_PARALLEL_LIB_BUILD)
                        set(step_uses_terminal OFF)
                        set(step_extra_env ${CMAKE_COMMAND} -E env CMAKE_BUILD_PARALLEL_LEVEL=${PARALLEL_LIB_BUILD_LEVELS})
                    endif()
                    ExternalProject_Add_Step(
                        runtimes-${variant}
                        ${subtarget}
                        COMMAND ${step_extra_env} ${CMAKE_COMMAND} --build <BINARY_DIR> --target ${subtarget}
                        DEPENDEES ${subtarget_dependee}
                        DEPENDERS build
                        USES_TERMINAL ${step_uses_terminal}
                    )
                    ExternalProject_Add_StepTargets(runtimes-${variant} ${subtarget})
                    add_dependencies(${subtarget}-all runtimes-${variant}-${subtarget})
                endforeach()

                # Second loop to set the steps that will depend on the new targets.
                foreach(subtarget subtarget_depender IN ZIP_LISTS subtargets subtarget_dependers)
                    ExternalProject_Add_StepDependencies(
                        runtimes-${variant}
                        ${subtarget_depender}
                        ${subtarget}-all
                    )
                endforeach()
            endif()

            # Add custom check targets.
            set(check_targets "")
            if(read_ENABLE_LIBC_TESTS)
                list(APPEND check_targets check-${C_LIBRARY})
            endif()
            if(read_ENABLE_COMPILER_RT_TESTS)
                list(APPEND check_targets check-compiler-rt)
            endif()
            if(read_ENABLE_LIBCXX_TESTS)
                list(APPEND check_targets check-cxx)
                list(APPEND check_targets check-cxxabi)
                list(APPEND check_targets check-unwind)
            endif()
            foreach(check_target ${check_targets})
                ExternalProject_Add_Step(
                    runtimes-${variant}
                    ${check_target}
                    COMMAND "${CMAKE_COMMAND}" --build <BINARY_DIR> --target ${check_target}
                    USES_TERMINAL TRUE
                    EXCLUDE_FROM_MAIN TRUE
                    ALWAYS TRUE
                )
                ExternalProject_Add_StepTargets(runtimes-${variant} ${check_target})
                ExternalProject_Add_StepDependencies(
                    runtimes-${variant}
                    ${check_target}
                    runtimes-${variant}-build
                )
                add_custom_target(${check_target}-${variant})
                add_dependencies(${check_target} runtimes-${variant}-${check_target})
                add_dependencies(${check_target}-${variant} runtimes-${variant}-${check_target})
            endforeach()

            # Add the variant to the multilib yaml
            string(APPEND multilib_yaml_content "- Dir: ${parent_dir_name}/${variant}\n")
            string(APPEND multilib_yaml_content "  Flags:\n")
            string(REPLACE " " ";" multilib_flags_list ${variant_multilib_flags})
            foreach(flag ${multilib_flags_list})
                string(APPEND multilib_yaml_content "  - ${flag}\n")
            endforeach()
            string(APPEND multilib_yaml_content "  Group: stdlibs\n")
        else()
            # In place of a json, an error message is expected.
            string(JSON variant_error_msg GET ${lib_def} "error")

            string(APPEND multilib_yaml_content "- Error: \"${variant_error_msg}\"\n")
            string(APPEND multilib_yaml_content "  Flags:\n")
            string(REPLACE " " ";" multilib_flags_list ${variant_multilib_flags})
            foreach(flag ${multilib_flags_list})
                string(APPEND multilib_yaml_content "  - ${flag}\n")
            endforeach()
            string(APPEND multilib_yaml_content "  Group: stdlibs\n")
        endif()
    endif()

endforeach()

# Multilib file is generated in two parts.
# 1. Template is filled with multilib flags from json
configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/multilib.yaml.in
    ${CMAKE_CURRENT_BINARY_DIR}/multilib-without-fpus.yaml
    @ONLY
)

# 2. multilib-generate.py maps compiler command line options to flags
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/multilib-fpus.yaml
    COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/multilib-generate.py"
        "--clang=${LLVM_BINARY_DIR}/bin/clang${CMAKE_EXECUTABLE_SUFFIX}"
        "--llvm-source=${FETCHCONTENT_SOURCE_DIR_LLVMPROJECT}"
    >> ${CMAKE_CURRENT_BINARY_DIR}/multilib-fpus.yaml
)

# Combine the two parts.
add_custom_command(
    OUTPUT
        ${CMAKE_CURRENT_BINARY_DIR}/multilib/multilib.yaml
    COMMAND
        ${CMAKE_COMMAND} -E cat
        ${CMAKE_CURRENT_BINARY_DIR}/multilib-without-fpus.yaml
        ${CMAKE_CURRENT_BINARY_DIR}/multilib-fpus.yaml
        > ${CMAKE_CURRENT_BINARY_DIR}/multilib/multilib.yaml
    DEPENDS
        ${CMAKE_CURRENT_BINARY_DIR}/multilib-without-fpus.yaml
        ${CMAKE_CURRENT_BINARY_DIR}/multilib-fpus.yaml
)

add_custom_target(multilib-yaml ALL DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/multilib/multilib.yaml)
install(
    FILES ${CMAKE_CURRENT_BINARY_DIR}/multilib/multilib.yaml
    DESTINATION .
)
