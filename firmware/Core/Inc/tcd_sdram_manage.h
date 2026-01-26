/**
 * CONFIGURACIÓN DE LA SDRAM
 * 		- BANK1 / SDCKE0 (reloj) + SDNE0 (chip enable)
 * 		- 32-bit data width (bus de datos de 32 lineas)
 * 		- 4 internal banks (bancos internos de la SDRAM, cada banco puede tener una fila abierta mientras otros se usan)
 * 		- Fila: 12  bits (4096 filas por banco; la SDRAM divide la dirección en [bank][row][colum]
 * 		- Data: 32 bits (cada acceso mueve 32 bits == 4 bytes)
 * 		- Byte enable: 32-bit byte enable (habilita las líneas DQM - Data Mask, que permite escribir 1 o 2 bytes dentro de una palabra de 32 bits)
 */


#ifndef TCD_SDRAM_MANAGE_H
#define TCD_SDRAM_MANAGEH

#define SDRAM_BANK_ADDR                 ((uint32_t)0xC0000000)					// FMC mapea la SDRAM en el espacio de memoria del Cortex-M, a partir de 0xC0000000 hasta 0xC0000000 + 16 MB es vista como RAM comun

#define SDRAM_MEMORY_WIDTH               FMC_SDRAM_MEM_BUS_WIDTH_32				// Describe cómo está cableado el chip (32 bits)

#define SDCLOCK_PERIOD                   FMC_SDRAM_CLOCK_PERIOD_2				// FMC genera el clock de SDRAM como clock base/2 (otro es /3). Cuanto más rápido, más estrés y CAS mayor


#define SDRAM_TIMEOUT     ((uint32_t)0xFFFF)

// Abrir una fila en SDRAM es caro en tiempo pero leer muchas columnas seguidas de esa fila es barato. El burst length describe cuántas palabras seguidas entrega la SDRAM automáticamente
#define SDRAM_MODEREG_BURST_LENGTH_1             ((uint16_t)0x0000)				// Cuantas palabras seguidas entrega por acceso [para accesos aleatorios, 1 es simple. Para streaming, >1 mejora el rendimiento] [REVISAR]
//#define SDRAM_MODEREG_BURST_LENGTH_2             ((uint16_t)0x0001)
//#define SDRAM_MODEREG_BURST_LENGTH_4             ((uint16_t)0x0002)
//#define SDRAM_MODEREG_BURST_LENGTH_8             ((uint16_t)0x0004)
#define SDRAM_MODEREG_BURST_TYPE_SEQUENTIAL      ((uint16_t)0x0000)				// La dirección durante un burst se incrementa en modo secuencial (intervaled es con un patrón especial)
//#define SDRAM_MODEREG_BURST_TYPE_INTERLEAVED     ((uint16_t)0x0008)
//#define SDRAM_MODEREG_CAS_LATENCY_2              ((uint16_t)0x0020)
#define SDRAM_MODEREG_CAS_LATENCY_3              ((uint16_t)0x0030)				// Cuántos ciclos tarda el dato en aparecer
#define SDRAM_MODEREG_OPERATING_MODE_STANDARD    ((uint16_t)0x0000)				// trabajar como SDRAM estandar, nada especial
//#define SDRAM_MODEREG_WRITEBURST_MODE_PROGRAMMED ((uint16_t)0x0000)			// Los writes respetan el Burst Length programado
#define SDRAM_MODEREG_WRITEBURST_MODE_SINGLE     ((uint16_t)0x0200)				// Aunque el burst length sea 4 u 8, los WRITE se hacen de a una palabra



#include "main.h"
#include "cachel1_armv7.h"														// Para SCB_InvalidateDCache_by_Addr()
#include "tcd_variables.h"

void SDRAM_Initialization_Sequence(SDRAM_HandleTypeDef *hsdram);
void dcache_invalidate_range(const void *addr, size_t len);

#endif
