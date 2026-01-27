#ifndef TCD_SEND_DATA_H
#define TCD_SEND_DATA_H

#include "main.h"
#include "tcd_signals.h"
#include "tcd_callbacks.h"
#include <tcd_sdram_manage.h>
#include "tcd_variables.h"

extern volatile uint8_t uart_busy;
extern volatile size_t read_frame_idx;
extern volatile size_t frames_to_send;
extern volatile size_t free_frame_space;
extern volatile uint16_t * read_frame;
extern volatile uint16_t tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS + 1];
extern volatile uint16_t fs_frames[2][CCD_PIXELS];


void send_data_fixed_length(void);
void send_data_continuous(void);
void send_data_fixed_length_dma(void);
void send_data_continuous_dma(void);

#endif
