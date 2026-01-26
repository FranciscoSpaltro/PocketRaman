#include "tcd_callbacks.h"

// CALLBACK DE FINAL DE CONVERSION DEL FRAME
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc) {
    if (hadc->Instance == ADC1) {
    	HAL_ADC_Stop_DMA(&hadc1);
    	adc_busy = 0;

    	// Si no se está en FREE-SHOOTING, se actualizan la posición del próximo frame y los contadores; en caso de haber llegado al número de acumulaciones solicitado se activa el envio por un total de saved_frames
    	if(free_shooting == 0) {
    		new_frame += CCD_PIXELS;
    		free_frame_space--;
    		saved_frames++;

    		if(saved_frames == number_of_accumulations){
    			send_now = 1;
    			frames_to_send = saved_frames;
    			read_frame_idx = 0;
    		}
    	}

    	// Si se está en FREE-SHOOTING, se intercambian los índices de envio-captura, se da aviso del nuevo frame disponible y se activa el envio
    	else {
    		send_idx = cap_idx;
    		cap_idx ^= 1;
    		fs_data_available = 1;
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
			if(is_flushing == 1)
				return;

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
