#!/usr/bin/env python3

# Helper script to modify the xml results from compiler-rt.

# compiler-rt always puts all the test results into the "compiler-rt"
# testsuite in the junit xml file. We have multiple variants of
# compiler-rt, so the xml is modified to group the tests by variant.

import argparse
import os
from xml.etree import ElementTree


def main():
    parser = argparse.ArgumentParser(description="Reformat compiler-rt xml results")
    parser.add_argument(
        "--dir",
        required=True,
        help="Path to compiler-rt build directory",
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

    xml_file = os.path.join(args.dir, "test", "results.junit.xml")

    tree = ElementTree.parse(xml_file)
    root = tree.getroot()

    # The compiler-rt Builtins tests runs two testsuites: TestCases and Unit
    # TestCases are recorded in the "Builtins" suite.
    # But the Unit tests are recorded in "Builtins-arm-generic" or similar.
    # For readability, combine them all under compiler-rt-{variant}-Builtins
    for testsuite in root.iter("testsuite"):
        old_suitename = testsuite.get("name")
        new_suitename = f"compiler-rt-{variant_name}-Builtins"
        testsuite.set("name", new_suitename)
        for testcase in testsuite.iter("testcase"):
            old_classname = testcase.get("classname")
            new_classname = old_classname.replace(old_suitename, new_suitename)
            testcase.set("classname", new_classname)

    tree.write(xml_file)
    print(f"Results written to {xml_file}")

if __name__ == "__main__":
    main()
