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

import functools
import logging
import os
import shutil
import util

import config
import execution


@functools.total_ordering
class Version:
    """Version number tuple."""
    def __init__(self, *args):
        self.ver = tuple(args)

    def __str__(self) -> str:
        """Convert version tuple into a dot-delimited version string."""
        return '.'.join(str(v) for v in self.ver)

    def __eq__(self, other):
        if not isinstance(other, Version):
            raise NotImplementedError
        return self.ver == other.ver

    def __lt__(self, other):
        if not isinstance(other, Version):
            raise NotImplementedError
        return self.ver < other.ver


# Minimum versions required by the LLVM Project
MIN_CLANG_VERSION = Version(6, 0, 0)
MIN_CMAKE_VERSION = Version(3, 14, 4)
MIN_MAKE_VERSION = Version(3, 79)
# If we use CCache, it must be recent enough. Older versions do weird things
# with Clang.
MIN_CCACHE_VERSION = Version(3, 2, 5)


def _str_to_ver(version_str: str) -> Version:
    """Covert version string to a tuple of numbers."""
    return Version(*[int(v) for v in version_str.split('.')])


def _print_version_error(program: str, path: str, actual_ver: Version,
                         required_ver: Version) -> None:
    """Print an error message saying the a given program version is not recent
       enough.
    """
    if path is not None:
        full_program = '{} {}'.format(program, path)
    else:
        full_program = program
    logging.error('Your %s version %s is not recent enough. '
                  'Please upgrade it to at least %s', full_program,
                  actual_ver, required_ver)


def _check_host_compiler(cfg: config.Config) -> bool:
    """Check availability and version of the host compiler (Clang or GCC
       depending on build configuration).
    """
    def check_compiler_executable(executable_path):
        if not os.path.exists(executable_path):
            logging.error('The specified host compiler path %s is '
                          'invalid: %s not found', cfg.host_compiler_path,
                          executable_path)
            return False
        return True

    if not check_compiler_executable(cfg.host_c_compiler):
        return False
    if not check_compiler_executable(cfg.host_cpp_compiler):
        return False

    args = [cfg.host_c_compiler, '--version']
    ver_line = execution.run_stdout(args)[0]
    assert 'clang version' in ver_line
    ver_str = ver_line.split(' ')[-1]
    # Remove distribution suffix (if any) and convert to a tuple
    ver = _str_to_ver(ver_str.split('-')[0])
    if ver < MIN_CLANG_VERSION:
        _print_version_error('Clang', cfg.host_c_compiler, ver,
                             MIN_CLANG_VERSION)
        return False
    if cfg.verbose:
        logging.info('Using host compiler: Clang version %s', ver_str)
    return True


def _check_availability(bin_name: str, name: str = None) -> bool:
    """Check availability of a tool."""
    if shutil.which(bin_name) is None:
        if name is None:
            name = bin_name
        print('{} not found.'.format(name))
        return False
    return True


def _check_tool(cfg: config.Config, bin_name: str, name: str,
                min_version: Version) -> bool:
    """Check availability and version of a tool."""
    _check_availability(bin_name, name)
    bin_path = shutil.which(bin_name)
    ver_line = execution.run_stdout([bin_name, '--version'])[0]
    assert '{} version'.format(bin_name) in ver_line
    ver = _str_to_ver(ver_line.split(' ')[-1])
    if ver < min_version:
        _print_version_error(name, bin_path, ver, min_version)
        return False
    if cfg.verbose:
        logging.info('Found %s version %s', name, ver)
    return True


def check_prerequisites(cfg: config.Config) -> None:
    """Check availability and versions of all required prerequisite software."""
    is_ok = True
    is_ok = is_ok and _check_host_compiler(cfg)
    is_ok = is_ok and _check_tool(cfg, 'cmake', 'CMake', MIN_CMAKE_VERSION)
    if cfg.use_ccache:
        is_ok = is_ok and _check_tool(cfg, 'ccache', 'CCache',
                                      MIN_CCACHE_VERSION)
    if cfg.use_ninja:
        is_ok = is_ok and _check_availability('ninja', 'Ninja')
    for tool in ['git', 'make', 'find', 'sort', 'tar', 'sed']:
        is_ok = is_ok and _check_availability(tool)
    if not is_ok:
        logging.error('Prerequisites check failed')
        raise util.ToolchainBuildError
