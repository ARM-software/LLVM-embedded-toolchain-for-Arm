#!/usr/bin/env python3

# Copyright (c) 2024, Arm Limited and affiliates.

# This is a helper script to run the picolibc tests.
#
# This is just a glue code for cmake the script, not intended to be run
# manually. If you want to run the tests manually, using meson directly will
# provide you more options and is better documented:
#   cd PICOLIBC_BUILD_DIR
#   meson setup . PICOLIBC_SOURCE_DIR -Dtests=true --reconfigure
#   meson test
#
# The tests for picolibc cannot be enabled at first invocation of meson,
# because compiler_rt is built after picolibc is built. If picolibc would be
# configured with tests enabled at before compiler_rt is built, the
# picolibc build would fail. This is why this script enables the tests just
# before picolibc is tested.
#
# Picolibc always puts all the test results into "picolibc" testsuite in the
# junit xml file. We have multiple variants of picolibc and so we add a
# classname to every test the tests are run. This has to be done even when the
# tests fail, while still returnning non-zero exit value, so that cmake detects
# failure. This would be hard to do from within the cmake script.

import argparse
import sys
import re
import os.path
import subprocess

help = "usage: run-picolibc-tests.py PICOLIBC_SOURCE_DIR PICOLIBC_BUILD_DIR"


def replace_classname(build_dir, classname):
    xml_file_name = os.path.join(build_dir, "meson-logs", "testlog.junit.xml")

    with open(xml_file_name, "r") as f:
        xml_file_data = f.read()

    xml_file_data = re.sub(
        'classname="picolibc"',
        f'classname="picolibc.{classname}"',
        xml_file_data,
    )

    with open(xml_file_name, "w") as f:
        f.write(xml_file_data)


def run_tests(meson_command, source_dir, build_dir, variant):

    # meson<0.64.0 does not properly apply new configuration after
    # "meson configure -Dtests=false"
    # use "meson setup --reconfigure" as a workaround
    subprocess.run(
        [
            meson_command,
            "setup",
            ".",
            source_dir,
            "-Dtests=true",
            "--reconfigure",
        ],
        cwd=build_dir,
        check=True,
    )

    returncode = subprocess.run(
        [meson_command, "test"],
        cwd=build_dir,
    ).returncode

    subprocess.run(
        [meson_command, "configure", "-Dtests=false"],
        cwd=build_dir,
        check=True,
    )

    replace_classname(build_dir, variant)

    return returncode


def main():
    parser = argparse.ArgumentParser(description="Run picolibc tests")
    parser.add_argument(
        "--meson-command", required=True, default="meson", help="meson path"
    )
    parser.add_argument(
        "--picolibc-source-dir",
        required=True,
        help="path to picolibc sources",
    )
    parser.add_argument(
        "--picolibc-build-dir",
        required=True,
        help="path to picolibc build",
    )
    parser.add_argument(
        "--variant",
        required=True,
        help="name of the variant to be appended to the testsuite name",
    )
    args = parser.parse_args()
    ret_code = run_tests(
        args.meson_command,
        args.picolibc_source_dir,
        args.picolibc_build_dir,
        args.variant,
    )
    sys.exit(ret_code)


if __name__ == "__main__":
    main()
