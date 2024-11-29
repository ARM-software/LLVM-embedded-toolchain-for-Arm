# To avoid duplicating the FetchContent code, this file can be
# included by either the top-level toolchain cmake, or the
# arm-runtimes sub-project.
# FETCHCONTENT_SOURCE_DIR_LLVMPROJECT should be passed down from the
# top level to any library builds to prevent repeated checkouts.

include(FetchContent)
include(${CMAKE_CURRENT_LIST_DIR}/patch_repo.cmake)

if(NOT VERSIONS_JSON)
    include(${CMAKE_CURRENT_LIST_DIR}/read_versions.cmake)
endif()
read_repo_version(llvmproject llvm-project)
get_patch_command(${CMAKE_CURRENT_LIST_DIR}/.. llvm-project llvm_patch_command)
if(APPLY_LLVM_PERFORMANCE_PATCHES)
    get_patch_command(${CMAKE_CURRENT_LIST_DIR}/.. llvm-project-perf llvm_perf_patch_command)
    set(llvm_patch_command ${llvm_patch_command} && ${llvm_perf_patch_command} )
endif()

FetchContent_Declare(llvmproject
    GIT_REPOSITORY https://github.com/llvm/llvm-project.git
    GIT_TAG "${llvmproject_TAG}"
    GIT_SHALLOW "${llvmproject_SHALLOW}"
    GIT_PROGRESS TRUE
    PATCH_COMMAND ${llvm_patch_command}
    # Add the llvm subdirectory later to ensure that
    # LLVMEmbeddedToolchainForArm is the first project declared.
    # Otherwise CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT
    # can't be used.
    SOURCE_SUBDIR do_not_add_llvm_subdir_yet
)
FetchContent_MakeAvailable(llvmproject)
FetchContent_GetProperties(llvmproject SOURCE_DIR FETCHCONTENT_SOURCE_DIR_LLVMPROJECT)
