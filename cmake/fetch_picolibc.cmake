# To avoid duplicating the FetchContent code, this file can be
# included by either the top-level toolchain cmake, or the
# arm-runtimes sub-project.
# FETCHCONTENT_SOURCE_DIR_PICOLIBC should be passed down from the
# top level to any library builss to prevent repeated checkouts.

include(FetchContent)

if(NOT VERSIONS_JSON)
    include(${CMAKE_CURRENT_LIST_DIR}/read_versions.cmake)
endif()
read_repo_version(picolibc picolibc)

set(
    picolibc_patches
    ${CMAKE_CURRENT_SOURCE_DIR}/patches/picolibc/0001-Enable-libcxx-builds.patch
    ${CMAKE_CURRENT_SOURCE_DIR}/patches/picolibc/0002-Add-bootcode-for-AArch64-FVPs.patch
)

FetchContent_Declare(picolibc
    GIT_REPOSITORY https://github.com/picolibc/picolibc.git
    GIT_TAG "${picolibc_TAG}"
    GIT_SHALLOW "${picolibc_SHALLOW}"
    GIT_PROGRESS TRUE
    PATCH_COMMAND git reset --quiet --hard && git clean --quiet --force -dx && git apply ${picolibc_patches}
    # We only want to download the content, not configure it at this
    # stage. picolibc will be built in many configurations using
    # ExternalProject_Add using the sources that are checked out here.
    SOURCE_SUBDIR do_not_add_picolibc_subdir
)
FetchContent_MakeAvailable(picolibc)
