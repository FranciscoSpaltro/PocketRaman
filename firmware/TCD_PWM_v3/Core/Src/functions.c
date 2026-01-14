#include "functions.h"

const int initial_n = 6;

volatile int state = 0;
volatile int n = initial_n;
volatile int real_SH_EDGES = 0;

volatile uint8_t sistema_listo_para_capturar = 1;
volatile uint8_t icg_is_high = 0;

const uint32_t TS0_tics = 50;
uint32_t TS1_tics = 122;
const uint32_t TS2_tics = 500;
uint32_t TS3_tics = 0;	// valores por default para 1 ms
uint32_t TS4_tics = 0;
uint32_t TS5_tics = 0;
uint32_t TS6_tics = 0;

uint32_t sh_ccr[SH_EDGES_MAX];
uint32_t icg_ccr[ICG_EDGES];

uint16_t adc_buffer[HEADER_SIZE + CCD_PIXELS];


const uint16_t SYNC_WORD_1 = 0x4652;
const uint16_t SYNC_WORD_2 = 0x414E;
const uint16_t SYNC_WORD_3 = 0xFFFF;
const uint16_t SYNC_WORD_4 = 0xFFFF;

extern TIM_HandleTypeDef htim2;
extern TIM_HandleTypeDef htim3;
extern ADC_HandleTypeDef hadc1;
extern UART_HandleTypeDef huart6;

const uint8_t HANDSHAKE_REQ[] = {0x46, 0x52, 0x41, 0x4E};

uint32_t wait_new_int_time_uart(void) {
    uint8_t rx_buffer[6]; // 2 bytes Header + 4 bytes uint32_t
    uint32_t t_int_recibido = 0;

    // Parpadeo rápido para indicar "Esperando PC..."
    while (1) {
        // 1. Enviar solicitud: "Estoy listo, dame el tiempo"
        HAL_UART_Transmit(&huart6, (uint8_t*)HANDSHAKE_REQ, 2, 100);

        // 2. Esperar respuesta durante 500ms
        if (HAL_UART_Receive(&huart6, rx_buffer, 6, 500) == HAL_OK) {

            // 3. Verificar Header (CC DD)
            if (rx_buffer[0] == HANDSHAKE_REQ[2] && rx_buffer[1] == HANDSHAKE_REQ[3]) {
                // 4. Decodificar uint32_t (Little Endian)
                // Byte 2 es el menos significativo
                t_int_recibido = (rx_buffer[5] << 24) |
                                 (rx_buffer[4] << 16) |
                                 (rx_buffer[3] << 8)  |
                                 rx_buffer[2];

                // Protección: Evitar tiempos absurdos (ej. 0)
                if (t_int_recibido < 10) t_int_recibido = 10;
                if (t_int_recibido > 7000) t_int_recibido = 7000;

                return t_int_recibido;
            }
        }

        // Si falló o hubo timeout, parpadeamos LED y reintentamos
        HAL_GPIO_TogglePin(LED2_GPIO_Port, LED2_Pin);
    }
}


void setup_timer_icg_sh(void){
	__HAL_TIM_SET_AUTORELOAD(&htim2, sh_ccr[real_SH_EDGES-1] + TS6_tics);

	  __HAL_TIM_SET_COUNTER(&htim2, 0);

	    // El primer flanco de ICG ocurrirá en START_OFFSET
	    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_3, icg_ccr[0]);

	    // El primer flanco de SH ocurrirá en START_OFFSET + TS0
	    __HAL_TIM_SET_COMPARE(&htim2, TIM_CHANNEL_2, sh_ccr[0]);

	  __HAL_TIM_DISABLE_DMA(&htim2, TIM_DMA_UPDATE);
	  __HAL_TIM_ENABLE_DMA(&htim2, TIM_DMA_CC2);
	  __HAL_TIM_ENABLE_DMA(&htim2, TIM_DMA_CC3);

	  // 4) Arrancar DMA apuntando a CCR2
	  HAL_TIM_OC_Start_DMA(&htim2, TIM_CHANNEL_2, (uint32_t*)sh_ccr, real_SH_EDGES);
	  HAL_TIM_OC_Start_DMA(&htim2, TIM_CHANNEL_3, (uint32_t*)icg_ccr, ICG_EDGES);

	  __HAL_TIM_ENABLE_IT(&htim2, TIM_IT_CC3);
}
void calculate_times(uint32_t t_int_us){
	uint32_t fM_period = 44 + 1; // 45 ticks

	uint32_t t_int_tics = 0;

	if(t_int_us < 100)
		t_int_tics = 100 * 90;
	else
		t_int_tics = t_int_us * 90;					// REFACTOR: quitar dependencia clock

	TS3_tics = t_int_tics - 600;
	TS4_tics = 100;
	TS5_tics = t_int_tics - 100;
	TS6_tics = TS5_tics - 50;

	// reemplazo los 7.4 ms * 90 MHz por 74 * 9000 para no usar librerias de punto flotante
	n = (74 * 9000 - TS0_tics - TS1_tics - TS2_tics - TS3_tics - TS4_tics - TS6_tics + t_int_tics - 1) / t_int_tics;

	// Reset de TS1 a un valor base seguro
	uint32_t TS1_base = 100;

	// Cálculo de 'n' (Pulsos de limpieza)
	uint32_t overhead = TS0_tics + TS1_base + TS2_tics + TS3_tics + TS4_tics + TS6_tics;
	uint32_t readout_time = 74 * 9000;

	if (readout_time + t_int_tics > overhead) {
		 n = (readout_time + t_int_tics - overhead - 1) / t_int_tics;
	} else {
		 n = 0;
	}

	// --- PADDING AUTOMÁTICO (Phase Lock) ---
	// 1. Duracion del frame completo con el TS1 base
	real_SH_EDGES = 4 + 2 * n; // Necesitamos saber cuántos pulsos hay realmente

	// Duración total sumando las partes fijas y las variables
	uint32_t total_duration_tics = TS0_tics + TS1_base + (TS2_tics + TS3_tics)
							  + n * (TS4_tics + TS5_tics) // Parte variable
							  + TS4_tics + TS6_tics;      // Parte final

	uint32_t total_physical_tics = START_OFFSET + total_duration_tics + 1;

	// 2. Cuánto sobra respecto al ciclo de fM
	uint32_t remainder = total_physical_tics % fM_period;

	// 3. Ajuste de TS1 para absorber la diferencia
	if (remainder != 0) {
		uint32_t padding = fM_period - remainder;
		TS1_tics = TS1_base + padding;
	} else {
		TS1_tics = TS1_base;
	}
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

void build_header(void){
	adc_buffer[0] = SYNC_WORD_1;
  adc_buffer[1] = SYNC_WORD_2;
  adc_buffer[2] = SYNC_WORD_3;
  adc_buffer[3] = SYNC_WORD_4;
}
