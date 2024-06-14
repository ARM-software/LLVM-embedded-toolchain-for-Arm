#!/bin/bash

mkdir repos
git -C repos clone https://github.com/32bitmicro/llvm-project.git
git -C repos/llvm-project am -k "$PWD"/../patches/llvm-project/*.patch
git -C repos clone https://github.com/32bitmicro/picolibc.git
git -C repos/picolibc apply "$PWD"/../patches/picolibc.patch
mkdir build-from-repos
cd build-from-repos
cmake .. -GNinja -DFETCHCONTENT_SOURCE_DIR_LLVMPROJECT=../repos/llvm-project -DFETCHCONTENT_SOURCE_DIR_PICOLIBC=../repos/picolibc
ninja llvm-toolchain