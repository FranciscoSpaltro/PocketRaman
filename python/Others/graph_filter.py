import serial
import numpy as np
import matplotlib.pyplot as plt
import struct

# --- CONFIGURACIÓN ---
PORT = "COM7"       
BAUD = 460800
CCD_PIXELS = 3694
OVERSAMPLING = 1   
TOTAL_POINTS = CCD_PIXELS * OVERSAMPLING 
PAYLOAD_BYTES = TOTAL_POINTS * 2 
HEADER_BYTES = b'\x52\x46\x4E\x41\xFF\xFF\xFF\xFF'

# --- CONFIGURACIÓN DEL FILTRO ---
ENABLE_FILTER = True       # <--- Booleano para activar el filtrado
DIFF_THRESHOLD = 500       # <--- Sensibilidad: Si el promedio varía más de 500 ADU, es un error.
ALPHA = 0.1                # <--- Inercia: 0.1 significa que la referencia cambia lento (promedio de últimos ~10 frames)

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
ax.set_title(f"Señal CCD ({'Filtrado ACTIVO' if ENABLE_FILTER else 'SIN Filtrar'})")
ax.grid(True)
plt.tight_layout()

# Variable para guardar la "forma de onda esperada"
reference_frame = None 

def sync_to_header(serial_port):
    buffer = b''
    while True:
        new_byte = serial_port.read(1)
        if not new_byte: continue
        buffer += new_byte
        if len(buffer) > len(HEADER_BYTES):
            buffer = buffer[-len(HEADER_BYTES):]
        if buffer == HEADER_BYTES: return

try:
    print("Iniciando captura...")
    while True:
        sync_to_header(ser)
        raw_data = ser.read(PAYLOAD_BYTES)

        if len(raw_data) != PAYLOAD_BYTES:
            continue

        # Convertir datos nuevos
        current_frame = np.frombuffer(raw_data, dtype=np.dtype('<u2'))

        # --- LÓGICA DE FILTRADO ---
        if ENABLE_FILTER:
            # 1. Si es el primer frame, lo aceptamos como referencia inicial
            if reference_frame is None:
                reference_frame = current_frame.astype(float)
                pass # Pasa directo a graficar
            
            else:
                # 2. Calcular la diferencia promedio absoluta (MAE) entre lo que llegó y lo esperado
                # Esto nos dice "en promedio, cuántos puntos de ADC varió cada pixel"
                diff = np.mean(np.abs(current_frame - reference_frame))
                
                # 3. Comparar con el umbral
                if diff > DIFF_THRESHOLD:
                    print(f"⚠️ Frame descartado! Diferencia absurda: {diff:.1f}")
                    continue # <--- SALTA al siguiente ciclo del while, NO GRAFICA
                
                # 4. Si el frame es bueno, actualizamos la referencia suavemente (Exponential Moving Average)
                # Esto hace que la referencia sea un promedio de los últimos ~10 frames
                reference_frame = (reference_frame * (1 - ALPHA)) + (current_frame * ALPHA)
        
        # --- GRAFICAR ---
        line.set_ydata(current_frame)
        fig.canvas.draw()
        fig.canvas.flush_events()

except KeyboardInterrupt:
    print("\nCerrando...")
    ser.close()
    plt.close()