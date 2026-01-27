#include <tcd_signals.h>

extern TIM_HandleTypeDef htim2;
extern TIM_HandleTypeDef htim3;
extern TIM_HandleTypeDef htim4;
extern ADC_HandleTypeDef hadc1;

volatile int n = 0;
volatile int real_SH_EDGES = 0;
uint32_t sh_ccr[SH_EDGES_MAX];
const uint32_t START_OFFSET = 10;
const uint32_t TS0_tics = 1;
const uint32_t TS1_tics = 2;
const uint32_t TS2_tics = 10;

uint32_t TS3_tics = 0;
uint32_t TS4_tics = 0;
uint32_t TS5_tics = 0;
uint32_t TS6_tics = 0;

const uint32_t icg_ccr[ICG_EDGES] = {START_OFFSET, START_OFFSET + TS0_tics + TS1_tics + TS2_tics};

/**
 * @brief Configura la secuencia de arranque para las señales SH e ICG.
 * Fuerza los pines a un estado inactivo conocido antes de cambiar al modo TOGGLE para evitar
 * inversiones de fase en el primer pulso al iniciar/reiniciar el Timer.
 *
 * @post Los pines SH e ICG quedan estáticos en su nivel inactivo.
 * El contador (CNT) está en 0. El DMA está habilitado.
 * Requiere START.
 */

void setup_timer_icg_sh(void){
    // Configuración de ARR (periodo) y CNT = 0
    __HAL_TIM_SET_AUTORELOAD(&htim2, sh_ccr[real_SH_EDGES-1] + TS6_tics);
    __HAL_TIM_SET_COUNTER(&htim2, 0);

    TIM_OC_InitTypeDef sConfigOC = {0};

    // Estado fisico del pin = modo logico (+) polaridad
    // SH
    sConfigOC.OCMode = TIM_OCMODE_FORCED_INACTIVE;						// Modo logico
    sConfigOC.Pulse = sh_ccr[0];
    sConfigOC.OCPolarity = TIM_OCPOLARITY_LOW;
    HAL_TIM_OC_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_2);		// 0 (+) 0 = 0 -> SH arranca en bajo

    // ICG
    sConfigOC.OCMode = TIM_OCMODE_FORCED_INACTIVE;
    sConfigOC.Pulse = icg_ccr[0];
    sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
    HAL_TIM_OC_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_3);		// 0 (+) 1 = 1 -> ICG arranca en alto

    // Generar un evento para que los cambios se apliquen inmediatamente al pin
    HAL_TIM_GenerateEvent(&htim2, TIM_EVENTSOURCE_UPDATE);


    // Aplicar el TOGGLE
    sConfigOC.OCMode = TIM_OCMODE_TOGGLE;
    sConfigOC.Pulse = sh_ccr[0];
    sConfigOC.OCPolarity = TIM_OCPOLARITY_LOW;
    HAL_TIM_OC_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_2);

    sConfigOC.OCMode = TIM_OCMODE_TOGGLE;
    sConfigOC.Pulse = icg_ccr[0];
    sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
    HAL_TIM_OC_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_3);

    // Activar DMA e Interrupciones
    __HAL_TIM_DISABLE_DMA(&htim2, TIM_DMA_UPDATE);
    __HAL_TIM_ENABLE_DMA(&htim2, TIM_DMA_CC2);
    __HAL_TIM_ENABLE_DMA(&htim2, TIM_DMA_CC3);
    __HAL_TIM_ENABLE_IT(&htim2, TIM_IT_CC3);
}


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
    // fM = 2 MHz -> 1 us = 2 tics
	const uint16_t tics_por_microsegundo = 2;			// [REVISAR] -> hacerlo portable
    uint32_t t_int_tics = 0;

    if(t_int_us < T_INT_MIN_US)
        t_int_tics = T_INT_MIN_US * tics_por_microsegundo;
    else if(t_int_us > T_INT_MAX_US)
    	t_int_tics = T_INT_MAX_US * tics_por_microsegundo;
    else
        t_int_tics = t_int_us * tics_por_microsegundo;

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
    TS3_tics = t_int_tics - TS1_tics - TS2_tics;
    TS4_tics = TS1_tics;
    TS5_tics = t_int_tics - TS4_tics;
    TS6_tics = TS5_tics - TS0_tics;

    const uint32_t t_readout_tics = 7400 * tics_por_microsegundo;

    // Cálculo de 'n' (Número de pulsos de limpieza durante el readout)
    /*
     * TS3 + n * (TS4 + TS5) + TS4 + TS6 >= t_readout
     * n >= (t_readout - TS3 - TS4 - TS6) / (TS4 + TS5) = (t_readout - TS3 - TS4 - TS6) / t_int
     */

    uint32_t overhead = TS0_tics + TS1_tics + TS2_tics + TS3_tics + TS4_tics + TS6_tics;	// Tiempo sin contar los ciclos TS4-TS5

    if (t_readout_tics + t_int_tics > overhead) {
         n = (t_readout_tics - TS3_tics - TS4_tics - TS6_tics + t_int_tics - 1) / t_int_tics;
    } else {
         n = 0;
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

	sh_dt[0] = TS0_tics;
	sh_dt[1] = TS1_tics;
	sh_dt[2] = TS2_tics + TS3_tics;

	for(int i = 0; i < n; i++){
		sh_dt[3 + 2 * i] = TS4_tics;
		sh_dt[3 + 2 * i + 1] = TS5_tics;
	}

	sh_dt[2 + 2 * n + 1] = TS4_tics;

	// De S0 a S0 hay 4 flancos (extremos de S1 y del último S4) más 2*n de cada S4 que se repite
	real_SH_EDGES = 4 + 2 * n;

    uint32_t t = START_OFFSET;

    // Se arma el CCR (acumulativo)
    for (uint32_t i = 0; i < real_SH_EDGES; i++) {
        t += sh_dt[i];
        sh_ccr[i] = t;
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
		HAL_TIM_OC_Start_DMA(&htim2, TIM_CHANNEL_2, (uint32_t*)sh_ccr, real_SH_EDGES);
		HAL_TIM_OC_Start_DMA(&htim2, TIM_CHANNEL_3, (uint32_t*)icg_ccr, ICG_EDGES);
		HAL_TIM_Base_Start(&htim2);
		HAL_TIM_OC_Start(&htim4, TIM_CHANNEL_4);
		HAL_TIM_Base_Start(&htim4);
		HAL_TIM_PWM_Start(&htim3, TIM_CHANNEL_1);
	} else if(start == 0){
		HAL_TIM_PWM_Stop(&htim3, TIM_CHANNEL_1);
		// HAL_ADC_Stop_DMA(&hadc1);
		HAL_TIM_OC_Stop(&htim4, TIM_CHANNEL_4);
		HAL_TIM_Base_Stop(&htim4);
		HAL_TIM_OC_Stop_DMA(&htim2, TIM_CHANNEL_2);
		HAL_TIM_OC_Stop_DMA(&htim2, TIM_CHANNEL_3);
		HAL_TIM_Base_Stop(&htim2);
	}

}
