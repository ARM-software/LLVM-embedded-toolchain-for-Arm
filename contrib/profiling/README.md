# Profiling

**Note that profiling is experimental.**

Output of the profile operation is always written via semihosting which means, that semihosting has to be enabled
in the debugging chain, either in gdb or pyOCD/OpenOCD.

Output goes always into the file `default.profraw`.

Assuming the toolchain can be found in `~/bin/clang-arm-none-eabi/bin/` and the build directory is in `_build`:

```bash
~/bin/clang-arm-none-eabi/bin/llvm-profdata merge -sparse default.profraw -o main.profdata
~/bin/clang-arm-none-eabi/bin/llvm-cov show $(find _build -iname "*.elf") -instr-profile=main.profdata
```
