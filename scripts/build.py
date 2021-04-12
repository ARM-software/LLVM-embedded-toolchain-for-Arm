#!/usr/bin/env python3

#
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
#

import argparse
import logging
import multiprocessing
import os
import sys
import shutil
from typing import Callable

import cfg_files
import check
import config
from config import Action, BuildMode, CheckoutMode, Config
import make
import repos
import tarball
import util


def parse_args_to_config() -> Config:
    """Parse command line arguments and create a Config object based on them."""
    cwd = os.path.abspath(os.getcwd())
    parser = argparse.ArgumentParser(
        description='Build LLVM Embedded Toolchain for Arm',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument('-v', '--verbose', help='log more information',
                        action='store_true')
    parser.add_argument('-r', '--revision', metavar='R', default='HEAD',
                        help='revision to build (default: HEAD)')
    variant_names = sorted(config.LIBRARY_SPECS.keys())
    parser.add_argument('--variants', metavar='VAR', nargs='+',
                        choices=variant_names + ['all'], default=['all'],
                        help='library variants to build, a space-separated '
                             'list of: {}, or "all" to build all variants. '
                             'Default: all'.format(', '.join(variant_names)))
    parser.add_argument('--source-dir', type=str, metavar='PATH', default=cwd,
                        help='location of the LLVM Embedded '
                             'Toolchain for Arm source checkout (default: .)')
    parser.add_argument('--build-dir', type=str,  metavar='PATH',
                        help='directory to use for build '
                             '(default: ./build-<revision>)')
    parser.add_argument('--install-dir', type=str, metavar='PATH',
                        default=cwd,
                        help='directory to install the toolchain to '
                             '(default: .)')
    parser.add_argument('--package-dir', type=str, metavar='PATH',
                        default=cwd,
                        help='directory to store the packaged toolchain in '
                             '(default: .)')
    parser.add_argument('--repositories-dir', type=str, metavar='PATH',
                        help='path to directory containing LLVM and newlib '
                             'repositories (default: ./repos-<revision>)')
    default_toolchain = config.ToolchainKind.CLANG.value
    parser.add_argument('--host-toolchain', type=str,
                        choices=util.values_of_enum(config.ToolchainKind),
                        default=default_toolchain,
                        help='host toolchain type '
                             '(default: {})'.format(default_toolchain))
    parser.add_argument('--host-toolchain-dir', type=str, metavar='PATH',
                        default='/usr/bin',
                        help='path to the directory containing the host '
                             'compiler binary (default: /usr/bin)')
    parser.add_argument('--skip-checks',
                        help='skip checks of build prerequisites',
                        action='store_true')
    parser.add_argument('--use-ninja',
                        help='use Ninja instead of GNU Make when building '
                             'LLVM components',
                        action='store_true')
    parser.add_argument('--use-ccache',
                        help='use CCache when building Clang (requires '
                             'CCache v. {} or '
                             'later)'.format(check.MIN_CCACHE_VERSION),
                        action='store_true')
    parser.add_argument('--checkout-mode', type=str,
                        choices=util.values_of_enum(CheckoutMode),
                        default=CheckoutMode.REUSE.value,
                        help='specifies behaviour of repository checkout ('
                             'default: reuse):\n'
                             '  force - delete existing repositories, perform '
                             'a checkout and apply patches\n'
                             '  patch - check out only if one of repositories '
                             'is missing, otherwise perform a hard reset and '
                             'apply patches\n'
                             '  reuse - check out and apply patches only if '
                             'one of repositories is missing, otherwise use '
                             'the checkout as-is')
    parser.add_argument('--build-mode', type=str,
                        choices=util.values_of_enum(BuildMode),
                        default=BuildMode.INCREMENTAL.value,
                        help='specifies behaviour of incremental builds '
                             '(default: incremental):\n'
                             '  rebuild - build everything from scratch\n'
                             '  reconfigure - always rerun cmake/configure\n'
                             '  incremental - avoid rerunning cmake/configure')
    cpu_count = multiprocessing.cpu_count()
    parser.add_argument('-j', '--parallel', type=int, metavar='N',
                        help='number of parallel threads to use in Make/Ninja '
                        '(default: number of CPUs, {})'.format(cpu_count),
                        default=cpu_count)
    parser.add_argument('actions',  nargs=argparse.REMAINDER,
                        choices=util.values_of_enum(Action),
                        help='actions to perform, a list of:\n'
                             '  prepare - check out and patch sources\n'
                             '  clang - build and install Clang, lld and other '
                             'binary utilities\n'
                             '  newlib - build and install newlib for each '
                             'target\n'
                             '  compiler-rt - build and install compiler-rt '
                             'for each target\n'
                             '  configure - write target configuration files\n'
                             '  package - create tarball\n'
                             '  all - perform all of the above\n'
                             'Default: all')
    args = parser.parse_args()
    return config.Config(args)


def prepare_repositories(cfg: config.Config,
                         toolchain_ver: repos.LLVMBMTC) -> None:
    """Prepare source repositories according to the selected --checkout-mode
       option and the current state of repositories.
    """
    patches_dir = os.path.join(cfg.source_dir, 'patches')

    # Determine which git action to perform
    do_remove_and_clone = False
    do_reset_and_patch = False
    repo_dirs = [cfg.llvm_repo_dir, cfg.newlib_repo_dir]
    if cfg.checkout_mode == CheckoutMode.FORCE:
        # In the 'force' mode always remove existing checkouts, then clone the
        # repositories.
        do_remove_and_clone = True
    elif cfg.checkout_mode == CheckoutMode.PATCH:
        # In the 'patch' mode perform check out only when any of the
        # repositories is not checked out, otherwise reset and patch existing
        # repositories.
        if all(os.path.exists(repo_dir) for repo_dir in repo_dirs):
            do_reset_and_patch = True
        else:
            do_remove_and_clone = True
    elif cfg.checkout_mode == CheckoutMode.REUSE:
        # In the 'reuse' mode perform check out only when any of the
        # repositories is not checked out, otherwise do nothing
        if all(os.path.exists(repo_dir) for repo_dir in repo_dirs):
            logging.info('Using existing checked out repositories')
        else:
            do_remove_and_clone = True
    else:
        # We should never get here
        raise NotImplementedError('Unexpected checkout '
                                  'mode {}'.format(cfg.checkout_mode))

    # Perform selected action
    ret = 0
    if do_remove_and_clone:
        if os.path.exists(cfg.repos_dir):
            logging.info('Deleting checked out repositories')
            shutil.rmtree(cfg.repos_dir)
        logging.info('Cloning repositories and applying patches')
        ret = repos.clone_repositories(cfg.repos_dir, toolchain_ver,
                                       patches_dir)
    elif do_reset_and_patch:
        logging.info('Resetting repositories and applying patches')
        ret = repos.patch_repositories(cfg.repos_dir, toolchain_ver,
                                       patches_dir)
    if ret != 0:
        raise util.ToolchainBuildError


def run_or_skip(cfg: Config, action: Action, func: Callable[[], None],
                desc: str) -> None:
    """Run func if action is specified in cfg.actions, otherwise log that
       the step was skipped (only in verbose logs).
    """
    if action in cfg.actions:
        func()
    elif cfg.verbose:
        logging.info('Skipping %s (not requested by the user)', desc)


def build_all(cfg: Config) -> None:
    """Build and install all components of the toolchain: Clang and LLVM
       binutils, newlib, compiler_rt, configuration files.
    """
    builder = make.ToolchainBuild(cfg)
    run_or_skip(cfg, Action.CLANG, builder.build_clang, 'Clang build')
    if any(action in cfg.actions for action in
           [Action.NEWLIB, Action.COMPILER_RT, Action.CONFIGURE]):
        logging.info('Building library variants and/or configurations: %s',
                     ', '.join(v.name for v in cfg.variants))

    for lib_spec in cfg.variants:
        run_or_skip(cfg, Action.NEWLIB,
                    lambda lspec=lib_spec: builder.build_newlib(lspec),
                    'newlib build for {}'.format(lib_spec.name))
        run_or_skip(cfg, Action.COMPILER_RT,
                    lambda lspec=lib_spec: builder.build_compiler_rt(lspec),
                    'compiler-rt build for {}'.format(lib_spec.name))
        run_or_skip(cfg, Action.CONFIGURE,
                    lambda lspec=lib_spec: cfg_files.configure_target(cfg,
                                                                      lspec),
                    'generation of config files for {}'.format(lib_spec.name))


def main() -> int:
    util.configure_logging()
    cfg = parse_args_to_config()
    versions = repos.get_all_versions(os.path.join(cfg.source_dir,
                                                   'versions.yml'))
    if cfg.revision not in versions:
        logging.error('Invalid revision %s', cfg.revision)
        return 1

    try:
        if not cfg.skip_checks:
            check.check_prerequisites(cfg)
        run_or_skip(cfg, Action.PREPARE,
                    lambda: prepare_repositories(cfg, versions[cfg.revision]),
                    'source code checkout')
        build_all(cfg)

        def do_package():
            tarball.write_version_file(cfg)
            tarball.package_toolchain(cfg)
        run_or_skip(cfg, Action.PACKAGE, do_package, 'packaging')
    except util.ToolchainBuildError:
        # By this time the error must have already been logged
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
