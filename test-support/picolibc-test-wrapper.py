#!/usr/bin/env python3

# Copyright (c) 2023, Arm Limited and affiliates.

# This is a wrapper script to run picolibc tests with QEMU.

from run_qemu import run_qemu
import argparse
import pathlib
import sys

# https://mesonbuild.com/Unit-tests.html#skipped-tests-and-hard-errors
EXIT_CODE_SKIP = 77

disabled_tests = [
    # compiler-rt does not properly set floating point exceptions for
    # computations on types implemented in software
    # https://github.com/picolibc/picolibc/pull/500
    "picolibc_armv7m_soft_fpv4_sp_d16-build/test/math_errhandling",
    "picolibc_armv7em_hard_fpv4_sp_d16-build/test/math_errhandling",
    "picolibc_armv8.1m.main_hard_fp_nomve-build/test/math_errhandling",
    "picolibc_armv8.1m.main_hard_nofp_mve-build/test/fenv",
    "picolibc_armv8.1m.main_hard_nofp_mve-build/test/math_errhandling",
    "picolibc_armv8m.main_hard_fp-build/test/math_errhandling",
]


def is_disabled(image):
    return any([image.endswith(t) for t in disabled_tests])


def run(args):
    if is_disabled(args.image):
        return EXIT_CODE_SKIP
    return run_qemu(
        args.qemu_command,
        args.qemu_machine,
        args.qemu_cpu,
        args.qemu_params.split(":") if args.qemu_params else [],
        args.image,
        args.arguments,
        None,
        pathlib.Path.cwd(),
    )


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
