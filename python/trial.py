import serial

PORT = "COM7"      
BAUD = 460800

try:
    ser = serial.Serial(PORT, BAUD, timeout=2)
    ser.flushInput()
except Exception as e:
    print(f"Error abriendo puerto: {e}")
    exit()


while True:
    byte = ser.read(1)
    if byte:
        print(byte.hex())
        if byte == b'\x46':
            next_byte = ser.read(1)
            print(next_byte.hex())
            if next_byte == b'\x73':
                print("Header encontrado")
                
        elif byte == b'\x47':
            next_byte = ser.read(1)
            print(next_byte.hex())
            if next_byte == b'\x73':
                print("Fin encontrado")
                break