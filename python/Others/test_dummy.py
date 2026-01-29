import serial
import numpy as np
import struct
import time

# --- CONFIGURACIÓN ---
PORT = "COM7"       # Ajusta tu puerto
BAUD = 460800       # Prueba bajar a 115200 si falla mucho
CCD_PIXELS = 3694

# Constantes del protocolo (Deben coincidir con tu C)
HEADER_VAL = 0x7346
CMD_VAL    = 0xF003 # DATA_SENDING
END_VAL    = 0x7347

# Estructura esperada después del Header:
# [CMD (1)] + [DATOS (3694)] + [CS (1)] + [END (1)] = 3697 palabras de 16-bit
WORDS_TO_READ = 1 + CCD_PIXELS + 1 + 1 
BYTES_TO_READ = WORDS_TO_READ * 2

try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    ser.reset_input_buffer()
    print(f"Abierto {PORT} a {BAUD}. Esperando rampa...")
except Exception as e:
    print(f"Error puerto: {e}")
    exit()

def sync_to_header(serial_port):
    """ Busca 0x7346 (Little Endian: 46 73) en el flujo """
    window = bytearray()
    target = struct.pack('<H', HEADER_VAL) # b'\x46\x73'
    
    while True:
        b = serial_port.read(1)
        if not b: return False # Timeout
        
        window += b
        if len(window) > 2:
            window.pop(0)
            
        if window == target:
            return True

# --- BUCLE PRINCIPAL ---
frames_ok = 0
frames_bad = 0

try:
    while True:
        # 1. Sincronizar (Consume los 2 bytes del Header)
        if sync_to_header(ser):
            
            # 2. Leer el resto del paquete de golpe
            raw_bytes = ser.read(BYTES_TO_READ)
            
            if len(raw_bytes) != BYTES_TO_READ:
                print("Frame incompleto (Timeout)")
                continue

            # 3. Convertir a array de 16-bit (Little Endian)
            # Estructura del array: [CMD, D0, D1... Dn, CS, END]
            frame = np.frombuffer(raw_bytes, dtype=np.dtype('<u2'))

            # --- VERIFICACIÓN 1: Footer ---
            if frame[-1] != END_VAL:
                print(f"[ERROR] Footer inválido. Recibido: {hex(frame[-1])}")
                frames_bad += 1
                ser.reset_input_buffer()
                continue

            # --- VERIFICACIÓN 2: Checksum ---
            # XOR inicial con el Header (que ya leímos antes)
            xor_calc = HEADER_VAL
            for val in frame:
                xor_calc ^= val
            
            # Nota: Si el STM32 envía el CS calculado, al hacer XOR de todo (incluido el CS recibido) debe dar 0
            if xor_calc != 0:
                print(f"[ERROR] Checksum falló. Residuo: {hex(xor_calc)}")
                # No hacemos continue, queremos ver si la rampa llegó bien aunque el CS falle
                frames_bad += 1
            
            # --- VERIFICACIÓN 3: LA RAMPA (Integridad de datos) ---
            # Extraemos solo la parte de datos (desde índice 1 hasta 1+3694)
            data_recibida = frame[1 : 1 + CCD_PIXELS]
            
            # Creamos la rampa perfecta generada por Python: [0, 1, 2, ..., 3693]
            data_esperada = np.arange(CCD_PIXELS, dtype=np.uint16)
            
            # Comparamos vectorialmente (muy rápido)
            if np.array_equal(data_recibida, data_esperada):
                frames_ok += 1
                print(f"Frame OK ({frames_ok}) | Rampa Perfecta", end='\r')
            else:
                frames_bad += 1
                print("\n--- ERROR DE INTEGRIDAD EN RAMPA ---")
                
                # Buscamos dónde falló
                diferencias = data_recibida != data_esperada
                indices_mal = np.where(diferencias)[0]
                
                idx = indices_mal[0] # Primer error
                val_rx = data_recibida[idx]
                val_ex = data_esperada[idx]
                
                print(f"Primer fallo en Pixel [{idx}]")
                print(f"  Esperado: {val_ex} ({hex(val_ex)})")
                print(f"  Recibido: {val_rx} ({hex(val_rx)})")
                
                # Análisis de desplazamiento
                if idx > 0:
                    print(f"  Pixel anterior [{idx-1}]: {data_recibida[idx-1]} (OK)")
                
                # Pausa para poder leer el error
                time.sleep(1) 
                ser.reset_input_buffer()

except KeyboardInterrupt:
    print(f"\nResumen: OK={frames_ok}, BAD={frames_bad}")
    ser.close()