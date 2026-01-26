#ifndef TCD_VARIABLES_H
#define TCD_VARIABLES_H

#include "stdint.h"
#include "stdlib.h"
#include "tcd_sdram_manage.h"

#define CCD_PIXELS 3694
#define SH_PIN GPIO_PIN_1
#define ICG_PIN GPIO_PIN_2
#define SH_EDGES_MAX 200
#define ICG_EDGES 2
#define OVERHEAD_8 										6 											// HEADER + CMD + CHECKSUM - EN BYTES
#define SIZE_RX_BUFFER_CMD_8 							OVERHEAD_8 + 2 * 2 							// Espacio (en bytes) para 2 palabras de PAYLOAD

extern uint8_t is_flushing;

// TCD_CALLBACKS
extern volatile uint8_t send_now;
extern volatile uint16_t number_of_accumulations;
extern volatile uint8_t adc_busy;
extern volatile uint8_t uart_busy;
extern volatile uint8_t acq_enabled;
extern volatile uint8_t ready_to_read;
extern volatile uint8_t fs_data_available;
extern volatile uint8_t processing;

// TCD_SIGNALS
extern const int initial_n;
extern volatile int state;
extern volatile int n;
extern volatile int real_SH_EDGES;
extern volatile uint8_t sistema_listo_para_capturar;
extern volatile uint8_t icg_is_high;
extern const uint32_t TS0_tics;
extern uint32_t TS1_tics;
extern const uint32_t TS2_tics;
extern const uint32_t START_OFFSET;
extern uint32_t TS3_tics;
extern uint32_t TS4_tics;
extern uint32_t TS5_tics;
extern uint32_t TS6_tics;
extern uint32_t sh_ccr[SH_EDGES_MAX];
extern uint32_t icg_ccr[ICG_EDGES];

// TCD_PROCESS_INSTRUCTION
extern volatile uint8_t rx_cmd_buffer[SIZE_RX_BUFFER_CMD_8];		// Vector para recibir comandos de la RPi
extern volatile uint8_t process_instruction_flag;				// Indicador de nueva instrucción válida recibida
extern volatile uint16_t cmd;									// Variable para separar el comando recibido
extern volatile uint8_t msg_received_flag; 					// Bandera para avisar al main que hay un mensaje para procesar

// TCD_SEND_DATA
extern volatile uint16_t fs_frames[2][CCD_PIXELS];
extern volatile uint8_t free_shooting;
extern volatile uint8_t cap_idx;
extern volatile uint8_t send_idx;
extern volatile uint16_t tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS + 1];

// TCD_SDRAM_MANAGE
extern volatile uint16_t * new_frame;
extern volatile uint16_t * read_frame;
extern volatile size_t read_frame_idx;
extern volatile size_t free_frame_space;							// 128 Mbit = 16 MB de SDRAM; cada frame es 3694*2 bytes=7388 bytes -> entran 2269 frames
extern volatile size_t saved_frames;
extern volatile size_t frames_to_send;

#endif
