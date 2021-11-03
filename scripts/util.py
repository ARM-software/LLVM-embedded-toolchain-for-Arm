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
from typing import Any, Sequence, List

import yaml


class ToolchainBuildError(RuntimeError):
    """A single error for all failures related to toolchain build: this
       includes git errors, errors that occur during CMake, configure, Ninja
       and Make runs, as well as packaging.
    """


def values_of_enum(enum_class: Any) -> List[str]:
    """Create a list of strings from Enum values."""
    return [str(enumerator.value) for enumerator in enum_class]


def write_lines(lines: Sequence[str], dest: str) -> None:
    """Write a list of lines to destination file."""
    with open(dest, 'wt') as out_f:
        out_f.writelines(line + '\n' for line in lines)


def configure_logging() -> None:
    """Set logging format and level threshold for the default logger."""
    log_format = '%(levelname)s: %(message)s'
    logging.basicConfig(format=log_format, level=logging.INFO)


def read_yaml(path: str) -> Any:
    """Read a YAML file and return its contents as a Python dict or list."""
    with open(path, 'rt') as in_f:
        try:
            return yaml.load(in_f, Loader=yaml.FullLoader)
        except yaml.YAMLError as ex:
            logging.error(ex)
            raise
