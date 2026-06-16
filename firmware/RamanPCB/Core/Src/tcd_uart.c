#include <tcd_uart.h>

extern volatile uint16_t frame[CCD_PIXELS];
extern volatile uint8_t can_save;
extern volatile uint8_t send_now;
extern UART_HandleTypeDef huart6;
extern ADC_HandleTypeDef hadc1;
extern volatile uint8_t process_instruction_flag;
extern volatile uint8_t adc_busy;
extern volatile uint32_t skip_counter;

extern volatile uint32_t accum_buffer[CCD_PIXELS];
extern volatile int acumulaciones;

volatile uint8_t process_instruction_flag = 0;
volatile uint8_t send_now = 0;
volatile uint32_t n_accum = 1;
volatile uint16_t cmd_rx;
volatile uint16_t payload_rx[2] = {0};
volatile uint16_t tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS + 1];
volatile uint16_t rx_cmd_buffer[SIZE_RX_BUFFER_CMD_BYTES/2] = {0};
volatile uint8_t uart_busy = 0;
volatile uint32_t n_skip_counter = 1;

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
	//if(uart_busy == 1)
		//return;

	send_now = 0;

	tx_packet_buffer[0] = HEADER;
	tx_packet_buffer[1] = DATA_SENDING;

	uint16_t cs = HEADER ^ DATA_SENDING ^ END_BUFFER;

	for (int i = 0; i < CCD_PIXELS; i++) {
		uint16_t value = frame[i];
		tx_packet_buffer[2 + i] = value;
		cs = checksum_fxn(cs, value);
	}

	tx_packet_buffer[2 + CCD_PIXELS] = cs;

	tx_packet_buffer[2 + CCD_PIXELS + 1] = END_BUFFER;

	uart_busy = 1;

	uint16_t bytes_to_send = (4 + CCD_PIXELS) * 2;
	HAL_UART_Transmit_DMA(&huart6, (uint8_t*)tx_packet_buffer, bytes_to_send);
	//HAL_UART_TxCpltCallback(&huart6);
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

    uint16_t cs = HEADER ^ DATA_SENDING ^ END_BUFFER;

    for (int i = 0; i < CCD_PIXELS; i++) {
        uint16_t value = frame[i];
        tx_packet_buffer[2 + i] = value;
        cs = checksum_fxn(cs, value);
    }

    tx_packet_buffer[2 + CCD_PIXELS] = cs;

    tx_packet_buffer[2 + CCD_PIXELS + 1] = END_BUFFER;

    // Transmisión Bloqueante (~160ms a 460800 baudios)
    uint16_t bytes_to_send = (4 + CCD_PIXELS) * 2;
    HAL_UART_Transmit(&huart6, (uint8_t*)tx_packet_buffer, bytes_to_send, HAL_MAX_DELAY);

    uart_busy = 0;
    can_save = 1;
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
    	// Verifico HEADER
    	if(rx_cmd_buffer[0] != HEADER)
    	    return;

    	uint16_t cs = 0;
    	for(int i = 0; i < SIZE_RX_BUFFER_CMD_BYTES/2; i++){
    		cs = checksum_fxn(cs, rx_cmd_buffer[i]);
    	}

    	if(cs != 0)
    		return;

    	cmd_rx = rx_cmd_buffer[1];
    	// HEADER (2 bytes) + CMD (2 bytes) + PAYLOAD (4 bytes) + CS (2 bytes)
    	payload_rx[0] = rx_cmd_buffer[2];
    	payload_rx[1] = rx_cmd_buffer[3];

    	process_instruction_flag = 1;

    	__HAL_UART_CLEAR_FLAG(huart, UART_FLAG_ORE | UART_FLAG_NE | UART_FLAG_FE);
    	HAL_UART_Receive_IT(huart, (uint8_t*)rx_cmd_buffer, SIZE_RX_BUFFER_CMD_BYTES);
    }
}


void HAL_UART_ErrorCallback(UART_HandleTypeDef *huart)
{
    if (huart->Instance == USART6)
    {
        // Si la UART tiró algún error en caliente, limpiamos los flags para destrabarla
        __HAL_UART_CLEAR_FLAG(huart, UART_FLAG_ORE | UART_FLAG_NE | UART_FLAG_FE | UART_FLAG_PE);

        // Y volvemos a encender de prepo la escucha de comandos
        HAL_UART_Receive_IT(huart, (uint8_t*)rx_cmd_buffer, SIZE_RX_BUFFER_CMD_BYTES);
    }
}
void reset_parameters(void){
	process_instruction_flag = 0;
	adc_busy = 0;
	uart_busy = 0;
	send_now = 0;
	can_save = 1;
	acumulaciones = 0;
	skip_counter = 0;
	for(int i = 0; i < CCD_PIXELS; i++){
		accum_buffer[i] = 0;
	}
}

void process_instruction(){
	start_timers(0);
	switch(cmd_rx){
		case RESET_DEVICE:{
			NVIC_SystemReset();
			break;
		}

		case SET_INTEGRATION_TIME:{
			uint32_t t_int_recibido = ((uint32_t)payload_rx[1] << 16) | payload_rx[0];
			calculate_times(t_int_recibido);
			build_SH_table();
			n_accum = 1;
			break;
		}

		case SET_NUMBER_OF_ACCUMULATIONS:{
			n_accum = ((uint32_t)payload_rx[1] << 16) | payload_rx[0];
			// Chequear valor
			break;
		}

		case SET_SKIP_COUNTER:{
			n_skip_counter = ((uint32_t)payload_rx[1] << 16) | payload_rx[0];
			break;
		}

		default:
			break;
	}

	reset_parameters();
	start_timers(1);
}


