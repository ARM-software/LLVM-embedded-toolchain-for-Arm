#!/usr/bin/env python3

# Copyright (c) 2023, Arm Limited and affiliates.

# This script is a bridge between lit-based tests of LLVM C++ runtime libraries
# (libc++abi, libunwind, libc++) and QEMU. It must handle the same command-line
# arguments as llvm-project/libcxx/utils/run.py.

import sys
import re
import argparse
import subprocess
import pathlib

# This script requires Python 3.6 or later
assert sys.version_info >= (3, 6)

picolibc_binary_name = "check-picolibc"
picolibc_non_zero_tests = {'abort': 134, "test-except": 1}

def picolibc_alt_retcode(test_name, test_ret_code):
    """ Some picolibc tests return non-zero retcode on succes
        all of them will be altered to zero in here
    """
    if test_name in picolibc_non_zero_tests:
        if test_ret_code == picolibc_non_zero_tests[test_name]:
            return 0
    return test_ret_code

def picolibc_test_name(binary_name):
    """ Extract test name from picolibc test binary name
    """
    if picolibc_binary_name in binary_name:
        picolibc_test_name = binary_name[binary_name.rfind("_")+1:]
        picolibc_test_name = picolibc_test_name[:picolibc_test_name.rfind(".out")]
        return picolibc_test_name
    return ""


def run(args):
    """Execute the program using QEMU and return the subprocess return code."""
    command = args.command
    assert command
    if command[0] == '--':
        command = command[1:]
    image = command[0]
    image_args = command[1:]
    qemu_params = args.qemu_params.split(':')
    qemu_cmd = ([args.qemu_command] + qemu_params +
        ['-semihosting', '-nographic', '-kernel', image])
    if image_args:
        image_args_concat = ','.join(['arg=' + arg.replace(',', ',,')
                                      for arg in image_args])
        qemu_cmd += ['-semihosting-config', image_args_concat]
    result = subprocess.run(qemu_cmd, stdout=subprocess.PIPE,
                            stderr=sys.stderr,
                            timeout=args.timeout,
                            cwd=args.execdir,
                            check=False)
    sys.stdout.buffer.write(result.stdout)
    ret_code = result.returncode
    if args.picolibc_test and ret_code != 0:
        ret_code = picolibc_alt_retcode( picolibc_test_name(image), ret_code)
    return ret_code


def main():
    parser = argparse.ArgumentParser(description='Run a single test using qemu')
    parser.add_argument('--qemu-command', required=True, help='qemu-system-<arch> path')
    parser.add_argument('--qemu-params', required=True,
                        help='list of arguments to pass to qemu, separated with ":"')
    parser.add_argument('--timeout', type=int, default=60,
                        help='timeout, in seconds (default: 60)')
    parser.add_argument('--execdir', type=pathlib.Path, default='.',
                        help='directory to run the program from')
    parser.add_argument('--codesign_identity', type=str,
                        help='ignored, used for compatibility with libc++ tests')
    parser.add_argument('--env', type=str, nargs='*',
                        help='ignored, used for compatibility with libc++ tests')
    parser.add_argument('command', nargs=argparse.REMAINDER,
                        help='image file to execute with optional arguments')
    parser.add_argument('--picolibc-test', nargs='?', default=False, const=True,
                        help="Enable return code fix for picolibc tests")
    args = parser.parse_args()
    ret_code = run(args)
    sys.exit(ret_code)


if __name__ == '__main__':
    main()
