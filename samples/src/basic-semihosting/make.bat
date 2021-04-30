@REM Copyright (c) 2021, Arm Limited and affiliates.
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
@if [%target%]==[clean] goto :clean
@echo Error: unknown target "%target%"
@exit /B 1

:build
@if [%BIN_PATH%]==[] goto :bin_path_empty
%BIN_PATH%\clang.exe --config armv6m-none-eabi_rdimon -g -o hello.elf hello.c
@exit /B

:clean
if exist hello.elf del /q hello.elf
@exit /B

:bin_path_empty
@echo Error: BIN_PATH environment variable is not set
@exit /B 1
