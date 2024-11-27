# To avoid duplicating the FetchContent code, this file can be
# included by either the top-level toolchain cmake, or the
# arm-runtimes sub-project.
# FETCHCONTENT_SOURCE_DIR_LLVMPROJECT should be passed down from the
# top level to any library builds to prevent repeated checkouts.

include(FetchContent)

if(NOT VERSIONS_JSON)
    include(${CMAKE_CURRENT_LIST_DIR}/read_versions.cmake)
endif()
read_repo_version(llvmproject llvm-project)

set(llvm_patch_script ${CMAKE_CURRENT_LIST_DIR}/patch_llvm.py)
set(patch_dir ${CMAKE_CURRENT_LIST_DIR}/../patches)
set(LLVM_PATCH_COMMAND ${Python3_EXECUTABLE} ${llvm_patch_script} ${patch_dir}/llvm-project)
if(APPLY_LLVM_PERFORMANCE_PATCHES)
    set(LLVM_PATCH_COMMAND ${LLVM_PATCH_COMMAND} && ${Python3_EXECUTABLE} ${llvm_patch_script} ${patch_dir}/llvm-project-perf)
endif()

FetchContent_Declare(llvmproject
    GIT_REPOSITORY https://github.com/llvm/llvm-project.git
    GIT_TAG "${llvmproject_TAG}"
    GIT_SHALLOW "${llvmproject_SHALLOW}"
    GIT_PROGRESS TRUE
    PATCH_COMMAND ${LLVM_PATCH_COMMAND}
    # Add the llvm subdirectory later to ensure that
    # LLVMEmbeddedToolchainForArm is the first project declared.
    # Otherwise CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT
    # can't be used.
    SOURCE_SUBDIR do_not_add_llvm_subdir_yet
)
FetchContent_MakeAvailable(llvmproject)
FetchContent_GetProperties(llvmproject SOURCE_DIR FETCHCONTENT_SOURCE_DIR_LLVMPROJECT)
