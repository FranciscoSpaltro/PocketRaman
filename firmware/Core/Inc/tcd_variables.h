#ifndef TCD_VARIABLES_H
#define TCD_VARIABLES_H

#include "stdint.h"
#include "stdlib.h"
#include "tcd_sdram_manage.h"

#define CCD_PIXELS 3694
#define OVERHEAD_8 										6 											// HEADER + CMD + CHECKSUM - EN BYTES
#define SIZE_RX_BUFFER_CMD_8 							OVERHEAD_8 + 2 * 2 							// Espacio (en bytes) para 2 palabras de PAYLOAD

// COMANDOS
#define HEADER_SIZE_8 									2											// EN BYTES - debe ser múltiplo de 2
#define HEADER 											0x7346
#define END_BUFFER										0x7347
#define SET_INTEGRATION_TIME 							0xF001
#define RESET_DEVICE 									0xF002
#define DATA_SENDING									0xF003
#define SET_NUMBER_OF_ACCUMULATIONS						0xF004
#define CONTINUOUS_MODE_ENABLE							0xF005

#define COMMAND_ASK_FOR_INTEGRATION_TIME 				0x01

#define T_INT_MIN_US									10
//#define T_INT_MAX_US									7000

#define T_INT_DEFAULT									100
#endif
