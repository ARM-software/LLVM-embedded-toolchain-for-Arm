#!/usr/bin/env python3

# Copyright (c) 2023, Arm Limited and affiliates.

# This script is a bridge between lit-based tests of LLVM C++ runtime libraries
# (libc++abi, libunwind, libc++) and QEMU. It must handle the same command-line
# arguments as llvm-project/libcxx/utils/run.py.
# This is also a wrapper script to run picolibc tests with QEMU.

import sys
import argparse
import subprocess
import pathlib

# https://mesonbuild.com/Unit-tests.html#skipped-tests-and-hard-errors
EXIT_CODE_SKIP = 77

disabled_tests = [
    "picolibc_aarch64-build/test/math_errhandling",
    "picolibc_armv7em_hard_fpv4_sp_d16-build/test/math_errhandling",
    "picolibc_armv7em_hard_fpv5_d16-build/test/math_errhandling",
    "picolibc_armv8m.main_hard_fp-build/test/printf_scanf",
    "picolibc_armv8m.main_hard_fp-build/test/printff_scanff",
    "picolibc_armv8m.main_hard_fp-build/test/printff-tests",
    "picolibc_armv8m.main_hard_fp-build/test/math_errhandling",
    "picolibc_armv8m.main_hard_fp-build/test/rounding-mode",
    "picolibc_armv8m.main_hard_fp-build/test/long_double",
    "picolibc_armv8m.main_hard_fp-build/test/rand",
    "picolibc_armv8m.main_hard_fp-build/test/fenv",
    "picolibc_armv8m.main_hard_fp-build/test/math-funcs",
    "picolibc_armv8m.main_hard_fp-build/test/test-strtod",
    "picolibc_armv8m.main_hard_fp-build/test/test-efcvt",
    "picolibc_armv8m.main_hard_fp-build/test/complex-funcs",
    "picolibc_armv8m.main_hard_fp-build/test/semihost/semihost-times",
    "picolibc_armv8m.main_hard_fp-build/newlib/libm/test/math_test",
    "picolibc_armv8m.main_hard_fp-build/test/libc-testsuite/sscanf",
    "picolibc_armv8m.main_hard_fp-build/test/libc-testsuite/strtod",
    "picolibc_armv8.1m.main_soft_nofp_nomve-build/newlib/libm/test/math_test",
    "picolibc_armv8.1m.main_hard_fp-build/test/math_errhandling",
    "picolibc_armv8.1m.main_hard_fp-build/newlib/libm/test/math_test",
    "picolibc_armv8.1m.main_hard_nofp_mve-build/test/fenv",
    "picolibc_armv8.1m.main_hard_nofp_mve-build/newlib/libm/test/math_test",
    "picolibc_armv8.1m.main_hard_nofp_mve-build/test/math_errhandling",
]


def is_disabled(image):
    return any([image.endswith(t) for t in disabled_tests])


def run(args):
    """Execute the program using QEMU and return the subprocess return code."""
    if is_disabled(args.image):
        return EXIT_CODE_SKIP
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
    # setting stdin to devnull prevents qemu from fiddling with the echo bit of
    # the parent terminal
    result = subprocess.run(
        qemu_cmd,
        stdin=subprocess.DEVNULL,
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
