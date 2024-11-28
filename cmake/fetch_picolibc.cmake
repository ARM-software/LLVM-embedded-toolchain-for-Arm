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

set(patch_script ${CMAKE_CURRENT_LIST_DIR}/patch_repo.py)
if(GIT_PATCH_METHOD STREQUAL "am")
    set(patch_script_args --method am)
elseif(GIT_PATCH_METHOD STREQUAL "apply")
    set(patch_script_args --method apply)
endif()
set(patch_dir ${CMAKE_CURRENT_LIST_DIR}/../patches)
set(PICOLIBC_PATCH_COMMAND ${Python3_EXECUTABLE} ${patch_script} ${patch_script_args} ${patch_dir}/picolibc)

FetchContent_Declare(picolibc
    GIT_REPOSITORY https://github.com/picolibc/picolibc.git
    GIT_TAG "${picolibc_TAG}"
    GIT_SHALLOW "${picolibc_SHALLOW}"
    GIT_PROGRESS TRUE
    PATCH_COMMAND ${PICOLIBC_PATCH_COMMAND}
    # We only want to download the content, not configure it at this
    # stage. picolibc will be built in many configurations using
    # ExternalProject_Add using the sources that are checked out here.
    SOURCE_SUBDIR do_not_add_picolibc_subdir
)
FetchContent_MakeAvailable(picolibc)
FetchContent_GetProperties(picolibc SOURCE_DIR FETCHCONTENT_SOURCE_DIR_PICOLIBC)
