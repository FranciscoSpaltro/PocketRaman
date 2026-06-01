import time
import serial
import numpy as np
import matplotlib.pyplot as plt
import struct

PORT = "COM7"      
BAUD = 460800
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


def read_exact(ser, n, timeout_s=1.0, chunk_size=4096):
    """
    Lee EXACTAMENTE n bytes del puerto serie, acumulando si llegan en partes.
    Devuelve bytes de largo n, o None si se agota el timeout total.
    
    - timeout_s: tiempo máximo TOTAL esperando completar n bytes
    - chunk_size: máximo a pedir en cada read (evita pedir 100k de golpe)
    """
    deadline = time.monotonic() + timeout_s
    buf = bytearray()

    while len(buf) < n:
        remaining = n - len(buf)

        # Pedimos como mucho chunk_size para mantenerlo ágil
        to_read = remaining if remaining < chunk_size else chunk_size

        # Tiempo restante del timeout global
        time_left = deadline - time.monotonic()
        if time_left <= 0:
            return None

        # Ajustamos el timeout del puerto SOLO para este read
        old_timeout = ser.timeout
        ser.timeout = time_left
        try:
            chunk = ser.read(to_read)
        finally:
            ser.timeout = old_timeout

        if not chunk:
            # read devolvió vacío -> venció el timeout de este read (y por ende el global)
            return None

        buf += chunk

    return bytes(buf)

def calcular_checksum(data_bytes):
    words = len(data_bytes) // 2
    # extraigo cada palabra de 2 bytes y hago XOR
    checksum = 0
    for i in range(words):
        word = struct.unpack_from('<H', data_bytes, i * 2)[0]
        checksum ^= word
    return checksum   

def sync_to_header(serial_port):
    """ Busca la secuencia 0x46, 0x73 en el flujo de datos """
    while True:
        byte = serial_port.read(1)
        if byte:
            # Buscamos el primer byte del cable (0x46)
            if byte == struct.pack('B', HEADER_BYTES & 0xFF):                   # Primero el LSB
                next_byte = serial_port.read(1)
                # Buscamos el segundo byte del cable (0x73)
                if next_byte == struct.pack('B', HEADER_BYTES >> 8):            # Luego el MSB
                    break

sync_to_header(ser)
PAYLOAD_BYTES = 3694 * 2
packet = read_exact(ser, 2 + PAYLOAD_BYTES + 2 + 2, timeout_s=2.0)  # cmd+data+cs+footer

if packet is None:
    print("Timeout leyendo paquete completo")
else:
    packet = HEADER_BYTES.to_bytes(2, 'little') + packet
    cmd      = packet[2:4]
    raw_data = packet[4:4+PAYLOAD_BYTES]
    cs_bytes = packet[4+PAYLOAD_BYTES:4+PAYLOAD_BYTES+2]
    footer   = packet[-2:]

    cs_calculado = calcular_checksum(packet)
    print(f"Comando: {cmd.hex()}")
    print(f"Footer: {footer.hex()}")
    print(f"Checksum: {cs_bytes.hex()}")
    print(f"Checksum calculado: {cs_calculado:04x}")

    print(packet.hex())

