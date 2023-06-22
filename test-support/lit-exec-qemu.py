#!/usr/bin/env python3

# Copyright (c) 2023, Arm Limited and affiliates.

# This script is a bridge between lit-based tests of LLVM C++ runtime libraries
# (libc++abi, libunwind, libc++) and QEMU. It must handle the same command-line
# arguments as llvm-project/libcxx/utils/run.py.

import sys
import argparse
import subprocess
import pathlib


def run(args):
    """Execute the program using QEMU and return the subprocess return code."""
    qemu_params = ["-M", args.qemu_machine]
    if args.qemu_cpu:
        qemu_params += ["-cpu", args.qemu_cpu]
    if args.qemu_params:
        qemu_params += args.qemu_params.split(":")

    # Setup semihosting with chardev bound to stdio.
    # This is needed to test semihosting functionality in picolibc.
    qemu_params += ["-chardev", "stdio,mux=on,id=stdio0"]
    semihosting_config = ["enable=on", "chardev=stdio0"] + [
        "arg=" + arg.replace(",", ",,") for arg in args.arguments
    ]
    qemu_params += ["-semihosting-config", ",".join(semihosting_config)]

    # Disable features we don't need and which could slow down the test or
    # interfere with semihosting.
    qemu_params += ["-monitor", "none", "-serial", "none", "-nographic"]

    # Load the image to machine's memory and set the PC.
    # "virt" machine cannot be used with load, as QEMU will try to put
    # device tree blob at start of RAM conflicting with our code
    # https://www.qemu.org/docs/master/system/arm/virt.html#hardware-configuration-information-for-bare-metal-programming
    if args.qemu_machine == "virt":
        qemu_params += ["-kernel", args.image]
    else:
        qemu_params += ["-device", f"loader,file={args.image},cpu-num=0"]

    qemu_cmd = [args.qemu_command] + qemu_params
    result = subprocess.run(
        qemu_cmd,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        timeout=args.timeout,
        cwd=args.execdir,
        check=False,
    )
    sys.stdout.buffer.write(result.stdout)
    return result.returncode


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
        default=".",
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
    ret_code = run(args)
    sys.exit(ret_code)


if __name__ == "__main__":
    main()
