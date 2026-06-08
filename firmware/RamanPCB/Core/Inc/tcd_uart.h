#ifndef TCD_SEND_DATA_H
#define TCD_SEND_DATA_H

#include "main.h"
#include "tcd_signals.h"
#include "tcd_variables.h"

void send_data_continuous(void);
void send_data_continuous_dma(void);
uint16_t checksum_fxn(uint16_t a, uint16_t b);

#endif
