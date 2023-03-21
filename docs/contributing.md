# Contribution Guide

LLVM Embedded Toolchain for Arm integrates llvm-project and picolibc.
Contributions are welcome that improve the project in areas including but not
limited to:
* Integration of upstream components
* Packaging
* Testing of the above
* Documentation

Where an issue is encountered that originates within llvm-project or picolibc,
it is strongly preferred that the issue is addressed directly within that
project. This benefits all users of the upstream projects and makes it easier to
support LLVM Embedded Toolchain for Arm going forward. For guidance on how to
contribute to LLVM see https://llvm.org/docs/Contributing.html. Picolibc follows
the conventional [GitHub pull request](https://docs.github.com/en/pull-requests)
flow.

Contributions are accepted under Apache-2.0. Only submit contributions where
you have authored all of the code.

This project follows the conventional
[GitHub pull request](https://docs.github.com/en/pull-requests) flow.

## Testing

Please ensure your change doesn't break tests. (The project doesn't yet have
GitHub actions to do this). Except for documentation changes, please check that
this passes:

```
ninja check-llvm-toolchain
```

## Coding style

Use the following commands to check the scripts before submitting a pull
request:

```
$ ./setup.sh
$ ./run-precommit-checks.sh
```
