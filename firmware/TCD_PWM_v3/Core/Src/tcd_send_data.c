#include <tcd_send_data.h>



// 1. CASO NO FREE-SHOOTING
void send_data_accumulation_dma(void){
	// Se enviaron todos los frames
	if (read_frame_idx >= frames_to_send) {
		  send_now = 0;
		  uart_busy = 0;
  } else if (uart_busy == 0) {
	  // Solo trabajo si UART esta libre
	  uart_busy = 1;
	  volatile uint16_t *frame_ptr = &read_frame[read_frame_idx * CCD_PIXELS];

	  // Si DMA escribió en SDRAM y SDRAM es cacheable:
	  dcache_invalidate_range((const void*)frame_ptr, CCD_PIXELS * sizeof(uint16_t));

	  tx_packet_buffer[0] = HEADER;
	  tx_packet_buffer[1] = DATA_SENDING;
	  tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS] = END_BUFFER;

	  uint16_t cs = HEADER ^ DATA_SENDING ^ END_BUFFER;

	  for (int i = 0; i < CCD_PIXELS; i++) {
		  uint16_t value = frame_ptr[i];
		  tx_packet_buffer[2 + i] = value;
		  cs ^= value;
	  }

	  tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS - 1] = cs;

	  HAL_UART_Transmit_DMA(&huart6, (uint8_t*)tx_packet_buffer, sizeof(tx_packet_buffer));

	  read_frame_idx++;
  }
}

void send_data_accumulation(void){
	// La función se llama desde un while: mientras el número de frame de lectura sea menor que los frames a enviar...
	if (read_frame_idx < frames_to_send) {
	  volatile uint16_t *frame_ptr = &read_frame[read_frame_idx * CCD_PIXELS];		// ... obtengo la dirección de memoria del comienzo del frame...

	  tx_packet_buffer[0] = HEADER;													// ... y armo el paquete
	  tx_packet_buffer[1] = DATA_SENDING;
	  tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS] = END_BUFFER;

	  uint16_t cs = HEADER ^ DATA_SENDING ^ END_BUFFER;

	  for (int i = 0; i < CCD_PIXELS; i++) {
		  uint16_t value = frame_ptr[i];
		  tx_packet_buffer[2 + i] = value;
		  cs ^= value;
	  }

	  tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS - 1] = cs;

	  HAL_UART_Transmit(&huart6, (uint8_t*)tx_packet_buffer, sizeof(tx_packet_buffer), HAL_MAX_DELAY);	// Lo envio
	  read_frame_idx++;																					// Dejo el índice correspondiente al próximo paquete sin leer
	  uart_busy = 0;
	} else {
		send_now = 0;
	}
}

// 2. CASO FREE-SHOOTING
void send_data_free_shooting_dma(void){
	// Verifico que haya un dato guardado y que UART este libre
    if(fs_data_available == 1){
        if(uart_busy == 1)
            return;

        fs_data_available = 0;
        uart_busy = 1;

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
            cs ^= value;
        }

        tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS - 1] = cs;

        HAL_UART_Transmit_DMA(&huart6, (uint8_t*)tx_packet_buffer, sizeof(tx_packet_buffer));
    }
}

void send_data_free_shooting(void){
    // Verifico si hay datos listos
    if(fs_data_available == 0){
        return;
    }

    // Ocupo UART para que TIM no inicie otra lectura
    uart_busy = 1;

    tx_packet_buffer[0] = HEADER;
    tx_packet_buffer[1] = DATA_SENDING;
    tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS] = END_BUFFER;

    uint16_t cs = HEADER ^ DATA_SENDING ^ END_BUFFER;

    // Por las dudas, guardo una copia del índice actual
    uint8_t idx = send_idx;

    for (int i = 0; i < CCD_PIXELS; i++) {
        uint16_t value = fs_frames[idx][i];
        tx_packet_buffer[2 + i] = value;
        cs ^= value;
    }

    tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS - 1] = cs;

    // Transmisión Bloqueante (~160ms a 460800 baudios)
    HAL_UART_Transmit(&huart6, (uint8_t*)tx_packet_buffer, sizeof(tx_packet_buffer), HAL_MAX_DELAY);


    fs_data_available = 0;
    uart_busy = 0;
}
