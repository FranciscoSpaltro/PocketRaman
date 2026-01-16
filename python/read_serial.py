import serial
import struct
import time

# --- CONFIGURACIÓN ---
PORT = "COM7"       # Ajusta a tu puerto
BAUD = 460800       # Debe coincidir con tu STM32

def calcular_checksum_python(words):
    """ Replica la lógica de checksum de la STM32 (XOR con semilla 0x0000) """
    res = 0x0000

    for i in range(5):
        res ^= words[i]
    return res

try:
    ser = serial.Serial(PORT, BAUD, timeout=2)
    ser.flushInput()
    print(f"Abierto {PORT} a {BAUD}. Esperando mensajes de 12 bytes...")
    print("="*40)

    while True:
        # Esperamos a tener al menos 12 bytes (6 palabras de 16 bits)
        if ser.in_waiting >= 12:
            raw_data = ser.read(12)
            
            # Desempaquetamos: '<5H'
            # <  : Little Endian (Standard de STM32)
            # 6H : 6 Unsigned Short (16-bit integers)
            words = struct.unpack('<6H', raw_data)
            
            # --- ASIGNACIÓN DE PALABRAS ---
            # Palabra 1 y 2: Header
            w_header_1 = words[0]
            w_header_2 = words[1]
            
            # Palabra 3: Comando (Byte Alto) y Secuencia (Byte Bajo)
            w_cmd_seq  = words[2]
            command    = (w_cmd_seq >> 8) & 0xFF  # Parte Alta
            sequence   = w_cmd_seq & 0xFF         # Parte Baja
            
            # Palabra 4: Payload
            w_payload_1  = words[3]
            w_payload_2 = words[4]
            
            # Palabra 5: Checksum recibido
            w_cs_recv  = words[5]
            
            # --- CÁLCULO ---
            w_cs_calc = calcular_checksum_python(words)
            
            # --- IMPRESIÓN SOLICITADA ---
            # Mostramos en Hexadecimal (0xXXXX) y ASCII si aplica
            
            print(f"HEADER:             {w_header_1:04X} {w_header_2:04X}  (ASCII: {raw_data[0:2].decode('ascii', errors='ignore')} {raw_data[2:4].decode('ascii', errors='ignore')})")
            print(f"COMMAND (Alta):     {command:02X}")
            print(f"SEQUENCE (Baja):    {sequence:02X}")
            print(f"PAYLOAD:            {w_payload_1:04X} {w_payload_2:04X}")
            print(f"CHECKSUM RECIBIDO:  {w_cs_recv:04X}")
            
            # Verificación visual
            match_icon = "✅" if w_cs_recv == w_cs_calc else "❌ ERROR"
            print(f"CHECKSUM CALCULADO: {w_cs_calc:04X} {match_icon}")
            
            print("-" * 30)

        else:
            time.sleep(0.01)

except serial.SerialException as e:
    print(f"Error con el puerto serial: {e}")
except KeyboardInterrupt:
    print("\nCerrando monitor...")
    if 'ser' in locals() and ser.is_open:
        ser.close()