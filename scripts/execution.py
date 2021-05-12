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
import shlex
import sys
import subprocess
from typing import Any, IO, List, Mapping, Optional, Sequence, Union


class Runner:
    """Class for running external process, the class stores the last current
       working directory (for logging).
    """

    last_cwd: Optional[str] = None

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.last_cwd = None

    def reset_cwd(self):
        """Reset current working directory. So that an 'Entering directory'
           message is logged next time.
        """
        self.last_cwd = None

    def _configure_env(self,
                       args: Sequence[str],
                       cwd: str = None,
                       env: Mapping[str, str] = None) -> \
            Optional[Mapping[str, str]]:
        if env is not None:
            env_strings = [
                '{}={} '.format(key, shlex.quote(env[key]))
                for key in sorted(env.keys())
            ]
        else:
            env_strings = []
        if cwd is not None:
            if cwd != self.last_cwd:
                logging.info('Entering directory "%s"', cwd)
            self.last_cwd = cwd
        logging.info('Executing: "%s%s"', ''.join(env_strings),
                     ' '.join(shlex.quote(arg) for arg in args))

        if env is not None:
            env = dict(os.environ, **env)

        return env

    def _log_exception(self, ex: subprocess.CalledProcessError) -> None:
        if not self.verbose:
            lines = ex.stderr.decode('utf-8', errors='replace').split('\n')
            if len(lines) > 30:
                lines = ['...'] + lines[-30:]
            logging.error('Command failed with return code %d, '
                          'stderr:\n%s', ex.returncode, '\n'.join(lines))
        else:
            # In verbose mode stderr has already been copied to sys.stderr,
            # so we only need to output the return code
            logging.error('Command failed with return code %d',
                          ex.returncode)
        raise ex

    def run(self, args: Sequence[str], cwd: str = None,
            env: Mapping[str, str] = None) -> None:
        """Run a specified program with arguments, optionally change current
           directory and change the environment. Note: env does not replace
           parent environment, but amends it for the subprocess."""
        env = self._configure_env(args, cwd, env)

        stdout: Union[IO[Any], int] = (sys.stdout if self.verbose
                                       else subprocess.DEVNULL)
        stderr: Union[IO[Any], int] = (sys.stderr if self.verbose
                                       else subprocess.PIPE)
        try:
            subprocess.run(args, stdout=stdout, stderr=stderr, check=True,
                           cwd=cwd, env=env)
        except subprocess.CalledProcessError as ex:
            self._log_exception(ex)

    def run_capture_output(self,
                           args: Sequence[str],
                           cwd: str = None,
                           env: Mapping[str, str] = None,
                           capture_stdout: List[str] = None,
                           capture_stderr: List[str] = None) -> None:
        """Run a specified program with arguments, optionally change current
           directory and change the environment. Note: env does not replace
           parent environment, but amends it for the subprocess.
           The program's output is captured into capture_stdout and
           capture_stderr arguments."""
        env = self._configure_env(args, cwd, env)

        try:
            result = subprocess.run(args,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    check=True,
                                    cwd=cwd,
                                    env=env)
        except subprocess.CalledProcessError as ex:
            self._log_exception(ex)

        if self.verbose:
            # Note that stdout is printed strictly before stderr. In case they
            # are redirected to the same stream, the ordering of events will
            # be lost.
            sys.stdout.write(result.stdout.decode('utf-8'))
            sys.stderr.write(result.stderr.decode('utf-8'))

        if capture_stdout is not None:
            capture_stdout[:] = result.stdout.decode('utf-8').splitlines()
        if capture_stderr is not None:
            capture_stderr[:] = result.stderr.decode('utf-8').splitlines()


def run(args: Sequence[str], cwd: str = None, env: Mapping[str, str] = None,
        verbose: bool = False) -> None:
    """A wrapper for the Runner class which invokes run once."""
    runner = Runner(verbose)
    runner.run(args, cwd, env)


def run_stdout(args: Sequence[str]) -> List[str]:
    """Run a process and return its stdout split into lines."""
    res = subprocess.run(args, stdout=subprocess.PIPE,
                         stderr=sys.stderr,
                         check=True)
    lines = res.stdout.decode('utf-8').strip().split('\n')
    return [line.strip() for line in lines]
