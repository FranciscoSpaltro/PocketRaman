#ifndef TCD_SIGNALS_H
#define TCD_SIGNALS_H

#include <stdint.h>
#include <tcd_process_instructions.h>
#include "main.h"

#define CCD_PIXELS 3694
#define SH_PIN GPIO_PIN_1
#define ICG_PIN GPIO_PIN_2
#define SH_EDGES_MAX 200
#define ICG_EDGES 2
#define START_OFFSET 44

void calculate_times(uint32_t t_int_us);
void build_SH_table(void);
void build_ICG_table(void);
void setup_timer_icg_sh(void);

#endif
