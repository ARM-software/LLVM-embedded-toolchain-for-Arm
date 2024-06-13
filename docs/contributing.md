# Contribution Guide

*LLVM Embedded Toolchain* integrates
[llvm-project](https://github.com/llvm/llvm-project)
and [picolibc](https://github.com/picolibc/picolibc).
Contributions are welcome that improve the project in areas including but not
limited to:
* Integration of upstream components
* Packaging
* Testing of the above
* Documentation

Where an issue is encountered that originates within `llvm-project`
or `picolibc`, it is strongly preferred that the issue is reported
and addressed directly within that project.
This benefits all users of the upstream projects and makes it easier to
support *LLVM Embedded Toolchain* going forward.

For guidance on how to contribute to the upstream projects see:
* `llvm-project` [Contributing to LLVM](https://llvm.org/docs/Contributing.html)
* `picolibc` GitHub 
[Pull requests documentation](https://docs.github.com/en/pull-requests)

## Ways to contribute

### Report an issue

Please create a Github issue in the *LLVM Embedded Toolchain* project
[Issues](https://github.com/32bitmicro/LLVM-Embedded-Toolchain/issues)
list and label is as a `bug`.

### Submit a fix

For a small change, please create a Pull Request as described in
_How to submit a change_ section below.

### Suggest a feature or bigger change

For a bigger change, please create an issue in the
*LLVM Embedded Toolchain* project
[Issues](https://github.com/32bitmicro/LLVM-Embedded-Toolchain/issues)
list and label is as an `rfc` (Request for Comments) to initiate the discussion
first, before submitting the change itself.

There is no formal template for an `rfc`, however it would be good to explain
the purpose of the change and the key design options, proposed decisions.

## How to submit a change

Contributions are accepted under the
[Apache License 2.0](https://github.com/32bitmicro/LLVM-Embedded-Toolchain/blob/main/LICENSE.txt).
Only submit contributions where you have authored all of the code.

### Pull request

This project follows the conventional
[GitHub pull request](https://docs.github.com/en/pull-requests) flow.

### Testing

Please ensure your change doesn't break tests. (The project doesn't yet have
GitHub actions to do this). Except for documentation changes, please check that
this passes:

```
ninja check-llvm-toolchain
```

### Coding style

Use the following commands to check the scripts before submitting a pull
request:

```
$ ./setup.sh
$ ./run-precommit-checks.sh
```
