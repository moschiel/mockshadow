#ifndef BOARD_H
#define BOARD_H
#include <stdint.h>

enum { BOARD_OK = 0, BOARD_UNAVAILABLE = -1, BOARD_UNSUPPORTED = -2,
       BOARD_INVALID = -3 };
int board_read_sample(unsigned channel, int *sample);
int board_write_output(int enabled);
uint32_t board_now_ms(void);
#endif
