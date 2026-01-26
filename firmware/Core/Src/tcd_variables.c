#include "tcd_variables.h"

volatile uint8_t is_flushing = 1;
volatile uint8_t adc_semaphore = 1;
volatile uint8_t adc_busy = 0;
volatile uint8_t uart_busy = 0;

// TCD_CALLBACKS
volatile uint8_t send_now = 0;
volatile uint16_t number_of_accumulations = 50;
volatile uint8_t acq_enabled = 1;
volatile uint8_t ready_to_read = 0;
volatile uint8_t fs_data_available = 0;
volatile uint8_t processing = 0;

// TCD_SIGNALS
const int initial_n = 6;

volatile int state = 0;
volatile int n = initial_n;
volatile int real_SH_EDGES = 0;

volatile uint8_t sistema_listo_para_capturar = 1;
volatile uint8_t icg_is_high = 0;

const uint32_t TS0_tics = 1;
uint32_t TS1_tics = 2;
const uint32_t TS2_tics = 10;
const uint32_t START_OFFSET = 10;
uint32_t TS3_tics = 0;
uint32_t TS4_tics = 0;
uint32_t TS5_tics = 0;
uint32_t TS6_tics = 0;

uint32_t sh_ccr[SH_EDGES_MAX];
uint32_t icg_ccr[ICG_EDGES];

// TCD_PROCESS_INSTRUCTION
volatile uint8_t rx_cmd_buffer[SIZE_RX_BUFFER_CMD_8];		// Vector para recibir comandos de la RPi
volatile uint8_t process_instruction_flag = 0;				// Indicador de nueva instrucción válida recibida
volatile uint16_t cmd = 0;									// Variable para separar el comando recibido

volatile uint8_t msg_received_flag = 0; 					// Bandera para avisar al main que hay un mensaje para procesar

// TCD_SEND_DATA
volatile uint16_t fs_frames[2][CCD_PIXELS];
volatile uint8_t continuous_mode = 1;
volatile uint8_t cap_idx = 0;
volatile uint8_t send_idx = 0;
volatile uint16_t tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS + 1];

// TCD_SDRAM_MANAGE
volatile uint16_t * new_frame = (uint16_t *) SDRAM_BANK_ADDR;
volatile uint16_t * read_frame = (uint16_t *) SDRAM_BANK_ADDR;
volatile size_t read_frame_idx = 0;
volatile size_t free_frame_space = 2000;							// 128 Mbit = 16 MB de SDRAM; cada frame es 3694*2 bytes=7388 bytes -> entran 2269 frames
volatile size_t saved_frames = 0;
volatile size_t frames_to_send = 0;
