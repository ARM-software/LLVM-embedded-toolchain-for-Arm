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
import functools
import logging
import multiprocessing
import os
import sys
import shutil
from typing import Callable, Optional

import cfg_files
import check
import config
from config import Action, BuildMode, CheckoutMode, CopyRuntime, Config
import make
import repos
import tarball
import util


def parse_args_to_config() -> Config:
    """Parse command line arguments and create a Config object based on them.
    """
    cwd = os.path.abspath(os.getcwd())
    parser = argparse.ArgumentParser(
        description='Build LLVM Embedded Toolchain for Arm',
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument('-v', '--verbose', help='log more information',
                        action='store_true')
    parser.add_argument('-r', '--revision', metavar='R', default='0.1',
                        help='revision to build (default: 0.1)')
    variant_names = sorted(config.LIBRARY_SPECS.keys())
    parser.add_argument('--variants', metavar='VAR', nargs='+',
                        choices=variant_names + ['all'], default=['all'],
                        help='library variants to build, a space-separated '
                             'list of: {}, or "all" to build all variants. '
                             'Default: all'.format(', '.join(variant_names)))
    parser.add_argument('--source-dir', type=str, metavar='PATH', default=cwd,
                        help='location of the LLVM Embedded '
                             'Toolchain for Arm source checkout (default: .)')
    parser.add_argument('--build-dir', type=str, metavar='PATH',
                        help='directory to use for build '
                             '(default: ./build-<revision>)')
    parser.add_argument('--install-dir', type=str, metavar='PATH',
                        help='directory to install the toolchain to '
                             '(default: ./install-<revision>)')
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
    native_toolchain_kinds = [
        config.ToolchainKind.CLANG.value,
        config.ToolchainKind.GCC.value,
    ]
    parser.add_argument('--native-toolchain', type=str,
                        choices=native_toolchain_kinds,
                        default=default_toolchain,
                        help='native toolchain type '
                             '(default: {})'.format(default_toolchain))
    parser.add_argument('--native-toolchain-dir', type=str, metavar='PATH',
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
    parser.add_argument('--copy-runtime-dlls', type=str,
                        choices=util.values_of_enum(CopyRuntime),
                        default=CopyRuntime.ASK.value,
                        help='specifies whether or not Mingw-w64 runtime DLLs '
                             'should be included in the toolchain package '
                             'when cross-compiling for Windows '
                             '(default: ask):\n'
                             '  no - don\'t include runtime DLLs in the '
                             'package\n'
                             '  yes - copy runtime DLLs from the local '
                             'machine\n'
                             '  ask - ask the user before starting the build')
    cpu_count = multiprocessing.cpu_count()
    parser.add_argument('-j', '--parallel', type=int, metavar='N',
                        help='number of parallel threads to use in Make/Ninja '
                        '(default: number of CPUs, {})'.format(cpu_count),
                        default=cpu_count)
    parser.add_argument('actions', nargs=argparse.REMAINDER,
                        choices=util.values_of_enum(Action),
                        help='actions to perform, a list of:\n'
                             '  prepare - check out and patch sources\n'
                             '  clang - build and install Clang, lld and '
                             'other binary utilities\n'
                             '  newlib - build and install newlib for each '
                             'target\n'
                             '  compiler-rt - build and install compiler-rt '
                             'for each target\n'
                             '  libcxx - build and install libc++abi and '
                             'libc++ for each target\n'
                             '  configure - write target configuration files\n'
                             '  package - create tarball\n'
                             '  all - perform all of the above\n'
                             '  test - run tests\n'
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
    if cfg.is_cross_compiling:
        run_or_skip(cfg, Action.CLANG, builder.build_native_tools,
                    'Native LLVM tools')
    run_or_skip(cfg, Action.CLANG, builder.build_clang, 'Clang build')
    if any(action in cfg.actions for action in
           [Action.NEWLIB, Action.COMPILER_RT, Action.LIBCXX,
            Action.CONFIGURE]):
        logging.info('Building library variants and/or configurations: %s',
                     ', '.join(v.name for v in cfg.variants))

    for lib_spec in cfg.variants:
        run_or_skip(cfg, Action.NEWLIB,
                    functools.partial(builder.build_newlib, lib_spec),
                    'newlib build for {}'.format(lib_spec.name))
        run_or_skip(cfg, Action.COMPILER_RT,
                    functools.partial(builder.build_compiler_rt, lib_spec),
                    'compiler-rt build for {}'.format(lib_spec.name))
        run_or_skip(cfg, Action.LIBCXX,
                    functools.partial(builder.build_cxx_libraries, lib_spec),
                    'libc++/libc++abi build for {}'.format(lib_spec.name))
        run_or_skip(cfg, Action.CONFIGURE,
                    functools.partial(cfg_files.configure_target, cfg,
                                      lib_spec),
                    'generation of config files for {}'.format(lib_spec.name))


def run_tests(cfg: Config) -> None:
    """Potentially run tests depending on which configuration is used
    """
    builder = make.ToolchainBuild(cfg)
    # Can grow if we add support for testing of more variants.
    # Currently, armv6m is hard coded in the smoke test's Makefile.
    testable_variants = set(["armv6m"])
    variants_to_test = [i for i in cfg.variants
                        if i.march in testable_variants]

    # Each tested variant throws an exception if any of its tests fails.
    # Here these exceptions are caught so that all variants tests are run.
    # Finally, if any test across all variants has failed, this failure is
    # propagated upwards via an exception.
    success = True

    for variant in variants_to_test:
        try:
            run_or_skip(cfg, Action.TEST,
                        functools.partial(builder.run_tests, variant),
                        'tests run for {}'.format(variant.name))
        except util.ToolchainBuildError:
            success = False

    if not success:
        raise util.ToolchainBuildError


def ask_about_runtime_dlls(cfg: Config) -> Optional[bool]:
    """Ask the user if they want to copy the Mingw-w64 runtime DLLs from the
       local machine to the toolchain 'bin' directory.
    """
    print('LLVM Embedded Toolchain for Arm requires several runtime libraries '
          'to be\n'
          'installed on the host machine. These libraries can be copied from '
          'your local\n'
          'machine to the toolchain distribution being built.\n'
          '\n'
          'If you intend to redistribute the toolchain, you must comply with '
          'the licenses\n'
          'of the projects that provide these runtime libraries:\n'
          '* GCC (https://gcc.gnu.org/)\n'
          '* Mingw-w64 (http://mingw-w64.org/)\n'
          '\n'
          'Please specify if you want to copy the following libraries from '
          'your local\n'
          'machine to the "bin" directory of the toolchain and include them '
          'in the packaged\n'
          'toolchain archive:')
    dlls = make.RuntimeDLLs(cfg)
    for dll_name, dll_path in dlls.get_runtime_dll_paths():
        print('* {} ({})'.format(dll_name, dll_path))
    print('\n'
          'Note: to avoid being asked this question please add '
          '"--copy-runtime-dlls yes"\n'
          'or "--copy-runtime-dlls no" to the build.py command line\n')
    while True:
        answer = input('Copy the libraries? ([c]ancel/[y]es/[n]o): ').lower()
        if answer.lower() in ['y', 'yes']:
            return True
        if answer.lower() in ['n', 'no']:
            return False
        if answer.lower() in ['', 'c', 'cancel']:
            return None
        print('Expected one of: "y", "yes", "n", "no", "", "c", cancel"')


def main() -> int:
    util.configure_logging()
    cfg = parse_args_to_config()
    versions = repos.get_all_versions(os.path.join(cfg.source_dir,
                                                   'versions.yml'))
    if cfg.revision not in versions:
        logging.error('Invalid revision %s', cfg.revision)
        return 1

    try:
        if (cfg.host_toolchain.kind == config.ToolchainKind.MINGW
                and cfg.ask_copy_runtime_dlls):
            res = ask_about_runtime_dlls(cfg)
            if res is None:
                return 1
            cfg.copy_runtime_dlls = res

        if not cfg.skip_checks:
            check.check_prerequisites(cfg)
        run_or_skip(cfg, Action.PREPARE,
                    lambda: prepare_repositories(cfg, versions[cfg.revision]),
                    'source code checkout')
        build_all(cfg)
        run_tests(cfg)

        def do_package():
            tarball.write_version_file(cfg)
            tarball.package_toolchain(cfg)
        run_or_skip(cfg, Action.PACKAGE, do_package, 'packaging')
    except util.ToolchainBuildError:
        # By this time the error must have already been logged
        return 1
    except KeyboardInterrupt:
        sys.stdout.write('\n')
        logging.info('Build interrupted by user')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
