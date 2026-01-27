#ifndef CONF_PROCESSING_H
#define CONF_PROCESSING_H

#include <stdint.h>
#include "main.h"
#include "tcd_variables.h"
#include "string.h"

extern volatile uint8_t rx_cmd_buffer[SIZE_RX_BUFFER_CMD_8];
extern volatile uint16_t cmd;
extern volatile uint8_t process_instruction_flag;
extern volatile size_t saved_frames;
extern volatile uint16_t * read_frame;
extern volatile size_t read_frame_idx;
extern volatile uint16_t * new_frame;
extern volatile size_t free_frame_space;
extern volatile uint8_t adc_semaphore;

uint16_t checksum_fxn(uint16_t a, uint16_t b);
void process_instruction(void);
void reset_parameters(void);


#endif
