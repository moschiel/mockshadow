/* Single-threaded teaching model; state is volatile and time is injected. */
#include "sim_io.h"
#include "board.h"
#include <stdio.h>

static uint32_t time_ms;
static int input_sample;
static int input_ready;
static int output_enabled;

void sim_reset(void)
{
    time_ms = 0;
    input_sample = 0;
    input_ready = 0;
    output_enabled = 0;
}

int sim_inject(int sample)
{
    if (sample < 0 || sample > 1000) {
        fprintf(stderr, "model: invalid sample=%d\n", sample);
        return BOARD_INVALID;
    }
    input_sample = sample;
    input_ready = 1;
    return BOARD_OK;
}

void sim_advance(uint32_t delta_ms)
{
    time_ms += delta_ms;
}

uint32_t sim_now_ms(void) { return time_ms; }
int sim_output(void) { return output_enabled; }

int sim_read_sample(unsigned channel, int *sample)
{
    if (channel != 0) {
        fprintf(stderr, "model: unsupported channel=%u\n", channel);
        return BOARD_UNSUPPORTED;
    }
    if (sample == NULL) {
        fprintf(stderr, "model: null sample destination\n");
        return BOARD_INVALID;
    }
    if (!input_ready) {
        return BOARD_UNAVAILABLE;
    }
    *sample = input_sample;
    return BOARD_OK;
}

int sim_write_output(int enabled)
{
    if (enabled != 0 && enabled != 1) {
        fprintf(stderr, "model: invalid output=%d\n", enabled);
        return BOARD_INVALID;
    }
    output_enabled = enabled;
    return BOARD_OK;
}
