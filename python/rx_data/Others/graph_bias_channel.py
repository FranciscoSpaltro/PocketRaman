import serial
import numpy as np
import matplotlib.pyplot as plt
import struct

nombre_archivo_export = "error.txt"
PORT = "COM7"      
BAUD = 460800
#BAUD = 115200
CCD_PIXELS = 3694
N_FRAMES = 1   
PAYLOAD_BYTES = CCD_PIXELS * 2 
DARK_VALUE = 3000

max_anterior = 0
max_actual = 0

HEADER_BYTES = 0x7346
END_BUFFER = 0x7347 

CONTADOR = 0

try:
    ser = serial.Serial(PORT, BAUD, timeout=2)
    ser.flushInput()
except Exception as e:
    print(f"Error abriendo puerto: {e}")
    exit()

plt.ion()
fig, ax = plt.subplots(1, 1, figsize=(10, 6))
zeros = np.zeros(CCD_PIXELS)
#line, = ax.plot(zeros, '.', color='blue', markersize=2)
line, = ax.plot(zeros, color='blue', markersize=2)
ax.set_ylim(0, 4200)
#ax.set_xlim(1000, 1010)
#ax.set_ylim(750, 3000)
#ax.set_ylim(-100, 100)
ax.set_ylabel("Amplitud (ADC)")
ax.set_xlabel("Número de Pixel")
ax.set_title(f"Señal CCD en Tiempo Real ({CCD_PIXELS} pixeles)")
ax.grid(True)
plt.tight_layout()

threshold = 50
filtering = True
    
def sync_to_header(serial_port):
    window = bytearray()
    while True:
        b = serial_port.read(1)
        if not b:
            continue
        window += b
        if len(window) > 2:
            window = window[-2:]
        if window == struct.pack('<H', HEADER_BYTES):  # 46 73
            return bytes(window)

try:
    print(f"Esperando datos ({PAYLOAD_BYTES} bytes por frame)...")
    
    while True:
        # 1. Sincronizar (consume los 2 bytes del header)
        array = sync_to_header(ser)
        array += ser.read(2 + PAYLOAD_BYTES + 2 + 2)
        if( len(array) != 2 + 2 + PAYLOAD_BYTES + 2 + 2):
            print("Frame incompleto (total)")
            continue

        array = np.frombuffer(array, dtype=np.dtype('<u2'))
        cmd = array[1]
        raw_data = array[2: 2 + CCD_PIXELS]
        end_buffer = array[-1]
        
        if end_buffer != END_BUFFER:
            print(f"Error de Footer: {end_buffer}")
            continue

        
        # Hago XOR de todos los datos y verifico que de 0
        xor_sum = 0x0000
        for val in array:
            xor_sum ^= val

        if xor_sum != 0x0000:
            print(f"Error de Checksum: {xor_sum:04x}")
            #exporto el array
            #with open(nombre_archivo_export, "w") as f:
            #    for val in array:
            #        f.write(f"{val:04x} ")
            #break
            
            continue
        
        
        pares   = raw_data[0::2]  # Indices 0, 2, 4...
        impares = raw_data[1::2]  # Indices 1, 3, 5...

        bias_par   = np.median(pares[0:9])
        bias_impar = np.median(impares[0:9])

        offset_par   = DARK_VALUE - bias_par
        offset_impar = DARK_VALUE - bias_impar

        # 4. Corregimos por separado
        pares_corr   = pares + offset_par
        impares_corr = impares + offset_impar

        # 5. Reconstruimos el array final intercalando
        corrected_data = np.empty_like(raw_data)
        corrected_data[0::2] = pares_corr
        corrected_data[1::2] = impares_corr

        # 6. Recorte de seguridad
        corrected_data = np.clip(corrected_data, 0, 4095)

        # 6. Graficar
        if CONTADOR == N_FRAMES - 1:
            line.set_ydata(corrected_data)
            fig.canvas.draw()
            fig.canvas.flush_events()
            print("Frame recibido correctamente.")
            CONTADOR = 0
        else:
            CONTADOR += 1
      

except KeyboardInterrupt:
    print("\nCerrando...")
    ser.close()
    plt.close()