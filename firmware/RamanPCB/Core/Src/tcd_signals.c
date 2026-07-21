#include <tcd_signals.h>
#include <tcd_variables.h>

extern TIM_HandleTypeDef htim1;
extern TIM_HandleTypeDef htim3;
extern TIM_HandleTypeDef htim5;
extern ADC_HandleTypeDef hadc1;
extern volatile uint8_t send_now;

extern volatile uint32_t n_accum;
extern volatile uint32_t n_skip_counter;

volatile uint8_t adc_busy = 0;
volatile uint8_t can_save = 1;
volatile uint32_t skip_counter = 0;

volatile uint16_t adc_buffer[CCD_PIXELS];
volatile uint32_t accum_buffer[CCD_PIXELS] = {0};
volatile uint16_t frame[CCD_PIXELS];

uint32_t n = 0;
uint32_t real_SH_EDGES = 0;
uint32_t sh_ccr[SH_EDGES_MAX];

volatile uint32_t acumulaciones = 0;

const uint32_t TS0_tics = 1;
const uint32_t TS1_tics = 2;
const uint32_t TS2_tics = 10;

uint32_t TS3_tics = 0;
uint32_t TS4_tics = 0;
uint32_t TS5_tics = 0;
uint32_t TS6_tics = 0;


/**
 * @brief Calculo de los tiempos de cada etapa de la integración y de la cantidad de overhead necesaria para cumplir con el tiempo de lectura
 *
 * @param[in]	t_int_us	Nuevo tiempo de integración en microsegundos
 * @return		void
 *
 * @post Se configuraron los nuevos valores de TS3_tics, TS4_tics, TS5_tics, TS6_tics y n
 * Deben recalcularse las tablas CCR de SH e ICG
 */
void calculate_times(uint32_t t_int_us){
    uint32_t t_int_us_final = t_int_us;

    if(t_int_us < T_INT_MIN_US){
    	t_int_us_final = T_INT_MIN_US;	/* GARANTIZA QUE T_INT_TICS > TS0_TICS + TS1_TICS */
    }

    /*
     * 	if(t_int_us > T_INT_MAX_US) {
     * 		t_int_us_final = T_INT_MAX_US;
     * 	}
     */

    const uint32_t t_int_tics = t_int_us_final * TICKS_PER_US;
    const uint32_t t_readout_tics = T_READOUT_US * TICKS_PER_US;
    const uint32_t t_flush_tics = T_FLUSH_PERIOD_US * TICKS_PER_US;	/* SE DEFINIO DE FORMA TAL QUE SEA MAYOR QUE TS1_TICS + TS2_TICS */

    /*
     * MODELO: desde el momento que baja ICG:
     * S0: desde la bajada de ICG hasta la subida de SH -> (100, 500, 1000) ns
     * S1: tiempo en ON de SH dentro del tiempo en OFF de ICG -> (1000, -, -) ns [si se necesita padding se puede modificar este -> hay que actualizar ICG]
     * S2: desde la bajada de SH hasta la subida de ICG -> (1000, 5000, - ) ns
     * S3: desde la subida de ICG hasta la subida de SH -> t_int - S1 - S2
     * S4: tiempo en ON de SH -> TS1 (sin padding)
     * S5: tiempo en OFF de SH -> t_int - S4
     * S6: desde la bajada de SH hasta la bajada de ICG -> TS5 - TS0
     */
    TS3_tics = t_flush_tics - TS1_tics - TS2_tics;
    TS4_tics = TS1_tics;
    TS5_tics = t_flush_tics - TS4_tics;
    TS6_tics = t_int_tics - TS0_tics - TS1_tics;

    const uint32_t first_fall_tics = TS0_tics + TS1_tics;
    uint32_t flush_intervals = 1U;

    if(t_readout_tics > first_fall_tics){
    	const uint32_t remaining_tics = t_readout_tics - first_fall_tics;
    	flush_intervals = (remaining_tics + t_flush_tics - 1U) / t_flush_tics;
    }

    n = flush_intervals - 1U;
    const uint32_t required_edges = 4U + 2U * n;
    if(required_edges > SH_EDGES_MAX) {
    	n = (SH_EDGES_MAX - 4U) / 2U;
    }
}

/**
 * @brief Actualización de la tabla de valores CCR para SH
 *
 * @post Se actualizaron los valores del vector sh_ccr
 */
void build_SH_table(void)
{
	// Se arma un vector local con todos los tiempos en base al 'n' actualizado
	static uint32_t sh_dt[SH_EDGES_MAX];
	uint32_t index = 0U;

	sh_dt[index++] = TS0_tics;
	sh_dt[index ++] = TS1_tics;
	sh_dt[index++] = TS2_tics + TS3_tics;

	for(uint32_t i = 0U; i < n; i++){
		sh_dt[index++] = TS4_tics;
		sh_dt[index++] = TS5_tics;
	}

	sh_dt[index++] = TS4_tics;

	// De S0 a S0 hay 4 flancos (extremos de S1 y del último S4) más 2*n de cada S4 que se repite
	real_SH_EDGES = index;

    uint32_t accumulated_tics = 0U;

    // Se arma el CCR (acumulativo)
    for (uint32_t i = 0U; i < real_SH_EDGES; i++) {
        accumulated_tics += sh_dt[i];
        sh_ccr[i] = accumulated_tics;
    }

}


/**
 * @brief Inicia o detiene los timers 2, 3 y 4
 *
 * @param[in]	start	1 para iniciarse, 0 para detenerse
 *
 * @return		void
 *
 * @post Se invierte el estado de funcionamiento de los canales y timers que correspondan, cargando los vectores de CCR via DMA en caso de ser necesario
 */
void start_timers(uint8_t start){
	if(start == 1){
		__HAL_TIM_SET_COUNTER(&htim1, 0);
		__HAL_TIM_SET_COUNTER(&htim3, 0);
		__HAL_TIM_SET_COUNTER(&htim5, 0);

		__HAL_TIM_SET_AUTORELOAD(&htim5, sh_ccr[real_SH_EDGES-1] + TS6_tics);
		__HAL_TIM_SET_COMPARE(&htim5, TIM_CHANNEL_2, sh_ccr[0]);

		HAL_TIM_PWM_Start_IT(&htim1, TIM_CHANNEL_1);
		HAL_TIM_OC_Start_DMA(&htim5, TIM_CHANNEL_2, (uint32_t*)sh_ccr, real_SH_EDGES);
		HAL_TIM_PWM_Start_IT(&htim5, TIM_CHANNEL_4);
		HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_3);

		HAL_TIM_Base_Start(&htim1);
		HAL_TIM_Base_Start(&htim5);
		HAL_TIM_Base_Start(&htim3);
	} else if(start == 0){
		HAL_TIM_PWM_Stop(&htim3, TIM_CHANNEL_3);
		HAL_TIM_PWM_Stop(&htim1, TIM_CHANNEL_1);
		HAL_TIM_OC_Stop_DMA(&htim5, TIM_CHANNEL_2);
		HAL_TIM_PWM_Stop_IT(&htim5, TIM_CHANNEL_4);
		HAL_TIM_PWM_Stop_IT(&htim1, TIM_CHANNEL_1);

		HAL_TIM_Base_Stop(&htim3);
		HAL_TIM_Base_Stop(&htim1);
		HAL_TIM_Base_Stop(&htim5);
	}

}


/**
 * @brief  Callback del Timer (Output Compare).
 * Sincroniza el inicio del ADC con la señal ICG (Integration Clear Gate) del CCD.
 *
 * @post	Si los recursos estaban permitidos, se activó el DMA-ADC
 */
void HAL_TIM_PWM_PulseFinishedCallback(TIM_HandleTypeDef *htim) {
	if(htim->Instance == TIM5 && htim->Channel == HAL_TIM_ACTIVE_CHANNEL_4){
		//if(is_flushing == 1)
			//return;

		if(skip_counter < n_skip_counter){
			skip_counter++;
			return;
		} else {
			skip_counter = 0;
		}

		if(adc_busy == 1 || can_save == 0)
			return;

		adc_busy = 1;
		HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buffer, CCD_PIXELS);
	}
}

/**
 * @brief  Callback de finalización de conversión ADC (DMA).
 * Se ejecuta cuando el buffer de píxeles del CCD se ha llenado.
 *
 * @post	Se detuvo el DMA-ADC y se liberó adc_busy. Se liberó el semáforo, se activó send_now (envío de datos)
 * y se intercambiaron los buffers.
 */
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef* hadc) {
    if (hadc->Instance == ADC1) {
    	if(n_accum == 1){
    		for (int i = 0; i < CCD_PIXELS; i++) {
				frame[i] = (uint16_t)(adc_buffer[i]);
			}

			adc_busy = 0;
			can_save = 0;
			send_now = 1;
			return;
    	}

    	for(int i = 0; i < CCD_PIXELS; i++){
    		accum_buffer[i] += adc_buffer[i];
    	}

    	acumulaciones++;

    	if(acumulaciones >= n_accum){
			for (int i = 0; i < CCD_PIXELS; i++) {
				frame[i] = (uint16_t)(accum_buffer[i] / n_accum);
				accum_buffer[i] = 0;
			}

			acumulaciones = 0;
    		adc_busy = 0;
    		can_save = 0;
    		send_now = 1;

    	}

    	else{
    		adc_busy = 0;
    		can_save = 1;
    		send_now = 0;
    	}
    }
}
