#!/usr/bin/env python3

# Copyright (c) 2023, Arm Limited and affiliates.

# This script is a bridge between lit-based tests of LLVM C++ runtime libraries
# (libc++abi, libunwind, libc++) and QEMU. It must handle the same command-line
# arguments as llvm-project/libcxx/utils/run.py.

from run_qemu import run_qemu
import argparse
import pathlib
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Run a single test using qemu"
    )
    parser.add_argument(
        "--qemu-command", required=True, help="qemu-system-<arch> path"
    )
    parser.add_argument(
        "--qemu-machine",
        required=True,
        help="name of the machine to pass to QEMU",
    )
    parser.add_argument(
        "--qemu-cpu", required=False, help="name of the cpu to pass to QEMU"
    )
    parser.add_argument(
        "--qemu-params",
        required=False,
        help='list of arguments to pass to qemu, separated with ":"',
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="timeout, in seconds (default: 60)",
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
    parser.add_argument("image", help="image file to execute")
    parser.add_argument(
        "arguments",
        nargs=argparse.REMAINDER,
        default=[],
        help="optional arguments for the image",
    )
    args = parser.parse_args()
    ret_code = run_qemu(
        args.qemu_command,
        args.qemu_machine,
        args.qemu_cpu,
        args.qemu_params.split(":") if args.qemu_params else [],
        args.image,
        args.arguments,
        args.timeout,
        args.execdir,
    )
    sys.exit(ret_code)


if __name__ == "__main__":
    main()
