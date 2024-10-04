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

    abs_patch_dir = os.path.abspath(args.patchdir)

    if args.reset:
        reset_args = git_cmd + ["reset", "--quiet", "--hard", args.reset]
        subprocess.check_output(reset_args)
        clean_args = git_cmd + ["clean", "--quiet", "--force", "-dx", args.reset]
        subprocess.check_output(clean_args)

    patch_names = [
        patch for patch in os.listdir(args.patchdir) if patch.endswith(".patch")
    ]
    patch_names.sort()

    print(f"Found {len(patch_names)} patches to apply:")
    print("\n".join(patch_names))

    if args.method == "am":
        merge_args = git_cmd + ["am", "-k", "--ignore-whitespace", "--3way"]
        for patch_name in patch_names:
            merge_args.append(os.path.join(abs_patch_dir, patch_name))
        p = subprocess.run(merge_args, capture_output=True, text=True)
        print(p.stdout)
        print(p.stderr)

        if p.returncode == 0:
            print(f"All patches applied.")
            sys.exit(0)
        if args.restore_on_fail:
            # Check that the operation can be aborted.
            # git am does give any specific return codes,
            # so check for unresolved working files.
            if os.path.isdir(os.path.join(args.llvm_dir, ".git", "rebase-apply")):
                print("Aborting git am...")
                subprocess.run(git_cmd + ["am", "--abort"], check=True)
                print(f"Abort successful.")
                sys.exit(2)
            else:
                print("Unable to abort.")
        sys.exit(1)
    else:
        applied_patches = []
        for patch_name in patch_names:
            patch_file = os.path.join(abs_patch_dir, patch_name)
            print(f"Checking {patch_name}...")
            # Check that the patch applies before trying to apply it.
            apply_check_args = git_cmd + [
                "apply",
                "--ignore-whitespace",
                "--3way",
                "--check",
                patch_file,
            ]
            p_check = subprocess.run(apply_check_args)

            if p_check.returncode == 0:
                # Patch will apply.
                print(f"Applying {patch_name}...")
                apply_args = git_cmd + [
                    "apply",
                    "--ignore-whitespace",
                    "--3way",
                    patch_file,
                ]
                apply_args = subprocess.run(apply_args, check=True)
                applied_patches.append(patch_name)
            else:
                # Patch won't apply.
                print(f"Unable to apply {patch_name}")
                if args.restore_on_fail:
                    # Remove any patches that have already been applied.
                    while len(applied_patches) > 0:
                        r_patch = applied_patches.pop()
                        print(f"Reversing {r_patch}...")
                        reverse_args = git_cmd + [
                            "apply",
                            "--ignore-whitespace",
                            "--3way",
                            "--reverse",
                            os.path.join(abs_patch_dir, r_patch),
                        ]
                        p_check = subprocess.run(reverse_args, check=True)
                    print(f"Rollback successful, failure occured on {patch_file}")
                    sys.exit(2)
                sys.exit(1)
        print(f"All patches applied.")


main()
