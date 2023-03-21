# Profiling

**Note that profiling is experimental.**

This add-on enables profiling support for embedded Arm targets.  Profiling uses the standard mechanisms
provided by clang, transmission of the collected data is done via semihosting which implies that a debugger
has to be connected.

Thus semihosting has to be enabled in the debugging chain, either in gdb or pyOCD/OpenOCD.

To simplify the library output goes always into the file `default.profraw`.  Additionally the actual semihosting 
libraries are not required because the profiling library provides its own version of semihosting invocation.


## Building libclang_rt.profile.a

Building the profiling library is controlled with the **LLVM_TOOLCHAIN_CONTRIB_PROFIL** switch on cmake
invocation.  To include the profiling library use:

```bash
# "cd" into build directory (one level below LLVM-embedded-toolchain-for-Arm)
cmake .. -GNinja -DFETCHCONTENT_QUIET=OFF -DLLVM_TOOLCHAIN_CONTRIB_PROFILE=ON
ninja llvm-toolchain
ninja package-llvm-toolchain
```

or with less effort:

```bash
# "cd" into build directory (one level below LLVM-embedded-toolchain-for-Arm)
cmake .. -GNinja -DLLVM_TOOLCHAIN_CONTRIB_PROFILE=ON -DFETCHCONTENT_FULLY_DISCONNECTED=ON -DLLVM_TOOLCHAIN_LIBRARY_VARIANTS="aarch64;armv6m_soft_nofp"
ninja llvm-toolchain
ninja package-llvm-toolchain
```

If enabled, the library will be built for all enabled target architectures.  After installation, the library
will be placed in the same location as `libclang_rt.builtins.a`, i.e. `$(SYSROOT)/lib`.



## Usage

### In the Code

#### With semihosting configuration

If the whole program is linked with semihost support, writing of `default.profraw` takes place on exit of the program.
If exit never happens `__llvm_profile_write_file()` has to be invoked manually.

#### Standalone

After data collection, `default.profraw` has to be written manually via a call to `__llvm_profile_write_file()`.
Note that for successful write operation, the debugger has to be connected.


### Compiling and Linking

Compile options must contain `-fprofile-instr-generate -fcoverage-mapping`,
linker options `-fprofile-instr-generate -fcoverage-mapping -lclang_rt.profile`.


### Using the collected data

After `default.profraw` has been written, the collected data can be evaluated further.
Assuming the toolchain can be found in `~/bin/clang-arm-none-eabi/bin/` and the build directory is in `_build`, a simple
visualization of the data could be:

```bash
~/bin/clang-arm-none-eabi/bin/llvm-profdata show default.profraw --all-functions -counts
~/bin/clang-arm-none-eabi/bin/llvm-profdata merge -sparse default.profraw -o program.profdata
~/bin/clang-arm-none-eabi/bin/llvm-cov show $(find _build -iname "*.elf") -instr-profile=program.profdata
```


## Notes

* again: consider this feature as experimental, feedback is welcome
* aarch64 is completely untested!  Even the semihost invocation via `hlt #0xf000` is not clear and has been
  taken blindly from picolib.
* a debugger must be connected for successful operation.  Take care that semihost applications issue
  a hard fault if no debugger is connected and a semihost operation should take place.
  For more about this and how to prevent it see 
  [Using Semihosting the Direct Way](https://mcuoneclipse.com/2023/03/09/using-semihosting-the-direct-way/)
