__flash = 0x80000;          /* init address: execution starts here */
__flash_size = 0x20000000;  /* first half of RAM */
__ram = 0x20000000;         /* second half of RAM */
__ram_size =0x20000000;     /* length of half RAM */
__stack_size = 4096;

INCLUDE picolibcpp.ld
