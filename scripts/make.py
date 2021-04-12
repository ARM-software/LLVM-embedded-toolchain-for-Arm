#  Copyright (c) 2021, Arm Limited and affiliates.
#  SPDX-License-Identifier: Apache-2.0
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import logging
import os
from typing import Mapping
import subprocess
import shutil

import execution
import config
import util


class ToolchainBuild:
    """Class for configuring/building/installing all toolchain components: LLVM,
       newlib, compiler_rt.
    """
    def __init__(self, cfg: config.Config):
        self.cfg = cfg
        self.runner = execution.Runner(cfg.verbose)

    def _cmake_configure(self, source_dir: str, build_dir: str,
                         defs: Mapping[str, str],
                         env: Mapping[str, str] = None) -> None:
        """Run the "configure" stage of CMake."""
        cmake_args = [
            'cmake',
            '-G', self.cfg.cmake_generator,
            source_dir,
        ]
        for def_name in sorted(defs.keys()):
            cmake_args.append('-D{}={}'.format(def_name, defs[def_name]))
        try:
            self.runner.run(cmake_args, cwd=build_dir, env=env)
        except subprocess.CalledProcessError as ex:
            raise util.ToolchainBuildError from ex

    def _cmake_build(self, build_dir: str, target: str = None) -> None:
        """Run a build tool (GNU Make or Ninja) using 'cmake --build'."""
        args = [
            'cmake',
            '--build', build_dir,
            '--parallel', str(self.cfg.num_threads),
        ]
        if target is not None:
            args += ['--target', target]
        try:
            self.runner.run(args)
        except subprocess.CalledProcessError as ex:
            raise util.ToolchainBuildError from ex

    def _write_llvm_index(self) -> None:
        """Record the list of files and links installed by Clang."""
        flist = []
        install_dir = self.cfg.target_llvm_dir
        for root, _, files in os.walk(install_dir):
            for fname in files:
                full_path = os.path.abspath(os.path.join(root, fname))
                if os.path.isfile(full_path) or os.path.islink(full_path):
                    flist.append(os.path.relpath(full_path, install_dir))
        util.write_lines(sorted(flist),
                         os.path.join(self.cfg.build_dir, 'llvm-index.txt'))

    def _prepare_build_dir(self, build_dir):
        if (self.cfg.build_mode == config.BuildMode.REBUILD
                and os.path.exists(build_dir)):
            if self.cfg.verbose:
                logging.info('Deleting build directory %s', build_dir)
            shutil.rmtree(build_dir)
        if not os.path.exists(build_dir):
            os.makedirs(build_dir)

    def build_clang(self) -> None:
        """Build and install Clang, LLD and LLVM binutils-like tools."""
        self.runner.reset_cwd()
        cfg = self.cfg
        llvm_source_dir = os.path.join(cfg.llvm_repo_dir, 'llvm')
        llvm_build_dir = os.path.join(cfg.build_dir, 'llvm')
        self._prepare_build_dir(llvm_build_dir)

        projects = [
            'clang',
            'lld',
        ]

        dist_comps = [
            'clang-format',
            'clang-resource-headers',
            'clang',
            'dsymutil',
            'lld',
            'llvm-ar',
            'llvm-config',
            'llvm-cov',
            'llvm-cxxfilt',
            'llvm-dwarfdump',
            'llvm-nm',
            'llvm-objdump',
            'llvm-profdata',
            'llvm-ranlib',
            'llvm-readelf',
            'llvm-readobj',
            'llvm-size',
            'llvm-strip',
            'llvm-symbolizer',
            'LTO',
        ]

        cmake_defs = {
            'LLVM_TARGETS_TO_BUILD:STRING': 'ARM',
            'LLVM_DEFAULT_TARGET_TRIPLE:STRING': cfg.default_target,
            'CMAKE_BUILD_TYPE:STRING': 'Release',
            'CMAKE_INSTALL_PREFIX:STRING': cfg.target_llvm_dir,
            'LLVM_ENABLE_PROJECTS:STRING': ';'.join(projects),
            'LLVM_DISTRIBUTION_COMPONENTS:STRING': ';'.join(dist_comps),
        }
        if cfg.use_ccache:
            cmake_defs['LLVM_CCACHE_BUILD:BOOL'] = 'ON'

        cmake_env = {
            'CC': cfg.host_toolchain.c_compiler,
            'CXX': cfg.host_toolchain.cpp_compiler,
        }

        if (os.path.exists(os.path.join(llvm_build_dir, 'CMakeCache.txt'))
                and cfg.skip_reconfigure):
            logging.info('LLVM CMakeCache.txt already exists, '
                         'skipping CMake configuration for LLVM')
        else:
            logging.info('Configuring LLVM projects: %s', ', '.join(projects))
            self._cmake_configure(llvm_source_dir, llvm_build_dir, cmake_defs,
                                  cmake_env)
        logging.info('Building and installing LLVM components: %s',
                     ', '.join(dist_comps))
        self._cmake_build(llvm_build_dir,
                          target='install-distribution-stripped')
        # Record the list of files and links installed by clang
        if cfg.release_mode:
            self._write_llvm_index()

    def build_compiler_rt(self, lib_spec: config.LibrarySpec) -> None:
        """Build and install a single variant of compiler-rt."""
        self.runner.reset_cwd()
        cfg = self.cfg
        target = lib_spec.target
        join = os.path.join
        rt_source_dir = join(cfg.llvm_repo_dir, 'compiler-rt')
        rt_build_dir = join(cfg.build_dir, 'compiler-rt', lib_spec.name)
        self._prepare_build_dir(rt_build_dir)
        rt_install_dir = join(cfg.target_llvm_rt_dir, target)
        cmake_defs = {
            'CMAKE_BUILD_TYPE:STRING': 'Release',
            'COMPILER_RT_BUILD_SANITIZERS:BOOL': 'OFF',
            'COMPILER_RT_BUILD_XRAY:BOOL': 'OFF',
            'COMPILER_RT_BUILD_LIBFUZZER:BOOL': 'OFF',
            'COMPILER_RT_BUILD_PROFILE:BOOL': 'OFF',
            'COMPILER_RT_BAREMETAL_BUILD:BOOL': 'ON',
            'CMAKE_TRY_COMPILE_TARGET_TYPE': 'STATIC_LIBRARY',
            'CMAKE_C_COMPILER_TARGET': target,
            'CMAKE_C_FLAGS': lib_spec.flags,
            'CMAKE_ASM_COMPILER_TARGET': target,
            'CMAKE_ASM_FLAGS': lib_spec.flags,
            'COMPILER_RT_DEFAULT_TARGET_ONLY': 'ON',
            'LLVM_CONFIG_PATH': join(cfg.build_dir, 'llvm', 'bin',
                                     'llvm-config'),
            'CMAKE_C_COMPILER': join(cfg.target_llvm_bin_dir, 'clang'),
            'CMAKE_AR': join(cfg.target_llvm_bin_dir, 'llvm-ar'),
            'CMAKE_NM': join(cfg.target_llvm_bin_dir, 'llvm-nm'),
            'CMAKE_RANLIB': join(cfg.target_llvm_bin_dir, 'llvm-ranlib'),
            'CMAKE_EXE_LINKER_FLAGS': '-fuse-ld=lld',
            'CMAKE_INSTALL_PREFIX': rt_install_dir,
        }
        if (os.path.exists(os.path.join(rt_build_dir, 'CMakeCache.txt'))
                and cfg.skip_reconfigure):
            logging.info('%s compiler-rt CMakeCache.txt already exists, '
                         'skipping CMake configuration', lib_spec.name)
        else:
            logging.info('Configuring compiler-rt for %s', lib_spec.name)
            self._cmake_configure(rt_source_dir, rt_build_dir, cmake_defs)
        logging.info('Building and installing compiler-rt for %s',
                     lib_spec.name)
        self._cmake_build(rt_build_dir)
        self._cmake_build(rt_build_dir, target='install')

        # Move the libraries from lib/linux to lib
        lib_dir = join(rt_install_dir, 'lib')
        linux_dir = join(lib_dir, 'linux')
        for name in os.listdir(linux_dir):
            assert name != 'linux'
            src = join(linux_dir, name)
            dest = join(lib_dir, name)
            if cfg.verbose:
                logging.info('Moving %s to %s', src, dest)
            shutil.move(src, dest)
        if cfg.verbose:
            logging.info('Removing %s', linux_dir)
        shutil.rmtree(linux_dir)

    def build_newlib(self, lib_spec: config.LibrarySpec) -> None:
        """Build and install a single variant of newlib."""
        self.runner.reset_cwd()
        cfg = self.cfg
        join = os.path.join
        newlib_src_dir = cfg.newlib_repo_dir
        newlib_build_dir = join(cfg.build_dir, 'newlib', lib_spec.name)
        self._prepare_build_dir(newlib_build_dir)

        def compiler_str(bin_name: str) -> str:
            bin_path = join(cfg.target_llvm_bin_dir, bin_name)
            return '{} -target {} -ffreestanding'.format(bin_path,
                                                         lib_spec.target)

        config_env = {
            'CC_FOR_TARGET': compiler_str('clang'),
            'CXX_FOR_TARGET': compiler_str('clang++'),
            'CFLAGS_FOR_TARGET': lib_spec.flags,
        }
        for tool in ['ar', 'nm', 'as', 'ranlib', 'strip', 'readelf', 'objdump']:
            var_name = '{}_FOR_TARGET'.format(tool.upper())
            tool_path = join(cfg.target_llvm_bin_dir, 'llvm-{}'.format(tool))
            config_env[var_name] = tool_path

        newlib_hw_fp = ('--enable-newlib-hw-fp' if lib_spec.newlib_fp_support
                        else '--disable-newlib-hw-fp')
        configure_args = [
            join(newlib_src_dir, 'configure'),
            '--target={}'.format(lib_spec.target),
            '--prefix={}'.format(cfg.target_llvm_dir),
            '--exec-prefix={}'.format(cfg.target_llvm_rt_dir),
            '--enable-newlib-io-long-long',
            '--enable-newlib-register-fini',
            '--disable-newlib-supplied-syscalls',
            '--enable-newlib-io-c99-formats',
            '--disable-nls',
            '--enable-lite-exit',
            newlib_hw_fp,
        ]
        make_args = [
            'make',
            '-j{}'.format(cfg.num_threads),
        ]
        try:
            logging.info('Configuring newlib for %s', lib_spec.name)
            self.runner.run(configure_args, cwd=newlib_build_dir,
                            env=config_env)
            logging.info('Building and installing newlib for %s', lib_spec.name)
            self.runner.run(make_args, cwd=newlib_build_dir)
            self.runner.run(['make', 'install'], cwd=newlib_build_dir)
        except subprocess.SubprocessError as ex:
            raise util.ToolchainBuildError from ex
