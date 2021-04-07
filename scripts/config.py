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
import os


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
class Action(enum.Enum):
    """Enumerations for the positional command line arguments. See
       build.py:parse_args_to_config() for description
    """
    PREPARE = 'prepare'
    CLANG = 'clang'
    NEWLIB = 'newlib'
    COMPILER_RT = 'compiler-rt'
    CONFIGURE = 'configure'
    PACKAGE = 'package'
    ALL = 'all'


class LibrarySpec:
    """Configuration for a single runtime library variant."""
    def __init__(self, arch: str, float_abi: FloatABI, name_suffix: str,
                 arch_options: str, other_flags: str = '',
                 newlib_fp_support: bool = None):
        # pylint: disable=too-many-arguments
        if float_abi == FloatABI.SOFT_FP:
            assert not newlib_fp_support
            self.newlib_fp_support = False
        else:
            self.newlib_fp_support = (newlib_fp_support
                                      if newlib_fp_support is not None
                                      else True)
        self.arch = arch
        self.float_abi = float_abi
        self.arch_options = arch_options
        self.other_flags = other_flags
        self.newlib_fp_support = newlib_fp_support
        self.name = '{}_{}_{}'.format(arch,  float_abi.value, name_suffix)

    @property
    def target(self):
        """Target triple"""
        return self.arch + '-none-eabi'

    @property
    def flags(self):
        """Compiler and assembler flags."""
        res = '-mfloat-abi={} -march={}{}'.format(self.float_abi.value,
                                                  self.arch, self.arch_options)
        if self.other_flags:
            res += ' ' + self.other_flags
        return res


def _make_library_specs():
    """Create a dict of LibrarySpec-s for each library variant."""
    hard = FloatABI.HARD_FP
    soft = FloatABI.SOFT_FP
    lib_specs = [
        LibrarySpec('armv8.1m.main', hard, 'fp', '+fp'),
        LibrarySpec('armv8.1m.main', hard, 'nofp_mve', '+nofp+mve',
                    newlib_fp_support=False),
        LibrarySpec('armv8.1m.main', soft, 'nofp_nomve', '+nofp+nomve'),
        LibrarySpec('armv8m.main', hard, 'fp', '+fp'),
        LibrarySpec('armv8m.main', soft, 'nofp', '+nofp'),
        LibrarySpec('armv7em', hard, 'fpv4_sp_d16', '', '-mfpu=fpv4-sp-d16'),
        LibrarySpec('armv7em', hard, 'fpv5_d16', '', '-mfpu=fpv5-d16'),
        LibrarySpec('armv7em', soft, 'nofp', '', '-mfpu=none'),
        LibrarySpec('armv7m', soft, 'nofp', '+nofp'),
        LibrarySpec('armv6m', soft, 'nofp', '')
    ]
    return {lib_spec.name: lib_spec for lib_spec in lib_specs}


LIBRARY_SPECS = _make_library_specs()
ARCH_ORDER = ['armv6m', 'armv7m', 'armv7em', 'armv8m.main', 'armv8.1m.main']


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

    def _fill_args(self, args: argparse.Namespace):
        if 'all' in args.variants:
            variant_names = LIBRARY_SPECS.keys()
        else:
            variant_names = set(args.variants)
        self.variants = [LIBRARY_SPECS[v] for v in sorted(variant_names)]

        if not args.actions or Action.ALL.value in args.actions:
            self.actions = set(action for action in Action
                               if action != Action.ALL)
        else:
            self.actions = set(Action(act_str) for act_str in args.actions)

        # Default value for the -target option: use the minimum architecture
        # version among the ones listed in self.variants
        archs = set(v.arch for v in self.variants)
        min_arch = min(archs, key=ARCH_ORDER.index)
        self.default_target = '{}-none-eabi'.format(min_arch)

        rev = args.revision
        self.revision = rev
        self.source_dir = os.path.abspath(args.source_dir)
        self.repos_dir = _assign_dir(args.repositories_dir, 'repos', rev)
        self.build_dir = _assign_dir(args.build_dir, 'build', rev)
        self.install_dir = os.path.abspath(args.install_dir)
        self.package_dir = os.path.abspath(args.package_dir)
        self.host_compiler_path = os.path.abspath(args.host_toolchain_dir)
        self.checkout_mode = CheckoutMode(args.checkout_mode)

        self.use_ninja = args.use_ninja
        self.use_ccache = args.use_ccache
        self.skip_checks = args.skip_checks
        self.verbose = args.verbose
        self.num_threads = args.parallel

    def _fill_inferred(self):
        """Fill in additional fields that can be inferred from the
           configuration, but are still useful for convenience."""
        self.llvm_repo_dir = os.path.join(self.repos_dir, 'llvm.git')
        self.newlib_repo_dir = os.path.join(self.repos_dir, 'newlib.git')
        self.host_c_compiler = os.path.join(self.host_compiler_path, 'clang')
        self.host_cpp_compiler = \
            os.path.join(self.host_compiler_path, 'clang++')
        self.cmake_generator = 'Ninja' if self.use_ninja else 'Unix Makefiles'
        self.release_mode = self.revision != 'HEAD'
        if self.release_mode:
            version_suffix = '-' + self.revision
            self.version_string = self.revision
        else:
            version_suffix = ''
            now = datetime.datetime.now()
            self.version_string = now.strftime('%Y-%m-%d-%H:%M:%S')
        product_name = 'LLVMEmbeddedToolchainForArm'
        self.tarball_base_name = product_name + version_suffix
        self.target_llvm_dir = os.path.join(
            self.install_dir,
            '{}-{}'.format(product_name, self.revision))
        self.target_llvm_bin_dir = os.path.join(self.target_llvm_dir, 'bin')
        self.target_llvm_rt_dir = os.path.join(self.target_llvm_dir,  'lib',
                                               'clang-runtimes')

    def __init__(self, args: argparse.Namespace):
        self._fill_args(args)
        self._fill_inferred()
