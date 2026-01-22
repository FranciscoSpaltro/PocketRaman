#ifndef TCD_FREE_SHOOTING_H
#define TCD_FREE_SHOOTING_H

#include "main.h"
#include "tcd_signals.h"
#include "tcd_callbacks.h"
#include <tcd_sdram_manage.h>

extern volatile uint16_t fs_frames[2][CCD_PIXELS];
extern volatile uint8_t cap_idx;
extern volatile uint8_t send_idx;
extern volatile uint16_t tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS + 1];

void send_data_accumulation(void);
void send_data_free_shooting(void);
void send_data_accumulation_dma(void);
void send_data_free_shooting_dma(void);

#endif
