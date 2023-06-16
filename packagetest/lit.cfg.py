# -*- Python -*-

import os
import sys

import lit.formats

from lit.llvm import llvm_config
from lit.llvm.subst import FindTool, ToolSubst

# Configuration file for the 'lit' test runner.

config.name = 'package'
config.test_format = lit.formats.ShTest(not llvm_config.use_lit_shell)
config.suffixes = ['.c', '.cpp', '.test']
config.excludes = ['CMakeLists.txt', 'README.md']
config.test_source_root = os.path.dirname(__file__)


# Copy-pasted from use_default_substitutions in
# llvm-project/llvm/utils/lit/lit/llvm/config.py
# FileCheck is not packaged so we need to get it from a different directory.
tool_patterns = [
    ToolSubst("FileCheck", unresolved="fatal"),
    # Handle these specially as they are strings searched for during
    # testing.
    ToolSubst(
        r"\| \bcount\b",
        command=FindTool("count"),
        verbatim=True,
        unresolved="fatal",
    ),
    ToolSubst(
        r"\| \bnot\b",
        command=FindTool("not"),
        verbatim=True,
        unresolved="fatal",
    ),
]
llvm_config.config.substitutions.append(("%python", '"%s"' % (sys.executable)))
llvm_config.add_tool_substitutions(tool_patterns, [os.path.join(config.llvm_obj_root, "bin")])
llvm_config.add_err_msg_substitutions()
llvm_config.use_clang()
llvm_config.config.substitutions.append(("%samples_dir", '"%s"' % config.samples_dir))
llvm_config.config.substitutions.append(("%unpack_directory", '"%s"' % config.unpack_directory))

config.environment["CLANG_NO_DEFAULT_CONFIG"] = "1"
