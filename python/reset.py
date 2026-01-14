import serial

PORT = "COM7"    
BAUD = 460800

try:
    ser = serial.Serial(PORT, BAUD, timeout=2)
    ser.flushInput()
    
    # Mando el comando 0x46 0x53
    print("Enviando comando de reset a la STM32...")
    ser.write(b'\x46\x53')
    

except Exception as e:
    print(f"Error abriendo puerto: {e}")
    exit()