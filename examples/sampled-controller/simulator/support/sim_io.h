#ifndef SIM_IO_H
#define SIM_IO_H
#include <stdint.h>

void sim_reset(void);
int sim_inject(int sample);
void sim_advance(uint32_t delta_ms);
int sim_output(void);
int sim_read_sample(unsigned channel, int *sample);
int sim_write_output(int enabled);
uint32_t sim_now_ms(void);
#endif
