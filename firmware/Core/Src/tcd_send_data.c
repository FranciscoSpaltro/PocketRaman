#include <tcd_send_data.h>

volatile uint16_t fs_frames[2][CCD_PIXELS];
volatile uint8_t continuous_mode = 1;
volatile uint8_t cap_idx = 0;
volatile uint8_t send_idx = 0;
volatile uint16_t tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS + 1];

/**
 * @brief Envía el próximo frame almacenado en SDRAM para el caso FIXED-LENGTH MODE via DMA
 *
 * @post Si uart_busy == 0 y hay frames disponibles, setea uart_busy = 1, modifica tx_packet_buffer e incrementa read_frame_idx; si no hay más frames disponibles, resetea send_now y uart_busy
 */
void send_data_fixed_length_dma(void){
	if (uart_busy == 1) {
		return;
	}

	if(read_frame_idx < frames_to_send){
		volatile uint16_t *frame_ptr = &read_frame[read_frame_idx * CCD_PIXELS];

		// [NOTA] Probar sacarlo
		dcache_invalidate_range((const void*)frame_ptr, CCD_PIXELS * sizeof(uint16_t));

		tx_packet_buffer[0] = HEADER;
		tx_packet_buffer[1] = DATA_SENDING;
		tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS] = END_BUFFER;

		uint16_t cs = HEADER ^ DATA_SENDING ^ END_BUFFER;

		for (int i = 0; i < CCD_PIXELS; i++) {
		  uint16_t value = frame_ptr[i];
		  tx_packet_buffer[2 + i] = value;
		  cs = checksum_fxn(cs, value);
		}

		SCB_CleanDCache_by_Addr((uint32_t*)tx_packet_buffer, sizeof(tx_packet_buffer));
		tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS - 1] = cs;

		HAL_UART_Transmit_DMA(&huart6, (uint8_t*)tx_packet_buffer, sizeof(tx_packet_buffer));
		uart_busy = 1;

		read_frame_idx++;
	} else {
		send_now = 0;
	}
}

/**
 * @brief Envía el próximo frame almacenado en SDRAM para el caso FIXED-LENGTH MODE de forma bloqueante.
 * @note Utiliza UART_BUSY
 *
 * @post Si hay frames disponibles, modifica tx_packet_buffer, envia el frame, incrementa read_frame_idx y resetea uart_busy; si no hay más frames disponibles, resetea send_now
 */
void send_data_fixed_length(void){
	// No hace falta verificar TX COMPLETE
	if (read_frame_idx < frames_to_send) {
	  volatile uint16_t *frame_ptr = &read_frame[read_frame_idx * CCD_PIXELS];		// Obtener la dirección de memoria del comienzo del frame

	  tx_packet_buffer[0] = HEADER;
	  tx_packet_buffer[1] = DATA_SENDING;
	  tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS] = END_BUFFER;

	  uint16_t cs = HEADER ^ DATA_SENDING ^ END_BUFFER;

	  for (int i = 0; i < CCD_PIXELS; i++) {
		  uint16_t value = frame_ptr[i];
		  tx_packet_buffer[2 + i] = value;
		  cs = checksum_fxn(cs, value);
	  }

	  tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS - 1] = cs;

	  HAL_UART_Transmit(&huart6, (uint8_t*)tx_packet_buffer, sizeof(tx_packet_buffer), HAL_MAX_DELAY);
	  read_frame_idx++;
	}
	else {
		send_now = 0;
	}
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

	// Obtengo el frame a partir del índice de envio de datos
	uint16_t *frame_ptr = (uint16_t*)fs_frames[send_idx];
	dcache_invalidate_range((void*)frame_ptr, CCD_PIXELS * sizeof(uint16_t));

	tx_packet_buffer[0] = HEADER;
	tx_packet_buffer[1] = DATA_SENDING;
	tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS] = END_BUFFER;

	uint16_t cs = HEADER ^ DATA_SENDING ^ END_BUFFER;
	uint8_t idx = send_idx;

	for (int i = 0; i < CCD_PIXELS; i++) {
		uint16_t value = fs_frames[idx][i];
		tx_packet_buffer[2 + i] = value;
		cs = checksum_fxn(cs, value);
	}

	tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS - 1] = cs;

	HAL_UART_Transmit_DMA(&huart6, (uint8_t*)tx_packet_buffer, sizeof(tx_packet_buffer));
	uart_busy = 1;
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

    // Por las dudas, guardo una copia del índice actual
    uint8_t idx = send_idx;

    for (int i = 0; i < CCD_PIXELS; i++) {
        uint16_t value = fs_frames[idx][i];
        tx_packet_buffer[2 + i] = value;
        cs = checksum_fxn(cs, value);
    }

    tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS - 1] = cs;

    // Transmisión Bloqueante (~160ms a 460800 baudios)
    HAL_UART_Transmit(&huart6, (uint8_t*)tx_packet_buffer, sizeof(tx_packet_buffer), HAL_MAX_DELAY);

    adc_semaphore = 1;
}
