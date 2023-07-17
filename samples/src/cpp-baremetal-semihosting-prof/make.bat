@REM Copyright (c) 2023, Arm Limited and affiliates.
@REM SPDX-License-Identifier: Apache-2.0
@REM
@REM Licensed under the Apache License, Version 2.0 (the "License");
@REM you may not use this file except in compliance with the License.
@REM You may obtain a copy of the License at
@REM
@REM     http://www.apache.org/licenses/LICENSE-2.0
@REM
@REM Unless required by applicable law or agreed to in writing, software
@REM distributed under the License is distributed on an "AS IS" BASIS,
@REM WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
@REM See the License for the specific language governing permissions and
@REM limitations under the License.

@if [%1]==[] goto :target_empty
@set target=%1
@goto :make
:target_empty
@set target=build

:make
@if [%target%]==[build] goto :build
@if [%target%]==[run] goto :run
@if [%target%]==[prof] goto :prof
@if [%target%]==[clean] goto :clean
@echo Error: unknown target "%target%"
@exit /B 1

:build
@if [%BIN_PATH%]==[] goto :bin_path_empty
@call :build_fn
@exit /B

:run
@if exist hello.hex goto :do_run
@if [%BIN_PATH%]==[] goto :bin_path_empty
@call :build_fn
:do_run
qemu-system-arm.exe -M microbit -semihosting -nographic -device loader,file=hello.hex
@exit /B

:prof
llvm-profdata.exe merge -sparse default.profraw -o hello.profdata
llvm-cov.exe show hello.elf -instr-profile=hello.profdata
@exit /B

:clean
if exist hello.elf del /q hello.elf
if exist hello.hex del /q hello.hex
if exist default.profraw del /q default.profraw
if exist hello.profdata del /q hello.profdata
if exist proflib.o del /q proflib.o
@exit /B

:bin_path_empty
@echo Error: BIN_PATH environment variable is not set
@exit /B 1

:build_fn
%BIN_PATH%\clang.exe --target=armv6m-none-eabi -mfloat-abi=soft -march=armv6m -g -c proflib.c
%BIN_PATH%\clang++.exe --target=armv6m-none-eabi -mfloat-abi=soft -march=armv6m -lcrt0-semihost -lsemihost -fno-exceptions -fno-rtti -g -T ..\..\ldscripts\microbit.ld -fprofile-instr-generate -fcoverage-mapping -o hello.elf hello.cpp proflib.o
%BIN_PATH%\llvm-objcopy.exe -O ihex hello.elf hello.hex
@exit /B
