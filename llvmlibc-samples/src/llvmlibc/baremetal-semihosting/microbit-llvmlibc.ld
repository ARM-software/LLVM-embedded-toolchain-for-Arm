/*
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * Copyright © 2019 Keith Packard
 * Copyright (c) 2024, Arm Limited and affiliates.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above
 *    copyright notice, this list of conditions and the following
 *    disclaimer in the documentation and/or other materials provided
 *    with the distribution.
 *
 * 3. Neither the name of the copyright holder nor the names of its
 *    contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 * FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 * COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
 * INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
 * STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
 * OF THE POSSIBILITY OF SUCH DAMAGE.
 */

/* Linker script adapted from picolibc linker script
 * llvm-libc uses different linker defined symbols for heap placement.
 */

/* Hard-coded for Cortex-M0 */
MEMORY
{
        boot_flash (rx!w) :
                ORIGIN = 0x00000000,
                LENGTH = 0x3000
        flash (rx!w) :
                ORIGIN = 0x3000,
                LENGTH = 0x3d000
        ram (w!rx) :
                ORIGIN = 0x20000000,
                LENGTH = 0x4000
}

PHDRS
{
        text_boot_flash PT_LOAD;
        text PT_LOAD;
        ram_init PT_LOAD;
        ram PT_LOAD;
        tls PT_TLS;
}

SECTIONS
{
        PROVIDE(__stack = ORIGIN(ram) + LENGTH(ram));

        .boot_flash : {
                KEEP (*(.vectors))
        } >boot_flash AT>boot_flash :text_boot_flash

        .text : {

                /* code */
                *(.text.unlikely .text.unlikely.*)
                *(.text.startup .text.startup.*)
                *(.text .text.* .opd .opd.*)
                PROVIDE (__start___lcxx_override = .);
                *(__lcxx_override)
                PROVIDE (__stop___lcxx_override = .);
                *(.gnu.linkonce.t.*)
                KEEP (*(.fini .fini.*))
                __text_end = .;

                PROVIDE (__etext = __text_end);
                PROVIDE (_etext = __text_end);
                PROVIDE (etext = __text_end);

                /* Need to pre-align so that the symbols come after padding */
                . = ALIGN(8);

                /* lists of constructors and destructors */
                PROVIDE_HIDDEN ( __preinit_array_start = . );
                KEEP (*(.preinit_array))
                PROVIDE_HIDDEN ( __preinit_array_end = . );

                PROVIDE_HIDDEN ( __init_array_start = . );
                KEEP (*(SORT_BY_INIT_PRIORITY(.init_array.*) SORT_BY_INIT_PRIORITY(.ctors.*)))
                KEEP (*(.init_array .ctors))
                PROVIDE_HIDDEN ( __init_array_end = . );

                PROVIDE_HIDDEN ( __fini_array_start = . );
                KEEP (*(SORT_BY_INIT_PRIORITY(.fini_array.*) SORT_BY_INIT_PRIORITY(.dtors.*)))
                KEEP (*(.fini_array .dtors))
                PROVIDE_HIDDEN ( __fini_array_end = . );

        } >flash AT>flash :text

       .rodata : {

                /* read-only data */
                *(.rdata)
                *(.rodata .rodata.*)
                *(.gnu.linkonce.r.*)

                *(.srodata.cst16)
                *(.srodata.cst8)
                *(.srodata.cst4)
                *(.srodata.cst2)
                *(.srodata .srodata.*)

        } >flash AT>flash :text

        .data.rel.ro : {

                /* data that needs relocating */
                *(.data.rel.ro .data.rel.ro.*)

        } >flash AT>flash :text


        /*
         * Needs to be in its own segment with the PLT entries first
         * so that the linker will compute the offsets to those
         * entries correctly.
         */
        .got : {
                *(.got.plt)
                *(.got)
        } >flash AT>flash :text

        .except_ordered : {
                *(.gcc_except_table *.gcc_except_table.*)
                *(.ARM.extab* .gnu.linkonce.armextab.*)
        } >flash AT>flash :text

	.except_unordered : {
                . = ALIGN(8);

                PROVIDE(__exidx_start = .);
                *(.ARM.exidx*)
                PROVIDE(__exidx_end = .);
        } >flash AT>flash :text


        .data : /* For ld.bfd:  ALIGN_WITH_INPUT */ {
                *(.data .data.*)
                *(.gnu.linkonce.d.*)

                /* Need to pre-align so that the symbols come after padding */
                . = ALIGN(8);

                PROVIDE( __global_pointer$ = . + 0x800 );
                PROVIDE( _gp = . + 0x8000);
                *(.sdata .sdata.* .sdata2.*)
                *(.gnu.linkonce.s.*)
        } >ram AT>flash :ram_init
        PROVIDE(__data_start = ADDR(.data));
        PROVIDE(__data_source = LOADADDR(.data));

        /* Thread local initialized data. This gets
         * space allocated as it is expected to be placed
         * in ram to be used as a template for TLS data blocks
         * allocated at runtime. We're slightly abusing that
         * by placing the data in flash where it will be copied
         * into the allocate ram addresses by the existing
         * data initialization code in crt0.
         * BFD includes .tbss alignment when computing .tdata
         * alignment, but for ld.lld we have to explicitly pad
         * as it only guarantees usage as a TLS template works
         * rather than supporting this use case.
         */
        .tdata :  ALIGN(__tls_align)  /* For ld.bfd:  ALIGN_WITH_INPUT */ {
                *(.tdata .tdata.* .gnu.linkonce.td.*)
                PROVIDE(__data_end = .);
                PROVIDE(__tdata_end = .);
        } >ram AT>flash :tls :ram_init
        PROVIDE( __tls_base = ADDR(.tdata));
        PROVIDE( __tdata_start = ADDR(.tdata));
        PROVIDE( __tdata_source = LOADADDR(.tdata) );
        PROVIDE( __tdata_source_end = LOADADDR(.tdata) + SIZEOF(.tdata) );
        PROVIDE( __data_source_end = __tdata_source_end );
        PROVIDE( __tdata_size = SIZEOF(.tdata) );

        PROVIDE( __edata = __data_end );
        PROVIDE( _edata = __data_end );
        PROVIDE( edata = __data_end );
        PROVIDE( __data_size = __data_end - __data_start );
        PROVIDE( __data_source_size = __data_source_end - __data_source );

        .tbss (NOLOAD) : {
                *(.tbss .tbss.* .gnu.linkonce.tb.*)
                *(.tcommon)
                PROVIDE( __tls_end = . );
                PROVIDE( __tbss_end = . );
        } >ram AT>ram :tls :ram
        PROVIDE( __bss_start = ADDR(.tbss));
        PROVIDE( __tbss_start = ADDR(.tbss));
        PROVIDE( __tbss_offset = ADDR(.tbss) - ADDR(.tdata) );
        PROVIDE( __tbss_size = SIZEOF(.tbss) );
        PROVIDE( __tls_size = __tls_end - __tls_base );
        PROVIDE( __tls_align = MAX(ALIGNOF(.tdata), ALIGNOF(.tbss)) );
        PROVIDE( __tls_size_align = (__tls_size + __tls_align - 1) & ~(__tls_align - 1));
        PROVIDE( __arm32_tls_tcb_offset = MAX(8, __tls_align) );
        PROVIDE( __arm64_tls_tcb_offset = MAX(16, __tls_align) );

        .bss (NOLOAD) : {
                *(.sbss*)
                *(.gnu.linkonce.sb.*)
                *(.bss .bss.*)
                *(.gnu.linkonce.b.*)
                *(COMMON)

                /* Align the heap */
                . = ALIGN(8);
                __bss_end = .;
        } >ram AT>ram :ram
        PROVIDE( __non_tls_bss_start = ADDR(.bss) );
        PROVIDE( __end = __bss_end );
        _end = __bss_end;
        PROVIDE( end = __bss_end );
        PROVIDE( __bss_size = __bss_end - __bss_start );

        /* Make the rest of memory available for heap storage
	 * LLVM libc denotes heap with [__end, __llvm_libc_heap_limit)
	 */
        PROVIDE (__llvm_libc_heap_limit = __stack - (DEFINED(__stack_size) ? __stack_size : 4K));
}

ASSERT( __data_size == __data_source_size, "ERROR: .data/.tdata flash size does not match RAM size");

