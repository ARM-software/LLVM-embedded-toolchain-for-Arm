Additional optimization flags
=============================

## Additional loop unroll in the LTO pipeline
In some cases it is benefitial to perform an additional loop unroll pass so that extra information becomes available to later passes, e.g. SROA. 
Use cases where this could be beneficial - multiple (N>=4) nested loops.

### Usage: 
    -mllvm -extra-LTO-loop-unroll=true/false
