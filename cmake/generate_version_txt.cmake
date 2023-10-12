# The following line will look different depending on how you got this
# source file. If you got it from a Git repository then it will contain
# a string in the git pretty format with dollar symbols. If you got it
# from a source archive then the `git archive` command should have
# replaced the format string with the Git revision at the time the
# archive was created. This is configured in the .gitattributes file.
# In the former case, this script will run a Git command to find out the
# current revision. In the latter case the revision will be used as is.
set(LLVMEmbeddedToolchainForArm_COMMIT "$Format:%H$")

if(NOT ${LLVMEmbeddedToolchainForArm_COMMIT} MATCHES "^[a-f0-9]+$")
    execute_process(
        COMMAND git -C ${LLVMEmbeddedToolchainForArm_SOURCE_DIR} rev-parse HEAD
        OUTPUT_VARIABLE LLVMEmbeddedToolchainForArm_COMMIT
        OUTPUT_STRIP_TRAILING_WHITESPACE
        COMMAND_ERROR_IS_FATAL ANY
    )
endif()

execute_process(
    COMMAND git -C ${llvmproject_SOURCE_DIR} rev-parse HEAD
    OUTPUT_VARIABLE llvmproject_COMMIT
    OUTPUT_STRIP_TRAILING_WHITESPACE
    COMMAND_ERROR_IS_FATAL ANY
)
execute_process(
    COMMAND git -C ${${LLVM_TOOLCHAIN_C_LIBRARY}_SOURCE_DIR} rev-parse HEAD
    OUTPUT_VARIABLE ${LLVM_TOOLCHAIN_C_LIBRARY}_COMMIT
    OUTPUT_STRIP_TRAILING_WHITESPACE
    COMMAND_ERROR_IS_FATAL ANY
)

configure_file(
    ${CMAKE_CURRENT_LIST_DIR}/VERSION.txt.in
    ${CMAKE_CURRENT_BINARY_DIR}/VERSION.txt
)
