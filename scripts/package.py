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
from typing import FrozenSet
import tarfile
import zipfile

import config
from config import PackageFormat
import util


def write_version_file(cfg: config.Config) -> None:
    """Create VERSION.txt in the install directory."""
    dest = os.path.join(cfg.target_llvm_dir, 'VERSION.txt')
    if cfg.verbose:
        logging.info('Writing "%s" to %s', cfg.version_string, dest)
    util.write_lines([cfg.version_string], dest)


def _get_excluded_symlinks(cfg: config.Config) -> FrozenSet[str]:
    """Get a list of symlinks that should be excluded when symlinks are
       converted to copies (i.e. when targeting Windows or using zip as archive
       format). """
    excludes = [
        'clang-cl',  # MSVC-compatible Clang driver
        'ld64.lld',  # Darwin (Mach-O) linker
        'ld64.lld.darwinold',  # Old Darwin (Mach-O) linker
        'ld64.lld.darwinnew',  # New Darwin (Mach-O) linker
        'lld-link',  # Windows (COFF) linker
        'wasm-ld',   # WebAssembly linker
    ]
    if cfg.is_cross_compiling:
        excludes = [name + '.exe' for name in excludes]
    return frozenset(excludes)


def _create_tarball(cfg: config.Config, dest_pkg: str) -> None:
    """Create a tarball package."""
    def reset_uid(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
        tarinfo.uid = tarinfo.gid = 0
        tarinfo.uname = tarinfo.gname = 'root'
        return tarinfo
    exclude_set: FrozenSet[str] = frozenset()
    dereference = False
    if cfg.is_cross_compiling:
        exclude_set = _get_excluded_symlinks(cfg)
        dereference = True
    with tarfile.open(dest_pkg, 'w:gz') as dest:
        for root, _, files in os.walk(cfg.target_llvm_dir):
            for fname in sorted(files):
                if fname in exclude_set:
                    continue
                abs_path = os.path.join(root, fname)
                arc_name = os.path.relpath(abs_path, cfg.install_dir)
                if cfg.verbose:
                    logging.info('Compressing %s', arc_name)
                if dereference and os.path.islink(abs_path):
                    abs_path = os.path.realpath(abs_path)
                dest.add(abs_path, arc_name, recursive=False,
                         filter=reset_uid)


def _create_zip(cfg: config.Config, dest_pkg: str) -> None:
    """Create a zip package."""
    exclude_set = _get_excluded_symlinks(cfg)
    with zipfile.ZipFile(dest_pkg, 'w', zipfile.ZIP_DEFLATED) as dest:
        for root, _, files in os.walk(cfg.target_llvm_dir):
            for fname in files:
                if fname in exclude_set:
                    continue
                abs_path = os.path.join(root, fname)
                arc_name = os.path.relpath(abs_path, cfg.install_dir)
                if cfg.verbose:
                    logging.info('Compressing %s', arc_name)
                dest.write(abs_path, arc_name)


def package_toolchain(cfg: config.Config) -> None:
    """Create a package with a newly built toolchain."""
    if not os.path.exists(cfg.package_dir):
        os.makedirs(cfg.package_dir)
    format_mapping = {
        PackageFormat.TGZ: ('.tar.gz', _create_tarball),
        PackageFormat.ZIP: ('.zip', _create_zip),
    }
    package_ext, package_fn = format_mapping[cfg.package_format]
    dest_pkg = os.path.join(cfg.package_dir,
                            cfg.package_base_name + package_ext)
    logging.info('Creating package %s', dest_pkg)
    try:
        package_fn(cfg, dest_pkg)
    except RuntimeError as ex:
        logging.error('Failed to create %s', dest_pkg)
        raise util.ToolchainBuildError from ex
