#ifndef CONF_PROCESSING_H
#define CONF_PROCESSING_H

#include <stdint.h>
#include "main.h"
#include "tcd_variables.h"

uint16_t checksum_fxn(uint16_t a, uint16_t b);
void process_instruction(void);

#endif
