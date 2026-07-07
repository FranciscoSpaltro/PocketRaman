# PocketRaman
Low-cost portable Raman spectrometer prototype developed at SUPSI. Based on Raspberry Pi 4 and STM32F469I-DISCO, using a TCD1304 linear CCD with ADC and DMA-based acquisition. Includes custom 3D-printed mechanical parts to reuse optical mounting components and reduce cost.

## Status

This project implements a first working pipeline for CCD readout using:
- Timer-driven ADC sampling with DMA
- UART DMA streaming to host
- Python-based real-time visualization

Data acquisition and transmission are functional.
Frame synchronization relative to ICG/SH is currently under refinement,
which may cause horizontal drift in the displayed signal.
