#ifndef TCD_SEND_DATA_H
#define TCD_SEND_DATA_H

#include "main.h"
#include "tcd_signals.h"
#include "tcd_callbacks.h"
#include <tcd_sdram_manage.h>
#include "tcd_variables.h"

void send_data_fixed_length(void);
void send_data_continuous(void);
void send_data_fixed_length_dma(void);
void send_data_continuous_dma(void);

#endif
