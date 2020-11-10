#include <stdio.h>

// https://infocenter.nordicsemi.com/pdf/nRF51_RM_v3.0.pdf sections 14.2 and 29.10

#define DEFINE_PORT(name,address) volatile unsigned int* name = (unsigned int*) address

DEFINE_PORT(gpio_dir_set, 0x50000518);

DEFINE_PORT(uart_starttx, 0x40002008);
DEFINE_PORT(uart_txdrdy, 0x4000211C);
DEFINE_PORT(uart_enable, 0x40002500);
DEFINE_PORT(uart_pseltxd, 0x4000250C);
DEFINE_PORT(uart_txd, 0x4000251C);
DEFINE_PORT(uart_baud_rate, 0x40002524);
DEFINE_PORT(uart_config, 0x4000256C);

void uart_init()
{
  *gpio_dir_set = 1 << 24;
  *uart_baud_rate = 0x01D7E000; // 115200
  *uart_config = 0;
  *uart_pseltxd = 24;
  *uart_enable = 4;
  *uart_starttx = 1;
}

void uart_send_message(char* message)
{
  for(char* next_char = message; *next_char != '\0'; next_char++) {
    *uart_txd = *next_char;
    while (!*uart_txdrdy) {};
  }
}

int main(void) 
{
  uart_init();
  uart_send_message("Hello World!");
  return 0;
}

void SystemInit() {}