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
from typing import FrozenSet, Optional
import tarfile
import zipfile

import config
from config import PackageFormat
import repos
import util


def _write_version_file(cfg: config.Config, version: repos.LLVMBMTC,
                        target_dir: str) -> None:
    """Create VERSION.txt in the install directory."""
    dest = os.path.join(target_dir, 'VERSION.txt')
    toolchain_ver = 'LLVM Embedded Toolchain for Arm ' + cfg.version_string
    if cfg.verbose:
        logging.info('Writing "%s" to %s', toolchain_ver, dest)
    lines = [toolchain_ver, '', 'Components:']
    for name in sorted(version.modules.keys()):
        comp_info = version.modules[name].checkout_info
        lines.append('* {}'.format(comp_info))
        if cfg.verbose:
            logging.info('Writing component %s info: "%s"', name, comp_info)
    util.write_lines(lines, dest)


def _write_versions_yml(cfg: config.Config, dest_dir: str) -> None:
    """Create versions.yml for a source package."""
    dest_file = os.path.join(dest_dir, 'versions.yml')
    logging.info('Creating %s', dest_file)
    with open(dest_file, 'wt') as out_f:
        source_type = config.SourceType.SOURCE_PACKAGE.value
        out_f.write('---\n'
                    'SourceType: "{}"\n'
                    'Revision: "{}"\n'.format(source_type, cfg.revision))


def _force_copy(src: str, dest: str, name: str, ignore=None) -> None:
    """Remove 'dest/name' if it exists and copy 'src/name' to 'dest/name'."""
    src = os.path.join(src, name)
    dest = os.path.join(dest, name)
    logging.info('Copying "%s" to "%s"', src, dest)
    if os.path.exists(dest):
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        else:
            os.remove(dest)
    if os.path.isdir(src):
        shutil.copytree(src, dest, ignore=ignore)
    else:
        shutil.copy2(src, dest)


def _copy_samples(cfg: config.Config) -> None:
    """Copy code samples, filter out files that are not usable on the target
       platform."""
    if cfg.is_windows:
        # We don't filter out Makefile and Makefile.conf because we support
        # using Windows+MSYS2
        ignore = shutil.ignore_patterns('.gitignore')
    else:
        # make.bat is useless on Linux/Mac
        ignore = shutil.ignore_patterns('.gitignore', 'make.bat')
    _force_copy(cfg.source_dir, cfg.target_llvm_dir, 'samples', ignore)


def _copy_docs(cfg: config.Config) -> None:
    """Copy documentation."""
    _force_copy(cfg.source_dir, cfg.target_llvm_dir, 'docs')
    _force_copy(cfg.source_dir, cfg.target_llvm_dir, 'README.md')


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
    if cfg.is_windows:
        excludes = [name + '.exe' for name in excludes]
    return frozenset(excludes)


def _create_tarball(cfg: config.Config, src_dir: str, dest_pkg: str) -> None:
    """Create a tarball package."""
    def reset_uid(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo:
        tarinfo.uid = tarinfo.gid = 0
        tarinfo.uname = tarinfo.gname = 'root'
        return tarinfo
    exclude_set: FrozenSet[str] = frozenset()
    dereference = False
    if cfg.is_windows:
        exclude_set = _get_excluded_symlinks(cfg)
        dereference = True
    with tarfile.open(dest_pkg, 'w:gz') as dest:
        for root, _, files in os.walk(src_dir):
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


def _create_zip(cfg: config.Config, src_dir: str, dest_pkg: str) -> None:
    """Create a zip package."""
    exclude_set = _get_excluded_symlinks(cfg)
    with zipfile.ZipFile(dest_pkg, 'w', zipfile.ZIP_DEFLATED) as dest:
        for root, _, files in os.walk(src_dir):
            for fname in files:
                if fname in exclude_set:
                    continue
                abs_path = os.path.join(root, fname)
                arc_name = os.path.relpath(abs_path, cfg.install_dir)
                if cfg.verbose:
                    logging.info('Compressing %s', arc_name)
                dest.write(abs_path, arc_name)


def _create_archive(cfg: config.Config, pkg_src_dir, pkg_dest_name) -> None:
    """Create a package from a given directory."""
    if not os.path.exists(cfg.package_dir):
        os.makedirs(cfg.package_dir)
    format_mapping = {
        PackageFormat.TGZ: ('.tar.gz', _create_tarball),
        PackageFormat.ZIP: ('.zip', _create_zip),
    }
    package_ext, package_fn = format_mapping[cfg.package_format]
    dest_pkg = os.path.join(cfg.package_dir, pkg_dest_name + package_ext)
    logging.info('Creating package %s', dest_pkg)
    try:
        package_fn(cfg, pkg_src_dir, dest_pkg)
    except RuntimeError as ex:
        logging.error('Failed to create %s', dest_pkg)
        raise util.ToolchainBuildError from ex


def create_binary_package(cfg: config.Config,
                          version: Optional[repos.LLVMBMTC]) -> None:
    """Create a binary package with a newly built toolchain."""
    if cfg.is_source_package:
        _force_copy(cfg.source_dir, cfg.target_llvm_dir, 'VERSION.txt')
    else:
        assert version is not None
        _write_version_file(cfg, version, cfg.target_llvm_dir)
    _copy_samples(cfg)
    _copy_docs(cfg)
    _create_archive(cfg, cfg.target_llvm_dir, cfg.bin_package_base_name)


def create_source_package(cfg: config.Config, version: repos.LLVMBMTC) -> None:
    """Create a source package with a newly built toolchain."""
    if os.path.exists(cfg.install_src_subdir):
        logging.info('Removing existing directory %s', cfg.install_src_subdir)
        shutil.rmtree(cfg.install_src_subdir)
    os.makedirs(cfg.install_src_subdir)
    repos.export_repository(cfg.source_dir, cfg.install_src_subdir, False)
    repos.export_toolchain_repositories(cfg.repos_dir, version,
                                        cfg.install_src_subdir)
    _write_version_file(cfg, version, cfg.install_src_subdir)
    _write_versions_yml(cfg, cfg.install_src_subdir)
    _create_archive(cfg, cfg.install_src_subdir, cfg.src_package_base_name)
