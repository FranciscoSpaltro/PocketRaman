#ifndef CONF_PROCESSING_H
#define CONF_PROCESSING_H

#include <stdint.h>
#include "main.h"
#include "tcd_variables.h"


// COMANDOS
#define HEADER_SIZE_8 									2											// EN BYTES - debe ser múltiplo de 2
#define HEADER 											0x7346
#define END_BUFFER										0x7347
#define SET_INTEGRATION_TIME 							0xF001
#define RESET_DEVICE 									0xF002
#define DATA_SENDING									0xF003
#define SET_NUMBER_OF_ACCUMULATIONS						0xF004
#define FREE_SHOOTING_ENABLE							0xF005

#define COMMAND_ASK_FOR_INTEGRATION_TIME 				0x01

// VALORES


uint32_t wait_new_int_time_uart(void);
uint16_t checksum(uint16_t * vec, uint16_t N);
void process_instruction(void);

#endif
