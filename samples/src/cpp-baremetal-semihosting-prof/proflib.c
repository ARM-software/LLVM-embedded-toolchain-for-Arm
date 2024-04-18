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
// Macros and __llvm functions derived from
// compiler_rt/lib/profile.

#define INSTR_PROF_RAW_VERSION 9
#define INSTR_PROF_RAW_VERSION_VAR __llvm_profile_raw_version
#define INSTR_PROF_PROFILE_RUNTIME_VAR __llvm_profile_runtime

uint64_t INSTR_PROF_RAW_VERSION_VAR = INSTR_PROF_RAW_VERSION;
uint64_t INSTR_PROF_PROFILE_RUNTIME_VAR;

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
  const IntPtrT BitmapPtr;
  const IntPtrT FunctionPointer;
  IntPtrT Values;
  const uint32_t NumCounters;
  const uint16_t NumValueSites[IPVK_Last + 1];
  const uint32_t NumBitmapBytes;
} __llvm_profile_data;

typedef struct __llvm_profile_header {
  uint64_t Magic;
  uint64_t Version;
  uint64_t BinaryIdsSize;
  uint64_t NumData;
  uint64_t PaddingBytesBeforeCounters;
  uint64_t NumCounters;
  uint64_t PaddingBytesAfterCounters;
  uint64_t NumBitmapBytes;
  uint64_t PaddingBytesAfterBitmapBytes;
  uint64_t NamesSize;
  uint64_t CountersDelta;
  uint64_t BitmapDelta;
  uint64_t NamesDelta;
  uint64_t ValueKindLast;
} __llvm_profile_header;

#define INSTR_PROF_SIMPLE_CONCAT(x, y) x##y
#define INSTR_PROF_CONCAT(x, y) INSTR_PROF_SIMPLE_CONCAT(x, y)

/* Macros to define start/stop section symbol for a given
 * section on Linux. For instance
 * INSTR_PROF_SECT_START(INSTR_PROF_DATA_SECT_NAME) will
 * expand to __start___llvm_prof_data
 */
#define INSTR_PROF_SECT_START(Sect) INSTR_PROF_CONCAT(__start_, Sect)
#define INSTR_PROF_SECT_STOP(Sect) INSTR_PROF_CONCAT(__stop_, Sect)

/* section name strings common to all targets other
   than WIN32 */
#define INSTR_PROF_DATA_COMMON __llvm_prf_data
#define INSTR_PROF_NAME_COMMON __llvm_prf_names
#define INSTR_PROF_CNTS_COMMON __llvm_prf_cnts
#define INSTR_PROF_BITS_COMMON __llvm_prf_bits
#define INSTR_PROF_VALS_COMMON __llvm_prf_vals
#define INSTR_PROF_VNODES_COMMON __llvm_prf_vnds
#define INSTR_PROF_COVMAP_COMMON __llvm_covmap
#define INSTR_PROF_COVFUN_COMMON __llvm_covfun
#define INSTR_PROF_COVDATA_COMMON __llvm_covdata
#define INSTR_PROF_COVNAME_COMMON __llvm_covnames
#define INSTR_PROF_ORDERFILE_COMMON __llvm_orderfile

/* Declare section start and stop symbols for various sections
 * generated by compiler instrumentation.
 */
#define PROF_DATA_START INSTR_PROF_SECT_START(INSTR_PROF_DATA_COMMON)
#define PROF_DATA_STOP INSTR_PROF_SECT_STOP(INSTR_PROF_DATA_COMMON)
#define PROF_NAME_START INSTR_PROF_SECT_START(INSTR_PROF_NAME_COMMON)
#define PROF_NAME_STOP INSTR_PROF_SECT_STOP(INSTR_PROF_NAME_COMMON)
#define PROF_CNTS_START INSTR_PROF_SECT_START(INSTR_PROF_CNTS_COMMON)
#define PROF_CNTS_STOP INSTR_PROF_SECT_STOP(INSTR_PROF_CNTS_COMMON)
#define PROF_BITS_START INSTR_PROF_SECT_START(INSTR_PROF_BITS_COMMON)
#define PROF_BITS_STOP INSTR_PROF_SECT_STOP(INSTR_PROF_BITS_COMMON)
#define PROF_ORDERFILE_START INSTR_PROF_SECT_START(INSTR_PROF_ORDERFILE_COMMON)
#define PROF_VNODES_START INSTR_PROF_SECT_START(INSTR_PROF_VNODES_COMMON)
#define PROF_VNODES_STOP INSTR_PROF_SECT_STOP(INSTR_PROF_VNODES_COMMON)

#define COMPILER_RT_VISIBILITY __attribute__((visibility("hidden")))
#define COMPILER_RT_WEAK __attribute__((weak))

/* Declare section start and stop symbols for various sections
 * generated by compiler instrumentation.
 */
extern __llvm_profile_data PROF_DATA_START COMPILER_RT_VISIBILITY
    COMPILER_RT_WEAK;
extern __llvm_profile_data PROF_DATA_STOP COMPILER_RT_VISIBILITY
    COMPILER_RT_WEAK;
extern char PROF_CNTS_START COMPILER_RT_VISIBILITY COMPILER_RT_WEAK;
extern char PROF_CNTS_STOP COMPILER_RT_VISIBILITY COMPILER_RT_WEAK;
extern char PROF_BITS_START COMPILER_RT_VISIBILITY COMPILER_RT_WEAK;
extern char PROF_BITS_STOP COMPILER_RT_VISIBILITY COMPILER_RT_WEAK;
extern uint32_t PROF_ORDERFILE_START COMPILER_RT_VISIBILITY COMPILER_RT_WEAK;
extern char PROF_NAME_START COMPILER_RT_VISIBILITY COMPILER_RT_WEAK;
extern char PROF_NAME_STOP COMPILER_RT_VISIBILITY COMPILER_RT_WEAK;

void __llvm_profile_dump(void);

static size_t __llvm_profile_counter_entry_size() { return sizeof(uint64_t); }

/* Register an atexit handler to dump the profile after main has exited
 * If this is omitted, a program must manually call __llvm_profile_dump
 * to write the profile
 */
__attribute__((constructor)) void __proflib_initialize() {
  atexit(__llvm_profile_dump);
}

/* Runtime registration has been disabled for ELF platforms. Runtime
 * registration can be used to find the bounds of the counter sections
 * when linker defined symbols are unavailable. This implementation
 * will always use linker defined symbols so we do not need to implement
 * this function. Provide a definition in case runtime registration is
 * enabled, as the compiler will generate references to it.
 */
COMPILER_RT_VISIBILITY void __llvm_profile_register_function(void *Data_) {
  (void)Data_;
}

COMPILER_RT_VISIBILITY void
__llvm_profile_register_names_function(void *NamesStart, uint64_t NamesSize) {
  (void)NamesStart;
  (void)NamesSize;
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
static uint64_t __llvm_profile_get_data_size(const __llvm_profile_data *Begin,
                                             const __llvm_profile_data *End) {
  intptr_t BeginI = (intptr_t)Begin, EndI = (intptr_t)End;
  return ((EndI + sizeof(__llvm_profile_data) - 1) - BeginI) /
         sizeof(__llvm_profile_data);
}
uint64_t __llvm_profile_get_num_data(const __llvm_profile_data *Begin,
                                     const __llvm_profile_data *End) {
  intptr_t BeginI = (intptr_t)Begin, EndI = (intptr_t)End;
  return ((EndI + sizeof(__llvm_profile_data) - 1) - BeginI) /
         sizeof(__llvm_profile_data);
}
static const __llvm_profile_data *__llvm_profile_begin_data(void) {
  return &PROF_DATA_START;
}
static const __llvm_profile_data *__llvm_profile_end_data(void) {
  return &PROF_DATA_STOP;
}
static const char *__llvm_profile_begin_names(void) { return &PROF_NAME_START; }
static const char *__llvm_profile_end_names(void) { return &PROF_NAME_STOP; }
static char *__llvm_profile_begin_counters(void) { return &PROF_CNTS_START; }
static char *__llvm_profile_end_counters(void) { return &PROF_CNTS_STOP; }
static char *__llvm_profile_begin_bitmap(void) { return &PROF_BITS_START; }
static char *__llvm_profile_end_bitmap(void) { return &PROF_BITS_STOP; }
static uint64_t __llvm_profile_get_num_padding_bytes(uint64_t SizeInBytes) {
  return 7 & (sizeof(uint64_t) - SizeInBytes % sizeof(uint64_t));
}
static uint64_t __llvm_profile_get_num_bitmap_bytes(const char *Begin,
                                                    const char *End) {
  return (End - Begin);
}
static uint64_t __llvm_profile_get_name_size(const char *Begin,
                                             const char *End) {
  return End - Begin;
}
static int __llvm_write_binary_ids(void) { return 0; }
static uint64_t __llvm_profile_get_num_counters(const char *Begin,
                                                const char *End) {
  intptr_t BeginI = (intptr_t)Begin, EndI = (intptr_t)End;
  return ((EndI + __llvm_profile_counter_entry_size() - 1) - BeginI) /
         __llvm_profile_counter_entry_size();
}
static uint64_t __llvm_profile_get_counters_size(const char *Begin,
                                                 const char *End) {
  return __llvm_profile_get_num_counters(Begin, End) *
         __llvm_profile_counter_entry_size();
}

/* At exit, the file is written out using semihosting using the default
 * filename of "default.profraw"
 */
void __llvm_profile_dump(void) {
  FILE *Fd;
  /* Header: __llvm_profile_header from InstrProfData.inc */
  const char *FileName = "default.profraw";
  /* Calculate size of sections. */
  const __llvm_profile_data *DataBegin = __llvm_profile_begin_data();
  const __llvm_profile_data *DataEnd = __llvm_profile_end_data();
  const char *CountersBegin = __llvm_profile_begin_counters();
  const char *CountersEnd = __llvm_profile_end_counters();
  const char *BitmapBegin = __llvm_profile_begin_bitmap();
  const char *BitmapEnd = __llvm_profile_end_bitmap();
  const char *NamesBegin = __llvm_profile_begin_names();
  const char *NamesEnd = __llvm_profile_end_names();
  const uint64_t DataSize = __llvm_profile_get_data_size(DataBegin, DataEnd);
  const uint64_t NumCounters =
      __llvm_profile_get_num_counters(CountersBegin, CountersEnd);
  const uint64_t CountersSize =
      __llvm_profile_get_counters_size(CountersBegin, CountersEnd);
  const uint64_t NamesSize = __llvm_profile_get_name_size(NamesBegin, NamesEnd);
  const uint64_t NumBitmapBytes =
      __llvm_profile_get_num_bitmap_bytes(BitmapBegin, BitmapEnd);
  uint64_t PaddingBytesAfterNames =
      __llvm_profile_get_num_padding_bytes(NamesSize);

#ifdef PROFLIB_DEBUG
  fprintf(stderr, "__llvm_profile_dump\n");
  fprintf(stderr, "NumCounters %" PRIu64 "\n", NumCounters);
#endif // PROFLIB_DEBUG

  __llvm_profile_header Hdr;
  Hdr.Magic = __llvm_profile_get_magic();
  Hdr.Version = __llvm_profile_get_version();
  Hdr.BinaryIdsSize = __llvm_write_binary_ids();
  Hdr.NumData = __llvm_profile_get_num_data(DataBegin, DataEnd);
  Hdr.PaddingBytesBeforeCounters = 0;
  Hdr.NumCounters = NumCounters;
  Hdr.PaddingBytesAfterCounters = 0;
  Hdr.NumBitmapBytes = NumBitmapBytes;
  Hdr.PaddingBytesAfterBitmapBytes = 0;
  Hdr.NamesSize = NamesSize;
  Hdr.CountersDelta = (uintptr_t)CountersBegin - (uintptr_t)DataBegin;
  Hdr.BitmapDelta = (uintptr_t)BitmapBegin - (uintptr_t)DataBegin;
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
#ifdef PROFLIB_DEBUG
  fprintf(stderr, "DataSize: %" PRIu64 "\n",
          DataSize * sizeof(__llvm_profile_data));
#endif // PROFLIB_DEBUG
  fwrite(DataBegin, sizeof(__llvm_profile_data), DataSize, Fd);

  /* Counters */
#ifdef PROFLIB_DEBUG
  fprintf(stderr, "CountersBegin: %p\n", CountersBegin);
  fprintf(stderr, "CountersEnd: %p\n", CountersEnd);
  fprintf(stderr, "NumCounters: %" PRIu64 "\n", NumCounters);
  fprintf(stderr, "CountersSize: %" PRIu64 "\n", CountersSize);
#endif // PROFLIB_DEBUG
  fwrite(CountersBegin, sizeof(uint8_t), CountersSize, Fd);

  /* Bitmap */
#ifdef PROFLIB_DEBUG
  fprintf(stderr, "NumBitmapBytes: %" PRIu64 "\n", NumBitmapBytes);
#endif // PROFLIB_DEBUG
  fwrite(BitmapBegin, sizeof(uint8_t), NumBitmapBytes, Fd);

  /* Names */
#ifdef PROFLIB_DEBUG
  fprintf(stderr, "NamesSize: %" PRIu64 "\n", NamesSize);
#endif // PROFLIB_DEBUG
  fwrite(NamesBegin, sizeof(uint8_t), NamesSize, Fd);

  /* Padding */
#ifdef PROFLIB_DEBUG
  fprintf(stderr, "PaddingBytesAfterNames: %" PRIu64 "\n",
          PaddingBytesAfterNames);
#endif // PROFLIB_DEBUG
  for (; PaddingBytesAfterNames != 0; --PaddingBytesAfterNames)
    fputc(0, Fd);

  fclose(Fd);
}
