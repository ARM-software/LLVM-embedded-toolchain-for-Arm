#!/usr/bin/env python3

"""
Script to copy target libraries into the build tree.
Building libraries can take a very long time on some platforms so
building them on another platform and copying them in can be a big
time saver.
"""

import argparse
import glob
import os
import shutil
import tarfile
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--distribution-file",
        required=True,
        help="""Copy from this LLVM Embedded Toolchain for Arm distribution
        tarfile. This is a glob to make things easier on Windows.""",
    )
    parser.add_argument(
        "--build-dir",
        required=True,
        help="The build root directory to copy into",
    )
    args = parser.parse_args()

    # Find the distribution. This is a glob because scripts may not
    # know the version number and we can't rely on the Windows shell to
    # do it.
    for distribution_file in glob.glob(args.distribution_file):
        break
    else:
        raise RuntimeError(
            f"Distribution glob '{args.distribution_file}' not found"
        )

    lib_dir = os.path.join(args.build_dir, "llvm", "lib")
    os.makedirs(lib_dir, exist_ok=True)

    destination = os.path.join(lib_dir, "clang-runtimes")

    if os.path.isdir(destination):
        shutil.rmtree(destination)

    with tempfile.TemporaryDirectory(
        dir=args.build_dir,
    ) as tmp:
        # Extract the distribution package.
        with tarfile.open(distribution_file) as tf:
            tf.extractall(tmp)

        # Find the clang-runtimes directory in the extracted package
        # directory.
        for clang_runtimes in glob.glob(
            os.path.join(tmp, "*", "lib", "clang-runtimes")
        ):
            break
        else:
            raise RuntimeError("Extracted distribution directory not found")

        # Move the directory containing the target libraries into
        # position. The rest of the files in the distribution folder
        # will be deleted automatically when the tmp object goes out of
        # scope.
        shutil.move(clang_runtimes, lib_dir)


if __name__ == "__main__":
    main()
