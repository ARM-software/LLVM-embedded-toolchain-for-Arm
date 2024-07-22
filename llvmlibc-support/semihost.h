//
// Copyright (c) 2022, Arm Limited and affiliates.
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//

// This header file provides internal definitions for libsemihost.a,
// including an inline function to make a semihosting call, and a lot
// of constant definitions.

#ifndef LLVMET_LLVMLIBC_SUPPORT_SEMIHOST_H
#define LLVMET_LLVMLIBC_SUPPORT_SEMIHOST_H

#include <llvm-libc-types/ssize_t.h>

#if __ARM_64BIT_STATE
#  define ARG_REG_0 "x0"
#  define ARG_REG_1 "x1"
#else
#  define ARG_REG_0 "r0"
#  define ARG_REG_1 "r1"
#endif

#if __ARM_64BIT_STATE // A64
#  define SEMIHOST_INSTRUCTION "hlt #0xf000"
#elif defined(__thumb__) // T32
#  if defined(__ARM_ARCH_PROFILE) && __ARM_ARCH_PROFILE == 'M'
#    define SEMIHOST_INSTRUCTION "bkpt #0xAB"
#  elif defined(HLT_SEMIHOSTING)
#    define SEMIHOST_INSTRUCTION ".inst.n 0xbabc" // hlt #60
#  else
#    define SEMIHOST_INSTRUCTION "svc 0xab"
#  endif
#else // A32
#  if defined(HLT_SEMIHOSTING)
#    define SEMIHOST_INSTRUCTION ".inst 0xe10f0070" // hlt #0xf000
#  else
#    define SEMIHOST_INSTRUCTION "svc 0x123456"
#  endif
#endif

__attribute__((always_inline))
static long semihosting_call(long val, const void *ptr) {
  register long v __asm__(ARG_REG_0) = val;
  register const void *p __asm__(ARG_REG_1) = ptr;
  __asm__ __volatile__(SEMIHOST_INSTRUCTION
                       : "+r"(v), "+r"(p)
                       :
                       : "memory", "cc");
  return v;
}

#define SYS_CLOCK 0x10
#define SYS_CLOSE 0x02
#define SYS_ELAPSED 0x30
#define SYS_ERRNO 0x13
#define SYS_EXIT 0x18
#define SYS_EXIT_EXTENDED 0x20
#define SYS_FLEN 0x0c
#define SYS_GET_CMDLINE 0x15
#define SYS_HEAPINFO 0x16
#define SYS_ISERROR 0x08
#define SYS_ISTTY 0x09
#define SYS_OPEN 0x01
#define SYS_READ 0x06
#define SYS_READC 0x07
#define SYS_REMOVE 0x0e
#define SYS_RENAME 0x0f
#define SYS_SEEK 0x0a
#define SYS_SYSTEM 0x12
#define SYS_TICKFREQ 0x31
#define SYS_TIME 0x11
#define SYS_TMPNAM 0x0d
#define SYS_WRITE0 0x04
#define SYS_WRITE 0x05
#define SYS_WRITEC 0x03

#define ADP_Stopped_BranchThroughZero 0x20000
#define ADP_Stopped_UndefinedInstr 0x20001
#define ADP_Stopped_SoftwareInterrupt 0x20002
#define ADP_Stopped_PrefetchAbort 0x20003
#define ADP_Stopped_DataAbort 0x20004
#define ADP_Stopped_AddressException 0x20005
#define ADP_Stopped_IRQ 0x20006
#define ADP_Stopped_FIQ 0x20007
#define ADP_Stopped_BreakPoint 0x20020
#define ADP_Stopped_WatchPoint 0x20021
#define ADP_Stopped_StepComplete 0x20022
#define ADP_Stopped_RunTimeErrorUnknown 0x20023
#define ADP_Stopped_InternalError 0x20024
#define ADP_Stopped_UserInterruption 0x20025
#define ADP_Stopped_ApplicationExit 0x20026
#define ADP_Stopped_StackOverflow 0x20027
#define ADP_Stopped_DivisionByZero 0x20028
#define ADP_Stopped_OSSpecific 0x20029

/* SYS_OPEN modes must be one of R,W,A, plus an optional B and optional PLUS */
#define OPENMODE_R 0
#define OPENMODE_W 4
#define OPENMODE_A 8
#define OPENMODE_B 1
#define OPENMODE_PLUS 2

struct __llvm_libc_stdio_cookie { int handle; };

#endif // LLVMET_LLVMLIBC_SUPPORT_SEMIHOST_H
