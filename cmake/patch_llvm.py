#!/usr/bin/env python3

"""
Script to apply a set of patches to llvm-project sources.
"""

import argparse
import os
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "patchdir",
        help="Set of patches to apply. This should be a directory containing one or more ordered *.patch files.",
    )
    parser.add_argument(
        "--llvm_dir",
        help="Directory of the llvm-project git checkout, if not the current directory.",
    )
    parser.add_argument(
        "--method",
        choices=["am", "apply"],
        default="apply",
        help="Git command to use. git am will add each patch as a commit, whereas git apply will leave patched changes staged.",
    )
    parser.add_argument(
        "--reset",
        help="Clean and reset the repo to a specified commit before patching.",
    )
    parser.add_argument(
        "--restore_on_fail",
        action="store_true",
        help="If a patch in a series cannot be applied, restore the original state instead of leaving patches missing. Return code will be 2 instead of 1.",
    )
    args = parser.parse_args()

    if args.reset:
        reset_args = ["git", "reset", "--quiet", "--hard"]
        subprocess.check_output(reset_args, cwd=args.llvm_dir)
        clean_args = ["git", "clean", "--quiet", "--force", "-dx"]
        subprocess.check_output(clean_args, cwd=args.llvm_dir)

    patch_names = []
    for patch_name in os.listdir(args.patchdir):
        if patch_name.endswith(".patch"):
            patch_names.append(patch_name)
    patch_names.sort()

    print(f"Found {len(patch_names)} patches to apply:")
    for patch_name in patch_names:
        print(patch_name)

    if args.method == "am":
        merge_args = ["git", "am", "-k", "--ignore-whitespace", "--3way"]
        for patch_name in patch_names:
            merge_args.append(os.path.join(args.patchdir, patch_name))
        p = subprocess.run(
            merge_args, cwd=args.llvm_dir, capture_output=True, text=True
        )
        print(p.stdout)
        print(p.stderr)

        if p.returncode == 0:
            print(f"All patches applied.")
            sys.exit(0)
        if args.restore_on_fail:
            # Check that the operation can be aborted.
            if (
                'To restore the original branch and stop patching, run "git am --abort".'
                in p.stdout
            ):
                print("Aborting git am...")
                subprocess.run(["git", "am", "--abort"], cwd=args.llvm_dir, check=True)
                sys.exit(2)
        sys.exit(1)
    else:
        applied_patches = []
        for patch_name in patch_names:
            patch_file = os.path.join(args.patchdir, patch_name)
            print(f"Checking {patch_file}...")
            # Check that the patch applies before trying to apply it.
            apply_check_args = [
                "git",
                "apply",
                "--ignore-whitespace",
                "--3way",
                "--check",
                patch_file,
            ]
            p_check = subprocess.run(apply_check_args, cwd=args.llvm_dir)

            if p_check.returncode == 0:
                # Patch will apply.
                print(f"Applying {patch_file}...")
                apply_args = [
                    "git",
                    "apply",
                    "--ignore-whitespace",
                    "--3way",
                    patch_file,
                ]
                apply_args = subprocess.run(apply_args, cwd=args.llvm_dir, check=True)
                applied_patches.append(patch_file)
            else:
                # Patch won't apply.
                print(f"Unable to apply {patch_file}")
                if args.restore_on_fail:
                    # Remove any patches that have already been applied.
                    while len(applied_patches) > 0:
                        r_patch = applied_patches.pop()
                        print(f"Reversing {r_patch}...")
                        reverse_args = [
                            "git",
                            "apply",
                            "--ignore-whitespace",
                            "--3way",
                            "--reverse",
                            r_patch,
                        ]
                        p_check = subprocess.run(
                            reverse_args, cwd=args.llvm_dir, check=True
                        )
                    print(f"Rollback successful, failure occured on {patch_file}")
                    sys.exit(2)
                sys.exit(1)
        print(f"All patches applied.")


main()
