#ifndef TCD_SEND_DATA_H
#define TCD_SEND_DATA_H

#include "main.h"
#include "tcd_signals.h"
#include "tcd_variables.h"

#define SIZE_RX_BUFFER_CMD_BYTES 10  // 2 bytes header, 2 bytes command, 4 bytes payload, 2 bytes cs

// COMANDOS
#define HEADER 											0x7346
#define END_BUFFER										0x7347
#define SET_INTEGRATION_TIME 							0xF001
#define RESET_DEVICE 									0xF002
#define DATA_SENDING									0xF003
#define SET_NUMBER_OF_ACCUMULATIONS						0xF004
#define CONTINUOUS_MODE_ENABLE							0xF005

void send_data_continuous(void);
void send_data_continuous_dma(void);
uint16_t checksum_fxn(uint16_t a, uint16_t b);
void process_instruction();

#endif
