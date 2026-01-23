import serial
import struct

PORT = "COM7"    
BAUD = 460800
HEADER = 0x7346
TIMEOUT = 2

HEADER_VAL = 0x7346             # "sF" en ASCII (Little Endian: 0x46, 0x73)
COMMAND_SET_INT = 0xF004        # Comando de set number of accumulations
PAYLOAD_SIZE_WORDS = 2          # 2 palabras de 16 bits = 1 uint32_t
PAYLOAD = 50                    # Número de acumulaciones

try:
    ser = serial.Serial(PORT, BAUD, timeout=TIMEOUT)
    ser.flushInput()
    print(f"Puerto {PORT} abierto")
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

try:
    paquete_sin_cs = struct.pack('<HHI', 
                                         HEADER_VAL, 
                                         COMMAND_SET_INT, 
                                         PAYLOAD)
            
    # 2. Calcular Checksum
    cs = calcular_checksum(paquete_sin_cs)
    
    # 3. Agregar Checksum al final
    paquete_final = paquete_sin_cs + struct.pack('<H', cs)
    
    print(f"Paquete: {paquete_final.hex().upper()}")
    ser.write(paquete_final)

except KeyboardInterrupt:
    print("\nCerrando...")
    ser.close()