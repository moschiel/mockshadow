/* Synthetic application: sample every 10 ms; enable output at 500 or above. */
#include "app.h"
#include "board.h"

static uint32_t last_sample_ms;

void app_reset(void)
{
    last_sample_ms = board_now_ms();
}

int app_step(void)
{
    int sample;
    int status;
    uint32_t now = board_now_ms();
    if ((uint32_t)(now - last_sample_ms) < 10u) {
        return APP_IDLE;
    }
    status = board_read_sample(0, &sample);
    if (status != BOARD_OK) {
        return status;
    }
    status = board_write_output(sample >= 500);
    if (status == BOARD_OK) {
        last_sample_ms = now;
    }
    return status;
}
