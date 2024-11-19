# Read which revisions of the repos to use.
file(READ ${CMAKE_CURRENT_LIST_DIR}/../versions.json VERSIONS_JSON)
function(read_repo_version output_variable_prefix repo)
    string(JSON tag GET ${VERSIONS_JSON} "repos" "${repo}" "tag")
    string(JSON tagType GET ${VERSIONS_JSON} "repos" "${repo}" "tagType")
    if(tagType STREQUAL "commithash")
        # GIT_SHALLOW doesn't work with commit hashes.
        set(shallow OFF)
    elseif(tagType STREQUAL "branch")
        set(shallow ON)
        # CMake docs recommend that "branch names and tags should
        # generally be specified as remote names"
        set(tag "origin/${tag}")
    elseif(tagType STREQUAL "tag")
        set(shallow ON)
    else()
        message(FATAL_ERROR "Unrecognised tagType ${tagType}")
    endif()

    set(${output_variable_prefix}_TAG "${tag}" PARENT_SCOPE)
    set(${output_variable_prefix}_SHALLOW "${shallow}" PARENT_SCOPE)
endfunction()
