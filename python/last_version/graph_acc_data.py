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
SEND_ACC_DATA = 0xF006
PAYLOAD = 0xFFFFFFFF
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
#line, = ax.plot(zeros, ',', color='blue', markersize=2)
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
i = 0
bias = True
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
    # Envio el comando
    paquete_sin_cs = struct.pack('<HHI', 
                                         HEADER_BYTES, 
                                         SEND_ACC_DATA,
                                         PAYLOAD)
    
    # Calcular Checksum
    def calcular_checksum(data_bytes):
        """ Interpreta los bytes como array de uint16 y hace XOR """
        if len(data_bytes) % 2 != 0: return 0
        
        # Desempaquetamos en palabras de 16 bits
        num_words = len(data_bytes) // 2
        words = struct.unpack(f'<{num_words}H', data_bytes)
        
        cs = 0x0000
        for w in words:
            cs ^= w
        return cs
    
    cs = calcular_checksum(paquete_sin_cs)
    # Agregar Checksum al final
    paquete_final = paquete_sin_cs + struct.pack('<H', cs)
    print(f"Paquete: {paquete_final.hex().upper()}")
    ser.write(paquete_final)
    
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

        if bias:
            dummy_pixels = raw_data[0:16]
            filtro = np.abs(dummy_pixels - np.median(dummy_pixels)) <= threshold
            dummy_pixels_clean = dummy_pixels[filtro]

            if len(dummy_pixels_clean) == 0:
                dummy_pixels_clean = dummy_pixels

            if filtering:
                current_bias_level = np.median(dummy_pixels_clean)
            else:
                current_bias_level = np.mean(dummy_pixels)
            correction_offset = DARK_VALUE - current_bias_level
            corrected_data = raw_data + correction_offset
            corrected_data = np.clip(corrected_data, 0, 4095)

            # 6. Graficar
            if CONTADOR == N_FRAMES - 1:
                line.set_ydata(corrected_data)
                fig.canvas.draw()
                fig.canvas.flush_events()
                print(f"Frame {i} recibido correctamente.")
                CONTADOR = 0
            else:
                CONTADOR += 1
        else:
            # 6. Graficar
            if CONTADOR == N_FRAMES - 1:
                line.set_ydata(raw_data)
                fig.canvas.draw()
                fig.canvas.flush_events()
                print(f"Frame {i} recibido correctamente.")
                CONTADOR = 0
            else:
                CONTADOR += 1
      
        i += 1

except KeyboardInterrupt:
    print("\nCerrando...")
    ser.close()
    plt.close()