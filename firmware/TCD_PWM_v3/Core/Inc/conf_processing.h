#ifndef CONF_PROCESSING_H
#define CONF_PROCESSING_H

#include <stdint.h>
#include "main.h"

#define COMMAND_ASK_FOR_INTEGRATION_TIME 0x01
#define CONF_MSG 0x00
#define DATA_MSG 0x01

#define HEADER_SIZE 1	// en PALABRAS (2 bytes)

uint32_t wait_new_int_time_uart(void);

#endif
