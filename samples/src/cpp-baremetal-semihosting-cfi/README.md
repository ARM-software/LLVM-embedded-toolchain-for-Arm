# Bare-metal CFI sample

This sample shows how to use 
[Control Flow Integrity (CFI)](https://clang.llvm.org/docs/ControlFlowIntegrity.html)
sanitizer to detect certain kinds of undefined behavior 
that can subvert the control flow of C++ code at run-time.

The default target `make build` enables CFI, 
to see the behavior without CFI use the following commands:
```
make build-no-cfi
make run
```
