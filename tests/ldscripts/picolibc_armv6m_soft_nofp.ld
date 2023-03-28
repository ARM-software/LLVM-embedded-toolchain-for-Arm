__flash         = 0x00000000; /* starting address of flash */
__flash_size    = 0x00400000; /* length of flash */
__ram           = 0x20000000; /* starting address of RAM bank 0 */
__ram_size      = 0x00200000; /* length of RAM bank 0 */
__stack_size    = 4k;

INCLUDE picolibcpp.ld
