#include "tcd_callbacks.h"

volatile uint8_t send_now = 0;
volatile uint16_t number_of_accumulations = 10;
volatile uint8_t adc_busy = 0;
volatile uint8_t uart_busy = 0;
volatile uint8_t acq_enabled = 1;
volatile uint8_t ready_to_read = 0;
volatile uint8_t fs_data_available = 0;


void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc) {
    if (hadc->Instance == ADC1) {
    	HAL_ADC_Stop_DMA(&hadc1);
    	adc_busy = 0;

    	if(free_shooting == 0) {								// FIXED CAPTURE
    		new_frame += CCD_PIXELS;							// Apunto a la siguiente posición de memoria libre
    		free_frame_space--;									// Decremento el contador de frames libres
    		saved_frames++;										// Incremento el contador de frames guardados

    		if(saved_frames == number_of_accumulations){		// Una vez que guardé el último frame
    			send_now = 1;									// activo el envío
    			frames_to_send = saved_frames;					// por un total de saved_frames
    			read_frame_idx = 0;								// y reseteo el índice de lectura para comenzar por el principio
    		}
    	} else {												// FREE CAPTURE
    		send_idx = cap_idx;									// Actualizo el índice de envío por el de que acabo de capturar
    		cap_idx ^= 1;										// Paso el índice de captura al que quedó disponible
    		fs_data_available = 1;									// Activo el envio
    		send_now = 1;
    	}
    }
}




void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
	if(huart->Instance == USART6){
		if(free_shooting == 0){
			if(read_frame_idx < frames_to_send){
				uart_busy = 0;
			}
		} else {		// FREE SHOOTING MODE
			uart_busy = 0;
		}
	}
}

void HAL_TIM_OC_DelayElapsedCallback(TIM_HandleTypeDef *htim) {
	if (htim->Instance == TIM2 && htim->Channel == HAL_TIM_ACTIVE_CHANNEL_3){

		icg_is_high ^= 1;				// Flag de flanco ascendente

		if(icg_is_high == 1){

			if(adc_busy == 1 || uart_busy == 1)
				return;

			adc_busy = 1;

			if(free_shooting == 0){

				if(acq_enabled == 0)
					return;

				if(saved_frames < number_of_accumulations && free_frame_space > 0){

					HAL_ADC_Start_DMA(&hadc1, (uint32_t*)new_frame, CCD_PIXELS);

				} else {
					acq_enabled = 0;
				}

			} else {	// FREE SHOOTING MODE

				HAL_ADC_Start_DMA(&hadc1, (uint32_t*)fs_frames[cap_idx], CCD_PIXELS);
			}
		}

    }
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    // Verificamos que sea la UART correcta
    if (huart->Instance == USART6)
    {
        process_instruction();
    }
}
