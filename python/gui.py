from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                               QSpinBox, QGroupBox, QMessageBox, QLineEdit, QStyle)
from PySide6.QtCore import Slot
from signalprocessor import SignalProcessor
from spectrometer import SpectrometerDriverMock
from adquisition import AcquisitionThread
from help_messages import *
import pyqtgraph as pg
import numpy as np   
    
class RamanGUI(QMainWindow):
    ###########################################################################
    # CONSTRUCTOR AND INITIALIZATION
    ###########################################################################
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spectrometer Raman - Control Panel")
        self.resize(1000, 600)

        self.peaks_enabled = False
        self.peak_labels_enabled = False
        self.peak_labels = []

        self.dev = None
        self.worker = None
        self.processor = SignalProcessor()

        self.setup_ui()

    ###########################################################################
    # GUI SETUP
    ###########################################################################
    def setup_ui(self):
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        ##########################################################################
        # LEFT PANEL (CONTROLS)
        #########################################################################
        control_widget = QWidget()
        control_widget.setFixedWidth(250)
        control_layout = QVBoxLayout(control_widget)

        #########################################################################
        # CONNECTION GROUP
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
        # COMMANDS GROUP
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

        # GROUP    
        group_cmds.setLayout(cmds_layout)

        ########################################################################
        # ADQUISITION GROUP
        group_acq = QGroupBox("Continuous Acquisition")
        acq_layout = QVBoxLayout()
        self.btn_start = QPushButton("▶ Start Reading")
        self.btn_start.setStyleSheet("background-color: #ccffcc;")
        self.btn_start.clicked.connect(self.toggle_acquisition)
        self.btn_start.setEnabled(False) # Deshabilitado hasta conectar
        acq_layout.addWidget(self.btn_start)
        group_acq.setLayout(acq_layout)

        # SIGNAL PROCESSING GROUP
        group_sig_processing = QGroupBox("Procesamiento en vivo")
        sig_processing_layout = QVBoxLayout()
        
        # Enable/Disable data processing
        self.lbl_enable_processing = QLabel("Data processing")
        self.btn_enable_processing = QPushButton("Enable")
        self.btn_enable_processing.clicked.connect(self.toggle_enable_processing)
        sig_processing_layout.addWidget(self.lbl_enable_processing)
        sig_processing_layout.addWidget(self.btn_enable_processing)
        
        # Noise label
        self.lbl_noise = QLabel("Noise: -")
        sig_processing_layout.addWidget(self.lbl_noise)

        # Baseline correction (0 is disabled)
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

        # Smoothing
        self.lbl_smoothing = QLabel("Smoothing")
        self.smoothing_help_button = QPushButton()
        self.smoothing_help_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation)
        )
        self.smoothing_help_button.setFixedSize(22, 22)
        self.smoothing_help_button.clicked.connect(lambda: show_smoothing_help(self))

        # (Window length)
        self.processor.set_smoothing_wd(2)
        self.edit_smoothing_wd = QLineEdit(str(self.processor.smoothing_wd))

        self.edit_smoothing_wd.editingFinished.connect(
            self.update_smoothing_wd
        )

        # (Polynomial order)
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

        # Peak height factor
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

        # Prominence
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

        # Min peak distance
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

        # Find peaks
        self.btn_find_peaks = QPushButton("Find peaks")
        self.btn_find_peaks.clicked.connect(self.toggle_find_peaks)
        sig_processing_layout.addWidget(self.btn_find_peaks)

        # Show peak labels
        self.btn_peak_labels = QPushButton("Show peak labels")
        self.btn_peak_labels.clicked.connect(self.toggle_peak_labels)
        sig_processing_layout.addWidget(self.btn_peak_labels)
        
        # Group
        group_sig_processing.setLayout(sig_processing_layout)

        # Construct the left panel
        control_layout.addWidget(group_conn)
        control_layout.addWidget(group_cmds)
        control_layout.addWidget(group_acq)
        control_layout.addWidget(group_sig_processing)
        control_layout.addStretch()

        ##########################################################################
        # RIGHT PANEL (GRAPH)
        #########################################################################
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.plot_widget = pg.PlotWidget(title="Spectrum in Real Time")
        self.plot_widget.setLabel('left', 'Intensity (ADC)', units='')
        self.plot_widget.setLabel('bottom', 'Pixel', units='')
        self.plot_widget.setYRange(0, 4200) # Límite del ADC
        self.plot_widget.setXRange(0, 3694)
        self.plot_widget.showGrid(x=True, y=True)
        
        self.curve = self.plot_widget.plot(pen=pg.mkPen('b', width=2)) # Curva azul

        self.peaks_curve = self.plot_widget.plot(
            pen=None,
            symbol='o',
            symbolSize=8,
            symbolBrush='r'
        )

        main_layout.addWidget(control_widget)
        main_layout.addWidget(self.plot_widget)

    ###########################################################################
    # DEVICE CONNECTION
    ###########################################################################
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

    ############################################################################
    # COMMANDS
    ############################################################################
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

    ############################################################################
    # UPDATERS
    ############################################################################
    # ADQUISITION BUTTON

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

    # ENABLE/DISABLE DATA PROCESSING BUTTON
    def toggle_enable_processing(self):
        enabled = self.btn_enable_processing.text() == "Enable"

        if enabled:
            self.btn_enable_processing.setText("Disable")
        else:
            self.btn_enable_processing.setText("Enable")

        self.processor.set_enable_processing(enabled)
    
    # BASELINE
    def update_baseline(self):
        val = float(self.edit_baseline_lambda.text())
        self.processor.set_baseline_lambda(val)
        self.edit_baseline_lambda.setText(f"{self.processor.baseline_lambda:.1e}")

    # SMOOTHING (WD)
    def update_smoothing_wd(self):
        val = int(self.edit_smoothing_wd.text())
        self.processor.set_smoothing_wd(val)    
        self.edit_smoothing_wd.setText(str(self.processor.smoothing_wd))
    
    # SMOOTHING (POLYORDER)
    def update_smoothing_poly(self):
        val = int(self.edit_smoothing_poly.text())
        self.processor.set_smoothing_poly(val)  
        self.edit_smoothing_poly.setText(str(self.processor.smoothing_poly))

    # PEAK HEIGHT FACTOR
    def update_peak_height_factor(self):
        val = float(self.edit_peak_height_factor.text())
        self.processor.set_peak_height_factor(val)
        self.edit_peak_height_factor.setText(f"{self.processor.peak_height_factor:.2f}")

    # PEAK PROMINENCE
    def update_peak_prominence(self):
        val = float(self.edit_peak_prominence.text())
        self.processor.set_peak_prominence(val)
        self.edit_peak_prominence.setText(f"{self.processor.peak_prominence:.2f}")


    # MIN DISTANCE
    def update_peak_min_distance(self):
        val = int(self.edit_peak_min_distance.text())
        self.processor.set_peak_min_distance(val)
        self.edit_peak_min_distance.setText(str(self.processor.peak_min_distance))

    # TOGGLE PEAK FINDING
    def toggle_find_peaks(self):
        self.peaks_enabled = not self.peaks_enabled

        if self.peaks_enabled:
            self.btn_find_peaks.setText("Hide peaks")
            self.find_and_plot_peaks()
        else:
            self.btn_find_peaks.setText("Find peaks")
            self.peaks_curve.setData([], [])

    # TOGGLE PEAK LABELS
    def toggle_peak_labels(self):
        self.peak_labels_enabled = not self.peak_labels_enabled

        if self.peak_labels_enabled:
            self.btn_peak_labels.setText("Hide peak labels")
            if self.peaks_enabled:
                self.find_and_plot_peaks()
        else:
            self.btn_peak_labels.setText("Show peak labels")
            self.clear_peak_labels()

    def clear_peak_labels(self):
        for label in self.peak_labels:
            self.plot_widget.removeItem(label)
        self.peak_labels.clear()

    # UPDATE PLOT
    @Slot(np.ndarray)
    def update_plot(self, data):
        processed_data, _ = self.processor.process(data)

        self.processor.last_processed_data = processed_data
        self.curve.setData(processed_data)

        self.lbl_noise.setText(
            f"Noise: {self.processor.last_noise:.2f} ADC counts"
        )

        if self.peaks_enabled:
            self.find_and_plot_peaks()

    # FIND AND PLOT PEAKS
    def find_and_plot_peaks(self):
        if self.processor.last_processed_data is None:
            return

        peaks = self.processor.find_peaks(self.processor.last_processed_data)

        self.clear_peak_labels()

        if len(peaks) > 0:
            x_peaks = peaks
            y_peaks = self.processor.last_processed_data[peaks]
            self.peaks_curve.setData(x_peaks, y_peaks)

            if self.peak_labels_enabled:
                for x, y in zip(x_peaks, y_peaks):
                    label = pg.TextItem(
                        text=f"{x}, {y:.0f}",
                        color=(30, 30, 30),
                        fill=pg.mkBrush(255, 255, 255, 255),
                        border=pg.mkPen((120, 120, 120)),
                        anchor=(0.5, 1.2),
                    )
                    label.setPos(x, y)
                    self.plot_widget.addItem(label)
                    self.peak_labels.append(label)
        else:
            self.peaks_curve.setData([], [])

    # CLOSE EVENT
    def closeEvent(self, event):
        if self.worker and self.worker.running:
            self.worker.stop()
        if self.dev:
            self.dev.close()
        event.accept()