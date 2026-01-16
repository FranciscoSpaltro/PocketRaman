import serial
import numpy as np
import matplotlib.pyplot as plt
import struct

# --- CONFIGURACIÓN ORIGINAL ---
PORT = "COM7"      
BAUD = 460800
CCD_PIXELS = 3694
OVERSAMPLING = 1   
contador = 0
N_FRAMES = 3 

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

# --- CONFIGURACIÓN GRÁFICA (3 PANELES) ---
plt.ion()
# width_ratios controla el ancho relativo: [1, 6, 1] significa que el del medio es 6 veces más ancho
fig, (ax_left, ax_main, ax_right) = plt.subplots(1, 3, figsize=(15, 6), gridspec_kw={'width_ratios': [1, 6, 1]})

# --- 1. IZQUIERDA: CALIBRACIÓN (0-31) ---
x_left = np.arange(0, 32)
zeros_left = np.zeros(len(x_left))
line_left, = ax_left.plot(x_left, zeros_left, 'b.-', markersize=3)

ax_left.set_ylim(0, 4200)
ax_left.set_title("Calibración (0-31)")
ax_left.set_ylabel("Amplitud (ADC)")
ax_left.grid(True)

# Líneas y Etiquetas (Estáticas)
ax_left.axvline(x=15, color='r', linestyle='--')
ax_left.axvline(x=28, color='r', linestyle='--')
ax_left.axvline(x=31, color='r', linestyle='--')

ax_left.text(7.5, 3800, "Dummy\n(0-15)", color='r', ha='center', fontsize=7, rotation=90)
ax_left.text(22, 3800, "Shielded\n(16-28)", color='r', ha='center', fontsize=7, rotation=90)
ax_left.text(30, 3500, "-", color='r', ha='center', fontsize=8)


# --- 2. CENTRO: EFECTIVOS (32-3679) ---
x_main = np.arange(32, 3680)
zeros_main = np.zeros(len(x_main))
line_main, = ax_main.plot(x_main, zeros_main, 'b')

ax_main.set_ylim(0, 4200)
ax_main.set_xlim(32, 3680)
ax_main.set_title("Señal Efectiva (32-3679)")
ax_main.set_xlabel("Número de Pixel")
ax_main.grid(True)


# --- 3. DERECHA: DUMMY FINAL (3680-Final) ---
x_right = np.arange(3680, CCD_PIXELS)
zeros_right = np.zeros(len(x_right))
line_right, = ax_right.plot(x_right, zeros_right, 'b.-', markersize=3)

ax_right.set_ylim(0, 4200)
ax_right.set_title("Fin")
ax_right.set_yticks([]) # Ocultamos eje Y para limpiar
ax_right.grid(True)

# Etiqueta
ax_right.text(3687, 3800, "Dummy\n(3680+)", color='r', ha='center', fontsize=7, rotation=90)


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
        sync_to_header(ser)
        
        contador += 1
        if contador < N_FRAMES:
            ser.read(PAYLOAD_BYTES)
            continue

        contador = 0
        
        # Leer datos
        raw_data = ser.read(PAYLOAD_BYTES)

        if len(raw_data) != PAYLOAD_BYTES:
            print("Frame incompleto")
            continue

        # Convertir a uint16
        full_data = np.frombuffer(raw_data, dtype=np.dtype('<u2'))

        # --- ACTUALIZAR LOS 3 GRÁFICOS ---
        
        # 1. Izquierda: Primeros 32
        line_left.set_ydata(full_data[:32])
        
        # 2. Centro: Del 32 al 3680
        line_main.set_ydata(full_data[32:3680])
        
        # 3. Derecha: Del 3680 al final
        line_right.set_ydata(full_data[3680:])
        
        fig.canvas.draw()
        fig.canvas.flush_events()

except KeyboardInterrupt:
    print("\nCerrando...")
    ser.close()
    plt.close()