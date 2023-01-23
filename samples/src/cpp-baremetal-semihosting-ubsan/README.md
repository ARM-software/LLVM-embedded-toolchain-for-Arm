# Bare-metal UBSan sample

This sample shows how to use 
[UndefinedBehaviorSanitizer (UBSan)](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html)
to detect undefined behavior in C++ code at run-time.

UBSan has two supported modes of operation: trap and minimal runtime, 
see `Makefile` for the respective command line options.

The default `make build` uses the minimal runtime mode.

Use the following commands to invoke the trap mode:
```
make build-trap
make run
```
