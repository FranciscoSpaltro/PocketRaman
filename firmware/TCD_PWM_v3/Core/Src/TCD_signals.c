#include <tcd_signals.h>

extern TIM_HandleTypeDef htim2;
extern TIM_HandleTypeDef htim3;
extern ADC_HandleTypeDef hadc1;


void setup_timer_icg_sh(void){
    // 1. Periodo y Reset Contador
    __HAL_TIM_SET_AUTORELOAD(&htim2, sh_ccr[real_SH_EDGES-1] + TS6_tics);
    __HAL_TIM_SET_COUNTER(&htim2, 0);

    TIM_OC_InitTypeDef sConfigOC = {0};

    // 2. Forzar el pin a "0" y "1", respectivamente (en especial cuando se quiere modificar en tiempo de ejecución, ya que sino realiza los toggles desde el último estado y el resultado es indefinido)
    // SH
    sConfigOC.OCMode = TIM_OCMODE_FORCED_INACTIVE;
    sConfigOC.Pulse = sh_ccr[0];
    sConfigOC.OCPolarity = TIM_OCPOLARITY_LOW; // Mantener tu polaridad
    HAL_TIM_OC_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_2);

    // ICG
    sConfigOC.OCMode = TIM_OCMODE_FORCED_INACTIVE;
    sConfigOC.Pulse = icg_ccr[0];
    sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
    HAL_TIM_OC_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_3);

    // 3. Generar un evento para que los cambios se apliquen inmediatamente al pin
    HAL_TIM_GenerateEvent(&htim2, TIM_EVENTSOURCE_UPDATE);


    // 4. Aplicar el TOGGLE
    // SH
    sConfigOC.OCMode = TIM_OCMODE_TOGGLE;
    sConfigOC.Pulse = sh_ccr[0];
    sConfigOC.OCPolarity = TIM_OCPOLARITY_LOW;
    HAL_TIM_OC_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_2);

    // ICG
    sConfigOC.OCMode = TIM_OCMODE_TOGGLE;
    sConfigOC.Pulse = icg_ccr[0];
    sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
    HAL_TIM_OC_ConfigChannel(&htim2, &sConfigOC, TIM_CHANNEL_3);

    // 5. Preparar DMA (pero no arrancar)
    __HAL_TIM_DISABLE_DMA(&htim2, TIM_DMA_UPDATE);
    __HAL_TIM_ENABLE_DMA(&htim2, TIM_DMA_CC2);
    __HAL_TIM_ENABLE_DMA(&htim2, TIM_DMA_CC3);
    __HAL_TIM_ENABLE_IT(&htim2, TIM_IT_CC3);
}

void calculate_times(uint32_t t_int_us){
    // 1. Conversión de microsegundos a Tics (Ciclos de fM)
    // fM = 2 MHz -> 1 us = 2 tics
    uint32_t t_int_tics = 0;

    if(t_int_us < 100)
        t_int_tics = 100 * 2;    // Mínimo de seguridad
    else
        t_int_tics = t_int_us * 2;

    // 2. Configuración de tiempos relativos al tiempo de integración
    TS3_tics = t_int_tics - 12;  // Ajuste fino según tu diagrama original
    TS4_tics = 2;                // Pulso SH breve
    TS5_tics = t_int_tics - 2;   // Complemento
    TS6_tics = TS5_tics - 3;     // Guard band final

    // 3. Definición de constantes para el readout
    uint32_t readout_time = 14800; // 7.4 ms expresados en ciclos de 500ns
    uint32_t TS1_base = 2;         // Valor fijo y estable para TS1

    // 4. Cálculo de 'n' (Número de pulsos de limpieza durante el readout)
    // Calculamos cuánto tiempo fijo ("overhead") gastamos por cada ciclo
    uint32_t overhead = TS0_tics + TS1_base + TS2_tics + TS3_tics + TS4_tics + TS6_tics;

    if (readout_time + t_int_tics > overhead) {
         // Fórmula para rellenar el tiempo muerto con pulsos extra
         n = (readout_time + t_int_tics - overhead - 1) / t_int_tics;
    } else {
         n = 0;
    }

    // --- SIN PADDING (Sincronización por Hardware) ---

    // Ya no calculamos restos ni módulos. El timer esclavo va clavado al maestro.
    TS1_tics = TS1_base;

    // Actualizamos la variable global para que el DMA sepa cuántos datos mandar
    real_SH_EDGES = 4 + 2 * n;
}


void build_SH_table(void)
{

	static uint32_t sh_dt[SH_EDGES_MAX];

	sh_dt[0] = TS0_tics;
	sh_dt[1] = TS1_tics;
	sh_dt[2] = TS2_tics + TS3_tics;

	for(int i = 0; i < n; i++){
		sh_dt[3 + 2 * i] = TS4_tics;
		sh_dt[3 + 2 * i + 1] = TS5_tics;
	}

	sh_dt[2 + 2 * n + 1] = TS4_tics;


	real_SH_EDGES = 4 + 2 * n;


    uint32_t t = START_OFFSET;

    for (uint32_t i = 0; i < real_SH_EDGES; i++) {
        t += sh_dt[i];
        sh_ccr[i] = t;
    }

}

void build_ICG_table(void)
{
	static uint32_t icg_dt[ICG_EDGES];
	icg_dt[0] = 0;
	icg_dt[1] = TS0_tics + TS1_tics + TS2_tics;

    uint32_t t = START_OFFSET;

    for (uint32_t i = 0; i < ICG_EDGES; i++) {
        t += icg_dt[i];
        icg_ccr[i] = t;
    }
}
