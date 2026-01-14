import serial

PORT = "COM7"       # Ajustá tu puerto
BAUD = 460800

# --- USO ---
try:
    ser = serial.Serial(PORT, BAUD, timeout=2)
    ser.flushInput()
    
    # Mando el comando 0x46 0x53
    print("Enviando comando de reset a la STM32...")
    ser.write(b'\x46\x53')
    
    # ... Aquí sigue tu plt.ion(), bucle while True, etc ...

except Exception as e:
    print(f"Error abriendo puerto: {e}")
    exit()