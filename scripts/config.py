# Copyright (c) 2021, Arm Limited and affiliates.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import datetime
import enum
import logging
import os
from typing import Optional, Set, TYPE_CHECKING

import execution


@enum.unique
class FloatABI(enum.Enum):
    """Enumeration for the -mfloat-abi compiler option values."""
    SOFT_FP = 'soft'
    HARD_FP = 'hard'


@enum.unique
class CheckoutMode(enum.Enum):
    """Enumeration for the --checkout-mode options for the build script. See
       build.py:parse_args_to_config() for description of each mode."""
    FORCE = 'force'
    PATCH = 'patch'
    REUSE = 'reuse'


@enum.unique
class BuildMode(enum.Enum):
    """Enumerator for the --rebuild-mode option."""
    REBUILD = 'rebuild'
    RECONFIGURE = 'reconfigure'
    INCREMENTAL = 'incremental'


if TYPE_CHECKING:
    class EnumValueStub:  # pylint: disable=too-few-public-methods
        """Stub class for the type checker, represents a single value of an
           enumeration
        """
        value = ''

    class ToolchainKind:  # pylint: disable=too-few-public-methods
        """Stub class for the type checker, replaces ToolchainKind"""
        def __init__(self, name: str):
            self.option_name = name
        option_name = ''
        pretty_name = ''
        host_triple = ''
        c_compiler = ''
        cpp_compiler = ''
        CLANG = EnumValueStub()
        GCC = EnumValueStub()
        MINGW = EnumValueStub()
else:
    @enum.unique
    class ToolchainKind(enum.Enum):
        """Enumeration for the --host-toolchain and --native-toolchain
           options.
        """
        CLANG = ('clang', 'Clang', None, 'clang', 'clang++')
        GCC = ('gcc', 'GCC', None, 'gcc', 'g++')
        # MINGW is only supported with --host-toolchain
        MINGW = ('mingw', 'Mingw-w64 GCC', 'x86_64-w64-mingw32',
                 'x86_64-w64-mingw32-gcc-posix',
                 'x86_64-w64-mingw32-g++-posix')

        def __new__(cls, option_name, pretty_name, host_triple, c_compiler,
                    cpp_compiler):
            obj = object.__new__(cls)
            obj._value_ = option_name
            obj.option_name = option_name
            obj.pretty_name = pretty_name
            obj.host_triple = host_triple
            obj.c_compiler = c_compiler
            obj.cpp_compiler = cpp_compiler
            return obj


@enum.unique
class CopyRuntime(enum.Enum):
    """Enumeration for the --copy-runtime-dlls options."""
    YES = 'yes'
    NO = 'no'
    ASK = 'ask'


@enum.unique
class Action(enum.Enum):
    """Enumerations for the positional command line arguments. See
       build.py:parse_args_to_config() for description
    """
    PREPARE = 'prepare'
    CLANG = 'clang'
    NEWLIB = 'newlib'
    COMPILER_RT = 'compiler-rt'
    LIBCXX = 'libcxx'
    CONFIGURE = 'configure'
    PACKAGE = 'package'
    ALL = 'all'
    # The 'test' phase is not part of 'all'
    TEST = 'test'


@enum.unique
class PackageFormat(enum.Enum):
    """Binary package format."""
    TGZ = 'tgz'
    ZIP = 'zip'


class Toolchain:  # pylint: disable=too-few-public-methods
    """This class is used for representing toolchains that run on the build
       machine (the one where build.py is run). In case of cross-compilation
       we need two toolchains: host and native (e.g. when cross-compiling from
       Linux to Windows the "host toolchain" is a Linux->Windows toolchain and
       the "native toolchain" is a Linux->Linux one).
    """
    def __init__(self, toolchain_dir: str, kind: ToolchainKind):
        self.toolchain_dir = toolchain_dir
        self.kind = kind
        self.c_compiler = os.path.join(toolchain_dir, kind.c_compiler)
        self.cpp_compiler = os.path.join(toolchain_dir, kind.cpp_compiler)
        if self.kind.host_triple is not None:
            self.sys_root = os.path.join(toolchain_dir, '..',
                                         self.kind.host_triple)

    def get_lib_search_dirs(self) -> Set[str]:
        """Returns a set of paths where the toolchain runtime libraries
           can be found.
        """
        lines = execution.run_stdout([self.c_compiler, '-print-search-dirs'])
        prefix = 'libraries: ='
        result = set()
        for line in lines:
            if not line.startswith(prefix):
                continue
            line = line[len(prefix):]
            for path in line.strip().split(':'):
                result.add(os.path.normpath(path))
        assert result, ('Failed to parse "{} -print-search-dirs" '
                        'output'.format(self.c_compiler))
        return result


class LibrarySpec:
    """Configuration for a single runtime library variant."""
    def __init__(self, triple_arch: str, march: str,
                 float_abi: FloatABI, name_suffix: str,
                 arch_options: str, other_flags: str = ''):
        # pylint: disable=too-many-arguments
        assert triple_arch in ('aarch64', 'arm')
        self.triple_arch = triple_arch
        self.march = march
        self.float_abi = float_abi
        self.arch_options = arch_options
        self.other_flags = other_flags
        if self.triple_arch == 'arm':
            self.name = '{}_{}_{}'.format(self.march, float_abi.value,
                                          name_suffix)
        else:
            self.name = '{}_{}'.format(self.triple_arch, name_suffix)

    @property
    def target(self):
        """Target triple"""
        if self.triple_arch == 'arm':
            return self.march + '-none-eabi'
        assert self.triple_arch == 'aarch64'
        return 'aarch64-none-elf'

    @property
    def flags(self):
        """Compiler and assembler flags."""
        res = '--target={}'.format(self.target)
        if self.float_abi is not None:
            res += ' -mfloat-abi={} '.format(self.float_abi.value)

        res += ' -march={}{}'.format(self.march, self.arch_options)
        if self.other_flags:
            res += ' ' + self.other_flags
        return res


def _make_library_specs():
    """Create a dict of LibrarySpec-s for each library variant."""
    hard = FloatABI.HARD_FP
    soft = FloatABI.SOFT_FP
    lib_specs = [
        LibrarySpec('aarch64', 'armv8-a', None, '', ''),
        LibrarySpec('arm', 'armv8.1m.main', hard, 'fp', '+fp'),
        LibrarySpec('arm', 'armv8.1m.main', hard, 'nofp_mve', '+nofp+mve'),
        LibrarySpec('arm', 'armv8.1m.main', soft, 'nofp_nomve', '+nofp+nomve'),
        LibrarySpec('arm', 'armv8m.main', hard, 'fp', '+fp'),
        LibrarySpec('arm', 'armv8m.main', soft, 'nofp', '+nofp'),
        LibrarySpec('arm', 'armv7em', hard, 'fpv4_sp_d16', '',
                    '-mfpu=fpv4-sp-d16'),
        LibrarySpec('arm', 'armv7em', hard, 'fpv5_d16', '', '-mfpu=fpv5-d16'),
        LibrarySpec('arm', 'armv7em', soft, 'nofp', '', '-mfpu=none'),
        LibrarySpec('arm', 'armv7m', soft, 'nofp', '+nofp'),
        LibrarySpec('arm', 'armv6m', soft, 'nofp', '')
    ]
    return {lib_spec.name: lib_spec for lib_spec in lib_specs}


LIBRARY_SPECS = _make_library_specs()
ARCH_ARCHVERSION_ORDER = \
    [('aarch64', 'armv8-a')] + \
    [('arm', arch)
     for arch in ('armv6m', 'armv7m', 'armv7em', 'armv8m.main',
                  'armv8.1m.main')]


def _assign_dir(arg, default, rev):
    if arg is not None:
        res = arg
    else:
        dir_name = '{}-{}'.format(default, rev)
        res = os.path.join(os.getcwd(), dir_name)
    return os.path.abspath(res)


class Config:  # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-few-public-methods
    """Configuration for the whole build process"""

    _copy_runtime_dlls: Optional[bool] = None

    def _default_target(self):
        # Default value for the -target option:
        # * Do not set a default if both ARM and AArch64 support is requested.
        # * Otherwise, use the minimum architecture version among the ones
        #   listed in self.variants
        archs = set((v.triple_arch, v.march) for v in self.variants)
        triple_archs = set(v.triple_arch for v in self.variants)
        if len(triple_archs) == 1:
            min_variant = min(archs, key=ARCH_ARCHVERSION_ORDER.index)
            min_arch_triple, min_march = min_variant
            if min_arch_triple == 'arm':
                return '{}-none-eabi'.format(min_march)
            assert min_arch_triple == 'aarch64'
            return 'aarch64-none-elf'
        return None

    def _fill_args(self, args: argparse.Namespace):
        if 'all' in args.variants:
            variant_names = LIBRARY_SPECS.keys()
        else:
            variant_names = set(args.variants)
        self.variants = [LIBRARY_SPECS[v] for v in sorted(variant_names)]

        if not args.actions or Action.ALL.value in args.actions:
            self.actions = set(action for action in Action
                               if action not in (Action.ALL, Action.TEST))
            if Action.TEST.value in args.actions:
                self.actions.add(Action.TEST)
        else:
            self.actions = set(Action(act_str) for act_str in args.actions)

        self.default_target = self._default_target()

        rev = args.revision
        self.revision = rev
        self.source_dir = os.path.abspath(args.source_dir)
        self.repos_dir = _assign_dir(args.repositories_dir, 'repos', rev)
        self.build_dir = _assign_dir(args.build_dir, 'build', rev)
        self.install_dir = _assign_dir(args.install_dir, 'install', rev)
        self.package_dir = os.path.abspath(args.package_dir)
        # According to
        # https://docs.python.org/3.6/library/enum.html#using-a-custom-new:
        # "The __new__() method, if defined, is used during creation of the
        # Enum members; it is then replaced by Enum’s __new__() which is used
        # after class creation for lookup of existing members."
        # This confuses pylint.
        # pylint: disable=no-value-for-parameter
        host_toolchain_kind = ToolchainKind(args.host_toolchain)
        host_toolchain_dir = os.path.abspath(args.host_toolchain_dir)
        self.host_toolchain = Toolchain(host_toolchain_dir,
                                        host_toolchain_kind)
        # pylint: disable=no-value-for-parameter
        native_toolchain_kind = ToolchainKind(args.native_toolchain)
        native_toolchain_dir = os.path.abspath(args.native_toolchain_dir)
        self.native_toolchain = Toolchain(native_toolchain_dir,
                                          native_toolchain_kind)
        self.checkout_mode = CheckoutMode(args.checkout_mode)
        self.build_mode = BuildMode(args.build_mode)

        is_using_mingw = self.host_toolchain.kind == ToolchainKind.MINGW
        is_windows = is_using_mingw

        copy_runtime = CopyRuntime(args.copy_runtime_dlls)
        self.ask_copy_runtime_dlls = True
        if is_using_mingw:
            self.ask_copy_runtime_dlls = (copy_runtime == CopyRuntime.ASK)
            if not self.ask_copy_runtime_dlls:
                self._copy_runtime_dlls = (copy_runtime == CopyRuntime.YES)
        else:
            if copy_runtime != CopyRuntime.ASK:
                logging.warning('the --copy-runtime-dlls option is only used '
                                'during cross-compilation')
            self.ask_copy_runtime = False
            self._copy_runtime_dlls = False

        if args.package_format is None:
            self.package_format = (PackageFormat.ZIP if is_windows else
                                   PackageFormat.TGZ)
        else:
            self.package_format = PackageFormat(args.package_format)

        self.use_ninja = args.use_ninja
        self.use_ccache = args.use_ccache
        self.skip_checks = args.skip_checks
        self.verbose = args.verbose
        self.num_threads = args.parallel

    @property
    def copy_runtime_dlls(self) -> bool:
        """Whether or not the build script needs to copy Mingw-w64 runtime
           DLLs to the target_llvm_bin_dir directory. """
        assert self._copy_runtime_dlls is not None
        return self._copy_runtime_dlls

    @copy_runtime_dlls.setter
    def copy_runtime_dlls(self, value: bool) -> None:
        self._copy_runtime_dlls = value

    def _fill_inferred(self):
        """Fill in additional fields that can be inferred from the
           configuration, but are still useful for convenience."""
        join = os.path.join
        self.llvm_repo_dir = join(self.repos_dir, 'llvm.git')
        self.newlib_repo_dir = join(self.repos_dir, 'newlib.git')
        is_using_mingw = self.host_toolchain.kind == ToolchainKind.MINGW
        self.is_cross_compiling = (os.name == 'posix' and is_using_mingw)
        self.cmake_generator = 'Ninja' if self.use_ninja else 'Unix Makefiles'
        self.release_mode = self.revision != 'HEAD'
        if self.release_mode:
            version_suffix = '-' + self.revision
            self.version_string = self.revision
        else:
            version_suffix = ''
            now = datetime.datetime.now()
            self.version_string = now.strftime('%Y-%m-%d-%H:%M:%S')
        self.skip_reconfigure = self.build_mode == BuildMode.INCREMENTAL
        product_name = 'LLVMEmbeddedToolchainForArm'
        self.package_base_name = product_name + version_suffix
        self.target_llvm_dir = join(
            self.install_dir,
            '{}-{}'.format(product_name, self.revision))
        if self.is_cross_compiling:
            self.native_llvm_build_dir = join(self.build_dir, 'native-llvm')
            self.native_llvm_dir = join(self.install_dir, 'native-llvm')
        else:
            self.native_llvm_build_dir = join(self.build_dir, 'llvm')
            self.native_llvm_dir = self.target_llvm_dir
        self.native_llvm_bin_dir = os.path.join(self.native_llvm_dir, 'bin')
        self.native_llvm_rt_dir = os.path.join(self.native_llvm_dir, 'lib',
                                               'clang-runtimes')
        self.target_llvm_bin_dir = os.path.join(self.target_llvm_dir, 'bin')
        self.target_llvm_rt_dir = os.path.join(self.target_llvm_dir, 'lib',
                                               'clang-runtimes')

    def __init__(self, args: argparse.Namespace):
        self._copy_runtime_dlls = None
        self._fill_args(args)
        self._fill_inferred()
