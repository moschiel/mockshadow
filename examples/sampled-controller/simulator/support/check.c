#include "app.h"
#include "board.h"
#include "sim_io.h"
#include <stdio.h>

#define CHECK(test) do { if (!(test)) { \
    fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #test); return 1; \
} } while (0)

int main(void)
{
    int sample = -99;
    sim_reset();
    app_reset();
    CHECK(sim_now_ms() == 0 && sim_output() == 0);
    puts("BOOT sampled-controller: time=0 output=0");

    sim_advance(10);
    CHECK(app_step() == BOARD_UNAVAILABLE && sim_output() == 0);
    CHECK(board_read_sample(0, &sample) == BOARD_UNAVAILABLE && sample == -99);
    puts("PASS unavailable input");

    CHECK(sim_inject(250) == BOARD_OK);
    CHECK(app_step() == BOARD_OK && sim_output() == 0);
    CHECK(sim_inject(750) == BOARD_OK);
    CHECK(app_step() == APP_IDLE && sim_output() == 0);
    sim_advance(9);
    CHECK(app_step() == APP_IDLE && sim_output() == 0);
    sim_advance(1);
    CHECK(app_step() == BOARD_OK && sim_output() == 1);
    CHECK(sim_inject(100) == BOARD_OK);
    sim_advance(10);
    CHECK(app_step() == BOARD_OK && sim_output() == 0);
    puts("PASS samples: 250->0 750->1 100->0; period=10 ms");

    CHECK(sim_inject(-1) == BOARD_INVALID);
    CHECK(board_read_sample(0, &sample) == BOARD_OK && sample == 100);
    sample = -99;
    CHECK(board_read_sample(7, &sample) == BOARD_UNSUPPORTED && sample == -99);
    CHECK(board_read_sample(0, NULL) == BOARD_INVALID);
    CHECK(board_write_output(2) == BOARD_INVALID && sim_output() == 0);
    puts("PASS invalid operations preserve state");

    CHECK(sim_inject(750) == BOARD_OK);
    sim_advance(10);
    CHECK(app_step() == BOARD_OK && sim_output() == 1);
    sim_reset();
    app_reset();
    CHECK(sim_now_ms() == 0 && sim_output() == 0);
    sim_advance(10);
    CHECK(app_step() == BOARD_UNAVAILABLE);
    puts("PASS reset clears state");

    sim_reset();
    sim_advance(UINT32_MAX - 5u);
    app_reset();
    CHECK(sim_inject(750) == BOARD_OK);
    sim_advance(9);
    CHECK(app_step() == APP_IDLE && sim_output() == 0);
    sim_advance(1);
    CHECK(app_step() == BOARD_OK && sim_output() == 1 && sim_now_ms() == 4);
    puts("PASS uint32 clock rollover");
    return 0;
}
