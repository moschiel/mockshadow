//__MOCK_TARGET: board.c
//__MOCK_MODE: patch
//__MOCK_TOP_START
#include "sim_io.h"
//__MOCK_TOP_END
//__MOCK_REPLACE_CODE_START: function board_read_sample
int board_read_sample(unsigned channel, int *sample)
{
    return sim_read_sample(channel, sample);
}
//__MOCK_REPLACE_CODE_END
//__MOCK_REPLACE_CODE_START: function board_write_output
int board_write_output(int enabled)
{
    return sim_write_output(enabled);
}
//__MOCK_REPLACE_CODE_END
//__MOCK_REPLACE_CODE_START: function board_now_ms
uint32_t board_now_ms(void)
{
    return sim_now_ms();
}
//__MOCK_REPLACE_CODE_END
