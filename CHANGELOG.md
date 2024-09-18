# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Armv8.1-M PACBTI library variants (#489).

### Changed
- -nostartfiles required when using crt0-semihosting (#460).

## [19.0.0]

### Added
- AArch32 v8-A and v8-R can now be targeted (#484) (#486).
- Experimental support for building llvm-libc overlay package (#452).
- Additional library variants for Armv7 (#464) (#491) (#494).
- Additional multilib mappings for v7ve and Thumb target triples (#479) (#481).
- Omax and OmaxLTO config files (#454).

### Changed
- Use unstable libc++ ABI (#294).
- Merge v7-M and v7E-M library variants (#482).
- AArch64 A-profile library made distinct (#468).

## [18.0.0]

### Added

- Documentation for the newlib overlay package (#399).
- Support for C++ exceptions and RTTI added in the standard libraries (#339).

## [17.0.0]

### Fixed
- Building from sources created by git archive (#242).
- macOS no longer quarantines files from the macOS package.

### Changed
- Updated multilib to use LLVM multilib.yaml 1.0 (#250).
- `*.cfg` files for library variant selection removed in favor of multilib
- The macOS package is now a `.dmg` instead of `.tar.gz`.
- Linux packages are now in `tar.xz` format instead of `tar.gz`.

### Removed

- Dependency on libtinfo.so.
- Coloured terminal output.

## [16.0.0]

### Added

- Support for locales and input/output streams (#149)
- Experimental support for Armv4T and Armv5TE architectures (#177)
- Provide binary releases for macOS (#86)
- Support for building locally on Windows & macOS (#188)
- Experimental support for multilib (#110).

### Fixed

- lld freezing on Windows (#83)
- Packages now extract into a LLVMEmbeddedToolchainForArm-VERSION-PLATFORM subdirectory (#179)

### Changed

- Updated to [LLVM 16.0.0](https://github.com/llvm/llvm-project/releases/tag/llvmorg-16.0.0)
- Windows release packages are now signed.


## [15.0.2]

### Added

- A changelog
- Support for building with CMake directly
- Support for C++17's aligned operator new

### Changed

- Updated to [LLVM 15.0.2](https://github.com/llvm/llvm-project/releases/tag/llvmorg-15.0.2)
- Replaced newlib with [picolibc](https://github.com/picolibc/picolibc) (GitHub issue #61)
- Renamed and updated configuration files
- Configuration files must now be specified including the file name suffix e.g. `--config armv6m_soft_nofp.cfg`

### Removed

- Wide character support in libc++


## [14.0.0] - 2022-05-03

### Changed

- Updated to [LLVM 14.0.0](https://github.com/llvm/llvm-project/releases/tag/llvmorg-14.0.0)

## [13.0.0] - 2021-12-16

### Added

- Initial release of LLVM Embedded Toolchain for Arm

[unreleased]: https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/compare/release-16.0.0...HEAD
[16.0.0]: https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/compare/release-15.0.2...release-16.0.0
[15.0.2]: https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/compare/release-14.0.0...release-15.0.2
[14.0.0]: https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/compare/release-13.0.0...release-14.0.0
[13.0.0]: https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/releases/tag/release-13.0.0
