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
import subprocess

import config
import execution
import util


def write_version_file(cfg: config.Config) -> None:
    """Create VERSION.txt in the install directory."""
    dest = os.path.join(cfg.target_llvm_dir, 'VERSION.txt')
    if cfg.verbose:
        logging.info('Writing "%s" to %s', cfg.version_string, dest)
    util.write_lines([cfg.version_string], dest)


def package_toolchain(cfg: config.Config) -> None:
    """Create a tarball with a newly built toolchain."""
    if not os.path.exists(cfg.package_dir):
        os.makedirs(cfg.package_dir)
    dest_bin = os.path.join(cfg.package_dir, cfg.tarball_base_name + '.tar.gz')
    logging.info('Creating package %s', dest_bin)
    args = [
        'tar',
        '--create',
        '--file={}'.format(dest_bin),
        '-a',
        '--owner=root',
        '--group=root',
    ]
    if cfg.verbose:
        args.append('--verbose')
    args.append(os.path.relpath(cfg.target_llvm_dir, cfg.install_dir))
    try:
        execution.run(args, cwd=cfg.install_dir, verbose=cfg.verbose)
    except subprocess.CalledProcessError as ex:
        logging.error('Failed to create %s', dest_bin)
        raise util.ToolchainBuildError from ex
