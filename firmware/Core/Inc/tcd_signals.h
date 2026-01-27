#ifndef TCD_SIGNALS_H
#define TCD_SIGNALS_H

#include <stdint.h>
#include <tcd_process_instructions.h>
#include "tcd_variables.h"
#include "main.h"

#define SH_EDGES_MAX 200
#define ICG_EDGES 2

extern volatile int n;

void calculate_times(uint32_t t_int_us);
void build_SH_table(void);
void setup_timer_icg_sh(void);
void start_timers(uint8_t start);

#endif
