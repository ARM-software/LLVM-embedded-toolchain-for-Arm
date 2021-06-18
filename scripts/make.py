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
import re
from typing import Dict, List, Mapping, Tuple
import subprocess
import shutil

import execution
import config
import util


class RuntimeDLLs:
    """Class for handling Mingw-w64 runtime DLLs"""
    def __init__(self, cfg: config.Config):
        self.cfg = cfg
        self.dlls = [
            'libwinpthread-1.dll',  # POSIX thread API implementation
            'libgcc_s_seh-1.dll',   # GCC runtime
            'libstdc++-6.dll',      # C++ Standard Library
        ]
        self.search_dirs = list(sorted(
            self.cfg.host_toolchain.get_lib_search_dirs()))
        self.dll_paths = self._get_dll_paths()

    def _get_dll_paths(self) -> Mapping[str, str]:
        """Find runtime DLLs in toolchain search directories."""
        dll_paths = {}
        for dll_name in self.dlls:
            for search_dir in self.search_dirs:
                dll_path = os.path.join(search_dir, dll_name)
                if os.path.exists(dll_path):
                    dll_paths[dll_name] = dll_path
                    break
        return dll_paths

    def get_runtime_dll_paths(self) -> List[Tuple[str, str]]:
        """Return a list of (dll name, path) tuples."""
        return [(dll_name, self.dll_paths.get(dll_name, 'NOT FOUND'))
                for dll_name in self.dlls]

    def copy_dlls(self, dest_dir: str) -> None:
        """Copy MinGW-w64 and GCC runtime DLLs required to run on Windows."""
        cfg = self.cfg
        logging.info('Copying Mingw-w64 runtime DLLs')
        for dll_name in self.dlls:
            if dll_name not in self.dll_paths:
                raise util.ToolchainBuildError(
                    'Required DLL {} not found in {}'.format(dll_name,
                                                             self.search_dirs))
            dll_path = self.dll_paths[dll_name]
            dest_path = os.path.join(dest_dir, dll_name)
            if cfg.verbose:
                logging.info('Copying %s to %s', dll_path, dest_path)
            shutil.copy(dll_path, dest_path)


class ToolchainBuild:
    """Class for configuring/building/installing all toolchain components:
       LLVM, newlib, compiler_rt.
    """
    def __init__(self, cfg: config.Config):
        self.cfg = cfg
        self.runner = execution.Runner(cfg.verbose)
        # Tools needed for newlib and compiler-rt build
        binutils = ['ar', 'nm', 'as', 'ranlib', 'strip', 'readelf', 'objdump']
        self.llvm_binutils = ['llvm-' + name for name in binutils]

    def _cmake_configure(self, name: str, source_dir: str, build_dir: str,
                         defs: Mapping[str, str],
                         env: Mapping[str, str] = None) -> None:
        """Run the "configure" stage of CMake."""
        if (os.path.exists(os.path.join(build_dir, 'CMakeCache.txt'))
                and self.cfg.skip_reconfigure):
            logging.info('%s CMakeCache.txt already exists, '
                         'skipping CMake configuration', name)
            return

        logging.info('Configuring %s', name)

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

    def _backends_to_build(self):
        triple_archs = set(v.triple_arch for v in self.cfg.variants)
        backends_to_build = [{'aarch64': 'AArch64',
                              'arm': 'ARM'}[triple_arch]
                             for triple_arch in triple_archs]
        assert len(backends_to_build) in (1, 2)
        return ";".join(backends_to_build)

    def build_native_tools(self) -> None:
        """Build a native LLVM toolchain (relevant for Linux -> Windows
           cross-compilation): an LLVM toolchain which runs on the same
           platform build.py is currently running on and targets embedded Arm.
        """
        self.runner.reset_cwd()
        cfg = self.cfg
        llvm_build_dir = os.path.join(cfg.build_dir, 'native-llvm')
        self._prepare_build_dir(llvm_build_dir)

        projects = ['clang', 'lld']
        dist_comps = [
            'clang',
            'clang-resource-headers',
            'lld',
            'llvm-config',
        ]
        dist_comps += self.llvm_binutils

        cmake_defs = self._get_common_cmake_defs_for_llvm()
        cmake_defs.update({
            'CMAKE_INSTALL_PREFIX:STRING': cfg.native_llvm_dir,
            'LLVM_ENABLE_PROJECTS:STRING': ';'.join(projects),
            'LLVM_DISTRIBUTION_COMPONENTS:STRING': ';'.join(dist_comps),
            'LLVM_INCLUDE_TESTS:BOOL': 'OFF',
            'LLVM_INCLUDE_EXAMPLES:BOOL': 'OFF',
            'LLVM_INCLUDE_BENCHMARKS:BOOL': 'OFF',
        })
        cmake_env = {
            'CC': cfg.native_toolchain.c_compiler,
            'CXX': cfg.native_toolchain.cpp_compiler,
        }

        self._cmake_configure('Native LLVM',
                              os.path.join(cfg.llvm_repo_dir, 'llvm'),
                              llvm_build_dir, cmake_defs, cmake_env)
        logging.info('Building and installing native LLVM toolchain')
        self._cmake_build(llvm_build_dir,
                          target='install-distribution-stripped')

    def build_clang(self) -> None:
        """Build and install Clang, LLD and LLVM binutils-like tools."""
        self.runner.reset_cwd()
        cfg = self.cfg
        join = os.path.join
        llvm_build_dir = join(cfg.build_dir, 'llvm')
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

        cmake_defs = self._get_common_cmake_defs_for_llvm()
        cmake_defs.update({
            'CMAKE_INSTALL_PREFIX:STRING': cfg.target_llvm_dir,
            'LLVM_ENABLE_PROJECTS:STRING': ';'.join(projects),
            'LLVM_DISTRIBUTION_COMPONENTS:STRING': ';'.join(dist_comps),
        })
        if cfg.is_cross_compiling:
            native_tools_dir = join(cfg.native_llvm_build_dir, 'bin')
            cmake_defs['CMAKE_CROSSCOMPILING:BOOL'] = 'ON'
            # We only support Linux -> Windows cross-compilation, not
            # vice-versa
            cmake_defs['CMAKE_SYSTEM_NAME'] = 'Windows'
            cmake_defs['CMAKE_FIND_ROOT_PATH'] = cfg.host_toolchain.sys_root
            cmake_defs['CMAKE_FIND_ROOT_PATH_MODE_PROGRAM'] = 'NEVER'
            cmake_defs['CMAKE_FIND_ROOT_PATH_MODE_INCLUDE'] = 'ONLY'
            cmake_defs['CMAKE_FIND_ROOT_PATH_MODE_LIBRARY'] = 'ONLY'
            cmake_defs['LLVM_TABLEGEN'] = join(native_tools_dir, 'llvm-tblgen')
            cmake_defs['CLANG_TABLEGEN'] = join(native_tools_dir,
                                                'clang-tblgen')
            cmake_defs['LLVM_CONFIG_PATH'] = join(native_tools_dir,
                                                  'llvm-config')

        cmake_env = {
            'CC': cfg.host_toolchain.c_compiler,
            'CXX': cfg.host_toolchain.cpp_compiler,
        }

        self._cmake_configure('LLVM', join(cfg.llvm_repo_dir, 'llvm'),
                              llvm_build_dir, cmake_defs, cmake_env)
        logging.info('Building and installing LLVM components: %s',
                     ', '.join(dist_comps))
        self._cmake_build(llvm_build_dir,
                          target='install-distribution-stripped')
        # When compiling for Windows copy required DLLs
        if cfg.host_toolchain.kind == config.ToolchainKind.MINGW:
            if cfg.copy_runtime_dlls:
                dlls = RuntimeDLLs(cfg)
                dlls.copy_dlls(cfg.target_llvm_bin_dir)
            else:
                if cfg.verbose:
                    logging.info('Skipping the copying Mingw-w64 runtime DLLs')
        # Record the list of files and links installed by clang
        if cfg.release_mode:
            self._write_llvm_index()

    def _get_common_cmake_defs_for_llvm(self) -> Dict[str, str]:
        """Return common CMake definitions used for building LLVM."""
        cfg = self.cfg
        cmake_defs = {
            'LLVM_TARGETS_TO_BUILD:STRING': self._backends_to_build(),
            'CMAKE_BUILD_TYPE:STRING': 'Release',
        }
        if cfg.default_target is not None:
            cmake_defs['LLVM_DEFAULT_TARGET_TRIPLE:STRING'] = \
                cfg.default_target
        if cfg.use_ccache:
            cmake_defs['LLVM_CCACHE_BUILD:BOOL'] = 'ON'
        return cmake_defs

    def _get_common_cmake_defs_for_libs(self, lib_spec: config.LibrarySpec) \
            -> Dict[str, str]:
        """Return common CMake definitions used for runtime libraries
           (compiler-rt, libc++abi, libc++).
        """
        cfg = self.cfg
        join = os.path.join
        flags = (lib_spec.flags
                 + ' -ffunction-sections -fdata-sections -fno-ident'
                 + ' --sysroot {}'.format(join(cfg.target_llvm_rt_dir,
                                               lib_spec.name)))
        defs = {
            'CMAKE_TRY_COMPILE_TARGET_TYPE': 'STATIC_LIBRARY',
            # Set the cmake system name to Generic so that no host system
            # include files are searched. At least on OSX this problem
            # occurs.
            'CMAKE_SYSTEM_NAME': 'Generic',
            'CMAKE_C_COMPILER': join(cfg.native_llvm_bin_dir, 'clang'),
            'CMAKE_C_COMPILER_TARGET': lib_spec.target,
            'CMAKE_C_FLAGS': flags,
            'CMAKE_AR': join(cfg.native_llvm_bin_dir, 'llvm-ar'),
            'CMAKE_NM': join(cfg.native_llvm_bin_dir, 'llvm-nm'),
            'CMAKE_RANLIB': join(cfg.native_llvm_bin_dir, 'llvm-ranlib'),
            'CMAKE_EXE_LINKER_FLAGS': '-fuse-ld=lld',
            'CMAKE_CXX_COMPILER': join(cfg.native_llvm_bin_dir, 'clang++'),
            'CMAKE_CXX_COMPILER_TARGET': lib_spec.target,
            'CMAKE_CXX_FLAGS': flags,
        }
        return defs

    def build_compiler_rt(self, lib_spec: config.LibrarySpec) -> None:
        """Build and install a single variant of compiler-rt."""
        self.runner.reset_cwd()
        cfg = self.cfg
        join = os.path.join
        rt_source_dir = join(cfg.llvm_repo_dir, 'compiler-rt')
        rt_build_dir = join(cfg.build_dir, 'compiler-rt', lib_spec.name)
        self._prepare_build_dir(rt_build_dir)
        rt_install_dir = join(cfg.target_llvm_rt_dir, lib_spec.name)
        cmake_defs = self._get_common_cmake_defs_for_libs(lib_spec)
        cmake_defs.update({
            'CMAKE_BUILD_TYPE:STRING': 'Release',
            'CMAKE_ASM_COMPILER_TARGET': lib_spec.target,
            'CMAKE_ASM_FLAGS': cmake_defs.get('CMAKE_C_FLAGS', ''),
            'LLVM_CONFIG_PATH': join(cfg.native_llvm_build_dir, 'bin',
                                     'llvm-config'),
            'COMPILER_RT_BUILD_SANITIZERS:BOOL': 'OFF',
            'COMPILER_RT_BUILD_XRAY:BOOL': 'OFF',
            'COMPILER_RT_BUILD_LIBFUZZER:BOOL': 'OFF',
            'COMPILER_RT_BUILD_PROFILE:BOOL': 'OFF',
            'COMPILER_RT_BAREMETAL_BUILD:BOOL': 'ON',
            'COMPILER_RT_DEFAULT_TARGET_ONLY': 'ON',
            'CMAKE_INSTALL_PREFIX': rt_install_dir,
        })
        self._cmake_configure('{} compiler-rt'.format(lib_spec.name),
                              rt_source_dir, rt_build_dir, cmake_defs)
        logging.info('Building and installing compiler-rt for %s',
                     lib_spec.name)
        self._cmake_build(rt_build_dir)
        self._cmake_build(rt_build_dir, target='install')

        # Move the libraries from lib/linux to lib
        lib_dir = join(rt_install_dir, 'lib')
        generic_dir = join(lib_dir, 'generic')
        for name in os.listdir(generic_dir):
            assert name != 'generic'
            src = join(generic_dir, name)
            dest = join(lib_dir, name)
            if cfg.verbose:
                logging.info('Moving %s to %s', src, dest)
            shutil.move(src, dest)
        if cfg.verbose:
            logging.info('Removing %s', generic_dir)
        shutil.rmtree(generic_dir)

        # Adjust compiler-rt library names. They were changed in
        # https://reviews.llvm.org/D98452, but in our configuration Clang still
        # uses the old name. Example names:
        # Old: libclang_rt.builtins-armv6m.a
        # New: libclang_rt.builtins-arm.a

        # Create a regular expression which matches 'arm' or 'armhf' preceded
        # by '-' and followed by '.'
        rex = re.compile(r'(?<=-)(?:arm|armhf)(?=\.)')
        for name in os.listdir(lib_dir):
            if not name.startswith('libclang_rt'):
                continue
            new_name = rex.sub(lib_spec.march, name)
            if new_name == name:
                continue
            src = join(lib_dir, name)
            dest = join(lib_dir, new_name)
            if cfg.verbose:
                logging.info('Renaming %s to %s', src, dest)
            shutil.move(src, dest)

    def _create_dummy_libunwind(self, lib_spec: config.LibrarySpec) -> None:
        """Create an empty libunwind.a library. It is needed because the Clang
           driver always adds -lunwind to the linker command line even when
           "-fno-exceptions" is specified on the command line.
        """
        dummy_unwind = os.path.join(self.cfg.target_llvm_rt_dir,
                                    lib_spec.name, 'lib', 'libunwind.a')
        logging.info('Creating dummy libunwind for %s', lib_spec.name)
        self.runner.run([
            os.path.join(self.cfg.native_llvm_bin_dir, 'llvm-ar'),
            '-rc', dummy_unwind,
        ])

    def build_cxx_libraries(self, lib_spec: config.LibrarySpec) -> None:
        """Build and install a single variant of lib++abi and libc++"""

        def updated_dict(dict1, dict2):
            result = dict1.copy()
            result.update(dict2)
            return result

        cmake_common_defs = self._get_common_cmake_defs_for_libs(lib_spec)
        # Disable C++17 aligned allocation feature because its implementation
        # in libc++ relies on posix_memalign() which is not available in our
        # newlib build
        cxx_flags = (cmake_common_defs.get('CMAKE_CXX_FLAGS', '')
                     + ' -D_LIBCPP_HAS_NO_LIBRARY_ALIGNED_ALLOCATION')
        install_dir = os.path.join(self.cfg.target_llvm_rt_dir,
                                   lib_spec.name)
        cmake_common_defs.update({
            'CMAKE_BUILD_TYPE:STRING': 'MinSizeRel',
            'CMAKE_CXX_FLAGS': cxx_flags,
            'CMAKE_INSTALL_PREFIX': install_dir,
        })

        cmake_libcxxabi_defs = {
            'LIBCXXABI_ENABLE_SHARED:BOOL': 'OFF',
            'LIBCXXABI_ENABLE_STATIC:BOOL': 'ON',
            'LIBCXXABI_ENABLE_EXCEPTIONS:BOOL': 'OFF',
            'LIBCXXABI_ENABLE_ASSERTIONS:BOOL': 'OFF',
            'LIBCXXABI_ENABLE_PIC:BOOL': 'OFF',
            'LIBCXXABI_USE_COMPILER_RT:BOOL': 'ON',
            'LIBCXXABI_ENABLE_THREADS:BOOL': 'OFF',
            'LIBCXXABI_BAREMETAL:BOOL': 'ON',
            'LIBCXXABI_LIBCXX_INCLUDES:PATH':
                os.path.join(install_dir, 'include', 'c++', 'v1'),
        }

        cmake_libcxx_defs = {
            # libc++ CMake files incorrectly detect that the "-GR-" flag
            # (the clang-cl analog of -fno-rtti) is supported. Manually mark it
            # as unsupported to avoid warnings.
            'LIBCXX_SUPPORTS_GR_FLAG': 'OFF',
            'LIBCXX_ENABLE_SHARED:BOOL': 'OFF',
            'LIBCXX_ENABLE_STATIC:BOOL': 'ON',
            'LIBCXX_ENABLE_FILESYSTEM:BOOL': 'OFF',
            'LIBCXX_ENABLE_PARALLEL_ALGORITHMS:BOOL': 'OFF',
            'LIBCXX_ENABLE_EXPERIMENTAL_LIBRARY:BOOL': 'OFF',
            'LIBCXX_ENABLE_DEBUG_MODE_SUPPORT:BOOL': 'OFF',
            'LIBCXX_ENABLE_RANDOM_DEVICE:BOOL': 'OFF',
            'LIBCXX_ENABLE_LOCALIZATION:BOOL': 'OFF',
            'LIBCXX_ENABLE_EXCEPTIONS:BOOL': 'OFF',
            'LIBCXX_ENABLE_RTTI:BOOL': 'OFF',
            'LIBCXX_ENABLE_THREADS:BOOL': 'OFF',
            'LIBCXX_ENABLE_MONOTONIC_CLOCK:BOOL': 'OFF',
            'LIBCXX_INCLUDE_BENCHMARKS:BOOL': 'OFF',
            'LIBCXX_CXX_ABI:STRING': 'libcxxabi',
        }

        libs = [
            ('libc++', 'libcxx', cmake_libcxx_defs),
            ('libc++abi', 'libcxxabi', cmake_libcxxabi_defs),
        ]

        for lib_pretty_name, lib_name, cmake_defs in libs:
            self.runner.reset_cwd()
            build_dir = os.path.join(self.cfg.build_dir, lib_name,
                                     lib_spec.name)
            self._prepare_build_dir(build_dir)

            full_name = '{} for {}'.format(lib_pretty_name, lib_spec.name)
            self._cmake_configure(full_name,
                                  os.path.join(self.cfg.llvm_repo_dir,
                                               lib_name),
                                  build_dir,
                                  updated_dict(cmake_common_defs,
                                               cmake_defs))
            logging.info('Building and installing %s', full_name)
            self._cmake_build(build_dir)
            self._cmake_build(build_dir, target='install')

        self._create_dummy_libunwind(lib_spec)

    def _copy_runtime_to_native(self, lib_spec: config.LibrarySpec) -> None:
        """Copy runtime libraries and headers from target LLVM to
           native target LLVM.
        """
        cfg = self.cfg
        logging.info('Copying newlib libraries and headers to the native '
                     'toolchain directory')
        from_path = os.path.join(cfg.target_llvm_rt_dir, lib_spec.name)
        to_path = os.path.join(cfg.native_llvm_rt_dir, lib_spec.name)
        try:
            if os.path.exists(to_path):
                if cfg.verbose:
                    logging.info('Deleting %s', to_path)
                shutil.rmtree(to_path)
            if cfg.verbose:
                logging.info('Copying %s to %s', from_path, to_path)
            shutil.copytree(from_path, to_path)
        except shutil.Error as ex:
            raise util.ToolchainBuildError from ex

    def _copy_newlib_headers_and_libs(self, source_dir: str,
                                      destination_dir: str) -> None:
        """ Copying newlib headers and libraries from
            lib_spec_name/target/{lib|include} to
            lib_spec_name/{lib|include} """
        cfg = self.cfg
        join = os.path.join
        # pylint: disable=too-many-nested-blocks
        try:
            if os.path.exists(source_dir):
                if cfg.verbose:
                    logging.info('Copying %s to %s', source_dir,
                                 destination_dir)
                for root, _, files in os.walk(source_dir):
                    dst_dir = root.replace(source_dir, destination_dir, 1)
                    if not os.path.exists(dst_dir):
                        os.makedirs(dst_dir)
                    for file_ in files:
                        src_file = join(root, file_)
                        dst_file = join(dst_dir, file_)
                        if os.path.exists(dst_file):
                            if os.path.samefile(src_file, dst_file):
                                continue
                            os.remove(dst_file)
                        shutil.copy(src_file, dst_dir)
            else:
                logging.error('Does not exist: %s', source_dir)
                raise util.ToolchainBuildError
        except shutil.Error as ex:
            raise util.ToolchainBuildError from ex

    def build_newlib(self, lib_spec: config.LibrarySpec) -> None:
        """Build and install a single variant of newlib."""
        self.runner.reset_cwd()
        cfg = self.cfg
        join = os.path.join
        newlib_build_dir = join(cfg.build_dir, 'newlib', lib_spec.name)
        # Newlib install is placed in build directory; later on it is copied
        # into installation directory.
        newlib_install_dir = join(cfg.build_dir, 'newlib', lib_spec.name,
                                  'install')
        self._prepare_build_dir(newlib_build_dir)

        def compiler_str(bin_name: str, cfg: config.Config) -> str:
            bin_path = join(cfg.native_llvm_bin_dir, bin_name)
            if cfg.use_ccache:
                bin_path = 'ccache ' + bin_path
            return '{} -target {} -ffreestanding'.format(bin_path,
                                                         lib_spec.target)

        # __USES_INITFINI__ and HAVE_INIT_FINI are related to the .init_array
        # mechanism implementation: __USES_INITFINI__ enables the call to
        # __libc_init_array in crt0.S. Undefining HAVE_INIT_FINI disables the
        # call to _init in __libc_init_array (the _init function was used in an
        # old initialization mechanism, and in the LLVM toolchain it is not
        # defined)
        config_env = {
            'CC_FOR_TARGET': compiler_str('clang', cfg),
            'CXX_FOR_TARGET': compiler_str('clang++', cfg),
            'CFLAGS_FOR_TARGET': lib_spec.flags +
            ' -D__USES_INITFINI__' +
            ' -UHAVE_INIT_FINI' +
            ' --sysroot {}'.format(
                join(cfg.target_llvm_rt_dir,
                     lib_spec.name,
                     lib_spec.target)),
        }
        for tool in ['ar', 'nm', 'as', 'ranlib',
                     'strip', 'readelf', 'objdump']:
            var_name = '{}_FOR_TARGET'.format(tool.upper())
            tool_path = join(cfg.native_llvm_bin_dir, 'llvm-{}'.format(tool))
            config_env[var_name] = tool_path

        configure_args = [
            join(cfg.newlib_repo_dir, 'configure'),
            '--target={}'.format(lib_spec.target),
            '--prefix={}'.format(cfg.target_llvm_dir),
            '--exec-prefix={}'.format(newlib_install_dir),
            '--enable-newlib-io-long-long',
            '--enable-newlib-register-fini',
            '--disable-newlib-supplied-syscalls',
            '--enable-newlib-io-c99-formats',
            '--disable-nls',
            '--enable-lite-exit',
        ]
        make_args = [
            'make',
            '-j{}'.format(cfg.num_threads),
        ]
        try:
            logging.info('Configuring newlib for %s', lib_spec.name)
            self.runner.run(configure_args, cwd=newlib_build_dir,
                            env=config_env)
            logging.info('Building and installing newlib for %s',
                         lib_spec.name)
            self.runner.run(make_args, cwd=newlib_build_dir)
            self.runner.run(['make', 'install'], cwd=newlib_build_dir)
        except subprocess.SubprocessError as ex:
            raise util.ToolchainBuildError from ex

        logging.info('Copying newlib include and lib directories to'
                     ' installation directory')

        self._copy_newlib_headers_and_libs(join(newlib_install_dir,
                                                lib_spec.target,
                                                'lib'),
                                           join(cfg.target_llvm_rt_dir,
                                                lib_spec.name,
                                                'lib'))
        self._copy_newlib_headers_and_libs(join(newlib_install_dir,
                                                lib_spec.target,
                                                'include'),
                                           join(cfg.target_llvm_rt_dir,
                                                lib_spec.name,
                                                'include'))

        if cfg.is_cross_compiling:
            self._copy_runtime_to_native(lib_spec)

    def _run_smoke_tests(self, lib_spec: config.LibrarySpec) -> bool:
        bin_path = self.cfg.target_llvm_bin_dir
        testdir_path = os.path.join(self.cfg.source_dir, "tests/smoketests")
        logging.info("Running smoke tests for %s", lib_spec.name)
        # If qemu-arm is not in PATH, just build, don't run
        if shutil.which("qemu-arm") is not None:
            do_not_run = False
        else:
            logging.warning(
                "qemu-arm is not present in your system path. Hence smoke "
                "tests will only be built, not executed.")
            do_not_run = True

        all_tests_succeeded = True

        for smoketest_dir in [
                entry for entry in os.scandir(testdir_path) if entry.is_dir()
        ]:
            smoketest_path = smoketest_dir.path
            commands = [
                "make", "build" if do_not_run else "run",
                f"BIN_PATH={bin_path}"
            ]
            stdout: List[str] = []
            stderr: List[str] = []
            try:
                self.runner.run_capture_output(commands,
                                               cwd=smoketest_path,
                                               capture_stdout=stdout,
                                               capture_stderr=stderr)
            except subprocess.SubprocessError as ex:
                logging.error("Failed to run test suite: smoketests")
                raise util.ToolchainBuildError from ex

            if do_not_run:
                continue

            def _check_output(output_type: str, smoketest_dir: os.DirEntry,
                              captured_output: List[str]) -> bool:
                smoketest_path = smoketest_dir.path
                expected_output_path = os.path.join(smoketest_path,
                                                    output_type)
                try:
                    with open(expected_output_path) as expected_output:
                        expected_output_str = [
                            s.rstrip('\n') for s in expected_output.readlines()
                        ]
                except OSError as ex:
                    logging.error("Failed to open %s", expected_output_path)
                    raise util.ToolchainBuildError from ex

                if expected_output_str != captured_output:
                    logging.error("Smoke test %s failed: %s doesn't match",
                                  smoketest_dir.name, output_type)
                    logging.error("Expected:")
                    logging.error('\n'.join(expected_output_str))
                    logging.error("Got:")
                    logging.error('\n'.join(captured_output))
                    return False

                return True

            if not _check_output("stdout", smoketest_dir, stdout):
                all_tests_succeeded = False
            if not _check_output("stderr", smoketest_dir, stderr):
                all_tests_succeeded = False

        if all_tests_succeeded:
            logging.info("Smoke tests passed")

        return all_tests_succeeded

    def run_tests(self, lib_spec: config.LibrarySpec) -> None:
        """Runs smoke tests."""
        result = self._run_smoke_tests(lib_spec)
        if not result:
            raise util.ToolchainBuildError
