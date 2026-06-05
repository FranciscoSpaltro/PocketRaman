#ifndef TCD_SIGNALS_H
#define TCD_SIGNALS_H

#include <stdint.h>
#include "main.h"

#define SH_EDGES_MAX 1500
#define T_INT_MIN_US 10

void calculate_times(uint32_t t_int_us);
void build_SH_table(void);
void setup_timer_sh(void);
void start_timers(uint8_t start);

#endif
