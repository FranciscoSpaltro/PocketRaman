#ifndef TCD_SIGNALS_H
#define TCD_SIGNALS_H

#include <stdint.h>
#include <tcd_process_instructions.h>
#include "tcd_variables.h"
#include "main.h"



void calculate_times(uint32_t t_int_us);
void build_SH_table(void);
void build_ICG_table(void);
void setup_timer_icg_sh(void);

#endif
