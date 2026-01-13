import serial
import numpy as np
import matplotlib.pyplot as plt
import struct

# --- CONFIGURACIÓN ---
PORT = "COM7"       # Ajustá tu puerto
BAUD = 460800
CCD_PIXELS = 3694
OVERSAMPLING = 4    # 4 muestras por cada pixel físico

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

# Creamos 4 gráficos apilados verticalmente
# sharex=True hace que si haces zoom en uno, se haga zoom en todos (ideal para comparar)
fig, (ax0, ax1, ax2, ax3) = plt.subplots(4, 1, figsize=(10, 10), sharex=True)

# Inicializamos las 4 líneas
# Cada una tendrá CCD_PIXELS de largo (3694 puntos)
zeros = np.zeros(CCD_PIXELS)
line0, = ax0.plot(zeros, color='blue')
line1, = ax1.plot(zeros, color='orange')
line2, = ax2.plot(zeros, color='green')
line3, = ax3.plot(zeros, color='red')

# Configuramos ejes
for ax, i in zip([ax0, ax1, ax2, ax3], range(4)):
    ax.set_ylim(0, 4200)
    ax.set_ylabel(f"Muestra {i}")
    ax.grid(True)

ax0.set_title(f"Desglose de las 4 muestras por Pixel (Total: {CCD_PIXELS} pixeles)")
ax3.set_xlabel("Número de Pixel")

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
    print("Esperando sincronización...")
    while True:
        # 1. Sincronizar
        sync_to_header(ser)
        
        # 2. Leer todo el bloque de 14776 muestras
        raw_data = ser.read(PAYLOAD_BYTES)

        if len(raw_data) != PAYLOAD_BYTES:
            print("Frame incompleto")
            continue

        # 3. Convertir a uint16
        # array completo: [M0, M1, M2, M3, M0, M1, M2, M3...]
        full_data = np.frombuffer(raw_data, dtype=np.dtype('<u2'))

        # 4. DESENTRELAZADO (La magia de Numpy)
        # Slicing: array[inicio : final : paso]
        
        sample_0 = full_data[0::4] # Empieza en 0, salta de a 4: [0, 4, 8...]
        sample_1 = full_data[1::4] # Empieza en 1, salta de a 4: [1, 5, 9...]
        sample_2 = full_data[2::4] # Empieza en 2, salta de a 4: [2, 6, 10...]
        sample_3 = full_data[3::4] # Empieza en 3, salta de a 4: [3, 7, 11...]

        # 5. Actualizar los 4 gráficos
        line0.set_ydata(sample_0)
        line1.set_ydata(sample_1)
        line2.set_ydata(sample_2)
        line3.set_ydata(sample_3)
        
        fig.canvas.draw()
        fig.canvas.flush_events()

except KeyboardInterrupt:
    print("\nCerrando...")
    ser.close()
    plt.close()