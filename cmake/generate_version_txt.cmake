execute_process(
    COMMAND git -C ${LLVMEmbeddedToolchainForArm_SOURCE_DIR} rev-parse HEAD
    OUTPUT_VARIABLE LLVMEmbeddedToolchainForArm_COMMIT
    OUTPUT_STRIP_TRAILING_WHITESPACE
    COMMAND_ERROR_IS_FATAL ANY
)
execute_process(
    COMMAND git -C ${llvmproject_SOURCE_DIR} rev-parse HEAD
    OUTPUT_VARIABLE llvmproject_COMMIT
    OUTPUT_STRIP_TRAILING_WHITESPACE
    COMMAND_ERROR_IS_FATAL ANY
)
execute_process(
    COMMAND git -C ${picolibc_SOURCE_DIR} rev-parse HEAD
    OUTPUT_VARIABLE picolibc_COMMIT
    OUTPUT_STRIP_TRAILING_WHITESPACE
    COMMAND_ERROR_IS_FATAL ANY
)

configure_file(
    ${CMAKE_CURRENT_LIST_DIR}/VERSION.txt.in
    ${CMAKE_CURRENT_BINARY_DIR}/VERSION.txt
)
