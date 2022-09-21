#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Handle symlinks such as clang++ when cross-building to Windows.
# CPack supports putting symlinks in zip files but to Windows they
# just look like a file containing text like "clang".

# 1. Convert required symlinks to regular files.
for name in \
    clang++ \
    clang-cpp \
    ld.lld \
    llvm-ranlib \
    llvm-readelf \
    llvm-strip
do
    ln -f $(realpath -m "bin/${name}.exe") bin/${name}.exe
done

# 2. Remove remaining symlinks
find -type l -exec rm {} +
