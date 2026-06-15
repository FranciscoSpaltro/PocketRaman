#ifndef TCD_SEND_DATA_H
#define TCD_SEND_DATA_H

#include "main.h"
#include "tcd_signals.h"
#include "tcd_variables.h"

#define SIZE_RX_BUFFER_CMD_BYTES 10  // 2 bytes header, 2 bytes command, 4 bytes payload, 2 bytes cs

void send_data_continuous(void);
void send_data_continuous_dma(void);
uint16_t checksum_fxn(uint16_t a, uint16_t b);
void process_instruction();

#endif
