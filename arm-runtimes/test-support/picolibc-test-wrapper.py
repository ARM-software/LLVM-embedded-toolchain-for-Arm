#!/usr/bin/env python3

# SPDX-FileCopyrightText: Copyright 2023-2024 Arm Limited and/or its affiliates <open-source-office@arm.com>

# This is a wrapper script to run picolibc tests with QEMU or FVPs.

from run_qemu import run_qemu
from run_fvp import run_fvp
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
    "picolibc_armv7m_hard_fpv4_sp_d16-build/test/math_errhandling",
    "picolibc_armv7r_hard_vfpv3xd-build/test/math_errhandling",
    "picolibc_armv7r_hard_vfpv3xd_exn_rtti-build/test/math_errhandling",
    "picolibc_armv8.1m.main_hard_fp_nomve-build/test/math_errhandling",
    "picolibc_armv7m_soft_fpv4_sp_d16_exn_rtti-build/test/math_errhandling",
    "picolibc_armv7m_hard_fpv4_sp_d16_exn_rtti-build/test/math_errhandling",
    "picolibc_armv8.1m.main_hard_fp_nomve_exn_rtti-build/test/math_errhandling",
    "picolibc_armv8.1m.main_hard_nofp_mve-build/test/fenv",
    "picolibc_armv8.1m.main_hard_nofp_mve-build/test/math_errhandling",
    "picolibc_armv8m.main_hard_fp-build/test/math_errhandling",
    "picolibc_armv8.1m.main_hard_nofp_mve_exn_rtti-build/test/fenv",
    "picolibc_armv8.1m.main_hard_nofp_mve_exn_rtti-build/test/math_errhandling",
    "picolibc_armv8m.main_hard_fp_exn_rtti-build/test/math_errhandling",
    "picolibc_armv8.1m.main_hard_nofp_mve_pacret_bti-build/test/fenv",
    "picolibc_armv8.1m.main_hard_nofp_mve_pacret_bti_exn_rtti-build/test/fenv",
    "picolibc_armv8.1m.main_hard_fp_nomve_pacret_bti-build/test/math_errhandling",
    "picolibc_armv8.1m.main_hard_fp_nomve_pacret_bti_exn_rtti-build/test/math_errhandling",
    "picolibc_armv8.1m.main_hard_nofp_mve_pacret_bti-build/test/math_errhandling",
    "picolibc_armv8.1m.main_hard_nofp_mve_pacret_bti_exn_rtti-build/test/math_errhandling",
]

disabled_tests_fvp = [
    # SDDKW-25808: SYS_SEEK returns wrong value.
    "test/semihost/semihost-seek",
    "test/test-fread-fwrite",
    "test/posix-io",
    # SDDKW-94045: rateInHz port not connected in Corstone-310 FVP.
    "test/semihost/semihost-gettimeofday",
]


def is_disabled(image, use_fvp):
    if any([image.endswith(t) for t in disabled_tests]):
        return True
    if use_fvp and any([image.endswith(t) for t in disabled_tests_fvp]):
        return True
    return False


def run(args):
    if is_disabled(args.image, args.qemu_command is None):
        return EXIT_CODE_SKIP
    # Some picolibc tests expect argv[0] to be literally "program-name", not
    # the actual program name.
    argv = ["program-name"] + args.arguments
    if args.qemu_command:
        return run_qemu(
            args.qemu_command,
            args.qemu_machine,
            args.qemu_cpu,
            args.qemu_params.split(":") if args.qemu_params else [],
            args.image,
            argv,
            None,
            pathlib.Path.cwd(),
            args.verbose,
        )
    else:
        return run_fvp(
            args.fvp_install_dir,
            args.fvp_config_dir,
            args.fvp_model,
            args.fvp_config,
            args.image,
            argv,
            None,
            pathlib.Path.cwd(),
            args.verbose,
            args.tarmac,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Run a single test using either qemu or an FVP"
    )
    main_arg_group = parser.add_mutually_exclusive_group(required=True)
    main_arg_group.add_argument(
        "--qemu-command", help="qemu-system-<arch> path"
    )
    main_arg_group.add_argument(
        "--fvp-install-dir", help="Directory in which FVP models are installed"
    )
    parser.add_argument(
        "--qemu-machine",
        help="name of the machine to pass to QEMU",
    )
    parser.add_argument(
        "--qemu-cpu", required=False, help="name of the cpu to pass to QEMU"
    )
    parser.add_argument(
        "--qemu-params",
        help='list of arguments to pass to qemu, separated with ":"',
    )
    parser.add_argument(
        "--fvp-config-dir", help="Directory in which FVP models are installed"
    )
    parser.add_argument(
        "--fvp-model",
        help="model name for FVP",
    )
    parser.add_argument(
        "--fvp-config",
        action="append",
        help="FVP config file(s) to use",
    )
    parser.add_argument(
        "--tarmac",
        help="file to wrote tarmac trace to (FVP only)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose output. This may affect test result, as the output "
        "will be added to the output of the test.",
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
