# -*- Python -*-

import os

import lit.formats

from lit.llvm import llvm_config

# Configuration file for the 'lit' test runner.

config.name = 'LLVM Embedded Toolchain for Arm'
config.test_format = lit.formats.ShTest(not llvm_config.use_lit_shell)
config.suffixes = ['.c', '.cpp', '.test']
config.excludes = ['CMakeLists.txt']
config.test_source_root = os.path.dirname(__file__)

llvm_config.use_default_substitutions()
llvm_config.use_clang()

config.environment["CLANG_NO_DEFAULT_CONFIG"] = "1"
