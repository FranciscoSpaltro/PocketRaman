#ifndef TCD_CALLBACKS_H
#define TCD_CALLBACKS_H

#include <tcd_send_data.h>
#include "main.h"
#include "tcd_process_instructions.h"
#include "tcd_signals.h"
#include "tcd_variables.h"
#include "string.h"

extern volatile uint8_t adc_busy;
extern volatile uint8_t continuous_mode;
extern volatile uint8_t adc_semaphore;
extern volatile uint8_t send_idx;
extern volatile uint8_t cap_idx;
extern volatile uint8_t send_now;
extern volatile uint16_t * new_frame;
extern volatile uint16_t number_of_accumulations;
extern volatile uint8_t icg_is_high;
extern volatile uint8_t is_flushing;
extern volatile uint16_t fs_frames[2][CCD_PIXELS];

extern ADC_HandleTypeDef hadc1;
extern DMA_HandleTypeDef hdma_adc1;

extern TIM_HandleTypeDef htim2;
extern TIM_HandleTypeDef htim3;
extern DMA_HandleTypeDef hdma_tim2_up_ch3;
extern DMA_HandleTypeDef hdma_tim2_ch2_ch4;

extern UART_HandleTypeDef huart6;
extern DMA_HandleTypeDef hdma_usart6_rx;
extern DMA_HandleTypeDef hdma_usart6_tx;

extern SDRAM_HandleTypeDef hsdram1;


#endif
