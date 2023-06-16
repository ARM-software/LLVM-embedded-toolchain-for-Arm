if(LLVM_ENABLE_BACKTRACES)
  set(ENABLE_BACKTRACES 1)
endif()
llvm_canonicalize_cmake_booleans(
  ENABLE_BACKTRACES
)

# If samples are included in the package then use the packaged samples in
# post-package tests, otherwise use the samples from the source directory.
if(llvm-toolchain-samples IN_LIST LLVM_TOOLCHAIN_DISTRIBUTION_COMPONENTS)
    set(samples_dir ${unpack_directory}/samples)
else()
    set(samples_dir ${CMAKE_CURRENT_SOURCE_DIR}/../samples)
endif()

configure_lit_site_cfg(
  ${CMAKE_CURRENT_SOURCE_DIR}/lit.site.cfg.py.in
  ${CMAKE_CURRENT_BINARY_DIR}/lit.site.cfg.py
  MAIN_CONFIG
  ${CMAKE_CURRENT_SOURCE_DIR}/lit.cfg.py
)

list(APPEND LLVM_TOOLCHAIN_PACKAGE_TEST_DEPS
  unpack-llvm-toolchain
  FileCheck
  count
  not
)

add_lit_testsuite(check-package-llvm-toolchain
  "Running LLVM Embedded Toolchain for Arm package tests"
  ${CMAKE_CURRENT_BINARY_DIR}
  DEPENDS ${LLVM_TOOLCHAIN_PACKAGE_TEST_DEPS}
)

add_lit_testsuites(package-llvm-toolchain ${CMAKE_CURRENT_SOURCE_DIR}
  DEPENDS ${LLVM_TOOLCHAIN_PACKAGE_TEST_DEPS}
)
