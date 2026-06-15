import sys
import serial
import struct
import numpy as np
import pyqtgraph as pg

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                               QSpinBox, QGroupBox, QMessageBox)
from PySide6.QtCore import QThread, Signal, Slot

# ==========================================
# 1. EL DRIVER (Tu código original casi intacto)
# ==========================================
class SpectrometerDriver:
    HEADER_VAL = 0x7346
    END_BUFFER_VAL = 0x7347
    
    # Comandos
    CMD_SET_INT_TIME        = 0xF001
    CMD_RESET               = 0xF002
    CMD_DATA_SENDING        = 0xF003
    CMD_SET_ACCUM           = 0xF004
    CMD_SET_SKIP_COUNTER    = 0xF005
    
    CCD_PIXELS = 3694

    def __init__(self, port="COM7", baud=921600, timeout=2):
        self.int_time_us = 100
        self.n_accum = 50
        self.skip_count = 0
        self.ser = None
        
        try:
            self.ser = serial.Serial(port, baud, timeout=timeout)
            self.ser.flushInput()
            print(f"Connected to {port} @ {baud}")
        except Exception as e:
            print(f"Error connecting to port: {e}")
            raise e

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Connection closed.")

    def _calculate_checksum(self, data_bytes):
        if len(data_bytes) % 2 != 0: return 0
        num_words = len(data_bytes) // 2
        words = struct.unpack(f'<{num_words}H', data_bytes)
        cs = 0x0000
        for w in words:
            cs ^= w
        return cs

    def _send_command(self, cmd_id, payload_val=0xFFFFFFFF):
        try:
            packet_no_cs = struct.pack('<HHI', self.HEADER_VAL, cmd_id, payload_val)
            cs = self._calculate_checksum(packet_no_cs)
            final_packet = packet_no_cs + struct.pack('<H', cs)
            self.ser.write(final_packet)
            print(f"TX: {final_packet.hex().upper()}")
        except struct.error as e:
            print(f"Error packaging data: {e}")

    def reset_device(self):
        print("Sending RESET...")
        self._send_command(self.CMD_RESET)

    def set_integration_time(self, time_us):
        print(f"Set Integration Time: {time_us} us")
        self._send_command(self.CMD_SET_INT_TIME, time_us)
        self.int_time_us = time_us

    def set_accumulations(self, n_accum):
        print(f"Set Accumulations: {n_accum}")
        self._send_command(self.CMD_SET_ACCUM, n_accum)
        self.n_accum = n_accum

    def set_skip_counter(self, skip_count):
        print(f"Set skip counter: {skip_count}")
        self._send_command(self.CMD_SET_SKIP_COUNTER, skip_count)
        self.skip_count = skip_count

    def read_frame(self):
        if not self.ser or not self.ser.is_open:
            return None

        header_bytes = struct.pack('<H', self.HEADER_VAL)
        window = bytearray()
        
        while True:
            b = self.ser.read(1)
            if not b: return None # Timeout
            window += b
            if len(window) > 2: window = window[-2:]
            if window == header_bytes:
                break
        
        payload_size = self.CCD_PIXELS * 2
        rest_len = 2 + payload_size + 2 + 2 
        data = self.ser.read(rest_len)
        
        if len(data) != rest_len:
            return None

        full_arr = np.frombuffer(data, dtype=np.dtype('<u2'))
        
        if full_arr[0] != self.CMD_DATA_SENDING or full_arr[-1] != self.END_BUFFER_VAL:
            return None
        
        return full_arr[1 : 1 + self.CCD_PIXELS]

# ==========================================
# 2. EL HILO DE ADQUISICIÓN (Worker)
# ==========================================
class AcquisitionThread(QThread):
    data_ready = Signal(np.ndarray)

    def __init__(self, driver):
        super().__init__()
        self.dev = driver
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            pixels = self.dev.read_frame()
            if pixels is not None:
                self.data_ready.emit(pixels)
            else:
                # Si hay timeout o error, esperamos un ratito antes de reintentar
                self.msleep(10)

    def stop(self):
        self.running = False
        self.wait()

# ==========================================
# 3. LA INTERFAZ GRÁFICA (PySide6)
# ==========================================
class RamanGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spectrometer Raman - Control Panel")
        self.resize(1000, 600)

        self.dev = None
        self.worker = None

        self.setup_ui()

    def setup_ui(self):
        # Widget central y layout principal (Horizontal: Controles izq, Gráfico der)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- PANEL IZQUIERDO (Controles) ---
        control_widget = QWidget()          # Creamos un widget contenedor
        control_widget.setFixedWidth(250)   # A este SÍ le podemos fijar el ancho
        control_layout = QVBoxLayout(control_widget) # El layout ahora maneja al widget

        # Grupo: Conexión
        group_conn = QGroupBox("Connection")
        conn_layout = QVBoxLayout()
        self.port_input = QLineEdit("COM7")
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clicked.connect(self.connect_device)
        conn_layout.addWidget(QLabel("Port COM:"))
        conn_layout.addWidget(self.port_input)
        conn_layout.addWidget(self.btn_connect)
        group_conn.setLayout(conn_layout)

        # Grupo: Comandos
        group_cmds = QGroupBox("STM32 configuration")
        cmds_layout = QVBoxLayout()
        
        # Tiempo de integración
        self.spin_time = QSpinBox()
        self.spin_time.setRange(1, 1000000)
        self.spin_time.setValue(100)
        self.btn_time = QPushButton("Set Integration Time (us)")
        self.btn_time.clicked.connect(lambda: self.send_cmd('time'))
        cmds_layout.addWidget(self.spin_time)
        cmds_layout.addWidget(self.btn_time)

        # Acumulaciones
        self.spin_accum = QSpinBox()
        self.spin_accum.setRange(1, 1000)
        self.spin_accum.setValue(50)
        self.btn_accum = QPushButton("Set Accumulations")
        self.btn_accum.clicked.connect(lambda: self.send_cmd('accum'))
        cmds_layout.addWidget(self.spin_accum)
        cmds_layout.addWidget(self.btn_accum)

        # Skip
        self.spin_skip = QSpinBox()
        self.spin_skip.setRange(0, 1000)
        self.spin_skip.setValue(0)
        self.btn_skip = QPushButton("Set Skip Counter")
        self.btn_skip.clicked.connect(lambda: self.send_cmd('skip'))
        cmds_layout.addWidget(self.spin_skip)
        cmds_layout.addWidget(self.btn_skip)

        # Reset
        self.btn_reset = QPushButton("Reset Device")
        self.btn_reset.setStyleSheet("background-color: #ffcccc;")
        self.btn_reset.clicked.connect(lambda: self.send_cmd('reset'))
        cmds_layout.addWidget(self.btn_reset)
        
        group_cmds.setLayout(cmds_layout)

        # Grupo: Adquisición
        group_acq = QGroupBox("Continuous Acquisition")
        acq_layout = QVBoxLayout()
        self.btn_start = QPushButton("▶ Start Reading")
        self.btn_start.setStyleSheet("background-color: #ccffcc;")
        self.btn_start.clicked.connect(self.toggle_acquisition)
        self.btn_start.setEnabled(False) # Deshabilitado hasta conectar
        acq_layout.addWidget(self.btn_start)
        group_acq.setLayout(acq_layout)

        # Armar el panel izquierdo
        control_layout.addWidget(group_conn)
        control_layout.addWidget(group_cmds)
        control_layout.addWidget(group_acq)
        control_layout.addStretch() # Empuja todo hacia arriba

        # --- PANEL DERECHO (Gráfico) ---
        pg.setConfigOption('background', 'w') # Fondo blanco
        pg.setConfigOption('foreground', 'k') # Texto negro
        self.plot_widget = pg.PlotWidget(title="Spectrum in Real Time")
        self.plot_widget.setLabel('left', 'Intensity (ADC)', units='')
        self.plot_widget.setLabel('bottom', 'Pixel', units='')
        self.plot_widget.setYRange(0, 4200) # Límite del ADC
        self.plot_widget.setXRange(0, SpectrometerDriver.CCD_PIXELS)
        self.plot_widget.showGrid(x=True, y=True)
        
        # Crear la curva
        self.curve = self.plot_widget.plot(pen=pg.mkPen('b', width=2)) # Curva azul

        # Unir paneles
        main_layout.addWidget(control_widget)
        main_layout.addWidget(self.plot_widget)

    # --- SLOTS (Acciones de la interfaz) ---
    def connect_device(self):
        port = self.port_input.text()
        try:
            self.dev = SpectrometerDriver(port=port)
            self.btn_connect.setText("Connected")
            self.btn_connect.setStyleSheet("background-color: #ccffcc;")
            self.btn_connect.setEnabled(False)
            self.port_input.setEnabled(False)
            self.btn_start.setEnabled(True)
            
            # Inicializar el hilo (pero no arrancarlo aún)
            self.worker = AcquisitionThread(self.dev)
            self.worker.data_ready.connect(self.update_plot)
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"Could not connect to {port}.\n\n{str(e)}")

    def send_cmd(self, cmd_type):
        if not self.dev: return
        
        if cmd_type == 'reset':
            self.dev.reset_device()
        elif cmd_type == 'time':
            val = self.spin_time.value()
            self.dev.set_integration_time(val)
        elif cmd_type == 'accum':
            val = self.spin_accum.value()
            self.dev.set_accumulations(val)
        elif cmd_type == 'skip':
            val = self.spin_skip.value()
            self.dev.set_skip_counter(val)

    def toggle_acquisition(self):
        if not self.worker.running:
            # Arrancar
            self.worker.start()
            self.btn_start.setText("⏸ Stop Reading")
            self.btn_start.setStyleSheet("background-color: #ffcccc;")
        else:
            # Detener
            self.worker.stop()
            self.btn_start.setText("▶ Start Reading")
            self.btn_start.setStyleSheet("background-color: #ccffcc;")

    @Slot(np.ndarray)
    def update_plot(self, data):
        # Actualiza el gráfico súper rápido
        self.curve.setData(data)

    def closeEvent(self, event):
        # Se ejecuta al cerrar la ventana con la "X"
        if self.worker and self.worker.running:
            self.worker.stop()
        if self.dev:
            self.dev.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RamanGUI()
    window.show()
    sys.exit(app.exec())