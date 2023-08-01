__boot_flash = 0x00000000;  /* fragment of the flash where interrupt vector goes */
__boot_flash_size = 0x1000; /* length of flash fragment with interrupt vector */
__flash = 0x00001000;       /* starting address of the remaining flash */
__flash_size = 0x3f000;     /* length of the remaining flash */
__ram = 0x20000000;         /* starting address of RAM bank 0 */
__ram_size = 0x4000;        /* length of RAM bank 0 */
__stack_size = 512;

INCLUDE picolibcpp.ld
