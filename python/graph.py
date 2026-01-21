import serial
import numpy as np
import matplotlib.pyplot as plt
import struct

nombre_archivo_export = "error.txt"
PORT = "COM7"      
#BAUD = 460800
BAUD = 115200
CCD_PIXELS = 3694
N_FRAMES = 4       

PAYLOAD_BYTES = CCD_PIXELS * 2 

HEADER_BYTES = 0x7346
END_BUFFER = 0x7347 

try:
    ser = serial.Serial(PORT, BAUD, timeout=2)
    ser.flushInput()
except Exception as e:
    print(f"Error abriendo puerto: {e}")
    exit()

plt.ion()
fig, ax = plt.subplots(1, 1, figsize=(10, 6))
zeros = np.zeros(CCD_PIXELS)
line, = ax.plot(zeros, color='blue')
ax.set_ylim(0, 4200)
ax.set_ylabel("Amplitud (ADC)")
ax.set_xlabel("Número de Pixel")
ax.set_title(f"Señal CCD en Tiempo Real ({CCD_PIXELS} pixeles)")
ax.grid(True)
plt.tight_layout()

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
        # 6. Graficar
        line.set_ydata(raw_data)
        fig.canvas.draw()
        fig.canvas.flush_events()

except KeyboardInterrupt:
    print("\nCerrando...")
    ser.close()
    plt.close()