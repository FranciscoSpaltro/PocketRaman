import serial
import numpy as np
import matplotlib.pyplot as plt
from enum import Enum
import struct
from dataclasses import dataclass

# --- CONFIGURACIÓN ---
PORT = "COM7"      
BAUD = 460800
#HEADER_WORDS = [0x5246, 0x4E41]
HEADER_WORDS = [0x7346]
HEADER_BYTES = struct.pack('<1H', *HEADER_WORDS)
COMMAND_ASK_FOR_INTEGRATION_TIME = 0x01
CONF_MSG = 0x00
DATA_MSG = 0x01
INTEGRATION_TIME_US = 10000

class Mensaje(Enum):
    SET_INTEGRATION_TIME_REQUEST = 1
    SET_INTEGRATION_TIME_RESPONSE = 2

try:
    ser = serial.Serial(PORT, BAUD, timeout=2)
    ser.flushInput()
except Exception as e:
    print(f"Error abriendo puerto: {e}")
    exit()

def sync_to_header(serial_port):
    buffer = b''
    while True:
        new_byte = serial_port.read(1)
        if not new_byte:
            continue
        
        buffer += new_byte
        if len(buffer) > len(HEADER_BYTES):
            buffer = buffer[-len(HEADER_BYTES):]
            
        if buffer == HEADER_BYTES:
            return buffer

def calcular_checksum(msg):
    words = struct.unpack(f'<{len(msg)//2}H', msg)
    
    cs = 0x0000 # Semilla
    for w in words:
        cs ^= w
    
    return cs

def obtener_mensaje_configuracion(serial_port):
    total_bytes = 10
    print("Sincronizando al header...")
    
    # Esto ya trae los 2 bytes del header
    raw_data = sync_to_header(serial_port) 
    print("Header encontrado.")

    # Leemos los 8 bytes restantes (Cmd/Type + Payload + CS)
    raw_data += serial_port.read(total_bytes - len(HEADER_BYTES))
    print(f"Mensaje completo recibido: {raw_data.hex()}")

    # Validamos Checksum (usamos todo MENOS los últimos 2 bytes que son el CS recibido)
    checksum_calculado = calcular_checksum(raw_data[:-2])
    checksum_recibido = struct.unpack('<H', raw_data[8:10])[0]

    if checksum_calculado != checksum_recibido:
        print(f"Checksum Error: Calc {checksum_calculado:04X} != Recv {checksum_recibido:04X}")
        return [-1, -1, 0, 0]
    
    # --- CORRECCIÓN 2: Índices correctos ---
    # raw_data tiene 10 bytes:
    # 0,1 -> Header
    # 2 -> Type (Parte baja de la palabra Cmd/Type)
    # 3 -> Command (Parte alta de la palabra Cmd/Type)
    # 4,5,6,7 -> Payload (4 bytes)
    # 8,9 -> Checksum
    
    return [
        raw_data[3],  # Command 
        raw_data[2],  # Type
        struct.unpack('<I', raw_data[4:8])[0], # Payload
        checksum_recibido
    ]

# --- BUCLE PRINCIPAL ---
try:
    while True:
        msg = obtener_mensaje_configuracion(ser)

        if msg[0] == -1:
            # print("Error de checksum...")
            continue

        if msg[0] == COMMAND_ASK_FOR_INTEGRATION_TIME and msg[1] == CONF_MSG:
            print("Solicitud para ingresar un nuevo tiempo de integración recibida")

            # Armamos respuesta (Header + Type + Cmd + Payload)
            # Nota: Ponemos Type antes que Command para que al unirse sea (CMD<<8)|TYPE
            msg_response_bytes = HEADER_BYTES + bytes([CONF_MSG]) + bytes([COMMAND_ASK_FOR_INTEGRATION_TIME]) + struct.pack('<I', INTEGRATION_TIME_US)
            
            checksum_response = calcular_checksum(msg_response_bytes)
            msg_response_bytes += struct.pack('<H', checksum_response)
            print(f"Mensaje de respuesta armado: {msg_response_bytes.hex()}")
            ser.write(msg_response_bytes)
            print(f"Respuesta enviada con tiempo de integración: {INTEGRATION_TIME_US} µs")

        msg = obtener_mensaje_configuracion(ser)
        if msg[0] == -1:
            # print("Error de checksum...")
            continue

        if msg[0] == COMMAND_ASK_FOR_INTEGRATION_TIME and msg[1] == CONF_MSG:
            tiempo_integracion_recibido = msg[2]
            print(f"Tiempo de integración confirmado por el microcontrolador: {tiempo_integracion_recibido} µs")

        break

        # Recibo echo (Opcional, depende de si tu micro responde al recibir la config)
        # msg_echo = obtener_mensaje_configuracion(ser)
        # ...

except KeyboardInterrupt:
    print("\nCerrando...")
    ser.close()