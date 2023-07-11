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
