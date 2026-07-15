from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QComboBox, QDialog,
                               QHBoxLayout, QPushButton, QLabel, QLineEdit, QCheckBox,
                               QSpinBox, QGroupBox, QMessageBox, QLineEdit, QDialogButtonBox)
from PySide6.QtCore import Slot
from signalprocessor import SignalProcessor
from spectrometer import SpectrometerDriver, SpectrometerDriverMock
from adquisition import AcquisitionThread
from help_messages import *
import pyqtgraph as pg
from serial.tools import list_ports
import numpy as np   
from signalprocessor import (DARK_N_SAMPLES_DEFAULT, SPIKE_WINDOW_DEFAULT, SPIKE_T_MULTIPLIER_DEFAULT, N_SPECTRA_DEFAULT,
                             FILTER_WINDOW_DEFAULT, FILTER_POLY_ORDER_DEFAULT, BASELINE_LAMBDA_DEFAULT, BASELINE_DIFF_ORDER_DEFAULT,
                             BASELINE_ITERATIONS_DEFAULT, BASELINE_TOLERANCE_DEFAULT, ENABLE_DARK_SUBTRACTION_DEFAULT, ENABLE_SPIKE_CORRECTION_DEFAULT,
                             ENABLE_FILTERING_DEFAULT, ENABLE_BASELINE_CORRECTION_DEFAULT, ENABLE_NORMALIZATION_DEFAULT)

class ProcessingConfigDialog(QDialog):
    def __init__(self, processor, parent=None):
        super().__init__(parent)
        self.processor = processor
        
        self.setWindowTitle("Processing Configuration")
        layout = QVBoxLayout(self)

        # Dark spectrum
        self.line_dark_n_samples = QLineEdit()
        self.line_dark_n_samples.setText(str(getattr(self.processor, "dark_n_samples", DARK_N_SAMPLES_DEFAULT)))

        row_dark = QHBoxLayout()
        row_dark.addWidget(QLabel("Dark samples:"))
        row_dark.addWidget(self.line_dark_n_samples)
        layout.addLayout(row_dark)

        # Spike window
        self.line_spike_window = QLineEdit()
        self.line_spike_window.setText(str(getattr(self.processor, "spike_window", SPIKE_WINDOW_DEFAULT)))

        row_spike = QHBoxLayout()
        row_spike.addWidget(QLabel("Spike window:"))
        row_spike.addWidget(self.line_spike_window)
        layout.addLayout(row_spike)

        # Spike T multiplier
        self.line_spike_T_multiplier = QLineEdit()
        self.line_spike_T_multiplier.setText(str(getattr(self.processor, "spike_T_multiplier", SPIKE_T_MULTIPLIER_DEFAULT)))
        
        row_spike_T = QHBoxLayout()
        row_spike_T.addWidget(QLabel("Spike T multiplier:"))
        row_spike_T.addWidget(self.line_spike_T_multiplier)
        layout.addLayout(row_spike_T)

        # Number of spectra
        self.line_n_spectra = QLineEdit()
        self.line_n_spectra.setText(str(getattr(self.processor, "n_spectra", N_SPECTRA_DEFAULT)))

        row_n_spectra = QHBoxLayout()
        row_n_spectra.addWidget(QLabel("Number of spectra:"))
        row_n_spectra.addWidget(self.line_n_spectra)
        layout.addLayout(row_n_spectra)

        # Filter window
        self.line_filter_window = QLineEdit()
        self.line_filter_window.setText(str(getattr(self.processor, "filter_window", FILTER_WINDOW_DEFAULT)))
        
        row_filter_window = QHBoxLayout()
        row_filter_window.addWidget(QLabel("Filter window:"))
        row_filter_window.addWidget(self.line_filter_window)
        layout.addLayout(row_filter_window)

        # Filter polynomial order
        self.line_filter_poly_order = QLineEdit()
        self.line_filter_poly_order.setText(str(getattr(self.processor, "filter_poly_order", FILTER_POLY_ORDER_DEFAULT)))
        
        row_filter_poly = QHBoxLayout()
        row_filter_poly.addWidget(QLabel("Filter polynomial order:"))
        row_filter_poly.addWidget(self.line_filter_poly_order)
        layout.addLayout(row_filter_poly)
        
        # Baseline lambda
        self.line_baseline_lambda = QLineEdit()
        self.line_baseline_lambda.setText(str(getattr(self.processor, "baseline_lambda", BASELINE_LAMBDA_DEFAULT)))

        row_baseline_lambda = QHBoxLayout()
        row_baseline_lambda.addWidget(QLabel("Baseline lambda:"))
        row_baseline_lambda.addWidget(self.line_baseline_lambda)
        layout.addLayout(row_baseline_lambda)

        # Baseline diff order
        self.line_baseline_diff_order = QLineEdit()
        self.line_baseline_diff_order.setText(str(getattr(self.processor, "baseline_diff_order", BASELINE_DIFF_ORDER_DEFAULT)))

        row_baseline_diff = QHBoxLayout()
        row_baseline_diff.addWidget(QLabel("Baseline diff order:"))
        row_baseline_diff.addWidget(self.line_baseline_diff_order)
        layout.addLayout(row_baseline_diff)

        # Baseline iterations
        self.line_baseline_iterations = QLineEdit()
        self.line_baseline_iterations.setText(str(getattr(self.processor, "baseline_iterations", BASELINE_ITERATIONS_DEFAULT)))

        row_baseline_iter = QHBoxLayout()
        row_baseline_iter.addWidget(QLabel("Baseline iterations:"))
        row_baseline_iter.addWidget(self.line_baseline_iterations)
        layout.addLayout(row_baseline_iter)

        # Baseline tolerance
        self.line_baseline_tolerance = QLineEdit()
        self.line_baseline_tolerance.setText(str(getattr(self.processor, "baseline_tolerance", BASELINE_TOLERANCE_DEFAULT)))

        row_baseline_tol = QHBoxLayout()
        row_baseline_tol.addWidget(QLabel("Baseline tolerance:"))
        row_baseline_tol.addWidget(self.line_baseline_tolerance)
        layout.addLayout(row_baseline_tol)

        # Checkboxes for enabling/disabling processing steps
        self.checkbox_dark_subtraction = QCheckBox("Enable dark subtraction")
        self.checkbox_dark_subtraction.setChecked(getattr(self.processor, "enable_dark_subtraction", ENABLE_DARK_SUBTRACTION_DEFAULT))
        layout.addWidget(self.checkbox_dark_subtraction)

        self.checkbox_spike_correction = QCheckBox("Enable spike correction")
        self.checkbox_spike_correction.setChecked(getattr(self.processor, "enable_spike_correction", ENABLE_SPIKE_CORRECTION_DEFAULT))
        layout.addWidget(self.checkbox_spike_correction)

        self.checkbox_filtering = QCheckBox("Enable filtering")
        self.checkbox_filtering.setChecked(getattr(self.processor, "enable_filtering", ENABLE_FILTERING_DEFAULT))
        layout.addWidget(self.checkbox_filtering)

        self.checkbox_baseline_correction = QCheckBox("Enable baseline correction")
        self.checkbox_baseline_correction.setChecked(getattr(self.processor, "enable_baseline_correction", ENABLE_BASELINE_CORRECTION_DEFAULT))
        layout.addWidget(self.checkbox_baseline_correction)

        self.checkbox_normalization = QCheckBox("Enable normalization")
        self.checkbox_normalization.setChecked(getattr(self.processor, "enable_normalization", ENABLE_NORMALIZATION_DEFAULT))
        layout.addWidget(self.checkbox_normalization)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


    def accept(self):
        self.processor.set_dark_n_samples(self.line_dark_n_samples.text())
        self.line_dark_n_samples.setText(str(self.processor.dark_n_samples))

        self.processor.set_spike_window(self.line_spike_window.text())
        self.line_spike_window.setText(str(self.processor.spike_window))

        self.processor.set_spike_T_multiplier(self.line_spike_T_multiplier.text())
        self.line_spike_T_multiplier.setText(str(self.processor.spike_T_multiplier))

        self.processor.set_n_spectra(self.line_n_spectra.text())
        self.line_n_spectra.setText(str(self.processor.n_spectra))

        self.processor.set_filter_window(self.line_filter_window.text())
        self.line_filter_window.setText(str(self.processor.filter_window))

        self.processor.set_filter_poly_order(self.line_filter_poly_order.text())
        self.line_filter_poly_order.setText(str(self.processor.filter_poly_order))

        self.processor.set_baseline_lambda(self.line_baseline_lambda.text())
        self.line_baseline_lambda.setText(str(self.processor.baseline_lambda))

        self.processor.set_baseline_diff_order(self.line_baseline_diff_order.text())
        self.line_baseline_diff_order.setText(str(self.processor.baseline_diff_order))

        self.processor.set_baseline_iterations(self.line_baseline_iterations.text())
        self.line_baseline_iterations.setText(str(self.processor.baseline_iterations))

        self.processor.set_baseline_tolerance(self.line_baseline_tolerance.text())
        self.line_baseline_tolerance.setText(str(self.processor.baseline_tolerance))

        self.processor.set_enable_dark_subtraction(self.checkbox_dark_subtraction.isChecked())
        self.processor.set_enable_spike_correction(self.checkbox_spike_correction.isChecked())
        self.processor.set_enable_filtering(self.checkbox_filtering.isChecked())
        self.processor.set_enable_baseline_correction(self.checkbox_baseline_correction.isChecked())
        self.processor.set_enable_normalization(self.checkbox_normalization.isChecked())

        super().accept()
        

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

        port_layout = QHBoxLayout()

        self.port_input = QComboBox()
        self.btn_refresh_ports = QPushButton("Refresh")
        self.btn_refresh_ports.clicked.connect(self.refresh_ports)

        port_layout.addWidget(self.port_input)
        port_layout.addWidget(self.btn_refresh_ports)

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clicked.connect(self.connect_device)

        conn_layout.addWidget(QLabel("Serial port:"))
        conn_layout.addLayout(port_layout)
        conn_layout.addWidget(self.btn_connect)

        group_conn.setLayout(conn_layout)
        self.refresh_ports()

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
        #self.spin_accum = QSpinBox()
        #self.spin_accum.setRange(1, 1000)
        #self.spin_accum.setValue(50)
        #self.btn_accum = QPushButton("Set Accumulations")
        #self.btn_accum.clicked.connect(lambda: self.send_cmd('accum'))
        #cmds_layout.addWidget(self.spin_accum)
        #cmds_layout.addWidget(self.btn_accum)

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

        # Toggle LED
        self.btn_toggle_led = QPushButton("Toggle LED")
        self.btn_toggle_led.clicked.connect(lambda: self.send_cmd('toggle_led'))
        cmds_layout.addWidget(self.btn_toggle_led)
        
        # Find peaks
        self.btn_find_peaks = QPushButton("Find Peaks")
        self.btn_find_peaks.clicked.connect(lambda: self.toggle_find_peaks())
        cmds_layout.addWidget(self.btn_find_peaks)
    

        # GROUP    
        group_cmds.setLayout(cmds_layout)

        ########################################################################
        # ADQUISITION GROUP
        group_acq = QGroupBox("Continuous Acquisition")
        acq_layout = QVBoxLayout()
        self.btn_start = QPushButton("Start Reading")
        self.btn_start.setStyleSheet("background-color: #ccffcc;")
        self.btn_start.clicked.connect(self.toggle_acquisition)
        self.btn_start.setEnabled(False) # Deshabilitado hasta conectar
        acq_layout.addWidget(self.btn_start)

        self.btn_dark = QPushButton("Capture Dark")
        self.btn_dark.setEnabled(False)
        self.btn_dark.clicked.connect(self.start_dark_capture)

        acq_layout.addWidget(self.btn_dark)
        self.lbl_dark_status = QLabel("Dark: not acquired")
        acq_layout.addWidget(self.lbl_dark_status)

        group_acq.setLayout(acq_layout)

        # SIGNAL PROCESSING GROUP
        group_processing = QGroupBox("Processing Configuration")
        processing_layout = QVBoxLayout()

        self.lbl_dark_n_samples = QLabel()

        self.lbl_spike_window = QLabel()
        self.lbl_spike_T_multiplier = QLabel()

        self.lbl_n_spectra = QLabel()

        self.lbl_filter_window = QLabel()
        self.lbl_filter_poly_order = QLabel()

        self.lbl_baseline_lambda = QLabel()
        self.lbl_baseline_diff_order = QLabel()
        self.lbl_baseline_iterations = QLabel()
        self.lbl_baseline_tolerance = QLabel()

        self.lbl_enable_dark_subtraction = QLabel()
        self.lbl_enable_spike_correction = QLabel()
        self.lbl_enable_filtering = QLabel()
        self.lbl_enable_baseline_correction = QLabel()
        self.lbl_enable_normalization = QLabel()

        processing_layout.addWidget(self.lbl_dark_n_samples)
        processing_layout.addWidget(self.lbl_spike_window)
        processing_layout.addWidget(self.lbl_spike_T_multiplier)
        processing_layout.addWidget(self.lbl_n_spectra)

        processing_layout.addWidget(self.lbl_filter_window)
        processing_layout.addWidget(self.lbl_filter_poly_order)

        processing_layout.addWidget(self.lbl_baseline_lambda)
        processing_layout.addWidget(self.lbl_baseline_diff_order)
        processing_layout.addWidget(self.lbl_baseline_iterations)
        processing_layout.addWidget(self.lbl_baseline_tolerance)

        processing_layout.addWidget(self.lbl_enable_dark_subtraction)
        processing_layout.addWidget(self.lbl_enable_spike_correction)
        processing_layout.addWidget(self.lbl_enable_filtering)
        processing_layout.addWidget(self.lbl_enable_baseline_correction)
        processing_layout.addWidget(self.lbl_enable_normalization)

        self.update_processing_config_labels()

        self.btn_processing_config = QPushButton("Settings")
        self.btn_processing_config.clicked.connect(self.open_processing_config)
        processing_layout.addWidget(self.btn_processing_config)

        self.btn_delete_config = QPushButton("Delete Configuration")
        self.btn_delete_config.clicked.connect(self.delete_configuration)
        processing_layout.addWidget(self.btn_delete_config)

        # Group
        group_processing.setLayout(processing_layout)

        # Construct the left panel
        control_layout.addWidget(group_conn)
        control_layout.addWidget(group_cmds)
        control_layout.addWidget(group_acq)
        control_layout.addWidget(group_processing)
        control_layout.addStretch()

        ##########################################################################
        # RIGHT PANEL (GRAPH)
        #########################################################################
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.plot_widget = pg.PlotWidget(title="Spectrum in Real Time")
        self.plot_widget.setLabel('left', 'Intensity (ADC)', units='')
        self.plot_widget.setLabel('bottom', 'Pixel', units='')
        self.plot_widget.setYRange(-50, 4200) # Límite del ADC
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

    def delete_configuration(self):
        self.processor.delete_config()
        self.update_processing_config_labels()
        QMessageBox.information(self, "Configuration Deleted", "The configuration file has been deleted and defaults have been restored.")

    def update_processing_config_labels(self):
        self.lbl_dark_n_samples.setText(
            f"Dark samples: {self.processor.dark_n_samples}"
        )
        self.lbl_spike_window.setText(
            f"Spike window: {self.processor.spike_window}"
        )
        self.lbl_spike_T_multiplier.setText(
            f"Spike T multiplier: {self.processor.spike_T_multiplier}"
        )
        self.lbl_n_spectra.setText(
            f"Number of spectra: {self.processor.n_spectra}"
        )

        self.lbl_filter_window.setText(
            f"Filter window: {self.processor.filter_window}"
        )
        self.lbl_filter_poly_order.setText(
            f"Filter polynomial order: {self.processor.filter_poly_order}"
        )

        self.lbl_baseline_lambda.setText(
            f"Baseline lambda: {self.processor.baseline_lambda:.2e}"
        )
        self.lbl_baseline_diff_order.setText(
            f"Baseline diff order: {self.processor.baseline_diff_order}"
        )
        self.lbl_baseline_iterations.setText(
            f"Baseline iterations: {self.processor.baseline_iterations}"
        )
        self.lbl_baseline_tolerance.setText(
            f"Baseline tolerance: {self.processor.baseline_tolerance:.2e}"
        )

        self.lbl_enable_dark_subtraction.setText(
            f"Dark subtraction: {self._enabled_text(self.processor.enable_dark_subtraction)}"
        )
        self.lbl_enable_spike_correction.setText(
            f"Spike correction: {self._enabled_text(self.processor.enable_spike_correction)}"
        )
        self.lbl_enable_filtering.setText(
            f"Filtering: {self._enabled_text(self.processor.enable_filtering)}"
        )
        self.lbl_enable_baseline_correction.setText(
            f"Baseline correction: {self._enabled_text(self.processor.enable_baseline_correction)}"
        )
        self.lbl_enable_normalization.setText(
            f"Normalization: {self._enabled_text(self.processor.enable_normalization)}"
        )

    @staticmethod
    def _enabled_text(enabled):
        return "Enabled" if enabled else "Disabled"
    ############################################################################
    def open_processing_config(self):
        if self.worker and self.worker.capturing_dark:
            QMessageBox.warning(
                self,
                "Dark acquisition",
                "Wait until the dark acquisition is complete.",
            )
            return
        
        dialog = ProcessingConfigDialog(self.processor, self)

        if dialog.exec() == QDialog.Accepted:
            self.update_processing_config_labels()
            self.processor.spectra_buffer.clear()  # Clear the buffer to avoid using old data
            self.processor.save_config()

    ###########################################################################
    # DEVICE CONNECTION
    ###########################################################################
    def connect_device(self):
        port = self.port_input.currentData()
        if port is None:
            QMessageBox.warning(self, "Connection error", "No serial port selected.")
            return
        
        try:
            if port == "__MOCK__":
                self.dev = SpectrometerDriverMock()
            else:
                self.dev = SpectrometerDriver(port=port, timeout=0.25)
            self.btn_connect.setText("Connected")
            self.btn_connect.setStyleSheet("background-color: #ccffcc;")
            self.btn_connect.setEnabled(False)
            self.port_input.setEnabled(False)
            self.btn_start.setEnabled(True)
            self.btn_start.setEnabled(True)
            self.btn_dark.setEnabled(True)
            
            # Inicializar el hilo (pero no arrancarlo aún)
            self.worker = AcquisitionThread(
                driver=self.dev,
                processor=self.processor,
            )

            self.worker.data_ready.connect(self.update_plot)
            self.worker.dark_progress.connect(self.update_dark_progress)
            self.worker.dark_finished.connect(self.dark_capture_finished)
            self.worker.acquisition_error.connect(self.show_acquisition_error)
            
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
        elif cmd_type == 'toggle_led':
            self.dev.toggle_led()

    def start_dark_capture(self):
        if self.worker is None:
            return

        if not self.worker.isRunning():
            QMessageBox.warning(
                self,
                "Dark acquisition",
                "Start the acquisition before capturing the dark spectrum.",
            )
            return

        if self.worker.capturing_dark:
            return

        self.processor.spectra_buffer.clear()

        self.worker.start_dark_capture()

        self.btn_dark.setEnabled(False)
        self.btn_start.setEnabled(False)

        self.lbl_dark_status.setText(
            f"Dark: 0 / {self.processor.dark_n_samples}"
        )

    def update_dark_progress(self, current, total):
        self.lbl_dark_status.setText(
            f"Dark: {current} / {total}"
        )

    def dark_capture_finished(self):
        self.lbl_dark_status.setText(
            f"Dark acquired: {len(self.processor.dark_buffer)} samples"
        )

        self.btn_dark.setEnabled(True)
        self.btn_start.setEnabled(True)

        QMessageBox.information(
            self,
            "Dark acquisition",
            (
                f"Dark spectrum acquired successfully.\n\n"
                f"Samples: {len(self.processor.dark_buffer)}"
            ),
        )
        ############################################################################
    # UPDATERS
    ############################################################################
    # ADQUISITION BUTTON
    def show_acquisition_error(self, message):
        print(f"Acquisition error: {message}")

    def toggle_acquisition(self):
        if self.worker is None:
            return

        if not self.worker.isRunning():
            self.processor.spectra_buffer.clear()

            self.worker.start()

            self.btn_start.setText("Stop Reading")
            self.btn_start.setStyleSheet("background-color: #ffcccc;")

            self.btn_processing_config.setEnabled(False)
            self.btn_delete_config.setEnabled(False)

        else:
            self.worker.stop()

            self.processor.spectra_buffer.clear()

            self.btn_start.setText("Start Reading")
            self.btn_start.setStyleSheet("background-color: #ccffcc;")

            self.btn_processing_config.setEnabled(True)
            self.btn_delete_config.setEnabled(True)


    @Slot(str)
    def on_acquisition_error(self, message):
        self.btn_start.setText("Start Reading")
        self.btn_start.setStyleSheet("background-color: #ccffcc;")
        self.btn_processing_config.setEnabled(True)
        self.btn_delete_config.setEnabled(True)
        QMessageBox.critical(self, "Acquisition error", message)

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
    def update_plot(self, processed_data):
        if processed_data is None:
            return

        self.processor.last_processed_data = processed_data
        self.curve.setData(processed_data)

        if self.processor.enable_normalization:
            self.plot_widget.setYRange(-0.5, 1.05)
        else:
            self.plot_widget.setYRange(-50, 4200) # Límite del ADC

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

    # REFRESH PORTS
    def refresh_ports(self):
        current = self.port_input.currentData()
        self.port_input.clear()

        ports = list(list_ports.comports())

        # The mock must always be available, even with no serial hardware.
        self.port_input.addItem("Mock (synthetic spectrum)", "__MOCK__")

        for port in ports:
            self.port_input.addItem(f"{port.device} ({port.description})", port.device)

        self.btn_connect.setEnabled(True)
        for i in range(self.port_input.count()):
            if self.port_input.itemData(i) == current:
                self.port_input.setCurrentIndex(i)
                break

    # CLOSE EVENT
    def closeEvent(self, event):
        if self.worker and self.worker.running:
            self.worker.stop()
        if self.dev:
            self.dev.close()
        event.accept()