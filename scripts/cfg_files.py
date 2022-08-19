# Copyright (c) 2021-2022, Arm Limited and affiliates.
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

import logging
import os

import config
import util


def write_cfg_files(cfg: config.Config, lib_spec: config.LibrarySpec) -> None:
    """Create target-specific configuration files for a single library
       variant."""

    sysroot = f'<CFGDIR>/../lib/clang-runtimes/{lib_spec.name}'

    base_cfg_lines = [
        lib_spec.flags,
        '-fuse-ld=lld',
        # libc++ is built with LIBCXX_ENABLE_EXCEPTIONS=OFF
        # and we don't build libunwind
        '-fno-exceptions',
        # libc++ is built with LIBCXX_ENABLE_RTTI=OFF
        '-fno-rtti',
        f'--sysroot {sysroot}',
    ]

    no_semihost_lines = base_cfg_lines + [
        f'{sysroot}/lib/crt0.o',
    ]

    semihost_lines = base_cfg_lines + [
        f'{sysroot}/lib/crt0-semihost.o',
        '-lsemihost',
    ]

    cfg_files = [
        ('', no_semihost_lines),
        ('_semihost', semihost_lines),
    ]

    for suffix, lines in cfg_files:
        file_name = f'{lib_spec.name}{suffix}.cfg'
        file_path = os.path.join(cfg.target_llvm_bin_dir, file_name)
        if cfg.verbose:
            logging.info('Writing %s', file_path)
        util.write_lines(lines, file_path)


def configure_target(cfg: config.Config, lib_spec: config.LibrarySpec) -> None:
    """Create linker script and configuration files for a single library
       variant."""
    logging.info('Creating toolchain configuration files')
    write_cfg_files(cfg, lib_spec)
