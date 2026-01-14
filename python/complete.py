import serial
import numpy as np
import matplotlib.pyplot as plt
import struct

# --- CONFIGURACIÓN ---
PORT = "COM7"      
BAUD = 460800
CCD_PIXELS = 3694
OVERSAMPLING = 1   
PAYLOAD_BYTES = CCD_PIXELS * 2 
HEADER_BYTES = b'\x52\x46\x4E\x41\xFF\xFF\xFF\xFF'

try:
    ser = serial.Serial(PORT, BAUD, timeout=2)
    ser.flushInput()
except Exception as e:
    print(f"Error abriendo puerto: {e}")
    exit()

# --- CONFIGURACIÓN GRÁFICA (3 PLOTS) ---
plt.ion()
# width_ratios=[1, 6, 1] hace que el centro sea 6 veces más ancho que los lados
fig, (ax_left, ax_main, ax_right) = plt.subplots(1, 3, figsize=(14, 6), gridspec_kw={'width_ratios': [1, 6, 1]})

# --- 1. GRÁFICO IZQUIERDO (0-31) ---
# Contiene Dummy (0-15), Shielded (16-28) y Buffer (29-31)
x_left = np.arange(0, 32)
line_left, = ax_left.plot(x_left, np.zeros(len(x_left)), 'b.-', markersize=3)
ax_left.set_ylim(0, 4500)
ax_left.set_title("Inicio (0-31)")

# Etiquetas Estáticas (Fuera del loop para no trabar el gráfico)
ax_left.axvline(x=15.5, color='r', linestyle='--')
ax_left.axvline(x=28.5, color='r', linestyle='--')
ax_left.axvline(x=31.5, color='k', linewidth=2) # Separador final
ax_left.text(7, 4200, "Dummy", color='r', ha='center', fontsize=7)
ax_left.text(22, 4200, "Shield", color='r', ha='center', fontsize=7)


# --- 2. GRÁFICO CENTRAL (32-3679) ---
# Pixeles efectivos
x_main = np.arange(32, 3680)
line_main, = ax_main.plot(x_main, np.zeros(len(x_main)), 'b')
ax_main.set_ylim(0, 4500)
ax_main.set_xlim(32, 3680)
ax_main.set_title("Pixeles Efectivos")
ax_main.set_xlabel("Número de Pixel")
ax_main.grid(True)
ax_main.text(1850, 4300, "Zona Efectiva", color='blue', ha='center', fontsize=10)


# --- 3. GRÁFICO DERECHO (3680-Final) ---
# Dummy finales
x_right = np.arange(3680, CCD_PIXELS)
line_right, = ax_right.plot(x_right, np.zeros(len(x_right)), 'b.-', markersize=3)
ax_right.set_ylim(0, 4500)
ax_right.set_title("Fin")
ax_right.text(3687, 4200, "Dummy", color='r', ha='center', fontsize=7)

plt.tight_layout()

# --- FUNCIONES ---
def sync_to_header(serial_port):
    buffer = b''
    while True:
        new_byte = serial_port.read(1)
        if not new_byte: continue
        buffer += new_byte
        if len(buffer) > len(HEADER_BYTES):
            buffer = buffer[-len(HEADER_BYTES):]
        if buffer == HEADER_BYTES:
            return

# --- BUCLE PRINCIPAL ---
contador = 0
N_FRAMES = 3 

try:
    print(f"Esperando datos ({PAYLOAD_BYTES} bytes por frame)...")
    
    while True:
        sync_to_header(ser)
        
        contador += 1
        if contador < N_FRAMES:
            ser.read(PAYLOAD_BYTES)
            continue
        contador = 0
        
        raw_data = ser.read(PAYLOAD_BYTES)
        if len(raw_data) != PAYLOAD_BYTES:
            print("Frame incompleto")
            continue

        full_data = np.frombuffer(raw_data, dtype=np.dtype('<u2'))

        # Actualizamos los 3 gráficos por separado
        # Slice [0:32]
        line_left.set_ydata(full_data[:32])
        
        # Slice [32:3680]
        line_main.set_ydata(full_data[32:3680])
        
        # Slice [3680:Final]
        line_right.set_ydata(full_data[3680:])
        
        fig.canvas.draw()
        fig.canvas.flush_events()

except KeyboardInterrupt:
    print("\nCerrando...")
    ser.close()
    plt.close()