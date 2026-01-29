#include <tcd_process_instructions.h>

extern UART_HandleTypeDef huart6;

volatile uint8_t rx_cmd_buffer[SIZE_RX_BUFFER_CMD_8];		// Vector para recibir comandos de la RPi
volatile uint8_t process_instruction_flag = 0;				// Indicador de nueva instrucción válida recibida
volatile uint16_t cmd = 0;									// Variable para separar el comando recibido
volatile uint8_t msg_received_flag = 0; 					// Bandera para avisar al main que hay un mensaje para procesar

/**
 * @brief Establece la operación del checksum
 *
 * @param[in]	a			Valor A
 * @param[in] 	b			Valor B
 * @return		uint16_t	Resultado de a ^ b
 */
uint16_t checksum_fxn(uint16_t a, uint16_t b){
	return a ^ b;
}


/**
 * @brief Procesa la instrucción con payload de dos palabras almacenada en el buffer de recepción.
 *
 * @post En caso de que la trama tenga una estructura válida, pone la #process_instruction_flag en 1.
 */
void process_instruction(void){
	uint16_t * p_rx_cmd_buffer = (uint16_t *) rx_cmd_buffer;

	if(!p_rx_cmd_buffer)
			return;

	// Verifico HEADER
	for(int i = 0; i < HEADER_SIZE_8/2; i++)
		if(p_rx_cmd_buffer[0] != HEADER)
			return;

	cmd = p_rx_cmd_buffer[1];

	uint16_t cs = 0;
	for(int i = 0; i < OVERHEAD_8/2 + 2; i++){
		cs = checksum_fxn(cs, p_rx_cmd_buffer[i]);
	}

	if(cs != 0)
		return;


	process_instruction_flag = 1;
}

/**
 * @brief Reinicia los parámetros luego de procesar una instrucción
 *
 * @post saved_frames, read_frames_idx = 0, free_frame_space = 2000, new_frame
 * y read_frame apuntan a SDRAM_BANK_ADDR, adc_semaphore activado, process_instruction_flag en cero y rx_cmd_buffer limpio
 */
void reset_parameters(void){
	saved_frames = 0;
	read_frame_idx = 0;
	free_frame_space = MAX_SDRAM_SPACE;
	new_frame = (uint16_t *) SDRAM_BANK_ADDR;
	read_frame = (uint16_t *) SDRAM_BANK_ADDR;
	adc_semaphore = 1;
	process_instruction_flag = 0;
	send_now = 0;
	is_flushing = 1;
	memset((uint8_t*) rx_cmd_buffer, 0, SIZE_RX_BUFFER_CMD_8);
}
