#!/usr/bin/env python3

# Helper script to modify the xml results from picolibc.

# Picolibc always puts all the test results into the "picolibc"
# testsuite in the junit xml file. We have multiple variants of
# picolibc, so the xml is modified to group the tests by variant.

import argparse
import os
from xml.etree import ElementTree


def main():
    parser = argparse.ArgumentParser(description="Reformat picolibc xml results")
    parser.add_argument(
        "--dir",
        required=True,
        help="Path to picolibc build directory",
    )
    parser.add_argument(
        "--variant",
        required=True,
        help="Name of the variant under test",
    )
    args = parser.parse_args()

    # A '.' character is used in junit xml to split classes/groups.
    # Variants such as armv8m.main need to be renamed.
    variant_name = args.variant.replace(".", "_")

    xml_file = os.path.join(args.dir, "meson-logs", "testlog.junit.xml")

    tree = ElementTree.parse(xml_file)
    root = tree.getroot()
    for testsuite in root.iter("testsuite"):
        testsuite.set("name", f"picolibc-{variant_name}")
    for testcase in root.iter("testcase"):
        testcase.set("classname", f"picolibc-{variant_name}.picolibc-{variant_name}")
    tree.write(xml_file)
    print(f"Results written to {xml_file}")


if __name__ == "__main__":
    main()
