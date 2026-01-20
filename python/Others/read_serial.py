import serial


# --- CONFIGURACIÓN ---
PORT = "COM7"       # Ajusta a tu puerto
BAUD = 460800       # Debe coincidir con tu STM32

try:
    ser = serial.Serial(PORT, BAUD, timeout=2)
    ser.flushInput()
    print(f"Abierto {PORT} a {BAUD}")

    try:
        while True:
            data = ser.read(2)
            if data:
                print(data.hex())

    except KeyboardInterrupt:
        print("Cerrando puerto...")
        ser.close()

except Exception as e:
    print(f"Error abriendo puerto: {e}")
    exit()