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
    "picolibc_armv7m_soft_fpv4_sp_d16_exceptions_rtti-build/test/math_errhandling",
    "picolibc_armv7em_hard_fpv4_sp_d16_exceptions_rtti-build/test/math_errhandling",
    "picolibc_armv8.1m.main_hard_fp_nomve_exceptions_rtti-build/test/math_errhandling",
    "picolibc_armv8.1m.main_hard_nofp_mve-build/test/fenv",
    "picolibc_armv8.1m.main_hard_nofp_mve-build/test/math_errhandling",
    "picolibc_armv8m.main_hard_fp-build/test/math_errhandling",
    "picolibc_armv8.1m.main_hard_nofp_mve_exceptions_rtti-build/test/fenv",
    "picolibc_armv8.1m.main_hard_nofp_mve_exceptions_rtti-build/test/math_errhandling",
    "picolibc_armv8m.main_hard_fp_exceptions_rtti-build/test/math_errhandling",
    # TODO: broken by https://github.com/picolibc/picolibc/commit/fe5191e347427a00e0b5aba34e002f914e6e5ad8
    "picolibc.aarch64.picolib/rand",
    "picolibc.aarch64_exceptions_rtti.picolib/rand",
    "picolibc.armv4t.picolib/rand",
    "picolibc.armv4t.picolib/tls",
    "picolibc.armv4t_exceptions_rtti.picolib/rand",
    "picolibc.armv4t_exceptions_rtti.picolib/tls",
    "picolibc.armv5te.picolib/rand",
    "picolibc.armv5te.picolib/tls",
    "picolibc.armv5te_exceptions_rtti.picolib/rand",
    "picolibc.armv5te_exceptions_rtti.picolib/tls",
    "picolibc.armv6m_soft_nofp.picolib/rand",
    "picolibc.armv6m_soft_nofp.picolib/tls",
    "picolibc.armv6m_soft_nofp_exceptions_rtti.picolib/rand",
    "picolibc.armv6m_soft_nofp_exceptions_rtti.picolib/tls",
    "picolibc.armv7a_hard_vfpv3_d16.picolib/rand",
    "picolibc.armv7a_hard_vfpv3_d16.picolib/tls",
    "picolibc.armv7a_hard_vfpv3_d16_exceptions_rtti.picolib/rand",
    "picolibc.armv7a_hard_vfpv3_d16_exceptions_rtti.picolib/tls",
    "picolibc.armv7a_soft_nofp.picolib/rand",
    "picolibc.armv7a_soft_nofp.picolib/tls",
    "picolibc.armv7a_soft_nofp_exceptions_rtti.picolib/rand",
    "picolibc.armv7a_soft_nofp_exceptions_rtti.picolib/tls",
    "picolibc.armv7em_hard_fpv4_sp_d16.picolib/rand",
    "picolibc.armv7em_hard_fpv4_sp_d16.picolib/tls",
    "picolibc.armv7em_hard_fpv4_sp_d16_exceptions_rtti.picolib/rand",
    "picolibc.armv7em_hard_fpv4_sp_d16_exceptions_rtti.picolib/tls",
    "picolibc.armv7em_hard_fpv5_d16.picolib/rand",
    "picolibc.armv7em_hard_fpv5_d16.picolib/tls",
    "picolibc.armv7em_hard_fpv5_d16_exceptions_rtti.picolib/rand",
    "picolibc.armv7em_hard_fpv5_d16_exceptions_rtti.picolib/tls",
    "picolibc.armv7em_soft_nofp.picolib/rand",
    "picolibc.armv7em_soft_nofp.picolib/tls",
    "picolibc.armv7em_soft_nofp_exceptions_rtti.picolib/rand",
    "picolibc.armv7em_soft_nofp_exceptions_rtti.picolib/tls",
    "picolibc.armv7m_soft_fpv4_sp_d16.picolib/rand",
    "picolibc.armv7m_soft_fpv4_sp_d16.picolib/tls",
    "picolibc.armv7m_soft_fpv4_sp_d16_exceptions_rtti.picolib/rand",
    "picolibc.armv7m_soft_fpv4_sp_d16_exceptions_rtti.picolib/tls",
    "picolibc.armv7m_soft_nofp.picolib/rand",
    "picolibc.armv7m_soft_nofp.picolib/tls",
    "picolibc.armv7m_soft_nofp_exceptions_rtti.picolib/rand",
    "picolibc.armv7m_soft_nofp_exceptions_rtti.picolib/tls",
    "picolibc.armv7r_hard_vfpv3_d16.picolib/rand",
    "picolibc.armv7r_hard_vfpv3_d16.picolib/tls",
    "picolibc.armv7r_hard_vfpv3_d16_exceptions_rtti.picolib/rand",
    "picolibc.armv7r_hard_vfpv3_d16_exceptions_rtti.picolib/tls",
    "picolibc.armv7r_soft_nofp.picolib/rand",
    "picolibc.armv7r_soft_nofp.picolib/tls",
    "picolibc.armv7r_soft_nofp_exceptions_rtti.picolib/rand",
    "picolibc.armv7r_soft_nofp_exceptions_rtti.picolib/tls",
    "picolibc.armv8.1m.main_hard_fp_nomve.picolib/rand",
    "picolibc.armv8.1m.main_hard_fp_nomve.picolib/tls",
    "picolibc.armv8.1m.main_hard_fp_nomve_exceptions_rtti.picolib/rand",
    "picolibc.armv8.1m.main_hard_fp_nomve_exceptions_rtti.picolib/tls",
    "picolibc.armv8.1m.main_hard_fpdp_nomve.picolib/rand",
    "picolibc.armv8.1m.main_hard_fpdp_nomve.picolib/tls",
    "picolibc.armv8.1m.main_hard_fpdp_nomve_exceptions_rtti.picolib/rand",
    "picolibc.armv8.1m.main_hard_fpdp_nomve_exceptions_rtti.picolib/tls",
    "picolibc.armv8.1m.main_hard_nofp_mve.picolib/rand",
    "picolibc.armv8.1m.main_hard_nofp_mve.picolib/tls",
    "picolibc.armv8.1m.main_hard_nofp_mve_exceptions_rtti.picolib/rand",
    "picolibc.armv8.1m.main_hard_nofp_mve_exceptions_rtti.picolib/tls",
    "picolibc.armv8.1m.main_soft_nofp_nomve.picolib/rand",
    "picolibc.armv8.1m.main_soft_nofp_nomve.picolib/tls",
    "picolibc.armv8.1m.main_soft_nofp_nomve_exceptions_rtti.picolib/rand",
    "picolibc.armv8.1m.main_soft_nofp_nomve_exceptions_rtti.picolib/tls",
    "picolibc.armv8m.main_hard_fp.picolib/rand",
    "picolibc.armv8m.main_hard_fp.picolib/tls",
    "picolibc.armv8m.main_hard_fp_exceptions_rtti.picolib/rand",
    "picolibc.armv8m.main_hard_fp_exceptions_rtti.picolib/tls",
    "picolibc.armv8m.main_soft_nofp.picolib/rand",
    "picolibc.armv8m.main_soft_nofp.picolib/tls",
    "picolibc.armv8m.main_soft_nofp_exceptions_rtti.picolib/rand",
    "picolibc.armv8m.main_soft_nofp_exceptions_rtti.picolib/tls",
    "/test/tls",
    "/test/rand",
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
        ["program-name"] + args.arguments,
        None,
        pathlib.Path.cwd(),
        args.verbose,
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
