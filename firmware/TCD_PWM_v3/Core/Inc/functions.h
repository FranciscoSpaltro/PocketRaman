#ifndef FUNCTIONS_H
#define FUNCTIONS_H

#include <stdint.h>
#include "main.h"

#define CCD_PIXELS 3694
#define SH_PIN GPIO_PIN_1
#define ICG_PIN GPIO_PIN_2
#define SH_EDGES_MAX 200
#define ICG_EDGES 2
#define START_OFFSET 44

#define HEADER_SIZE 4

void calculate_times(uint32_t t_int_us);
void build_SH_table(void);
void build_ICG_table(void);
void build_header(void);
void setup_timer_icg_sh(void);
void change_integration_time(uint32_t t_int_us);
uint32_t wait_new_int_time_uart(void);

#endif
