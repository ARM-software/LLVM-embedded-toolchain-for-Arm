# Code profiling and coverage sample

This sample shows how to use instrumentation to emit profile data 
and use it to show code coverage.

Use `make run` to build with instrumentation, run and collect the raw profile data,
then `make prof` to visualize the code coverage.

NOTE: The upstream runtime implementation changes regularly,
thus `proflib.c` file needs to be updated to keep in sync.
