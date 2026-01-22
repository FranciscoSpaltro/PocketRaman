#include "tcd_free_shooting.h"

volatile uint16_t fs_frames[2][CCD_PIXELS];
volatile uint8_t free_shooting = 0;
volatile uint8_t cap_idx = 0;
volatile uint8_t send_idx = 0;
volatile uint16_t tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS + 1];

void send_data_accumulation_dma(void){

  if (read_frame_idx >= frames_to_send) {
		  send_now = 0;
		  uart_busy = 0;   // por si quedó algo raro
  } else if (uart_busy == 0) {
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
	if (read_frame_idx < frames_to_send) {											// La función se llama desde un while: mientras el número de frame de lectura sea menor que los frames a enviar
	  volatile uint16_t *frame_ptr = &read_frame[read_frame_idx * CCD_PIXELS];		// Obtengo la dirección de memoria del comienzo del frame

	  tx_packet_buffer[0] = HEADER;													// Armo el paquete
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

void send_data_free_shooting_dma(void){
	if(ready_to_read == 1){
	  if(uart_busy == 1)
		  return;

	  ready_to_read = 0;
	  uart_busy = 1;

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
    // 1. Chequeo de seguridad: si no hay datos, solo salimos.
    // NO bajar send_now a 0, o el main dejará de intentar.
    if(fs_data_available == 0){
        return;
    }

    // 2. PROTECCIÓN CRÍTICA: Avisar al sistema que la UART está ocupada.
    // Esto evita que el Timer inicie una nueva captura que pueda
    // sobrescribir el buffer que estamos a punto de leer.
    uart_busy = 1;

    // Preparar cabecera
    tx_packet_buffer[0] = HEADER;
    tx_packet_buffer[1] = DATA_SENDING;
    tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS] = END_BUFFER;

    uint16_t cs = HEADER ^ DATA_SENDING ^ END_BUFFER;

    // Tomamos una "foto" del índice actual para evitar condiciones de carrera
    // si una interrupción ocurriera justo (aunque con uart_busy=1 protegemos bastante)
    uint8_t idx = send_idx;

    // Copia y Checksum
    for (int i = 0; i < CCD_PIXELS; i++) {
        uint16_t value = fs_frames[idx][i];
        tx_packet_buffer[2 + i] = value;
        cs ^= value;
    }

    tx_packet_buffer[OVERHEAD_8/2 + CCD_PIXELS - 1] = cs;

    // Transmisión Bloqueante (~160ms a 460800 baudios)
    HAL_UART_Transmit(&huart6, (uint8_t*)tx_packet_buffer, sizeof(tx_packet_buffer), HAL_MAX_DELAY);

    // 3. Limpieza de banderas
    // Primero indicamos que ya consumimos este dato
    fs_data_available = 0;

    // Finalmente liberamos la UART para permitir nuevas capturas si el timer lo pide
    uart_busy = 0;
}
