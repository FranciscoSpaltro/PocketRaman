#ifndef TCD_SIGNALS_H
#define TCD_SIGNALS_H

#include <stdint.h>
#include "main.h"

#define SH_EDGES_MAX 		1500	/* MIN: 150 PARA EL READOUT */
#define T_INT_MIN_US 		10		/* GARANTIZA QUE T_INT_TICS > TS0_TICS + TS1_TICS */
#define TICKS_PER_US 		2U
#define T_READOUT_US		7400U
#define T_FLUSH_PERIOD_US	100U	/* DEBE SER MAYOR QUE TS1_TICS + TS2_TICS */

void calculate_times(uint32_t t_int_us);
void build_SH_table(void);
void setup_timer_sh(void);
void start_timers(uint8_t start);

#endif
