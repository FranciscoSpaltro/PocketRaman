#include "tcd_callbacks.h"

extern UART_HandleTypeDef huart6;

volatile uint8_t is_flushing = 1;
volatile uint8_t adc_semaphore = 1;
volatile uint8_t adc_busy = 0;
volatile uint8_t uart_busy = 0;

volatile uint8_t send_now = 0;
volatile uint16_t number_of_accumulations = 50;
volatile uint8_t acq_enabled = 1;
volatile uint8_t ready_to_read = 0;
volatile uint8_t fs_data_available = 0;
volatile uint8_t processing = 0;

volatile uint8_t icg_is_high = 0;

/**
 * @brief  Callback de finalización de conversión ADC (DMA).
 * Se ejecuta cuando el buffer de píxeles del CCD se ha llenado.
 * Gestiona el doble buffer en el modo continuo y el espacio disponible en el modo fixed-length.
 *
 * @post	Se detuvo el DMA-ADC y se liberó adc_busy. Si estaba en modo continuo, se liberó el semáforo, se activó send_now (envío de datos)
 * y se intercambiaron los buffers. Si estaba en modo fixed-length, se incrementó la posición de memoria del nuevo frame, se actualizaron los
 * contadores de espacio disponible y, si se había llegado al número de acumulaciones requerido, se liberó el semáforo, se activó send_now,
 * se reseteó el índice de lectura y se actualizó la cantidad de frames a enviar
 */
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc) {
    if (hadc->Instance == ADC1) {
    	HAL_ADC_Stop_DMA(&hadc1);
    	adc_busy = 0;

    	if(continuous_mode == 1){
    		adc_semaphore = 0;
    		send_idx = cap_idx;
			cap_idx ^= 1;
			send_now = 1;
    	} else if(continuous_mode == 0){
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


/**
 * @brief  Callback de finalización de transmisión UART (DMA).
 * Libera los semáforos para permitir nuevas capturas en modo continuo.
 */
void HAL_UART_TxCpltCallback(UART_HandleTypeDef *huart)
{
	if(huart->Instance == USART6){
		if(continuous_mode == 1)
			adc_semaphore = 1;
		uart_busy = 0;
	}
}

/**
 * @brief  Callback del Timer (Output Compare).
 * Sincroniza el inicio del ADC con la señal ICG (Integration Clear Gate) del CCD.
 *
 * @post	Se actualizó el flag de flanco ascendente y, si los recursos estaban permitidos, se activó el DMA-ADC
 */
void HAL_TIM_OC_DelayElapsedCallback(TIM_HandleTypeDef *htim) {
	if (htim->Instance == TIM2 && htim->Channel == HAL_TIM_ACTIVE_CHANNEL_3){

		icg_is_high ^= 1;				// Flag de flanco ascendente

		if(icg_is_high == 1){
			if(is_flushing == 1 || adc_semaphore == 0)
				return;

			if(adc_busy == 1)
				return;

			if(continuous_mode == 1) {
			    HAL_ADC_Start_DMA(&hadc1, (uint32_t*)fs_frames[cap_idx], CCD_PIXELS);
			} else if(continuous_mode == 0){
			    HAL_ADC_Start_DMA(&hadc1, (uint32_t*)new_frame, CCD_PIXELS);
			}

		}

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
        process_instruction();
    }
}
