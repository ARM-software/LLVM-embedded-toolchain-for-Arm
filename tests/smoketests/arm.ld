OUTPUT_FORMAT("elf32-littlearm")
OUTPUT_ARCH(arm)
ENTRY(_start)

__heap_size = 16K;
__stack_size = 16K;

SECTIONS
{
  . = 0x10000;
  .text :
  {
    *(.text)
  }

  /* Thread-local storage */
  .tdata :
  {
    __tls_base = .;
    *(.tdata)
  }

  .data :
  {
    __data_start = .;
    *(.data)
  }
  __data_size = SIZEOF(.data);
  __data_source = LOADADDR(.data);

  .bss :
  {
    __bss_start = .;
    *(.bss)
    *(COMMON)
  }
  __bss_size = SIZEOF(.bss);

  . = ALIGN(16);
  .heap :
  {
    __heap_start = .;
    . += __heap_size;
    __heap_end = .;
  }

  .stack :
  {
    __stack = .;
    . += __stack_size;
  }
}
