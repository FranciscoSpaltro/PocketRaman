import struct
import time
import serial
PORT = "COM7"
BAUD = 460800

TIEMPO_INTEGRACION_US = 100  # <--- CONF

def realizar_handshake(serial_port, t_int_val):
    print("Esperando solicitud de la STM32...")
    
    while True:
        if serial_port.in_waiting >= 2:
            req = serial_port.read(2)
            
            if req == b'\x46\x52':
                print(f"Solicitud recibida. Enviando T_int = {t_int_val} us")
                
                # 2. Empaquetar respuesta: Header (CC DD) + uint32 (Little Endian)
                # '<H I': H = unsigned short (2 bytes), I = unsigned int (4 bytes)
                header = b'\x41\x4E'
                payload = struct.pack('<I', t_int_val) # < = Little Endian
                
                packet = header + payload
                serial_port.write(packet)
                
                print("Configuración enviada. Iniciando captura...")
                return
            else:
                serial_port.reset_input_buffer()
        
        time.sleep(0.01)

try:
    ser = serial.Serial(PORT, BAUD, timeout=2)
    ser.flushInput()
    
    realizar_handshake(ser, TIEMPO_INTEGRACION_US) 
    
except Exception as e:
    print(f"Error abriendo puerto: {e}")
    exit()