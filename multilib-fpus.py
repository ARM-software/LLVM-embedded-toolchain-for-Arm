#!/usr/bin/env python3

"""Auto-generate implications between -mfpu options for multilib.yaml.in.

Each FPU name that clang knows about is mapped to all the FPU names
that clang considers to be a subset of it (determined by extracting
the cc1 command from `clang -###` for each one and looking at the set
of -target-feature options).

An exception is that we don't consider any hardware FP configuration
to be compatible with -mfpu=none. It would work in most cases to
cross-call between code compiled for an FPU or no FPU, if you were
using the soft float ABI. But it wouldn't work in all cases: setjmp
needs to know whether to save FP registers in the jmp_buf, so a
non-FPU-aware setjmp would not behave correctly if linked into an
otherwise FPU-using application. Similarly for exception unwinding. So
we don't permit selecting an -mfpu=none library as a fallback for any
hard-FP library.

However, it's fine for ABI purposes to mix code compiled for 16 and 32
d-registers, because the extra 16 d-registers are caller-saved, so
setjmp and exceptions need not preserve them. Interrupt handlers would
have to preserve them, but our libraries don't define any.
"""

import argparse
import json
import os
import shlex
import subprocess


def get_fpu_list(args):
    """Extract the list of FPUs from ARMTargetParser.def.

    Strategy: the intended use of ARMTargetParser.def in the actual
    LLVM build is to run it through the C preprocessor with whatever
    #defines will generate the output you want. So the most reliable
    way to get what _we_ want is to do exactly the same.

    The output format I've chosen is actually JSON, because that's
    close enough to C-like syntax that you can generate it easily
    using cpp features like stringification, and also convenient for
    Python to consume afterwards.
    """

    command = [
        args.clang,
        # For this purpose we're only interested in the calls to the
        # ARM_FPU macro in the input file, and want the first and
        # third argument of each of those.
        #
        # The first argument will be a string literal giving the FPU
        # name, which we copy into the JSON output still as a string
        # literal.
        #
        # The third argument indicates the general FPU category, which
        # we need so as to exclude FPUVersion::NONE. That is not
        # already a string literal, so we stringify it in the
        # preprocessor to make it legal JSON.
        "-DARM_FPU(name,kind,version,...)=[name,#version],",
        "-E",  # preprocess
        "-P",  # don't output linemarkers
        "-xc",  # treat input as C, even though no .c filename extension
        os.path.join(
            args.llvm_source,
            "llvm",
            "include",
            "llvm",
            "TargetParser",
            "ARMTargetParser.def",
        ),
    ]

    raw_output = subprocess.check_output(command)

    # The output of the above is a collection of JSON arrays each
    # containing two strings, and each followed by a comma. Turn it
    # into a single legal JSON declaration by deleting the final comma
    # and wrapping it in array brackets.
    json_output = b"[" + raw_output.strip().rstrip(b",") + b"]"

    # Filter the list of 2-tuples to exclude the FPU names that aren't
    # FPUs.
    for name, fputype in json.loads(json_output):
        assert fputype.startswith("FPUVersion::"), (
            f"FPU type value {fputype} not of the expected form!\n"
            "Has ARMTargetParser.def been refactored?"
        )

        if fputype != "FPUVersion::NONE":
            yield name


def get_target_features(args, fpu):
    """Return the set of feature names for a given FPU.

    Strategy: run a clang compile command with that FPU, including
    the -### argument to print all the subsidiary command lines, and
    extract the list of "-target-feature" "+foo" options from the
    clang -cc1 command line in the output. This shows what low-level
    LLVM feature names are enabled by that FPU.

    It will also include the feature names enabled by the CPU or
    architecture we specified. But since we only care about which
    FPUs are subsets of which other ones, that doesn't affect the
    output, as long as the architecture is the same for all the FPUs
    we do this with.
    """

    command = [
        args.clang,
        "--target=arm-none-eabi",
        "-march=armv7a",
        "-mfpu=" + fpu,
        "-S",  # tell clang to do as little as possible
        "-xc",  # interpret input as C
        "-",  # read from standard input (not that we'll get that far)
        "-###",  # print all the command lines rather than actually doing it
    ]

    output = subprocess.check_output(
        command, stderr=subprocess.STDOUT
    ).decode()

    # Find the clang -cc1 command, and parse it into an argv list.
    for line in output.splitlines():
        try:
            words = shlex.split(line)
        except ValueError:
            # We expect that some of the output lines won't parse as
            # valid shell syntax, because -### doesn't output *only*
            # command lines. So this is fine; any line that doesn't
            # parse is not the one we were looking for anyway.
            continue

        if len(words) > 1 and words[1] == "-cc1":
            # We've found the cc1 command.
            break
    else:
        assert False, "no cc1 command found in output of: " + " ".join(
            map(shlex.quote, command)
        )

    # Now we've found the clang command, go through it for
    # -target-feature options. We only care about the ones that add
    # rather than removing features, i.e. "-target-feature +foo"
    # rather than "-target-feature -bar".
    it = iter(words)
    features = set()
    for word in it:
        if word == "-target-feature":
            arg = next(it)
            if arg.startswith("+"):
                features.add(arg[1:])

    assert len(features) > 0, (
        "This cc1 command contained no argument pairs of the form"
        " '-target-feature +something':\n"
        f"{line}\n"
        "Has the clang -cc1 command-line syntax changed?"
    )

    return features


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--clang", required=True, help="Path to clang executable."
    )
    parser.add_argument(
        "--llvm-source",
        required=True,
        help="Path to root of llvm-project source tree.",
    )
    args = parser.parse_args()

    # Collect all the data: make the list of FPU names, and the set of
    # features that LLVM maps each one to.
    fpu_features = {
        fpuname: get_target_features(args, fpuname)
        for fpuname in get_fpu_list(args)
    }

    # Now, for each FPU, find all the FPUs that are subsets of it
    # (excluding itself).
    sorted_fpus = list(sorted(fpu_features))
    for super_fpu in sorted_fpus:
        subsets = [
            sub_fpu
            for sub_fpu in sorted_fpus
            if sub_fpu != super_fpu
            and fpu_features[sub_fpu].issubset(fpu_features[super_fpu])
        ]

        # If this FPU has any subsets at all, write a multilib.yaml
        # snippet that adds all the subset FPU flags if it sees the
        # superset flag.
        #
        # The YAML is trivial enough that it's easier to do this by
        # hand than to rely on everyone having python3-yaml available.
        if len(subsets) > 0:
            print("- Match: -mfpu=" + super_fpu)
            print("  Flags:")
            for sub_fpu in subsets:
                print("  - -mfpu=" + sub_fpu)


if __name__ == "__main__":
    main()
