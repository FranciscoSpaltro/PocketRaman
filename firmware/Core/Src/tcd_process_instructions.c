#include <tcd_process_instructions.h>

extern UART_HandleTypeDef huart6;


/**
 * @brief Establece la operación del checksum
 *
 * @param[in]	a			Valor A
 * @param[in] 	N			Valor B
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
