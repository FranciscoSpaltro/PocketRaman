import serial
import numpy as np
import matplotlib.pyplot as plt
import struct

PORT = "COM7"      
BAUD = 460800
CCD_PIXELS = 3694
OVERSAMPLING = 1    # 1 muestra por pixel
contador = 0
N_FRAMES = 4       # 4

# Total de datos que llegan
TOTAL_POINTS = CCD_PIXELS * OVERSAMPLING 
PAYLOAD_BYTES = TOTAL_POINTS * 2 

# Header
HEADER_BYTES_1 = b'\x73'    # Cambiar despues para que sea todo unico
HEADER_BYTES_2 = b'\x46'

try:
    ser = serial.Serial(PORT, BAUD, timeout=2)
    ser.flushInput()
except Exception as e:
    print(f"Error abriendo puerto: {e}")
    exit()

plt.ion()

fig, ax = plt.subplots(1, 1, figsize=(10, 6))

zeros = np.zeros(TOTAL_POINTS)
line, = ax.plot(zeros, color='blue')

ax.set_ylim(0, 4200)
ax.set_ylabel("Amplitud (ADC)")
ax.set_xlabel("Número de Pixel")
ax.set_title(f"Señal CCD en Tiempo Real ({CCD_PIXELS} pixeles)")
ax.grid(True)

plt.tight_layout()

def sync_to_header(serial_port):
    """ Busca la secuencia exacta del header """
    while True:
        byte = ser.read(1)
        if byte:
            #print(byte.hex())
            if byte == b'\x46':
                next_byte = ser.read(1)
                if next_byte == b'\x73':
                    break

try:
    print(f"Esperando datos ({PAYLOAD_BYTES} bytes por frame)...")
    
    while True:
        sync_to_header(ser)
        
        #contador += 1
        #if contador < N_FRAMES:
            # Ignorar los primeros N_FRAMES frames para estabilizar
        #    ser.read(PAYLOAD_BYTES)
        #    continue

        contador = 0
        # 2. Leer el bloque de datos exacto
        raw_data = ser.read(PAYLOAD_BYTES)
        if len(raw_data) != PAYLOAD_BYTES:
            print("Frame incompleto1")
            continue
        aux = ser.read(2)

        end_buffer = ser.read(1)
        if end_buffer:
            #print(byte.hex())
            if end_buffer != b'\x47':
                print(end_buffer.hex())
                print("Frame incompleto2")
                continue
            else:
                end_buffer = ser.read(1)
                if end_buffer != b'\x73':
                    print("Frame incompleto3")
                    continue

        # 3. Convertir a uint16
        # Como OVERSAMPLING = 1, full_data ya es EL array de pixeles final
        full_data = np.frombuffer(raw_data, dtype=np.dtype('<u2'))

        line.set_ydata(full_data)
        
        fig.canvas.draw()
        fig.canvas.flush_events()

except KeyboardInterrupt:
    print("\nCerrando...")
    ser.close()
    plt.close()