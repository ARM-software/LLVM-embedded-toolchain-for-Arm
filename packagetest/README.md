This directory contains LLVM lit tests to be run against LLVM Embedded
Toolchain for Arm that has been extracted from a package in the same way
that a user of the product would. This is unlike the tests in the test
directory, which run against tools in the build directory.

You can run the tests ensuring that all dependencies are built:

    ninja check-package-llvm-toolchain

Or run the tests with lit directly:

    ${BUILD_DIR}/llvm/bin/llvm-lit -sv ${BUILD_DIR}/packagetest
