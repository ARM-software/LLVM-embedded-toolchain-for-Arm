# To avoid duplicating the FetchContent code, this file can be
# included by either the top-level toolchain cmake, or the
# arm-runtimes sub-project.
# FETCHCONTENT_SOURCE_DIR_NEWLIB should be passed down from the
# top level to any library builss to prevent repeated checkouts.

include(FetchContent)

set(newlib_patch ${CMAKE_CURRENT_SOURCE_DIR}/../patches/newlib.patch)

FetchContent_Declare(newlib
    GIT_REPOSITORY https://sourceware.org/git/newlib-cygwin.git
    GIT_TAG "${newlib_TAG}"
    GIT_SHALLOW "${newlib_SHALLOW}"
    GIT_PROGRESS TRUE
    PATCH_COMMAND git reset --quiet --hard && git clean --quiet --force -dx && git apply ${newlib_patch}
    # Similarly to picolibc, we don't do the configuration here.
    SOURCE_SUBDIR do_not_add_newlib_subdir
)
FetchContent_MakeAvailable(newlib)
