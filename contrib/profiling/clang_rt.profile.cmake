# Configuration for libclang_rt.profile.a

function(add_contrib_lib_profile directory variant target_triple flags libc_target)
    get_runtimes_flags("${directory}" "${flags}")

    set(LIB_PROFILE compiler_rt_profile_${variant})
    
    ExternalProject_Add(
        ${LIB_PROFILE}
        SOURCE_DIR                 ${CMAKE_SOURCE_DIR}/contrib/profiling
        PREFIX                     compiler-rt-profile/${variant}
        INSTALL_DIR                compiler-rt-profile/${variant}
        DEPENDS                    clang lld llvm-ar llvm-config llvm-nm llvm-ranlib ${libc_target}
        CMAKE_ARGS                 -DCMAKE_AR=${LLVM_BINARY_DIR}/bin/llvm-ar${CMAKE_EXECUTABLE_SUFFIX}
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
                                   -DLLVM_LIT_ARGS=${LLVM_LIT_ARGS}
                                   -DLLVM_CCACHE_BUILD=${LLVM_CCACHE_BUILD}
                                   -DLLVM_CONFIG_PATH=${LLVM_BINARY_DIR}/bin/llvm-config${CMAKE_EXECUTABLE_SUFFIX}
                                   -DLLVM_ENABLE_PER_TARGET_RUNTIME_DIR=ON
                                   -Dllvmproject_SOURCE_DIR=${llvmproject_SOURCE_DIR}
                                   -Dpicolibc_SOURCE_DIR=${picolibc_SOURCE_DIR}
        USES_TERMINAL_CONFIGURE    TRUE
        USES_TERMINAL_BUILD        TRUE
        USES_TERMINAL_INSTALL      TRUE
        USES_TERMINAL_TEST         TRUE
        LIST_SEPARATOR             ,
        # Always run the build command so that incremental builds are correct.
        BUILD_ALWAYS               TRUE
        CONFIGURE_HANDLED_BY_BUILD TRUE
    )
    
    ExternalProject_Get_Property(${LIB_PROFILE} INSTALL_DIR)
    
    # Copy generated library to its detination. 
    add_custom_command(
        TARGET       ${LIB_PROFILE}
        POST_BUILD
        COMMAND      "${CMAKE_COMMAND}" -E copy "${INSTALL_DIR}/src/${LIB_PROFILE}-build/libclang_rt.profile.a"
                                                "${LLVM_BINARY_DIR}/${directory}/lib"
    )

    add_dependencies(
        llvm-toolchain-runtimes
        compiler_rt_profile_${variant}
    )
endfunction()
