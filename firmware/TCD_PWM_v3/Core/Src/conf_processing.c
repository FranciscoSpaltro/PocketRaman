#include "conf_processing.h"


// ADC va de 0-4095 asique valores sobre 0x0FFF son headers adecuados; 16 bits para que se alinee facil con los mensajes DMA ADC
/** ESTRUCTURA:
  *		- HEADER    [2 bytes]
  *		- COMMAND   [2 bytes]
  *		- PAYLOAD	[N bytes]
  *		- CHECKSUM	[2 bytes]
*/

extern UART_HandleTypeDef huart6;
volatile uint8_t rx_cmd_buffer[SIZE_RX_BUFFER_CMD_8];		// Vector para recibir comandos de la RPi
volatile uint8_t process_instruction_flag = 0;				// Indicador de nueva instrucción válida recibida
volatile uint16_t cmd = 0;									// Variable para separar el comando recibido

volatile uint8_t msg_received_flag = 0; 					// Bandera para avisar al main que hay un mensaje para procesar


/**
 * @brief Calcula la suma de verificación (checksum) para un vector de N palabras de 16 bits
 *
 * @param[in]	vec			Puntero al vector de datos de 16 bits
 * @param[in] 	N			Número de elementos contenidos en el vector
 * @return		uint16_t	Resultado de la suma calculada (0x0000 si N es 0)
 */
uint16_t checksum(uint16_t * vec, uint16_t N){
	uint16_t res = 0x0000;

	for(int i = 0; i < N; i++)
		res ^= vec[i];

	return res;
}


/**
 * @brief Procesa la instrucción con payload de dos palabras almacenada en el buffer de recepción.
 *
 * @post En caso de que la trama tenga una estructura válida, pone la #process_instruction_flag en 1.
 */
void process_instruction(void){										// ver si reseteo buffer ante error
	uint16_t * p_rx_cmd_buffer = (uint16_t *) rx_cmd_buffer;

	if(!p_rx_cmd_buffer)
			return;

	// Verifico HEADER
	for(int i = 0; i < HEADER_SIZE_8/2; i++)
		if(p_rx_cmd_buffer[0] != HEADER)
			return;

	cmd = p_rx_cmd_buffer[1];

	if(checksum(p_rx_cmd_buffer, OVERHEAD_8/2 + 2) != p_rx_cmd_buffer[OVERHEAD_8/2 + 2])
		return;

	process_instruction_flag = 1;
}
