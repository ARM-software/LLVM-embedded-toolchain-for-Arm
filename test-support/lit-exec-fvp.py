#!/usr/bin/env python3

# SPDX-FileCopyrightText: Copyright 2023-2024 Arm Limited and/or its affiliates <open-source-office@arm.com>

# This script is a bridge between lit-based tests of LLVM C++ runtime libraries
# (libc++abi, libunwind, libc++) and FVP models. It must handle the same
# command-line arguments as llvm-project/libcxx/utils/run.py.

from run_fvp import run_fvp
import argparse
import pathlib
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Run a single test using Arm FVPs"
    )
    parser.add_argument(
        "--fvp-install-dir",
        help="Directory in which FVP models are installed",
        required=True,
    )
    parser.add_argument(
        "--fvp-config-dir",
        help="Directory containing FVP config files",
        required=True,
    )
    main_arg_group.add_argument(
        "--fvp-model",
        help="model name for FVP",
        required=True,
    )
    parser.add_argument(
        "--fvp-config",
        action="append",
        help="FVP config file(s) to use",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="timeout, in seconds (default: 900)",
    )
    parser.add_argument(
        "--execdir",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="directory to run the program from",
    )
    parser.add_argument(
        "--codesign_identity",
        type=str,
        help="ignored, used for compatibility with libc++ tests",
    )
    parser.add_argument(
        "--env",
        type=str,
        nargs="*",
        help="ignored, used for compatibility with libc++ tests",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose output. This may affect test result, as the output "
        "will be added to the output of the test.",
    )
    parser.add_argument(
        "--tarmac",
        help="File to write tarmac trace to (slows execution significantly)",
    )
    parser.add_argument("image", help="image file to execute")
    parser.add_argument(
        "arguments",
        nargs=argparse.REMAINDER,
        default=[],
        help="optional arguments for the image",
    )
    args = parser.parse_args()
    return run_fvp(
        args.fvp_install_dir,
        args.fvp_config_dir,
        args.fvp_model,
        args.fvp_config,
        args.image,
        [args.image] + args.arguments,
        args.timeout,
        args.execdir,
        args.verbose,
        args.tarmac,
    )
    sys.exit(ret_code)


if __name__ == "__main__":
    main()
