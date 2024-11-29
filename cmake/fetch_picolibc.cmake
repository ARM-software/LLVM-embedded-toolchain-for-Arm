# To avoid duplicating the FetchContent code, this file can be
# included by either the top-level toolchain cmake, or the
# arm-runtimes sub-project.
# FETCHCONTENT_SOURCE_DIR_PICOLIBC should be passed down from the
# top level to any library builss to prevent repeated checkouts.

include(FetchContent)
include(${CMAKE_CURRENT_LIST_DIR}/patch_repo.cmake)

if(NOT VERSIONS_JSON)
    include(${CMAKE_CURRENT_LIST_DIR}/read_versions.cmake)
endif()
read_repo_version(picolibc picolibc)
get_patch_command(${CMAKE_CURRENT_LIST_DIR}/.. picolibc picolibc_patch_command)

FetchContent_Declare(picolibc
    GIT_REPOSITORY https://github.com/picolibc/picolibc.git
    GIT_TAG "${picolibc_TAG}"
    GIT_SHALLOW "${picolibc_SHALLOW}"
    GIT_PROGRESS TRUE
    PATCH_COMMAND ${picolibc_patch_command}
    # We only want to download the content, not configure it at this
    # stage. picolibc will be built in many configurations using
    # ExternalProject_Add using the sources that are checked out here.
    SOURCE_SUBDIR do_not_add_picolibc_subdir
)
FetchContent_MakeAvailable(picolibc)
FetchContent_GetProperties(picolibc SOURCE_DIR FETCHCONTENT_SOURCE_DIR_PICOLIBC)
