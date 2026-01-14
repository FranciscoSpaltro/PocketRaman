import serial
import numpy as np
import matplotlib.pyplot as plt
import struct

# --- CONFIGURACIÓN ---
PORT = "COM7"       # Ajustá tu puerto
BAUD = 460800
CCD_PIXELS = 3694
OVERSAMPLING = 1    # CAMBIO: Ahora es 1 muestra por pixel (Timer chaining)

# Total de datos que llegan
TOTAL_POINTS = CCD_PIXELS * OVERSAMPLING 
PAYLOAD_BYTES = TOTAL_POINTS * 2 

# Header (Little Endian)
HEADER_BYTES = b'\x52\x46\x4E\x41\xFF\xFF\xFF\xFF'

try:
    ser = serial.Serial(PORT, BAUD, timeout=2)
    ser.flushInput()
except Exception as e:
    print(f"Error abriendo puerto: {e}")
    exit()

plt.ion()

# --- CAMBIO: Un solo gráfico ---
fig, ax = plt.subplots(1, 1, figsize=(10, 6))

# Inicializamos la línea
zeros = np.zeros(TOTAL_POINTS)
line, = ax.plot(zeros, color='blue')

# Configuración del eje
ax.set_ylim(0, 4200) # Ajusta según tu ADC (0 a 4095)
ax.set_ylabel("Amplitud (ADC)")
ax.set_xlabel("Número de Pixel")
ax.set_title(f"Señal CCD en Tiempo Real ({CCD_PIXELS} pixeles)")
ax.grid(True)

plt.tight_layout()

def sync_to_header(serial_port):
    """ Busca la secuencia exacta del header """
    buffer = b''
    while True:
        new_byte = serial_port.read(1)
        if not new_byte:
            continue
        
        buffer += new_byte
        if len(buffer) > len(HEADER_BYTES):
            buffer = buffer[-len(HEADER_BYTES):]
            
        if buffer == HEADER_BYTES:
            return

# --- BUCLE PRINCIPAL ---
try:
    print(f"Esperando datos ({PAYLOAD_BYTES} bytes por frame)...")
    
    while True:
        # 1. Sincronizar con el encabezado
        sync_to_header(ser)
        
        # 2. Leer el bloque de datos exacto
        raw_data = ser.read(PAYLOAD_BYTES)

        if len(raw_data) != PAYLOAD_BYTES:
            print("Frame incompleto")
            continue

        # 3. Convertir a uint16
        # Como OVERSAMPLING = 1, full_data ya es tu array de pixeles final
        full_data = np.frombuffer(raw_data, dtype=np.dtype('<u2'))

        # 4. Actualizar gráfico
        line.set_ydata(full_data)
        
        # Refrescar ventana
        fig.canvas.draw()
        fig.canvas.flush_events()

except KeyboardInterrupt:
    print("\nCerrando...")
    ser.close()
    plt.close()