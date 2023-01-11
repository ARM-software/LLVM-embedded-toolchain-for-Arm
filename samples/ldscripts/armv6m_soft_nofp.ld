__flash = 0x00000000;   /* starting address of flash */
__flash_size = 0x40000; /* length of flash */
__ram = 0x20000000;     /* starting address of RAM bank 0 */
__ram_size = 0x4000;    /* length of RAM bank 0 */
__stack_size = 512;

INCLUDE picolibc.ld
