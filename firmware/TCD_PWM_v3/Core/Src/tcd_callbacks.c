#include "tcd_callbacks.h"



extern UART_HandleTypeDef huart6;

// CALLBACK DE FINAL DE CONVERSION DEL FRAME
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc) {
    if (hadc->Instance == ADC1) {
    	HAL_ADC_Stop_DMA(&hadc1);
    	adc_busy = 0;

    	if(continuous_mode == 1){
    		adc_semaphore = 0;
    		send_idx = cap_idx;
			cap_idx ^= 1;
			send_now = 1;
    	}
    	else {
    		new_frame += CCD_PIXELS;
			free_frame_space--;
			saved_frames++;

			if(saved_frames == number_of_accumulations){
				adc_semaphore = 0;
				send_now = 1;
				frames_to_send = saved_frames;
				read_frame_idx = 0;
			}
    	}

    }
}


// Para casos con DMA en la TX
void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
	if(huart->Instance == USART6){
		if(continuous_mode == 1)
			adc_semaphore = 1;
		uart_busy = 0;
	}
}

void HAL_TIM_OC_DelayElapsedCallback(TIM_HandleTypeDef *htim) {
	if (htim->Instance == TIM2 && htim->Channel == HAL_TIM_ACTIVE_CHANNEL_3){

		icg_is_high ^= 1;				// Flag de flanco ascendente

		if(icg_is_high == 1){
			if(is_flushing == 1 || adc_semaphore == 0)
				return;

			/*if((HAL_ADC_GetState(&hadc1) != HAL_ADC_STATE_READY)){
				return;
			}*/
			if(adc_busy == 1)
				return;

			if(continuous_mode == 1) {
			    HAL_ADC_Start_DMA(&hadc1, (uint32_t*)fs_frames[cap_idx], CCD_PIXELS);
			} else {
			    HAL_ADC_Start_DMA(&hadc1, (uint32_t*)new_frame, CCD_PIXELS);
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
