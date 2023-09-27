/*===-- InstrProfData.inc - instr profiling runtime structures -*- C++ -*-=== *\
|*
|* Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
|* See https://llvm.org/LICENSE.txt for license information.
|* SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
|*
\*===----------------------------------------------------------------------===*/

// This file is derived from various files in compiler-rt of the llvm-project,
// see https://github.com/llvm/llvm-project/tree/main/compiler-rt/lib/profile

// NOTE: The profile format changes regularly. See INSTR_PROF_RAW_VERSION. 
// This runtime will need updating if the version changes.

// This C file should be compiled without -fprofile-instr-generate. 
// It will provide enough of the runtime for files compiled with
// -fprofile-instr-generate and, optionally, -fcoverage-mapping

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

// Structures are derived from InstrProfData.inc
enum ValueKind {
  IPVK_IndirectCallTarget = 0,
  IPVK_MemOPSize = 1,
  IPVK_First = IPVK_IndirectCallTarget,
  IPVK_Last = IPVK_MemOPSize,
};

typedef void *IntPtrT;

typedef struct __attribute__((aligned(8))) __llvm_profile_data {
  const uint64_t NameRef;
  const uint64_t FuncHash;
  const IntPtrT CounterPtr;
  const IntPtrT FunctionPointer;
  IntPtrT Values;
  const uint32_t NumCounters;
  const uint16_t NumValueSites[IPVK_Last + 1];
} __llvm_profile_data;

typedef struct __llvm_profile_header {
  uint64_t Magic;
  uint64_t Version;
  uint64_t BinaryIdsSize;
  uint64_t DataSize; // now implicitly NumData
  uint64_t PaddingBytesBeforeCounters;
  uint64_t CountersSize; // now implicitly NumCounters
  uint64_t PaddingBytesAfterCounters;
  uint64_t NamesSize;
  uint64_t CountersDelta;
  uint64_t NamesDelta;
  uint64_t ValueKindLast;
} __llvm_profile_header;

/* Record where the data is in memory. Within each of the types of data,
 * it's stored consecutively.
 */
static const __llvm_profile_data *DataFirst = NULL;
static const __llvm_profile_data *DataLast = NULL;
static const char *NamesFirst = NULL;
static const char *NamesLast = NULL;
static char *CountersFirst = NULL;
static char *CountersLast = NULL;

#define INSTR_PROF_RAW_VERSION 8
#define INSTR_PROF_RAW_VERSION_VAR __llvm_profile_raw_version
#define INSTR_PROF_PROFILE_RUNTIME_VAR __llvm_profile_runtime

uint64_t INSTR_PROF_RAW_VERSION_VAR = INSTR_PROF_RAW_VERSION;
int INSTR_PROF_PROFILE_RUNTIME_VAR;

void __llvm_profile_dump(void);

static const void *getMinAddr(const void *A1, const void *A2) {
  return A1 < A2 ? A1 : A2;
}

static const void *getMaxAddr(const void *A1, const void *A2) {
  return A1 > A2 ? A1 : A2;
}

static size_t __llvm_profile_counter_entry_size() {
  return sizeof(uint64_t);
}

// Given a pointer to the __llvm_profile_data for the function, record the
// bounds of the profile data and profile count sections.
// This function is called several time by the __llvm_profile_init function
// at program start.
//
// If this function is called we register __llvm_profile_dump() with
// atexit to write out the profile information to file.
void __llvm_profile_register_function(void *Data_) {
  const __llvm_profile_data *Data = (__llvm_profile_data *)Data_;
  static int RegisteredDumper = 0;
  if (!RegisteredDumper) {
    RegisteredDumper = 1;
    atexit(__llvm_profile_dump);
  }
  // The __llvm_profile_init function in each .o file first
  // calls __llvm_profile_register_function with a pointer
  // to the INSTR_PROF_PROFILE_RUNTIME_VAR. In some runtime
  // implementation this might provoke some action, but for
  // us it is a no-op. We must return before trying to
  // interpret the contents as __llvm_profile_data.
  if (Data == (void*)&INSTR_PROF_PROFILE_RUNTIME_VAR) {
#ifdef PROFLIB_DEBUG
    fprintf(stderr, "skipping __llvm_profile_register_function for llvm_profile_runtime\n");
#endif // PROFLIB_DEBUG
    return;
  }
#ifdef PROFLIB_DEBUG
  fprintf(stderr, "__llvm_profile_register_function Data_ %p\n", Data);
  fprintf(stderr, "  counters: %u at %p\n", Data->NumCounters,
          Data->CounterPtr);
#endif // PROFLIB_DEBUG

  if (!DataFirst) {
    DataFirst = Data;
    DataLast = Data + 1;
    CountersFirst = (char *)((uintptr_t)Data_ + Data->CounterPtr);
    CountersLast =
        CountersFirst + Data->NumCounters * __llvm_profile_counter_entry_size();
    return;
  }

  DataFirst = (const __llvm_profile_data *)getMinAddr(DataFirst, Data);
  CountersFirst = (char *)getMinAddr(
      CountersFirst, (char *)((uintptr_t)Data_ + Data->CounterPtr));

  DataLast = (const __llvm_profile_data *)getMaxAddr(DataLast, Data + 1);
  CountersLast = (char *)getMaxAddr(
      CountersLast,
      (char *)((uintptr_t)Data_ + Data->CounterPtr) +
          Data->NumCounters * __llvm_profile_counter_entry_size());
}

void __llvm_profile_register_names_function(void *NamesStart,
                                            uint64_t NamesSize) {
#ifdef PROFLIB_DEBUG
  fprintf(stderr, "__llvm_profile: register names %p length %" PRIu64 "\n",
          NamesStart, NamesSize);
#endif // PROFLIB_DEBUG

  if (!NamesFirst) {
    NamesFirst = (const char *)NamesStart;
    NamesLast = (const char *)NamesStart + NamesSize;
    return;
  }
  NamesFirst = (const char *)getMinAddr(NamesFirst, NamesStart);
  NamesLast =
      (const char *)getMaxAddr(NamesLast, (const char *)NamesStart + NamesSize);
}

/* Magic number to detect file format and endianness.
 * Use 255 at one end, since no UTF-8 file can use that character.  Avoid 0,
 * so that utilities, like strings, don't grab it as a string.  129 is also
 * invalid UTF-8, and high enough to be interesting.
 * Use "lprofr" in the centre to stand for "LLVM Profile Raw", or "lprofR"
 * for 32-bit platforms.
 */
#define INSTR_PROF_RAW_MAGIC_64                                                \
  (uint64_t)255 << 56 | (uint64_t)'l' << 48 | (uint64_t)'p' << 40 |            \
      (uint64_t)'r' << 32 | (uint64_t)'o' << 24 | (uint64_t)'f' << 16 |        \
      (uint64_t)'r' << 8 | (uint64_t)129
#define INSTR_PROF_RAW_MAGIC_32                                                \
  (uint64_t)255 << 56 | (uint64_t)'l' << 48 | (uint64_t)'p' << 40 |            \
      (uint64_t)'r' << 32 | (uint64_t)'o' << 24 | (uint64_t)'f' << 16 |        \
      (uint64_t)'R' << 8 | (uint64_t)129

static uint64_t __llvm_profile_get_magic(void) {
  return sizeof(void *) == sizeof(uint64_t) ? (INSTR_PROF_RAW_MAGIC_64)
                                            : (INSTR_PROF_RAW_MAGIC_32);
}

static uint64_t __llvm_profile_get_version(void) {
  return __llvm_profile_raw_version;
}

static uint64_t __llvm_profile_get_num_data(const __llvm_profile_data *Begin,
                                            const __llvm_profile_data *End) {
  intptr_t BeginI = (intptr_t)Begin, EndI = (intptr_t)End;
  return ((EndI + sizeof(__llvm_profile_data) - 1) - BeginI) /
         sizeof(__llvm_profile_data);
}

static uint64_t __llvm_profile_get_num_counters(const char *Begin, const char *End) {
  intptr_t BeginI = (intptr_t)Begin, EndI = (intptr_t)End;
  return ((EndI + __llvm_profile_counter_entry_size() - 1) - BeginI) /
         __llvm_profile_counter_entry_size();
}

static const __llvm_profile_data *__llvm_profile_begin_data(void) {
  return DataFirst;
}

static const __llvm_profile_data *__llvm_profile_end_data(void) {
  return DataLast;
}

static int __llvm_write_binary_ids(void) {
  return 0;
}

static const char *__llvm_profile_begin_names(void) { return NamesFirst; }

static const char *__llvm_profile_end_names(void) { return NamesLast; }

static char *__llvm_profile_begin_counters(void) { return CountersFirst; }

static char *__llvm_profile_end_counters(void) { return CountersLast; }

static uint64_t __llvm_profile_get_num_padding_bytes(uint64_t SizeInBytes) {
  return 7 & (sizeof(uint64_t) - SizeInBytes % sizeof(uint64_t));
}

// Called by an atexit handler. Writes a file called default.profraw
// containing the profile data. This needs to be merged by
// llvm-prof. See the clang profiling documentation for details.
void __llvm_profile_dump(void) {
  FILE *Fd;
  /* Header: __llvm_profile_header from InstrProfData.inc */
  const char *FileName = "default.profraw";
  /* Calculate size of sections. */
  const __llvm_profile_data *DataBegin = __llvm_profile_begin_data();
  const __llvm_profile_data *DataEnd = __llvm_profile_end_data();
  const uint64_t NumData = __llvm_profile_get_num_data(DataBegin, DataEnd);
  const char *CountersBegin = __llvm_profile_begin_counters();
  const char *CountersEnd = __llvm_profile_end_counters();
  const uint64_t NumCounters = __llvm_profile_get_num_counters(CountersBegin, CountersEnd);
  const char *NamesBegin = __llvm_profile_begin_names();
  const char *NamesEnd = __llvm_profile_end_names();
  const uint64_t NamesSize = (NamesEnd - NamesBegin) * sizeof(char);
  uint64_t PaddingBytesAfterNames = __llvm_profile_get_num_padding_bytes(NamesSize);

#ifdef PROFLIB_DEBUG
  fprintf(stderr, "__llvm_profile_dump\n");
  fprintf(stderr, "NumCounters %"PRIu64"\n", NumCounters);
#endif // PROFLIB_DEBUG

  __llvm_profile_header Hdr;
  Hdr.Magic = __llvm_profile_get_magic();
  Hdr.Version = __llvm_profile_get_version();
  Hdr.BinaryIdsSize = __llvm_write_binary_ids();
  Hdr.DataSize = NumData; // DataSize is now NumData
  Hdr.PaddingBytesBeforeCounters = 0; // padding for mmap mode
  Hdr.CountersSize = NumCounters; // CounterSize is now NumCounters
  Hdr.PaddingBytesAfterCounters = 0; // padding for mmap mode
  Hdr.NamesSize = NamesSize;
  Hdr.CountersDelta = (uintptr_t)CountersBegin - (uintptr_t)DataBegin;
  Hdr.NamesDelta = (uintptr_t)NamesBegin;
  Hdr.ValueKindLast = IPVK_Last;

  Fd = fopen(FileName, "wb");
  if (!Fd) {
    perror("fopen default.profraw failed");
    return;
  }
  /* Header */
  fwrite(&Hdr, sizeof Hdr, 1, Fd);
  /* Data */
  fwrite(DataBegin, sizeof(__llvm_profile_data), NumData, Fd);
  /* Counters */
  fwrite(CountersBegin, sizeof(uint64_t), NumCounters, Fd);
  /* Names */
  fwrite(NamesBegin, sizeof(uint8_t), NamesSize, Fd);
  /* Padding */
  for (; PaddingBytesAfterNames != 0; --PaddingBytesAfterNames)
    fputc(0, Fd);
  fclose(Fd);
}
