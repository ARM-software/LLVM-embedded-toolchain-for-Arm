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
import re
import shutil
from typing import Optional
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
MIN_GCC_VERSION = Version(5, 1, 0)
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


def _check_compiler_version(cfg: config.Config, toolchain: config.Toolchain,
                            role: str, ver: Version, min_ver: Version) -> bool:
    if ver < min_ver:
        _print_version_error(toolchain.kind.pretty_name,
                             toolchain.c_compiler, ver, min_ver)
        return False
    if cfg.verbose:
        logging.info('Using %s toolchain: %s version %s', role,
                     toolchain.kind.pretty_name, ver)
    return True


def _parse_clang_version(c_compiler: str) -> Optional[Version]:
    args = [c_compiler, '--version']
    ver_line = execution.run_stdout(args)[0]
    # Example output:
    # Ubuntu 20.04: clang version 10.0.0-4ubuntu1
    # Ubuntu 18.04: clang version 6.0.0-1ubuntu2 (tags/RELEASE_600/final)
    # Ubuntu 16.04: clang version 3.8.0-2ubuntu4 (tags/RELEASE_380/final)
    # Debian testing (bullseye): Debian clang version 11.0.1-2
    # Built from source: clang version 9.0.1
    # Remove distribution suffix (if any) and convert to a tuple
    assert ver_line.startswith('clang version ') \
        or ver_line.startswith('Debian clang version') \
        or ver_line.startswith('Apple clang version')
    ver_match = re.search(r'version ([0-9.]+)', ver_line)
    assert ver_match is not None
    return _str_to_ver(ver_match.group(1))


def _parse_gcc_version(c_compiler: str) -> Optional[Version]:
    args = [c_compiler, '--version']
    ver_line = execution.run_stdout(args)[0]
    # Example output:
    # Ubuntu 20.04: "gcc (Ubuntu 9.3.0-17ubuntu1~20.04) 9.3.0"
    # Ubuntu 16.04: "gcc (Ubuntu 5.5.0-12ubuntu1~16.04) 5.5.0 20171010"
    # Ubuntu 20.04 mingw: "x86_64-w64-mingw32-gcc (GCC) 9.3-win32 20200320"
    # Ubuntu 16.04 mingw: "x86_64-w64-mingw32-gcc (GCC) 5.3.1 20160211"
    # RHEL 7.6: "gcc (GCC) 4.8.5 20150623 (Red Hat 4.8.5-36)"
    ver_rex = re.compile(r'(\d+\.\d+(?:\.\d+)?)(?:-.*)')
    for part in ver_line.split(' '):
        match = ver_rex.match(part)
        if match is not None:
            ver_str = match.group(1)
            break
    else:
        logging.error('Failed to parse GCC version "%s"', ver_rex)
        return None
    return _str_to_ver(ver_str)


def _check_toolchain(cfg: config.Config, toolchain: config.Toolchain,
                     role: str) -> bool:
    """Check availability and version of the host compiler (Clang or GCC
       depending on build configuration).
    """
    def check_compiler_executable(executable_path):
        if not os.path.exists(executable_path):
            logging.error('The specified toolchain path %s is '
                          'invalid: %s not found', toolchain.toolchain_dir,
                          executable_path)
            return False
        return True

    if not check_compiler_executable(toolchain.c_compiler):
        return False
    if not check_compiler_executable(toolchain.cpp_compiler):
        return False

    if toolchain.kind == config.ToolchainKind.CLANG:
        ver = _parse_clang_version(toolchain.c_compiler)
        min_ver = MIN_CLANG_VERSION
    else:
        assert toolchain.kind in [config.ToolchainKind.GCC,
                                  config.ToolchainKind.MINGW]
        ver = _parse_gcc_version(toolchain.c_compiler)
        min_ver = MIN_GCC_VERSION

    if ver is None:
        return False

    return _check_compiler_version(cfg, toolchain, role, ver, min_ver)


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
    if not _check_availability(bin_name, name):
        return False
    bin_path = shutil.which(bin_name)
    assert bin_path is not None
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
    """Check availability and versions of all required prerequisite software.
    """
    is_ok = True
    is_ok = is_ok and _check_toolchain(cfg, cfg.host_toolchain, 'host')
    if cfg.is_cross_compiling:
        is_ok = is_ok and _check_toolchain(cfg, cfg.native_toolchain, 'native')
    is_ok = is_ok and _check_tool(cfg, 'cmake', 'CMake', MIN_CMAKE_VERSION)
    if cfg.use_ccache:
        is_ok = is_ok and _check_tool(cfg, 'ccache', 'CCache',
                                      MIN_CCACHE_VERSION)
    if cfg.use_ninja:
        is_ok = is_ok and _check_availability('ninja', 'Ninja')
    for tool in ['git', 'make', 'find', 'sort', 'sed']:
        is_ok = is_ok and _check_availability(tool)
    if not is_ok:
        logging.error('Prerequisites check failed')
        raise util.ToolchainBuildError
