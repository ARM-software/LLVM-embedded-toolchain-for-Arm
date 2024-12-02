# To avoid duplicating the FetchContent code, this file can be
# included by either the top-level toolchain cmake, or the
# arm-runtimes sub-project.
# FETCHCONTENT_SOURCE_DIR_NEWLIB should be passed down from the
# top level to any library builss to prevent repeated checkouts.

include(FetchContent)
include(${CMAKE_CURRENT_LIST_DIR}/patch_repo.cmake)

if(NOT VERSIONS_JSON)
    include(${CMAKE_CURRENT_LIST_DIR}/read_versions.cmake)
endif()
read_repo_version(newlib newlib)
get_patch_command(${CMAKE_CURRENT_LIST_DIR}/.. newlib newlib_patch_command)

FetchContent_Declare(newlib
    GIT_REPOSITORY https://sourceware.org/git/newlib-cygwin.git
    GIT_TAG "${newlib_TAG}"
    GIT_SHALLOW "${newlib_SHALLOW}"
    GIT_PROGRESS TRUE
    PATCH_COMMAND ${newlib_patch_command}
    # Similarly to picolibc, we don't do the configuration here.
    SOURCE_SUBDIR do_not_add_newlib_subdir
)
FetchContent_MakeAvailable(newlib)
FetchContent_GetProperties(newlib SOURCE_DIR FETCHCONTENT_SOURCE_DIR_NEWLIB)
