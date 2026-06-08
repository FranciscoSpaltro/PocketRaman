#include <tcd_uart.h>

extern volatile uint16_t continuous_frames[CCD_PIXELS];
extern volatile uint8_t can_save;
extern volatile uint8_t send_now;

volatile uint16_t tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS + 1];

extern UART_HandleTypeDef huart6;

volatile uint8_t uart_busy = 0;


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
 * @brief Envía el último frame almacenado en RAM para el caso CONTINUOUS-MODE via DMA
 *
 * @post Si hay un frame disponible y uart_busy == 0, modifica tx_packet_buffer y envia el paquete por DMA
 */
void send_data_continuous_dma(void){
	if(uart_busy == 1)
		return;

	send_now = 0;
	tx_packet_buffer[0] = HEADER;
	tx_packet_buffer[1] = DATA_SENDING;
	tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS] = END_BUFFER;

	uint16_t cs = HEADER ^ DATA_SENDING ^ END_BUFFER;

	for (int i = 0; i < CCD_PIXELS; i++) {
		uint16_t value = continuous_frames[i];
		tx_packet_buffer[2 + i] = value;
		cs = checksum_fxn(cs, value);
	}

	tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS - 1] = cs;

	uart_busy = 1;
	HAL_UART_Transmit_DMA(&huart6, (uint8_t*)tx_packet_buffer, sizeof(tx_packet_buffer));
}

/**
 * @brief Envía el último frame almacenado en RAM para el caso CONTINUOUS-MODE de forma bloqueante
 *
 * @post Si hay un frame disponible y uart_busy == 0, modifica tx_packet_buffer y envia el paquete por DMA
 */
void send_data_continuous(void){
	send_now = 0;

    tx_packet_buffer[0] = HEADER;
    tx_packet_buffer[1] = DATA_SENDING;
    tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS] = END_BUFFER;

    uint16_t cs = HEADER ^ DATA_SENDING ^ END_BUFFER;


    for (int i = 0; i < CCD_PIXELS; i++) {
        uint16_t value = continuous_frames[i];
        tx_packet_buffer[2 + i] = value;
        cs = checksum_fxn(cs, value);
    }

    tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS - 1] = cs;

    // Transmisión Bloqueante (~160ms a 460800 baudios)
    HAL_UART_Transmit(&huart6, (uint8_t*)tx_packet_buffer, sizeof(tx_packet_buffer), HAL_MAX_DELAY);
}

/**
 * @brief  Callback de finalización de transmisión UART (DMA).
 * Libera los semáforos para permitir nuevas capturas en modo continuo.
 */
void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
	if(huart->Instance == USART6){
		uart_busy = 0;
		can_save = 1;
	}
}

/**
 * @brief  Callback de recepción de UART.
 * Recepción de comandos desde la PC.
 *
 * @post	Se ejecutó el procesamiento de la instrucción almacenado en el buffer de recepción configurado
 */
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    // Verificamos que sea la UART correcta
    if (huart->Instance == USART6)
    {
        //process_instruction();
    }
}
