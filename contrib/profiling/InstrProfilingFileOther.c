/*===- InstrProfilingFileOther.c - Write instrumentation to a file --------===*\
|*
|* Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
|* See https://llvm.org/LICENSE.txt for license information.
|* SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
|*
\*===----------------------------------------------------------------------===*/

#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <fcntl.h>

#include "InstrProfiling.h"
#include "InstrProfilingInternal.h"
#include "InstrProfilingPort.h"
#include "InstrProfilingUtil.h"



#define FILE_NAME   "default.profraw"

static void writeFileWithoutReturn(void);


//----------------------------------------------------------------------------------------------------------------------
//
// In the original sources the following functions reside in InstrProfilingPlatformOther.c
// Changes:
// - register writeFileWithoutReturn() with atexit()
// - skip function which tries to register INSTR_PROF_PROFILE_RUNTIME_VAR
//

static const __llvm_profile_data *DataFirst = NULL;
static const __llvm_profile_data *DataLast = NULL;
static const char *NamesFirst = NULL;
static const char *NamesLast = NULL;
static char *CountersFirst = NULL;
static char *CountersLast = NULL;

#define INSTR_PROF_PROFILE_RUNTIME_VAR __llvm_profile_runtime
int INSTR_PROF_PROFILE_RUNTIME_VAR;


static inline const void *getMinAddr(const void *A1, const void *A2)
{
    return A1 < A2 ? A1 : A2;
}


static inline const void *getMaxAddr(const void *A1, const void *A2)
{
    return A1 > A2 ? A1 : A2;
}


// Given a pointer to the __llvm_profile_data for the function, record the
// bounds of the profile data and profile count sections.
// This function is called several time by the __llvm_profile_init function
// at program start.
//
// If this function is called we register __llvm_profile_dump() with
// atexit to write out the profile information to file.
void __llvm_profile_register_function(void *Data_)
{
    static int RegisteredDumper = 0;
    const __llvm_profile_data *Data = (__llvm_profile_data *)Data_;

    if ( !RegisteredDumper)
    {
        RegisteredDumper = 1;
        atexit(writeFileWithoutReturn);
    }

    // The __llvm_profile_init function in each .o file first
    // calls __llvm_profile_register_function with a pointer
    // to the INSTR_PROF_PROFILE_RUNTIME_VAR. In some runtime
    // implementation this might provoke some action, but for
    // us it is a no-op. We must return before trying to
    // interpret the contents as __llvm_profile_data.
    if (Data == (void*)&INSTR_PROF_PROFILE_RUNTIME_VAR)
    {
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

    if ( !DataFirst)
    {
        DataFirst = Data;
        DataLast = Data + 1;
        CountersFirst = (char *)((uintptr_t)Data_ + Data->CounterPtr);
        CountersLast = CountersFirst + Data->NumCounters * __llvm_profile_counter_entry_size();
        return;
    }

    DataFirst = (const __llvm_profile_data *)getMinAddr(DataFirst, Data);
    CountersFirst = (char *)getMinAddr(CountersFirst, (char *)((uintptr_t)Data_ + Data->CounterPtr));

    DataLast = (const __llvm_profile_data *)getMaxAddr(DataLast, Data + 1);
    CountersLast = (char *)getMaxAddr(CountersLast, (char *)((uintptr_t)Data_ + Data->CounterPtr) +
                                                    Data->NumCounters * __llvm_profile_counter_entry_size());
}   // __llvm_profile_register_function


void __llvm_profile_register_names_function(void *NamesStart, uint64_t NamesSize)
{
#ifdef PROFLIB_DEBUG
    fprintf(stderr, "__llvm_profile: register names %p length %" PRIu64 "\n",
            NamesStart, NamesSize);
#endif // PROFLIB_DEBUG

    if (!NamesFirst)
    {
        NamesFirst = (const char *)NamesStart;
        NamesLast = (const char *)NamesStart + NamesSize;
        return;
    }
    NamesFirst = (const char *)getMinAddr(NamesFirst, NamesStart);
    NamesLast = (const char *)getMaxAddr(NamesLast, (const char *)NamesStart + NamesSize);
}   // __llvm_profile_register_names_function


const __llvm_profile_data *__llvm_profile_begin_data(void)
{
    return DataFirst;
}   // __llvm_profile_begin_data


const __llvm_profile_data *__llvm_profile_end_data(void)
{
    return DataLast;
}   // __llvm_profile_end_data


int __llvm_write_binary_ids(ProfDataWriter *Writer)
{
    return 0;
}   // __llvm_write_binary_ids


const char *__llvm_profile_begin_names(void)
{
    return NamesFirst;
}   // __llvm_profile_begin_names


const char *__llvm_profile_end_names(void)
{
    return NamesLast;
}   // __llvm_profile_end_names


char *__llvm_profile_begin_counters(void)
{
    return CountersFirst;
}   // __llvm_profile_begin_counters


char *__llvm_profile_end_counters(void)
{
    return CountersLast;
}   // __llvm_profile_end_counters


//----------------------------------------------------------------------------------------------------------------------
//
// Actual dumper is very simple.  Idea is to use semihosting for file IO, but if other functions
// are provided, the dumper is still happy.

/* Return 1 if there is an error, otherwise return  0.  */
static uint32_t fileWriter(ProfDataWriter *This, ProfDataIOVec *IOVecs, uint32_t NumIOVecs)
{
    uint32_t I;
    int fd = (int)This->WriterCtx;
    char Zeroes[sizeof(uint64_t)] = {0};
    for (I = 0; I < NumIOVecs; I++)
    {
        size_t Length = IOVecs[I].ElmSize * IOVecs[I].NumElm;

        if (IOVecs[I].Data)
        {
            if (write(fd, IOVecs[I].Data, Length) != Length)
                return 1;
        }
        else if (IOVecs[I].UseZeroPadding)
        {
            while (Length > 0)
            {
                size_t PartialWriteLen = (sizeof(uint64_t) > Length) ? Length : sizeof(uint64_t);
                if (write(fd, Zeroes, PartialWriteLen) != PartialWriteLen)
                {
                    return 1;
                }
                Length -= PartialWriteLen;
            }
        }
    }
    return 0;
}



static void initFileWriter(ProfDataWriter *This, int fd)
{
    This->Write = fileWriter;
    This->WriterCtx = (void *)fd;
}   // initFileWriter



void __llvm_profile_initialize_file(void)
{
}   // __llvm_profile_initialize_file



int __llvm_profile_write_file(void)
{
    ProfDataWriter fileWriter;
    int fd;
    int r;

    fd = open(FILE_NAME, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    initFileWriter(&fileWriter, fd);
    r = lprofWriteData(&fileWriter, 0, 0);
    close(fd);
    return r;
}   // __llvm_profile_write_file



static void writeFileWithoutReturn(void)
{
    __llvm_profile_write_file();
}   // writeFileWithoutReturn
