#ifndef TCD_CALLBACKS_H
#define TCD_CALLBACKS_H

#include "main.h"
#include "tcd_process_instructions.h"
#include "tcd_signals.h"
#include "tcd_free_shooting.h"

extern volatile size_t read_frame_idx;
extern volatile size_t free_frame_space;
extern volatile size_t saved_frames;
extern volatile size_t frames_to_send;
extern volatile uint16_t * new_frame;
extern volatile uint16_t * read_frame;
extern volatile uint8_t icg_is_high;

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

extern volatile uint8_t send_now;
extern volatile uint16_t number_of_accumulations;
extern volatile uint8_t adc_busy;
extern volatile uint8_t uart_busy;
extern volatile uint8_t acq_enabled;

extern volatile uint8_t free_shooting;
extern volatile uint8_t ready_to_read;
extern volatile uint8_t fs_data_available;

#endif
