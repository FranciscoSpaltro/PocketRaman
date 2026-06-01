import serial
import struct
import time

# --- CONFIGURACIÓN ---
PORT = "COM7"
BAUD = 460800
TIMEOUT = 2

# Definición clara de Constantes (Coinciden con conf_processing.h)
HEADER_VAL = 0x7346             # "sF" en ASCII (Little Endian: 0x46, 0x73)
CMD_ASK_INT_TIME = 0x01         # Solicitud del Micro
CMD_SET_INT_TIME = 0xF001       # Respuesta de la PC / Confirmación
PAYLOAD_SIZE_WORDS = 2          # 2 palabras de 16 bits = 1 uint32_t

INTEGRATION_TIME_US = 10

# Pre-calculamos los bytes del header para búsqueda rápida
HEADER_BYTES = struct.pack('<H', HEADER_VAL)

try:
    ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
    ser.flushInput()
    print(f"Puerto {PORT} abierto. Esperando Header: 0x{HEADER_VAL:04X}...")
except Exception as e:
    print(f"Error abriendo puerto: {e}")
    exit()

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

def sync_to_header(serial_port):
    buffer = b''
    while True:
        byte = serial_port.read(1)
        if not byte: continue
        
        buffer += byte
        if len(buffer) > 2: # El header son 2 bytes
            buffer = buffer[-2:]
            
        if buffer == HEADER_BYTES:
            return

def recibir_paquete(serial_port):
    """ Recibe un paquete completo respetando la estructura del C """
    print("Sincronizando...")
    sync_to_header(serial_port)
    print("Header encontrado.")
    
    # 1. Leer COMMAND (2 bytes) y SIZE (2 bytes)
    # Total 4 bytes después del header
    overhead_data = serial_port.read(4)
    if len(overhead_data) < 4: return None
    
    cmd, size_words = struct.unpack('<HH', overhead_data)
    
    # 2. Calcular cuántos bytes de payload faltan
    # size_words viene del C, indica cantidad de uint16_t. 
    # Bytes = size_words * 2
    payload_bytes_count = size_words * 2
    
    # 3. Leer Payload + Checksum (2 bytes extra)
    resto_data = serial_port.read(payload_bytes_count + 2)
    if len(resto_data) < payload_bytes_count + 2: return None
    
    # --- VALIDACIÓN ---
    # Reconstruimos el frame completo (Header + Overhead + Payload) para el checksum
    # Excluimos los últimos 2 bytes del frame total (que son el CS recibido)
    full_frame_received = HEADER_BYTES + overhead_data + resto_data
    data_para_checksum = full_frame_received[:-2]
    cs_recibido_bytes = full_frame_received[-2:]
    
    cs_calc = calcular_checksum(data_para_checksum)
    cs_recv = struct.unpack('<H', cs_recibido_bytes)[0]
    
    if cs_calc != cs_recv:
        print(f"❌ Error Checksum: Calc {cs_calc:04X} != Recv {cs_recv:04X}")
        return [-1, 0, 0]

    # 4. Extraer Payload
    # El payload está al inicio de 'resto_data'. 
    # Asumimos que es un uint32 (I) porque size_words era 2.
    payload_val = struct.unpack('<I', resto_data[:4])[0]
    
    return [cmd, size_words, payload_val]

# --- BUCLE PRINCIPAL ---
try:
    while True:
        # Esperamos mensaje del Micro
        msg = recibir_paquete(ser)
        
        if msg is None or msg[0] == -1:
            continue

        cmd_rx = msg[0]
        payload_rx = msg[2]

        # CASO 1: El micro pide el tiempo (Solicitud)
        if cmd_rx == CMD_ASK_INT_TIME:
            print(f"📩 Solicitud recibida. Payload dummy: {payload_rx:X}")

            # --- ARMAR RESPUESTA ---
            # Estructura C: HEADER + CMD + SIZE + PAYLOAD + CS
            # Usamos struct para evitar errores manuales de endianness
            
            # 1. Parte de Datos (Todo menos CS)
            # Header(H), Cmd(H), Size(H), Payload(I = 2 words)
            paquete_sin_cs = struct.pack('<HHHI', 
                                         HEADER_VAL, 
                                         CMD_SET_INT_TIME, 
                                         PAYLOAD_SIZE_WORDS, 
                                         INTEGRATION_TIME_US)
            
            # 2. Calcular Checksum
            cs = calcular_checksum(paquete_sin_cs)
            
            # 3. Agregar Checksum al final
            paquete_final = paquete_sin_cs + struct.pack('<H', cs)
            
            ser.write(paquete_final)
            print(f"📤 Respuesta enviada: CMD={CMD_SET_INT_TIME:04X}, T_int={INTEGRATION_TIME_US} us")
            print(f"   Bytes: {paquete_final.hex().upper()}")

        # CASO 2: El micro confirma el cambio (Echo)
        elif cmd_rx == CMD_SET_INT_TIME:
            print(f"✅ Confirmación recibida del micro.")
            print(f"   Tiempo configurado: {payload_rx} µs")
            break # Terminamos el proceso
            
        else:
            print(f"⚠️ Comando desconocido: {cmd_rx:04X}")

except KeyboardInterrupt:
    print("\nCerrando...")
    ser.close()