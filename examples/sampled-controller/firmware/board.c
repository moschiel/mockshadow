/* Synthetic board boundary. No device implementation is supplied. */
#include "board.h"

int board_read_sample(unsigned channel, int *sample)
{
    (void)channel;
    (void)sample;
    return BOARD_UNAVAILABLE;
}

int board_write_output(int enabled)
{
    (void)enabled;
    return BOARD_UNSUPPORTED;
}

uint32_t board_now_ms(void)
{
    return 0;
}
