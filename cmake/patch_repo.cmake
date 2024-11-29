
# Function to generate a PATCH_COMMAND, calling the
# patch_repo.py script using a target set of patches.

function(get_patch_command patch_dir patch_command_out)
    set(patch_script ${CMAKE_CURRENT_LIST_DIR}/patch_repo.py)
    list(APPEND patch_script_args ${Python3_EXECUTABLE} ${patch_script})
    if(GIT_PATCH_METHOD STREQUAL "am")
        list(APPEND patch_script_args "--method" "am")
    elseif(GIT_PATCH_METHOD STREQUAL "apply")
        list(APPEND patch_script_args "--method" "apply")
    endif()
    list(APPEND patch_script_args ${CMAKE_CURRENT_LIST_DIR}/../patches/${patch_dir})

    set(${patch_command_out} ${patch_script_args} PARENT_SCOPE)
endfunction()
