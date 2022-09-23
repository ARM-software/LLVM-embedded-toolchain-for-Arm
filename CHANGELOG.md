# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added

- A changelog

### Changed 

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

[unreleased]: https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/compare/release-14.0.0...HEAD
[14.0.0]: https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/compare/release-13.0.0...release-14.0.0
[13.0.0]: https://github.com/ARM-software/LLVM-embedded-toolchain-for-Arm/releases/tag/release-13.0.0
