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
from typing import List, Mapping, Sequence


class Runner:
    """Class for running external process, the class stores the last current
       working directory (for logging).
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.last_cwd = None

    def reset_cwd(self):
        """Reset current working directory. So that an 'Entering directory'
           message is logged next time.
        """
        self.last_cwd = None

    def run(self, args: Sequence[str], cwd: str = None,
            env: Mapping[str, str] = None) -> None:
        """Run a specified program with arguments, optionally change current
           directory and change the environment. Note: env does not replace
           parent environment, but amends it for the subprocess."""
        if env is not None:
            env_strings = ['{}={} '.format(key, shlex.quote(env[key]))
                           for key in sorted(env.keys())]
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
        stdout = sys.stdout if self.verbose else subprocess.DEVNULL
        stderr = sys.stderr if self.verbose else subprocess.PIPE
        try:
            subprocess.run(args, stdout=stdout, stderr=stderr, check=True,
                           cwd=cwd, env=env)
        except subprocess.CalledProcessError as ex:
            lines = ex.stderr.decode('utf-8', errors='replace').split('\n')
            if len(lines) > 30:
                lines = ['...'] + lines[-30:]
            logging.error('Command failed with return code %d, stderr:\n%s',
                          ex.returncode, '\n'.join(lines))
            raise


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
