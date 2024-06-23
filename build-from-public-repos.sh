#!/bin/bash

RELEASE=18.x
SUFFIX=rc1
PICOLIBC=1.8.6
REPOS=repos-$RELEASE-$SUFFIX
BUILD=build-$RELEASE-$SUFFIX

git config --global user.email $EMAIL
git config --global user.name  $NAME

PATHPREFIX="${PREFIX:-/tmp}"
cd $PATHPREFIX
git clone https://github.com/32bitmicro/LLVM-Embedded-Toolchain.git

mkdir $REPOS
git -C $REPOS clone -b release/$RELEASE git@github.com:32bitmicro/llvm-project.git
#git -C $REPOS/llvm-project am -k "$PWD"/patches/llvm-project/*.patch
git -C $REPOS clone git@github.com:32bitmicro/picolibc.git
git -C $REPOS/picolibc checkout $PICOLIBC -b $PICOLIBC
git -C $REPOS/picolibc apply "$PWD"/patches/picolibc.patch

mkdir $BUILD
cd $BUILD
cmake $PATHPREFIX/LLVM-Embedded-Toolchain -G"Unix Makefiles" -DCMAKE_BUILD_TYPE=Debug -DFETCHCONTENT_SOURCE_DIR_LLVMPROJECT=$PATHPREFIX/$REPOS/llvm-project -DFETCHCONTENT_SOURCE_DIR_PICOLIBC=$PATHPREFIX/$REPOS/picolibc -DETOOL_VERSION_SUFFIX=$SUFFIX
ninja llvm-toolchain
ninja package-llvm-toolchain
