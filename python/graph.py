import serial
import numpy as np
import matplotlib.pyplot as plt

PORT = "COM7"
BAUD = 460800
PIXELS = 3694
FRAME_SIZE = PIXELS * 2

ser = serial.Serial(PORT, BAUD, timeout=1)

plt.ion()

fig1, ax1 = plt.subplots()
line1, = ax1.plot(np.zeros(PIXELS))
ax1.set_ylim(0, 4500)
ax1.set_xlim(0, PIXELS)
ax1.set_title("Frame completo")


def sync_to_header():
    while True:
        b = ser.read(1)
        if len(b) == 0:
            continue
        if b[0] == 0xAA:
            b2 = ser.read(1)
            if len(b2) == 0:
                continue
            if b2[0] == 0x55:
                return    

while True:
    sync_to_header()
    data = ser.read(FRAME_SIZE)

    if len(data) != FRAME_SIZE:
        print("Frame incompleto", len(data))
        continue

    arr = np.frombuffer(data, dtype=np.uint16)

    line1.set_ydata(arr)
    fig1.canvas.draw()
    fig1.canvas.flush_events()
