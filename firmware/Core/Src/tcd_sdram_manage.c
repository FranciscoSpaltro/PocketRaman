#include "tcd_sdram_manage.h"

volatile uint16_t * new_frame = (uint16_t *) SDRAM_BANK_ADDR;
volatile uint16_t * read_frame = (uint16_t *) SDRAM_BANK_ADDR;
volatile size_t read_frame_idx = 0;
volatile size_t free_frame_space = MAX_SDRAM_SPACE;
volatile size_t saved_frames = 0;
volatile size_t frames_to_send = 0;

void SDRAM_Initialization_Sequence(SDRAM_HandleTypeDef *hsdram)
{
    FMC_SDRAM_CommandTypeDef Command = {0};
    __IO uint32_t tmpmrd = 0;

    // Step 1: Clock enable command
    Command.CommandMode            = FMC_SDRAM_CMD_CLK_ENABLE;
    Command.CommandTarget          = FMC_SDRAM_CMD_TARGET_BANK1;
    Command.AutoRefreshNumber      = 1;
    Command.ModeRegisterDefinition = 0;
    HAL_SDRAM_SendCommand(hsdram, &Command, 0xFFFF);

    // Step 2: delay >= 100us (HAL_Delay(1) = 1ms, suficiente)
    HAL_Delay(1);

    // Step 3: Precharge all
    Command.CommandMode = FMC_SDRAM_CMD_PALL;
    Command.CommandTarget = FMC_SDRAM_CMD_TARGET_BANK1;
    Command.AutoRefreshNumber = 1;
    Command.ModeRegisterDefinition = 0;
    HAL_SDRAM_SendCommand(hsdram, &Command, 0xFFFF);

    // Step 4: Auto refresh
    Command.CommandMode = FMC_SDRAM_CMD_AUTOREFRESH_MODE;
    Command.CommandTarget = FMC_SDRAM_CMD_TARGET_BANK1;
    Command.AutoRefreshNumber = 8;
    Command.ModeRegisterDefinition = 0;
    HAL_SDRAM_SendCommand(hsdram, &Command, 0xFFFF);

    // Step 5: Load mode register
    tmpmrd = (uint32_t)SDRAM_MODEREG_BURST_LENGTH_1 |
                        SDRAM_MODEREG_BURST_TYPE_SEQUENTIAL |
                        SDRAM_MODEREG_CAS_LATENCY_3 |
                        SDRAM_MODEREG_OPERATING_MODE_STANDARD |
                        SDRAM_MODEREG_WRITEBURST_MODE_SINGLE;

    Command.CommandMode            = FMC_SDRAM_CMD_LOAD_MODE;
    Command.CommandTarget          = FMC_SDRAM_CMD_TARGET_BANK1;
    Command.AutoRefreshNumber      = 1;
    Command.ModeRegisterDefinition = tmpmrd;
    HAL_SDRAM_SendCommand(hsdram, &Command, 0xFFFF);

    // Step 6: Set refresh rate
    // OJO: este valor depende del clock real. Para arrancar, usá el del ejemplo ST.
    // (15.62us * Freq) - 20
    // En el ejemplo usan 1386.
    HAL_SDRAM_ProgramRefreshRate(hsdram, 1386);
}


void dcache_invalidate_range(const void *addr, size_t len)
{
    // DCache line = 32 bytes en Cortex-M7
    uintptr_t a = (uintptr_t)addr;
    uintptr_t a32 = a & ~((uintptr_t)31);              // baja a múltiplo de 32
    size_t len32 = (size_t)((a + len + 31) - a32) & ~(size_t)31; // sube a múltiplo de 32

    SCB_InvalidateDCache_by_Addr((uint32_t*)a32, (int32_t)len32);
}
