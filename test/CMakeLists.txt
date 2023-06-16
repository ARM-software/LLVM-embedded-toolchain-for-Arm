if(LLVM_ENABLE_BACKTRACES)
  set(ENABLE_BACKTRACES 1)
endif()
llvm_canonicalize_cmake_booleans(
  ENABLE_BACKTRACES
)

configure_lit_site_cfg(
  ${CMAKE_CURRENT_SOURCE_DIR}/lit.site.cfg.py.in
  ${CMAKE_CURRENT_BINARY_DIR}/lit.site.cfg.py
  MAIN_CONFIG
  ${CMAKE_CURRENT_SOURCE_DIR}/lit.cfg.py
)

list(APPEND LLVM_TOOLCHAIN_TEST_DEPS
  llvm-toolchain
  FileCheck
  count
  not
)

add_lit_testsuite(check-llvm-toolchain-lit
  "Running LLVM Embedded Toolchain for Arm regression tests"
  ${CMAKE_CURRENT_BINARY_DIR}
  DEPENDS ${LLVM_TOOLCHAIN_TEST_DEPS}
)

add_lit_testsuites(llvm-toolchain-lit ${CMAKE_CURRENT_SOURCE_DIR}
  DEPENDS ${LLVM_TOOLCHAIN_TEST_DEPS}
)
