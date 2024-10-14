#!/usr/bin/env python3

"""
Script to apply a set of patches to llvm-project sources.
"""

import argparse
import os
import pathlib
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
        help="Clean and hard reset the repo to a specified commit before patching.",
    )
    parser.add_argument(
        "--restore_on_fail",
        action="store_true",
        help="If a patch in a series cannot be applied, restore the original state instead of leaving patches missing. Return code will be 2 instead of 1.",
    )
    args = parser.parse_args()

    if args.llvm_dir:
        git_cmd = ["git", "-C", args.llvm_dir]
    else:
        git_cmd = ["git"]

    if args.reset:
        reset_args = git_cmd + ["reset", "--quiet", "--hard", args.reset]
        subprocess.check_output(reset_args)
        clean_args = git_cmd + ["clean", "--quiet", "--force", "-dx", args.reset]
        subprocess.check_output(clean_args)

    abs_patch_dir = os.path.abspath(args.patchdir)
    patch_list = list(pathlib.Path(abs_patch_dir).glob("*.patch"))
    patch_list.sort()

    print(f"Found {len(patch_list)} patches to apply:")
    print("\n".join(p.name for p in patch_list))

    if args.method == "am":
        merge_args = git_cmd + ["am", "-k", "--ignore-whitespace", "--3way"]
        for patch in patch_list:
            merge_args.append(str(patch))
        p = subprocess.run(merge_args, capture_output=True, text=True)
        print(p.stdout)
        print(p.stderr)

        if p.returncode == 0:
            print(f"All patches applied.")
            sys.exit(0)
        if args.restore_on_fail:
            # Check that the operation can be aborted.
            # git am doesn't give any specific return codes,
            # so check for unresolved working files.
            rebase_apply_path = os.path.join(".git", "rebase-apply")
            if args.llvm_dir:
                rebase_apply_path = os.path.join(args.llvm_dir, rebase_apply_path)
            if os.path.isdir(rebase_apply_path):
                print("Aborting git am...")
                subprocess.run(git_cmd + ["am", "--abort"], check=True)
                print(f"Abort successful.")
                sys.exit(2)
            else:
                print("Unable to abort.")
        sys.exit(1)
    else:
        applied_patches = []
        for current_patch in patch_list:
            print(f"Checking {current_patch.name}...")
            # Check that the patch applies before trying to apply it.
            apply_check_args = git_cmd + [
                "apply",
                "--ignore-whitespace",
                "--3way",
                "--check",
                str(current_patch),
            ]
            p_check = subprocess.run(apply_check_args)

            if p_check.returncode == 0:
                # Patch will apply.
                print(f"Applying {current_patch.name}...")
                apply_args = git_cmd + [
                    "apply",
                    "--ignore-whitespace",
                    "--3way",
                    str(current_patch),
                ]
                apply_args = subprocess.run(apply_args, check=True)
                applied_patches.append(current_patch)
            else:
                # Patch won't apply.
                print(f"Unable to apply {current_patch.name}")
                if args.restore_on_fail:
                    # Remove any patches that have already been applied.
                    while len(applied_patches) > 0:
                        previous_patch = applied_patches.pop()
                        print(f"Reversing {previous_patch.name}...")
                        reverse_args = git_cmd + [
                            "apply",
                            "--ignore-whitespace",
                            "--3way",
                            "--reverse",
                            str(previous_patch),
                        ]
                        p_check = subprocess.run(reverse_args, check=True)
                    print(
                        f"Rollback successful, failure occured on {current_patch.name}"
                    )
                    sys.exit(2)
                sys.exit(1)
        print(f"All patches applied.")


main()
