from PySide6.QtWidgets import (QDoubleSpinBox, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                               QSpinBox, QGroupBox, QSlider, QMessageBox, QLineEdit, QStyle)
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Slot, Qt
from signalprocessor import SignalProcessor
from spectrometer import SpectrometerDriverMock
from adquisition import AcquisitionThread
from help_messages import *
import pyqtgraph as pg
import numpy as np

# ==========================================
# INTERFAZ GRÁFICA (PySide6)
# ==========================================
class ScientificDoubleSpinBox(QDoubleSpinBox):
    def textFromValue(self, value):
        return f"{value:.1e}"

    def valueFromText(self, text):
        return float(text)
    
    
class RamanGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spectrometer Raman - Control Panel")
        self.resize(1000, 600)

        self.dev = None
        self.worker = None
        self.processor = SignalProcessor()

        self.setup_ui()

    def setup_ui(self):
        # Widget central y layout principal (Horizontal: Controles izq, Gráfico der)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- PANEL IZQUIERDO (Controles) ---
        control_widget = QWidget()          # Widget contenedor
        control_widget.setFixedWidth(250)   # Fija el ancho
        control_layout = QVBoxLayout(control_widget) # El layout ahora maneja al widget

        ########################################################################
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
        ########################################################################

        # Grupo: Comandos
        group_cmds = QGroupBox("STM32 configuration")
        cmds_layout = QVBoxLayout()

        ########################################################################        
        # Tiempo de integración
        self.spin_time = QSpinBox()
        self.spin_time.setRange(1, 1000000)
        self.spin_time.setValue(100)
        self.btn_time = QPushButton("Set Integration Time (us)")
        self.btn_time.clicked.connect(lambda: self.send_cmd('time'))
        cmds_layout.addWidget(self.spin_time)
        cmds_layout.addWidget(self.btn_time)
        ########################################################################

        ########################################################################
        # Acumulaciones
        self.spin_accum = QSpinBox()
        self.spin_accum.setRange(1, 1000)
        self.spin_accum.setValue(50)
        self.btn_accum = QPushButton("Set Accumulations")
        self.btn_accum.clicked.connect(lambda: self.send_cmd('accum'))
        cmds_layout.addWidget(self.spin_accum)
        cmds_layout.addWidget(self.btn_accum)
        ########################################################################

        ########################################################################
        # Skip
        self.spin_skip = QSpinBox()
        self.spin_skip.setRange(0, 1000)
        self.spin_skip.setValue(0)
        self.btn_skip = QPushButton("Set Skip Counter")
        self.btn_skip.clicked.connect(lambda: self.send_cmd('skip'))
        cmds_layout.addWidget(self.spin_skip)
        cmds_layout.addWidget(self.btn_skip)
        ########################################################################

        ########################################################################
        # Reset
        self.btn_reset = QPushButton("Reset Device")
        self.btn_reset.setStyleSheet("background-color: #ffcccc;")
        self.btn_reset.clicked.connect(lambda: self.send_cmd('reset'))
        cmds_layout.addWidget(self.btn_reset)
        ########################################################################
        
        group_cmds.setLayout(cmds_layout)

        ########################################################################
        ########################################################################
        ########################################################################

        # Grupo: Adquisición
        group_acq = QGroupBox("Continuous Acquisition")
        acq_layout = QVBoxLayout()
        self.btn_start = QPushButton("▶ Start Reading")
        self.btn_start.setStyleSheet("background-color: #ccffcc;")
        self.btn_start.clicked.connect(self.toggle_acquisition)
        self.btn_start.setEnabled(False) # Deshabilitado hasta conectar
        acq_layout.addWidget(self.btn_start)
        group_acq.setLayout(acq_layout)

        ########################################################################
        ########################################################################
        ########################################################################

        # Grupo: Procesamiento de señales
        group_sig_processing = QGroupBox("Procesamiento en vivo")
        sig_processing_layout = QVBoxLayout()
        
        ########################################################################
        ### Enable/Disable data processing
        self.lbl_enable_processing = QLabel("Data processing")
        self.btn_enable_processing = QPushButton("Enable")
        self.btn_enable_processing.clicked.connect(self.toggle_enable_processing)
        sig_processing_layout.addWidget(self.lbl_enable_processing)
        sig_processing_layout.addWidget(self.btn_enable_processing)
        ########################################################################
        ### NOISE
        self.lbl_noise = QLabel("Noise: -")
        sig_processing_layout.addWidget(self.lbl_noise)


        ########################################################################
        ### Baseline correction
        # En 0 no hace nada (por implementación de signalprocessor), el máximo se configuró experimentalmente en 1e14
        self.lbl_baseline = QLabel("Baseline λ")
        self.baseline_help_button = QPushButton()
        self.baseline_help_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        )
        self.baseline_help_button.setFixedSize(22, 22)
        self.baseline_help_button.clicked.connect(lambda: show_baseline_help(self))

        self.processor.set_baseline_lambda(10000)
        self.edit_baseline_lambda = QLineEdit(
            f"{self.processor.baseline_lambda:.1e}"
        )

        self.edit_baseline_lambda.editingFinished.connect(
            self.update_baseline
        )

        baseline_layout = QHBoxLayout()
        baseline_layout.addWidget(self.edit_baseline_lambda)
        baseline_layout.addWidget(self.baseline_help_button)

        sig_processing_layout.addWidget(self.lbl_baseline)
        sig_processing_layout.addLayout(baseline_layout)
        ########################################################################

        ########################################################################
        ### Suavizado
        self.lbl_smoothing = QLabel("Smoothing")
        self.smoothing_help_button = QPushButton()
        self.smoothing_help_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        )
        self.smoothing_help_button.setFixedSize(22, 22)
        self.smoothing_help_button.clicked.connect(lambda: show_smoothing_help(self))

        # Window length
        self.processor.set_smoothing_wd(2)
        self.edit_smoothing_wd = QLineEdit(str(self.processor.smoothing_wd))

        self.edit_smoothing_wd.editingFinished.connect(
            self.update_smoothing_wd
        )

        # Polynomial order
        self.processor.set_smoothing_poly(1)
        self.edit_smoothing_poly = QLineEdit(str(self.processor.smoothing_poly))

        self.edit_smoothing_poly.editingFinished.connect(
            self.update_smoothing_poly
        )

        smoothing_layout = QHBoxLayout()
        smoothing_layout.addWidget(QLabel("Window:"))
        smoothing_layout.addWidget(self.edit_smoothing_wd)
        smoothing_layout.addWidget(QLabel("Poly:"))
        smoothing_layout.addWidget(self.edit_smoothing_poly)
        smoothing_layout.addWidget(self.smoothing_help_button)

        sig_processing_layout.addWidget(self.lbl_smoothing)
        sig_processing_layout.addLayout(smoothing_layout)
        ########################################################################

        ########################################################################
        ### Altura
        self.lbl_peak_height_factor = QLabel(f"Height factor")

        self.height_factor_help_button = QPushButton()
        self.height_factor_help_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        )
        self.height_factor_help_button.setFixedSize(22, 22)
        self.height_factor_help_button.clicked.connect(lambda: show_height_factor_help(self))

        self.processor.set_peak_height_factor(1)
        self.edit_peak_height_factor = QLineEdit(str(self.processor.peak_height_factor))

        self.edit_peak_height_factor.editingFinished.connect(
            self.update_peak_height_factor
        )

        height_factor_layout = QHBoxLayout()
        height_factor_layout.addWidget(self.edit_peak_height_factor)
        height_factor_layout.addWidget(self.height_factor_help_button)

        sig_processing_layout.addWidget(self.lbl_peak_height_factor)
        sig_processing_layout.addLayout(height_factor_layout)
        ########################################################################

        ########################################################################
        ### Prominence
        self.lbl_prominence = QLabel(f"Prominence factor")

        self.prominence_help_button = QPushButton()
        self.prominence_help_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        )
        self.prominence_help_button.setFixedSize(22, 22)
        self.prominence_help_button.clicked.connect(lambda: show_prominence_factor_help(self))

        self.processor.set_peak_prominence(1)
        self.edit_peak_prominence = QLineEdit(str(self.processor.peak_prominence))

        self.edit_peak_prominence.editingFinished.connect(
            self.update_peak_prominence
        )

        prominence_layout = QHBoxLayout()
        prominence_layout.addWidget(self.edit_peak_prominence)
        prominence_layout.addWidget(self.prominence_help_button)

        sig_processing_layout.addWidget(self.lbl_prominence)
        sig_processing_layout.addLayout(prominence_layout)
        ########################################################################

        ########################################################################
        ### Distancia minima entre picos
        self.lbl_min_distance = QLabel(f"Min peak distance")
        self.min_distance_help_button = QPushButton()
        self.min_distance_help_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        )
        self.min_distance_help_button.setFixedSize(22, 22)
        self.min_distance_help_button.clicked.connect(lambda: show_minmum_peak_distance_help(self))

        self.processor.set_peak_min_distance(1)
        self.edit_peak_min_distance = QLineEdit(str(self.processor.peak_min_distance))

        self.edit_peak_min_distance.editingFinished.connect(
            self.update_peak_min_distance
        )

        min_distance_layout = QHBoxLayout()
        min_distance_layout.addWidget(self.edit_peak_min_distance)
        min_distance_layout.addWidget(self.min_distance_help_button)

        sig_processing_layout.addWidget(self.lbl_min_distance)
        sig_processing_layout.addLayout(min_distance_layout)

        ##############################################
        # FIND PEAKS
        self.btn_find_peaks = QPushButton("Find peaks")
        self.btn_find_peaks.clicked.connect(self.find_and_plot_peaks)
        sig_processing_layout.addWidget(self.btn_find_peaks)
        
        ########################################################################
        group_sig_processing.setLayout(sig_processing_layout)

        # Armar el panel izquierdo
        control_layout.addWidget(group_conn)
        control_layout.addWidget(group_cmds)
        control_layout.addWidget(group_acq)
        control_layout.addWidget(group_sig_processing)
        control_layout.addStretch() # Empuja todo hacia arriba

        # --- PANEL DERECHO (Gráfico) ---
        pg.setConfigOption('background', 'w') # Fondo blanco
        pg.setConfigOption('foreground', 'k') # Texto negro
        self.plot_widget = pg.PlotWidget(title="Spectrum in Real Time")
        self.plot_widget.setLabel('left', 'Intensity (ADC)', units='')
        self.plot_widget.setLabel('bottom', 'Pixel', units='')
        self.plot_widget.setYRange(0, 4200) # Límite del ADC
        self.plot_widget.setXRange(0, 3694)
        self.plot_widget.showGrid(x=True, y=True)
        
        # Crear la curva
        self.curve = self.plot_widget.plot(pen=pg.mkPen('b', width=2)) # Curva azul

        # Picos
        self.peaks_curve = self.plot_widget.plot(
            pen=None,
            symbol='o',
            symbolSize=8,
            symbolBrush='r'
        )

        # Unir paneles
        main_layout.addWidget(control_widget)
        main_layout.addWidget(self.plot_widget)

    # --- SLOTS (Acciones de la interfaz) ---
    def connect_device(self):
        port = self.port_input.text()
        try:
            self.dev = SpectrometerDriverMock(port=port)
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

    ### ENABLE/DISABLE DATA PROCESSING
    def toggle_enable_processing(self):
        enabled = self.btn_enable_processing.text() == "Enable"

        if enabled:
            self.btn_enable_processing.setText("Disable")
        else:
            self.btn_enable_processing.setText("Enable")

        self.processor.set_enable_processing(enabled)
    
    ### BASELINE CORRECTION
    def update_baseline(self):
        val = float(self.edit_baseline_lambda.text())

        val = min(max(val, 0), 1e14)  # Limitar entre 0 y 1e14
        
        self.edit_baseline_lambda.setText(f"{val:.1e}")
        self.processor.set_baseline_lambda(val)

    ### SMOOTHING
    def update_smoothing_wd(self):
        val = int(self.edit_smoothing_wd.text())
        
        if val < 2:
            val = 2
        elif val > 3694:
            val = 3694

        self.edit_smoothing_wd.setText(str(val))
        self.processor.set_smoothing_wd(val)    
        
    def update_smoothing_poly(self):
        val = int(self.edit_smoothing_poly.text())
        
        if val < 1:
            val = 1
        elif val > self.processor.smoothing_wd - 1:
            val = self.processor.smoothing_wd - 1

        self.edit_smoothing_poly.setText(str(val))
        self.processor.set_smoothing_poly(val)  

    ### HEIGHT
    def update_peak_height_factor(self):
        val = float(self.edit_peak_height_factor.text())
        if val < 0:
            val = 0

        self.edit_peak_height_factor.setText(f"{val:.2f}")
        self.processor.set_peak_height_factor(val)

     ### PROMINENCE
    def update_peak_prominence(self):
        val = float(self.edit_peak_prominence.text())
        if val < 0:
            val = 0

        self.edit_peak_prominence.setText(f"{val:.2f}")
        self.processor.set_peak_prominence(val)

    ### MIN DISTANCE
    def update_peak_min_distance(self):
        val = int(self.edit_peak_min_distance.text())
        if val < 1:
            val = 1
        elif val > 3693:
            val = 3693

        self.edit_peak_min_distance.setText(str(val))
        self.processor.set_peak_min_distance(val)

    @Slot(np.ndarray)
    def update_plot(self, data):
        processed_data, _ = self.processor.process(data)

        self.processor.last_processed_data = processed_data
        self.curve.setData(processed_data)

    def find_and_plot_peaks(self):
        if self.processor.last_processed_data is None:
            return

        peaks = self.processor.find_peaks(self.processor.last_processed_data)

        self.lbl_noise.setText(
            f"Noise: {self.processor.last_noise:.2f} ADC counts"
        )

        if len(peaks) > 0:
            x_peaks = peaks
            y_peaks = self.processor.last_processed_data[peaks]
            self.peaks_curve.setData(x_peaks, y_peaks)
        else:
            self.peaks_curve.setData([], [])

    def closeEvent(self, event):
        # Se ejecuta al cerrar la ventana con la "X"
        if self.worker and self.worker.running:
            self.worker.stop()
        if self.dev:
            self.dev.close()
        event.accept()