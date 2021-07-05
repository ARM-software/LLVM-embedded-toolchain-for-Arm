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

import logging
import os
import shutil

import config
import util


def _get_base_ld_name(lib_spec: config.LibrarySpec) -> str:
    ld_name = {'arm': 'base_arm.ld',
               'aarch64': 'base_aarch64.ld'}[lib_spec.triple_arch]
    return ld_name


def copy_base_ld_script(cfg: config.Config, lib_spec: config.LibrarySpec) \
        -> None:
    """Copy the linker script to target-specific directory."""
    ld_name = _get_base_ld_name(lib_spec)
    base_ld_src = os.path.join(cfg.source_dir, 'ldscript', ld_name)
    base_ld_dest = os.path.join(cfg.target_llvm_rt_dir, lib_spec.name,
                                ld_name)
    if cfg.verbose:
        logging.info('Copying %s to %s', base_ld_src, base_ld_dest)
    shutil.copy(base_ld_src, base_ld_dest)


def write_cfg_files(cfg: config.Config, lib_spec: config.LibrarySpec) -> None:
    """Create target-specific configuration files for a single library
       variant."""
    target = lib_spec.target
    base_cfg_lines = [
        '--target={}'.format(target),
        lib_spec.flags,
        '-fuse-ld=lld',
        '-fno-exceptions -fno-rtti',
        '--sysroot $@/../lib/clang-runtimes/{}'.format(lib_spec.name)
    ]

    # No semihosting and no linker script
    nosys_lines = base_cfg_lines + [
        '$@/../lib/clang-runtimes/{}/lib/crt0.o'.format(lib_spec.name),
        '-lnosys',
    ]
    # Semihosting and linker script provided
    rdimon_lines = base_cfg_lines + [
        '-Wl,-T$@/../lib/clang-runtimes/{}/{}'.format(
            lib_spec.name,
            _get_base_ld_name(lib_spec)),
        '$@/../lib/clang-runtimes/{}/lib/rdimon-crt0.o'.format(lib_spec.name),
        '-lrdimon',
    ]
    # Semihosting, but no linker script, e.g. to use with QEMU Arm System
    # emulator
    rdimon_baremetal_lines = base_cfg_lines + [
        '$@/../lib/clang-runtimes/{}/lib/rdimon-crt0.o'.format(lib_spec.name),
        '-lrdimon',
    ]

    cfg_files = [
        ('nosys', nosys_lines),
        ('rdimon', rdimon_lines),
        ('rdimon_baremetal', rdimon_baremetal_lines),
    ]

    for name, lines in cfg_files:
        file_name = '{}_{}.cfg'.format(lib_spec.name, name)
        file_path = os.path.join(cfg.target_llvm_bin_dir, file_name)
        if cfg.verbose:
            logging.info('Writing %s', file_path)
        util.write_lines(lines, file_path)


def configure_target(cfg: config.Config, lib_spec: config.LibrarySpec) -> None:
    """Create linker script and configuration files for a single library
       variant."""
    logging.info('Creating toolchain configuration files')
    copy_base_ld_script(cfg, lib_spec)
    write_cfg_files(cfg, lib_spec)
