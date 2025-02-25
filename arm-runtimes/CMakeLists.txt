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

# CMake build for a library variant, combining a chosen C library
# with builtins from compiler-rt and libcx/libcxxabi/libunwind

cmake_minimum_required(VERSION 3.20)

project(arm-runtimes)

# Root directory of the repo.
set(TOOLCHAIN_SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/..)

# CMake arguments are loaded from the JSON file depending on which C
# library is used, so this must be set before the JSON is processed.
set(C_LIBRARY "picolibc" CACHE STRING "Which C library to use.")
set_property(CACHE C_LIBRARY PROPERTY STRINGS picolibc newlib llvmlibc)

set(VARIANT_JSON "" CACHE STRING "JSON file to load args from.")
if(VARIANT_JSON)
    file(READ ${VARIANT_JSON} variant_json_read)
    # Load arguments common to all libraries.
    string(JSON json_args GET ${variant_json_read} "args" "common")
    string(JSON json_args_len LENGTH ${json_args})
    math(EXPR json_args_len_dec "${json_args_len} - 1")
    foreach(json_idx RANGE ${json_args_len_dec})
        string(JSON json_param MEMBER ${json_args} ${json_idx})
        string(JSON json_val GET ${json_args} ${json_param})
        string(JSON json_val_type TYPE ${json_args} ${json_param})
        set(${json_param}_def ${json_val})
    endforeach()
    # Load arguments specific to the chosen library, overwriting any existing values.
    string(JSON json_args GET ${variant_json_read} "args" ${C_LIBRARY})
    string(JSON json_args_len LENGTH ${json_args})
    math(EXPR json_args_len_dec "${json_args_len} - 1")
    foreach(json_idx RANGE ${json_args_len_dec})
        string(JSON json_param MEMBER ${json_args} ${json_idx})
        string(JSON json_val GET ${json_args} ${json_param})
        string(JSON json_val_type TYPE ${json_args} ${json_param})
        set(${json_param}_def ${json_val})
    endforeach()
endif()

# Default values will be populated by the json above.
# Any user specified options will override the default.
set(TARGET_ARCH ${TARGET_ARCH_def} CACHE STRING "Architecture being targetted.")
set(VARIANT ${VARIANT_def} CACHE STRING "Name for the variant, usually architecture + suffix.")
set(COMPILE_FLAGS ${COMPILE_FLAGS_def} CACHE STRING "Flags required to build the variant.")
set(TEST_EXECUTOR ${TEST_EXECUTOR_def} CACHE STRING "Program used to run tests.")
set_property(CACHE TEST_EXECUTOR PROPERTY STRINGS fvp qemu)
set(FVP_MODEL ${FVP_MODEL_def} CACHE STRING "FVP model to use, if FVP is the test executor.")
set(FVP_CONFIG ${FVP_CONFIG_def} CACHE STRING "FVP config to use, if FVP is the test executor.")
set(
    FVP_INSTALL_DIR
    "" CACHE STRING
    "The directory in which the FVP models are installed. These are not
    included in this repository, but can be downloaded by the script
    fvp/get_fvps.sh"
)
set(FVP_CONFIG_DIR "${TOOLCHAIN_SOURCE_DIR}/fvp/config" CACHE STRING "The directory in which the FVP models are installed.")

set(QEMU_MACHINE ${QEMU_MACHINE_def} CACHE STRING "Machine for QEMU to emulate.")
set(QEMU_CPU ${QEMU_CPU_def} CACHE STRING "CPU for QEMU to emulate.")
set(QEMU_PARAMS ${QEMU_PARAMS_def} CACHE STRING "Any additional parameters to pass to QEMU.")

set(BOOT_FLASH_ADDRESS ${BOOT_FLASH_ADDRESS_def} CACHE STRING "")
set(BOOT_FLASH_SIZE ${BOOT_FLASH_SIZE_def} CACHE STRING "")
set(FLASH_ADDRESS ${FLASH_ADDRESS_def} CACHE STRING "")
set(FLASH_SIZE ${FLASH_SIZE_def} CACHE STRING "")
set(RAM_ADDRESS ${RAM_ADDRESS_def} CACHE STRING "")
set(RAM_SIZE ${RAM_SIZE_def} CACHE STRING "")
set(STACK_SIZE ${STACK_SIZE_def} CACHE STRING "")

set(ENABLE_EXCEPTIONS ${ENABLE_EXCEPTIONS_def} CACHE BOOL "Enable C++ exceptions.")
set(ENABLE_RTTI ${ENABLE_RTTI_def} CACHE BOOL "Enable C++ exceptions.")

set(PICOLIBC_BUILD_TYPE ${PICOLIBC_BUILD_TYPE_def} CACHE STRING "Picolibc configuration to use.")
set_property(CACHE PICOLIBC_BUILD_TYPE PROPERTY STRINGS minsize release)

set(ENABLE_CXX_LIBS ${ENABLE_CXX_LIBS_def} CACHE BOOL "Build CXX libs")
set(ENABLE_LIBC_TESTS ${ENABLE_LIBC_TESTS_def} CACHE BOOL "Enable libc tests (picolibc, newlib or llvm-libc).")
set(ENABLE_COMPILER_RT_TESTS ${ENABLE_COMPILER_RT_TESTS_def} CACHE BOOL "Enable compiler-rt tests.")
set(ENABLE_LIBCXX_TESTS ${ENABLE_LIBCXX_TESTS_def} CACHE BOOL "Enable libcxx tests.")
set(LLVM_BINARY_DIR "" CACHE PATH "Path to LLVM toolchain root to build libraries with")

# Temporary location to collect the libraries as they are built.
set(TEMP_LIB_DIR "${CMAKE_CURRENT_BINARY_DIR}/tmp_install")

find_package(Python3 REQUIRED COMPONENTS Interpreter)

include(ExternalProject)
include(${TOOLCHAIN_SOURCE_DIR}/cmake/fetch_llvm.cmake)

# If a compiler launcher such as ccache has been set, it should be
# passed down to each subproject build.
set(compiler_launcher_cmake_args "")
if(CMAKE_C_COMPILER_LAUNCHER)
    list(APPEND compiler_launcher_cmake_args "-DCMAKE_C_COMPILER_LAUNCHER=${CMAKE_C_COMPILER_LAUNCHER}")
endif()
if(CMAKE_CXX_COMPILER_LAUNCHER)
    list(APPEND compiler_launcher_cmake_args "-DCMAKE_CXX_COMPILER_LAUNCHER=${CMAKE_CXX_COMPILER_LAUNCHER}")
endif()

if(TARGET_ARCH MATCHES "^aarch64")
    set(target_triple "aarch64-none-elf")
    set(cpu_family aarch64)
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
    if(TARGET_ARCH MATCHES "^armv[4-6]")
        set(target_triple "${TARGET_ARCH}-none-eabi")
    else()
        set(target_triple "arm-none-eabi")
    endif()
    if(COMPILE_FLAGS MATCHES "-mfloat-abi=hard")
        # Also, compiler-rt looks in the ABI component of the
        # triple to decide whether to use the hard float ABI.
        set(target_triple "${target_triple}hf")
    endif()
    set(cpu_family arm)
endif()

# Create a single target for all testing. If no testing is enabled, this
# will simply do nothing.
add_custom_target(check-all)

# If any testing is enabled, prepare test executor settings.
if(ENABLE_LIBC_TESTS OR ENABLE_COMPILER_RT_TESTS OR ENABLE_LIBCXX_TESTS)
    # Flags required to link tests.
    if(C_LIBRARY STREQUAL picolibc)
        set(test_link_flags "-nostartfiles -lcrt0-semihost -lsemihost -T picolibcpp.ld")
    else()
        message(FATAL_ERROR "Tests can only be enabled using picolibc.")
    endif()

    if(TEST_EXECUTOR STREQUAL qemu)
        if(TARGET_ARCH MATCHES "^aarch64")
            find_program(QEMU_EXECUTABLE qemu-system-aarch64 REQUIRED)
        else()
            find_program(QEMU_EXECUTABLE qemu-system-arm REQUIRED)
        endif()

        # Use colon as a separator because comma and semicolon are used for
        # other purposes in CMake.
        string(REPLACE " " ":" qemu_params_list "${QEMU_PARAMS}")

        set(test_executor_params --qemu-command ${QEMU_EXECUTABLE} --qemu-machine ${QEMU_MACHINE})
        if(QEMU_CPU)
            list(APPEND test_executor_params --qemu-cpu ${QEMU_CPU})
        endif()
        if(qemu_params_list)
            list(APPEND test_executor_params "--qemu-params=${qemu_params_list}")
        endif()
        set(
            lit_test_executor
            ${CMAKE_CURRENT_SOURCE_DIR}/test-support/lit-exec-qemu.py
            ${test_executor_params}
        )
    elseif(TEST_EXECUTOR STREQUAL fvp)
        if(NOT EXISTS "${FVP_INSTALL_DIR}")
            message(FATAL_ERROR "FVPs must be installed to run tests using FVPs.")
        endif()
        set(
            test_executor_params
            --fvp-install-dir ${FVP_INSTALL_DIR}
            --fvp-config-dir ${FVP_CONFIG_DIR}
            --fvp-model ${FVP_MODEL}
        )
        string(REPLACE " " ";" fvp_config_list ${FVP_CONFIG})
        foreach(cfg ${fvp_config_list})
            set(
                test_executor_params
                ${test_executor_params}
                --fvp-config ${cfg}
            )
        endforeach()
        set(
            lit_test_executor
            ${CMAKE_CURRENT_SOURCE_DIR}/test-support/lit-exec-fvp.py
            ${test_executor_params}
        )
    endif()
    list(JOIN lit_test_executor " " lit_test_executor)
endif()

set(compile_arch_flags "--target=${target_triple} ${COMPILE_FLAGS}")
# Compiling the libraries benefits from some extra optimization
# flags, and requires a sysroot.
set(lib_compile_flags "${compile_arch_flags} -ffunction-sections -fdata-sections -fno-ident --sysroot ${TEMP_LIB_DIR}")

# Generic target names for the C library.
# Declare these now, since compiler-rt requires the 'install' dependency.
add_custom_target(clib-configure)
add_custom_target(clib-build)
add_custom_target(clib-install)

###############################################################################
# compiler-rt
###############################################################################

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
string(REPLACE "-none-" "-unknown-none-" normalized_target_triple ${target_triple})

# This prevents a test failure due to insufficient available registers.
# TODO: Which test, can this be fixed upstream?
if(VARIANT STREQUAL "armv6m_soft_nofp")
    set(compiler_rt_test_flags "${compiler_rt_test_flags} -fomit-frame-pointer")
endif()

if(ENABLE_COMPILER_RT_TESTS)
    set(compiler_rt_test_flags "${lib_compile_flags} ${test_link_flags}")
    set(compiler_rt_lit_args "${LLVM_LIT_ARGS} --xunit-xml-output=results.junit.xml")
    set(
        compiler_rt_test_cmake_args
        -DCOMPILER_RT_INCLUDE_TESTS=ON
        -DCOMPILER_RT_EMULATOR=${lit_test_executor}
        -DCOMPILER_RT_TEST_COMPILER=${LLVM_BINARY_DIR}/bin/clang
        -DCOMPILER_RT_TEST_COMPILER_CFLAGS=${compiler_rt_test_flags}
        -DLLVM_LIT_ARGS=${compiler_rt_lit_args}
    )
endif()

ExternalProject_Add(
    compiler_rt
    SOURCE_DIR ${llvmproject_SOURCE_DIR}/compiler-rt
    INSTALL_DIR compiler-rt/install
    CMAKE_ARGS
    ${compiler_launcher_cmake_args}
    -DCMAKE_AR=${LLVM_BINARY_DIR}/bin/llvm-ar${CMAKE_EXECUTABLE_SUFFIX}
    -DCMAKE_ASM_COMPILER_TARGET=${target_triple}
    -DCMAKE_ASM_FLAGS=${lib_compile_flags}
    -DCMAKE_BUILD_TYPE=Release
    -DCMAKE_CXX_COMPILER=${LLVM_BINARY_DIR}/bin/clang++${CMAKE_EXECUTABLE_SUFFIX}
    -DCMAKE_CXX_COMPILER_TARGET=${target_triple}
    -DCMAKE_CXX_FLAGS=${lib_compile_flags}
    -DCMAKE_C_COMPILER=${LLVM_BINARY_DIR}/bin/clang${CMAKE_EXECUTABLE_SUFFIX}
    -DCMAKE_C_COMPILER_TARGET=${target_triple}
    -DCMAKE_C_FLAGS=${lib_compile_flags}
    -DCMAKE_INSTALL_MESSAGE=${CMAKE_INSTALL_MESSAGE}
    -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
    -DCMAKE_NM=${LLVM_BINARY_DIR}/bin/llvm-nm${CMAKE_EXECUTABLE_SUFFIX}
    -DCMAKE_RANLIB=${LLVM_BINARY_DIR}/bin/llvm-ranlib${CMAKE_EXECUTABLE_SUFFIX}
    -DCMAKE_SYSTEM_NAME=Generic
    -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY
    -DCOMPILER_RT_BAREMETAL_BUILD=ON
    -DCOMPILER_RT_BUILD_LIBFUZZER=OFF
    -DCOMPILER_RT_BUILD_PROFILE=OFF
    -DCOMPILER_RT_BUILD_SANITIZERS=OFF
    -DCOMPILER_RT_BUILD_XRAY=OFF
    -DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON
    -DLLVM_CMAKE_DIR=${LLVM_BINARY_DIR}
    -DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=ON
    ${compiler_rt_test_cmake_args}
    STEP_TARGETS configure build install
    USES_TERMINAL_CONFIGURE TRUE
    USES_TERMINAL_BUILD TRUE
    USES_TERMINAL_INSTALL TRUE
    LIST_SEPARATOR ,
    CONFIGURE_HANDLED_BY_BUILD TRUE
    INSTALL_COMMAND ${CMAKE_COMMAND} --install .
    # Copy compiler-rt lib directory, moving libraries out of their
    # target-specific subdirectory.
    COMMAND
        ${CMAKE_COMMAND}
        -E copy_directory
        <INSTALL_DIR>/lib/${normalized_target_triple}
        "${TEMP_LIB_DIR}/lib"
)

add_custom_target(check-compiler-rt)
add_dependencies(check-all check-compiler-rt)
if(ENABLE_COMPILER_RT_TESTS)
    ExternalProject_Add_Step(
        compiler_rt
        check-compiler-rt
        COMMAND "${CMAKE_COMMAND}" --build <BINARY_DIR> --target check-compiler-rt
        COMMAND ${Python3_EXECUTABLE}
        ${CMAKE_CURRENT_SOURCE_DIR}/test-support/modify-compiler-rt-xml.py
        --dir <BINARY_DIR>
        --variant ${VARIANT}
        USES_TERMINAL TRUE
        EXCLUDE_FROM_MAIN TRUE
        ALWAYS TRUE
    )
    ExternalProject_Add_StepTargets(compiler_rt check-compiler-rt)
    ExternalProject_Add_StepDependencies(
        compiler_rt
        check-compiler-rt
        compiler_rt-build
        clib-install
    )
    add_dependencies(check-compiler-rt compiler_rt-check-compiler-rt)
endif()

###############################################################################
# picolibc
###############################################################################

if(C_LIBRARY STREQUAL picolibc)
    include(${TOOLCHAIN_SOURCE_DIR}/cmake/fetch_picolibc.cmake)
    include(${CMAKE_CURRENT_SOURCE_DIR}/to_meson_list.cmake)

    # For building picolibc use Meson.
    # Although picolibc has support for building with CMake, the Meson code
    # is more mature and works better with LLVM.
    find_program(MESON_EXECUTABLE meson REQUIRED)

    if(CMAKE_INSTALL_MESSAGE STREQUAL NEVER)
        set(MESON_INSTALL_QUIET "--quiet")
    endif()

    if(PICOLIBC_BUILD_TYPE MATCHES "minsize")
        set(newlib_nano_malloc "true")
    else()
        set(newlib_nano_malloc "false")
    endif()

    # TODO: xfail these tests instead of disabling.
    if(target_triple MATCHES "^aarch64")
        set(enable_picolibc_long_double_test false)
    else()
        set(enable_picolibc_long_double_test true)
    endif()

    # Set meson_c_args to a comma-separated list of the clang path
    # and flags e.g. 'path/to/clang', '--target=armv6m-none-eabi',
    # '-march=armv6m'
    set(picolibc_flags "${LLVM_BINARY_DIR}/bin/clang${CMAKE_EXECUTABLE_SUFFIX} ${lib_compile_flags}")
    if(CMAKE_C_COMPILER_LAUNCHER)
        set(picolibc_flags "${CMAKE_C_COMPILER_LAUNCHER} ${picolibc_flags}")
    endif()
    separate_arguments(picolibc_flags)
    to_meson_list("${picolibc_flags}" picolibc_meson_flags)

    if(ENABLE_LIBC_TESTS)
        set(picolibc_test_executor_bin ${CMAKE_CURRENT_SOURCE_DIR}/test-support/picolibc-test-wrapper.py)
        to_meson_list("${test_executor_params}" meson_test_executor_params)
    endif()

    configure_file(${CMAKE_CURRENT_SOURCE_DIR}/meson-cross-build.txt.in ${CMAKE_CURRENT_BINARY_DIR}/meson-cross-build.txt @ONLY)

    ExternalProject_Add(
        picolibc
        SOURCE_DIR ${picolibc_SOURCE_DIR}
        INSTALL_DIR ${TEMP_LIB_DIR}
        DEPENDS compiler_rt-install
        CONFIGURE_COMMAND
            ${MESON_EXECUTABLE}
            setup
            -Dincludedir=include
            -Dlibdir=lib
            -Dspecsdir=none
            -Dmultilib=false
            -Ddebug=false
            -Dtests-enable-stack-protector=false
            -Dtest-long-double=${enable_picolibc_long_double_test}
            -Dtest-machine=${TEST_EXECUTOR}
            -Dnewlib-nano-malloc=${newlib_nano_malloc}
            -Dtests=false
            --prefix <INSTALL_DIR>
            --cross-file ${CMAKE_CURRENT_BINARY_DIR}/meson-cross-build.txt
            --buildtype=${PICOLIBC_BUILD_TYPE}
            <SOURCE_DIR>
        BUILD_COMMAND ${MESON_EXECUTABLE} compile
        INSTALL_COMMAND ${MESON_EXECUTABLE} install ${MESON_INSTALL_QUIET}
        USES_TERMINAL_CONFIGURE TRUE
        USES_TERMINAL_BUILD TRUE
        USES_TERMINAL_INSTALL TRUE
        LIST_SEPARATOR ,
        CONFIGURE_HANDLED_BY_BUILD TRUE
        TEST_EXCLUDE_FROM_MAIN TRUE
        STEP_TARGETS configure build install
    )

    add_custom_target(check-picolibc)
    add_dependencies(check-all check-picolibc)
    if(ENABLE_LIBC_TESTS)
        # meson builds the tests at the same time as the library.
        # So reconfigure to enable tests at a later point.
        ExternalProject_Add_Step(
            picolibc
            enable-tests
            COMMAND ${MESON_EXECUTABLE} setup -Dtests=true --reconfigure <BINARY_DIR> <SOURCE_DIR>
            USES_TERMINAL TRUE
            EXCLUDE_FROM_MAIN TRUE
        )
        ExternalProject_Add_StepTargets(picolibc enable-tests)
        ExternalProject_Add_StepDependencies(
            picolibc
            enable-tests
            picolibc-build
            compiler_rt-install
        )
        ExternalProject_Add_Step(
            picolibc
            check
            COMMAND ${MESON_EXECUTABLE} test -C <BINARY_DIR>
            COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/test-support/modify-picolibc-xml.py
            --dir <BINARY_DIR>
            --variant ${VARIANT}
            USES_TERMINAL TRUE
            EXCLUDE_FROM_MAIN TRUE
            ALWAYS TRUE
        )
        ExternalProject_Add_StepTargets(picolibc check)
        ExternalProject_Add_StepDependencies(
            picolibc
            check
            picolibc-enable-tests
        )
        add_dependencies(check-picolibc picolibc-check)
    endif()

endif()

###############################################################################
# newlib
###############################################################################

if(C_LIBRARY STREQUAL newlib)
    if(ENABLE_LIBC_TESTS)
        message(FATAL_ERROR "Tests cannot yet be enabled using newlib libc.")
    endif()

    include(${TOOLCHAIN_SOURCE_DIR}/cmake/fetch_newlib.cmake)
    set(build_env
        "CC_FOR_TARGET=${LLVM_BINARY_DIR}/bin/clang -target ${target_triple} -ffreestanding"
        "CXX_FOR_TARGET=${LLVM_BINARY_DIR}/bin/clang++ -target ${target_triple} -ffreestanding"
        "AR_FOR_TARGET=${LLVM_BINARY_DIR}/bin/llvm-ar"
        "NM_FOR_TARGET=${LLVM_BINARY_DIR}/bin/llvm-nm"
        "OBJDUMP_FOR_TARGET=${LLVM_BINARY_DIR}/bin/llvm-objdump"
        "RANLIB_FOR_TARGET=${LLVM_BINARY_DIR}/bin/llvm-ranlib"
        "READELF_FOR_TARGET=${LLVM_BINARY_DIR}/bin/llvm-readelf"
        "STRIP_FOR_TARGET=${LLVM_BINARY_DIR}/bin/llvm-strip"
        "CFLAGS_FOR_TARGET=${flags} -Wno-error=implicit-function-declaration -D__USES_INITFINI__ -U_HAVE_INIT_FINI --sysroot ${TEMP_LIB_DIR}"
        "CCASFLAGS=${flags} -Wno-error=implicit-function-declaration -D__USES_INITFINI__ -U_HAVE_INIT_FINI --sysroot ${TEMP_LIB_DIR}"
    )

    include(ProcessorCount)
    set(make_flags)
    ProcessorCount(nproc)
    if(NOT nproc EQUAL 0)
        set(make_flags -j${nproc})
    endif()

    ExternalProject_Add(
        newlib
        SOURCE_DIR ${newlib_SOURCE_DIR}
        INSTALL_DIR ${TEMP_LIB_DIR}
        CONFIGURE_COMMAND
            ${CMAKE_COMMAND} -E env ${build_env}
            <SOURCE_DIR>/configure
            --target=${target_triple}
            --prefix "${TEMP_LIB_DIR}"
            --exec_prefix <BINARY_DIR>/tmpinstall
            --enable-newlib-io-long-long
            --enable-newlib-register-fini
            --disable-newlib-supplied-syscalls
            --enable-newlib-io-c99-formats
            --disable-nls
            --enable-lite-exit
            --disable-multilib
            --enable-newlib-retargetable-locking
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
            ${TEMP_LIB_DIR}
            &&
            ${CMAKE_COMMAND} -E copy
            <BINARY_DIR>/${target_triple}/libgloss/${cpu_family}/libcrt0-rdimon.a
            ${TEMP_LIB_DIR}/lib
            &&
            ${CMAKE_COMMAND} -E copy
            <BINARY_DIR>/${target_triple}/libgloss/${cpu_family}/libcrt0-nosys.a
            ${TEMP_LIB_DIR}/lib
        # FIXME: TEST_COMMAND?
        USES_TERMINAL_CONFIGURE TRUE
        USES_TERMINAL_BUILD TRUE
        USES_TERMINAL_INSTALL TRUE
        # Always run the build command so that incremental builds are correct.
        CONFIGURE_HANDLED_BY_BUILD TRUE
        TEST_EXCLUDE_FROM_MAIN TRUE
        STEP_TARGETS configure build install # FIXME: test?
    )
endif()

###############################################################################
# llvmlibc
###############################################################################

if(C_LIBRARY STREQUAL llvmlibc)
    if(ENABLE_LIBC_TESTS)
        message(FATAL_ERROR "Tests cannot yet be enabled using llvm libc.")
    endif()
    if(ENABLE_CXX_LIBS)
        message(FATAL_ERROR "We aren't yet able to build C++ libraries to go with llvm-libc.")
    endif()

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

    set(lib_compile_flags "${lib_compile_flags} -Wno-error=atomic-alignment")

    set(common_llvmlibc_cmake_args
        -DCMAKE_AR=${LLVM_BINARY_DIR}/bin/llvm-ar${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_ASM_COMPILER=${LLVM_BINARY_DIR}/bin/clang${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_ASM_COMPILER_TARGET=${target_triple}
        -DCMAKE_ASM_FLAGS=${lib_compile_flags}
        -DCMAKE_BUILD_TYPE=Release
        -DCMAKE_CXX_COMPILER=${LLVM_BINARY_DIR}/bin/clang++${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_CXX_COMPILER_TARGET=${target_triple}
        -DCMAKE_CXX_FLAGS=${lib_compile_flags}
        -DCMAKE_C_COMPILER=${LLVM_BINARY_DIR}/bin/clang${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_C_COMPILER_TARGET=${target_triple}
        -DCMAKE_C_FLAGS=${lib_compile_flags}
        -DCMAKE_INSTALL_MESSAGE=${CMAKE_INSTALL_MESSAGE}
        -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
        -DCMAKE_NM=${LLVM_BINARY_DIR}/bin/llvm-nm${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_RANLIB=${LLVM_BINARY_DIR}/bin/llvm-ranlib${CMAKE_EXECUTABLE_SUFFIX}
        # Let CMake know we're cross-compiling
        -DCMAKE_SYSTEM_NAME=Generic
        -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY
    )

    ExternalProject_Add(
        llvmlibc
        SOURCE_DIR ${llvmproject_SOURCE_DIR}/runtimes
        INSTALL_DIR llvmlibc/install
        CMAKE_ARGS
        ${compiler_launcher_cmake_args}
        ${common_llvmlibc_cmake_args}
        -DLIBC_TARGET_TRIPLE=${target_triple}
        -DLIBC_CONFIG_PATH=${LIBC_CFG_DIR}
        -DLIBC_CONF_TIME_64BIT=ON
        -DLLVM_CMAKE_DIR=${LLVM_BINARY_DIR}/lib/cmake/llvm
        -DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=ON
        -DLLVM_ENABLE_RUNTIMES=libc
        -DLLVM_INCLUDE_TESTS=OFF # llvmlibc's tests require C++, so can't be built until llvmlibc can support libc++
        -DLLVM_LIBC_FULL_BUILD=ON
        STEP_TARGETS configure build install
        USES_TERMINAL_CONFIGURE TRUE
        USES_TERMINAL_BUILD TRUE
        USES_TERMINAL_INSTALL TRUE
        LIST_SEPARATOR ,
        CONFIGURE_HANDLED_BY_BUILD TRUE
        INSTALL_COMMAND ${CMAKE_COMMAND} --install .
        # Copy llvm-libc lib directory, moving libraries out of their
        # target-specific subdirectory.
        COMMAND
            ${CMAKE_COMMAND}
            -E copy_directory
            <INSTALL_DIR>/lib/${target_triple}
            "${TEMP_LIB_DIR}/lib"
        # And copy the include directory, which is already arranged right.
        COMMAND
            ${CMAKE_COMMAND}
            -E copy_directory
            <INSTALL_DIR>/include
            "${TEMP_LIB_DIR}/include"
    )

    ExternalProject_Add(
        llvmlibc-support
        SOURCE_DIR ${TOOLCHAIN_SOURCE_DIR}/llvmlibc-support
        INSTALL_DIR ${TEMP_LIB_DIR}
        DEPENDS ${lib_tool_dependencies} llvmlibc-install
        CMAKE_ARGS
        ${compiler_launcher_cmake_args}
        ${common_llvmlibc_cmake_args}
        STEP_TARGETS build install
        USES_TERMINAL_CONFIGURE TRUE
        USES_TERMINAL_BUILD TRUE
        USES_TERMINAL_INSTALL TRUE
        USES_TERMINAL_TEST TRUE
        LIST_SEPARATOR ,
        CONFIGURE_HANDLED_BY_BUILD TRUE
    )
endif()

add_dependencies(clib-configure ${C_LIBRARY}-configure)
add_dependencies(clib-build ${C_LIBRARY}-build)
add_dependencies(clib-install ${C_LIBRARY}-install)

###############################################################################
# runtimes (libcxx, libcxxabi, libunwind)
###############################################################################

if(ENABLE_CXX_LIBS)
    if(C_LIBRARY STREQUAL picolibc)
        set(cxxlibs_extra_cmake_options
            -DLIBCXXABI_ENABLE_THREADS=OFF
            -DLIBCXX_ENABLE_MONOTONIC_CLOCK=OFF
            -DLIBCXX_ENABLE_RANDOM_DEVICE=OFF
            -DLIBCXX_ENABLE_THREADS=OFF
            -DLIBCXX_ENABLE_WIDE_CHARACTERS=OFF
            -DLIBUNWIND_ENABLE_THREADS=OFF
            -DLIBCXXABI_ENABLE_EXCEPTIONS=${ENABLE_EXCEPTIONS}
            -DLIBCXXABI_ENABLE_STATIC_UNWINDER=${ENABLE_EXCEPTIONS}
            -DLIBCXX_ENABLE_EXCEPTIONS=${ENABLE_EXCEPTIONS}
            -DLIBCXX_ENABLE_RTTI=${ENABLE_RTTI}
        )
        if(ENABLE_LIBCXX_TESTS)
            set(cxxlibs_lit_args "${LLVM_LIT_ARGS} --xunit-xml-output=results.junit.xml")
            set(cxxlibs_test_cmake_options
                -DLIBCXX_TEST_CONFIG=${CMAKE_CURRENT_SOURCE_DIR}/test-support/llvm-libc++-picolibc.cfg.in
                -DLIBCXX_TEST_PARAMS=executor=${lit_test_executor}
                -DLIBCXXABI_TEST_CONFIG=${CMAKE_CURRENT_SOURCE_DIR}/test-support/llvm-libc++abi-picolibc.cfg.in
                -DLIBCXXABI_TEST_PARAMS=executor=${lit_test_executor}
                -DLIBUNWIND_TEST_CONFIG=${CMAKE_CURRENT_SOURCE_DIR}/test-support/llvm-libunwind-picolibc.cfg.in
                -DLIBUNWIND_TEST_PARAMS=executor=${lit_test_executor}
                -DRUNTIME_TEST_ARCH_FLAGS=${compile_arch_flags}
                -DRUNTIME_TEST_LINK_FLAGS=${test_link_flags}
                -DLLVM_LIT_ARGS=${cxxlibs_lit_args}
            )
        endif()
    elseif(C_LIBRARY STREQUAL newlib)
        set(cxxlibs_extra_cmake_options
            -DLIBCXXABI_ENABLE_THREADS=OFF
            -DLIBCXX_ENABLE_THREADS=OFF
            -DLIBCXX_ENABLE_MONOTONIC_CLOCK=OFF
            -DLIBCXX_ENABLE_RANDOM_DEVICE=OFF
            -DLIBCXX_ENABLE_WIDE_CHARACTERS=ON
            -DLIBCXX_ENABLE_LOCALIZATION=OFF
            -DLIBUNWIND_ENABLE_THREADS=OFF
        )
    endif()

    ExternalProject_Add(
        cxxlibs
        SOURCE_DIR ${llvmproject_SOURCE_DIR}/runtimes
        INSTALL_DIR ${TEMP_LIB_DIR}
        DEPENDS compiler_rt-install clib-install
        CMAKE_ARGS
        ${compiler_launcher_cmake_args}
        -DCMAKE_AR=${LLVM_BINARY_DIR}/bin/llvm-ar${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_ASM_FLAGS=${lib_compile_flags}
        -DCMAKE_BUILD_TYPE=MinSizeRel
        -DCMAKE_CXX_COMPILER=${LLVM_BINARY_DIR}/bin/clang++${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_CXX_COMPILER_TARGET=${target_triple}
        -DCMAKE_CXX_FLAGS=${lib_compile_flags}
        -DCMAKE_C_COMPILER=${LLVM_BINARY_DIR}/bin/clang${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_C_COMPILER_TARGET=${target_triple}
        -DCMAKE_C_FLAGS=${lib_compile_flags}
        -DCMAKE_INSTALL_MESSAGE=${CMAKE_INSTALL_MESSAGE}
        -DCMAKE_INSTALL_PREFIX=${TEMP_LIB_DIR}
        -DCMAKE_NM=${LLVM_BINARY_DIR}/bin/llvm-nm${CMAKE_EXECUTABLE_SUFFIX}
        -DCMAKE_RANLIB=${LLVM_BINARY_DIR}/bin/llvm-ranlib${CMAKE_EXECUTABLE_SUFFIX}
        # Let CMake know we're cross-compiling
        -DCMAKE_SYSTEM_NAME=Generic
        -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY
        -DLIBCXXABI_BAREMETAL=ON
        -DLIBCXXABI_ENABLE_ASSERTIONS=OFF
        -DLIBCXXABI_ENABLE_SHARED=OFF
        -DLIBCXXABI_ENABLE_STATIC=ON
        -DLIBCXXABI_LIBCXX_INCLUDES="${TEMP_LIB_DIR}/include/c++/v1"
        -DLIBCXXABI_USE_COMPILER_RT=ON
        -DLIBCXXABI_USE_LLVM_UNWINDER=ON
        -DLIBCXXABI_SHARED_OUTPUT_NAME="c++abi-shared"
        -DLIBCXX_ABI_UNSTABLE=ON
        -DLIBCXX_CXX_ABI=libcxxabi
        -DLIBCXX_STATICALLY_LINK_ABI_IN_STATIC_LIBRARY=ON
        -DLIBCXX_ENABLE_FILESYSTEM=OFF
        -DLIBCXX_ENABLE_SHARED=OFF
        -DLIBCXX_ENABLE_STATIC=ON
        -DLIBCXX_INCLUDE_BENCHMARKS=OFF
        -DLIBCXX_SHARED_OUTPUT_NAME="c++-shared"
        -DLIBUNWIND_ENABLE_ASSERTIONS=OFF
        -DLIBUNWIND_ENABLE_SHARED=OFF
        -DLIBUNWIND_ENABLE_STATIC=ON
        -DLIBUNWIND_IS_BAREMETAL=ON
        -DLIBUNWIND_REMEMBER_HEAP_ALLOC=ON
        -DLIBUNWIND_USE_COMPILER_RT=ON
        -DLIBUNWIND_SHARED_OUTPUT_NAME="unwind-shared"
        -DLLVM_LIT_ARGS=${LLVM_LIT_ARGS}
        -DLLVM_ENABLE_RUNTIMES=libcxxabi,libcxx,libunwind
        -DRUNTIME_VARIANT_NAME=${VARIANT}
        ${cxxlibs_extra_cmake_options}
        ${cxxlibs_test_cmake_options}
        STEP_TARGETS configure build install
        USES_TERMINAL_CONFIGURE TRUE
        USES_TERMINAL_BUILD TRUE
        USES_TERMINAL_INSTALL TRUE
        LIST_SEPARATOR ,
        CONFIGURE_HANDLED_BY_BUILD TRUE
    )
    add_custom_target(check-cxx)
    add_dependencies(check-all check-cxx)
    add_custom_target(check-cxxabi)
    add_dependencies(check-all check-cxxabi)
    add_custom_target(check-unwind)
    add_dependencies(check-all check-unwind)
    if(ENABLE_LIBCXX_TESTS)
        foreach(check_target check-cxx check-cxxabi check-unwind)
            ExternalProject_Add_Step(
                cxxlibs
                ${check_target}
                COMMAND "${CMAKE_COMMAND}" --build <BINARY_DIR> --target ${check_target}
                USES_TERMINAL TRUE
                EXCLUDE_FROM_MAIN TRUE
                ALWAYS TRUE
            )
            ExternalProject_Add_StepTargets(cxxlibs ${check_target})
            ExternalProject_Add_StepDependencies(
                cxxlibs
                ${check_target}
                cxxlibs-install
            )
            add_dependencies(${check_target} cxxlibs-${check_target})
        endforeach()
    endif()

else() # if not ENABLE_CXX_LIBS

    # The parent arm-multilib cmake script will still want to invoke
    # build targets like 'cxxlibs-configure', whether we actually have
    # C++ libraries or not. So we should define them, even if they
    # don't do anything.
    add_custom_target(cxxlibs-configure)
    add_custom_target(cxxlibs-build)
endif()

install(
    DIRECTORY ${TEMP_LIB_DIR}/
    DESTINATION .
)
