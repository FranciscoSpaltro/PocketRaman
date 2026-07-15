from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QComboBox, QDialog, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QCheckBox, QSpinBox, QGroupBox, QMessageBox, QDialogButtonBox,
    QFormLayout, QScrollArea, QFileDialog, QSlider,)
from datetime import datetime
from PySide6.QtCore import Qt, Slot
from signalprocessor import SignalProcessor
from spectrometer import SpectrometerDriver, SpectrometerDriverMock
from adquisition import AcquisitionThread
from help_messages import *
import pyqtgraph as pg
from serial.tools import list_ports
import numpy as np   
from pathlib import Path
import json
from signalprocessor import (USEFUL_CCD_PIXELS)
      
class CalibrationDialog(QDialog):
    def __init__(self, coefficients=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Wavelength Calibration")
        self.setMinimumWidth(380)

        self.coefficients = None

        layout = QVBoxLayout(self)

        equation_label = QLabel(
            "λ(x) = a₂·x² + a₁·x + a₀"
        )
        layout.addWidget(equation_label)

        form_layout = QFormLayout()

        self.edit_a2 = QLineEdit()
        self.edit_a1 = QLineEdit()
        self.edit_a0 = QLineEdit()

        self.edit_a2.setPlaceholderText("Quadratic coefficient")
        self.edit_a1.setPlaceholderText("Linear coefficient")
        self.edit_a0.setPlaceholderText("Constant coefficient")

        form_layout.addRow("a₂:", self.edit_a2)
        form_layout.addRow("a₁:", self.edit_a1)
        form_layout.addRow("a₀:", self.edit_a0)

        layout.addLayout(form_layout)

        if coefficients is not None:
            self.edit_a2.setText(f"{coefficients[0]:.12g}")
            self.edit_a1.setText(f"{coefficients[1]:.12g}")
            self.edit_a0.setText(f"{coefficients[2]:.12g}")

        self.btn_pixel_scale = QPushButton("Use pixel scale")
        self.btn_pixel_scale.clicked.connect(
            self.use_pixel_scale
        )
        layout.addWidget(self.btn_pixel_scale)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok |
            QDialogButtonBox.Cancel
        )

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

    def accept(self):
        texts = [
            self.edit_a2.text().strip(),
            self.edit_a1.text().strip(),
            self.edit_a0.text().strip(),
        ]

        if not any(texts):
            QMessageBox.warning(
                self,
                "Calibration error",
                "Enter at least one calibration coefficient.",
            )
            return

        try:
            a2 = float(texts[0]) if texts[0] else 0.0
            a1 = float(texts[1]) if texts[1] else 0.0
            a0 = float(texts[2]) if texts[2] else 0.0

        except ValueError:
            QMessageBox.warning(
                self,
                "Calibration error",
                "Calibration coefficients must be valid numbers.",
            )
            return

        if a2 == 0.0 and a1 == 0.0:
            QMessageBox.warning(
                self,
                "Calibration error",
                "At least a₁ or a₂ must be different from zero.",
            )
            return

        self.coefficients = np.array(
            [a2, a1, a0],
            dtype=float,
        )

        super().accept()

    def use_pixel_scale(self):
        self.coefficients = None
        super().accept()

###############################################################################
###############################################################################
        
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

        self.is_recording = False
        self.recorded_raw_spectra = []

        self.imported_raw_spectra = None
        self.data_source = "live"

        # None significa que el eje X se muestra en píxeles.
        # Si hay calibración, contiene [a2, a1, a0].
        self.wavelength_coefficients = None

        self.calibration_path = (
            Path(__file__).parent / "calibration.json"
        )

        self.setup_ui()
        self.load_wavelength_calibration()

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
        control_widget.setMinimumWidth(245)
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


        ########################################################################
        # SIGNAL PROCESSING GROUP
        group_processing = QGroupBox("Processing")
        processing_layout = QVBoxLayout()

        processing_form = QFormLayout()
        processing_form.setFieldGrowthPolicy(
            QFormLayout.AllNonFixedFieldsGrow
        )

        # ---------------------------------------------------------------------
        # Dark subtraction
        # ---------------------------------------------------------------------
        self.checkbox_dark_subtraction = QCheckBox()
        self.checkbox_dark_subtraction.setChecked(
            self.processor.enable_dark_subtraction
        )
        self.checkbox_dark_subtraction.toggled.connect(
            lambda checked: self.update_processing_toggle(
                self.processor.set_enable_dark_subtraction,
                checked,
            )
        )
        processing_form.addRow(
            "Dark subtraction:",
            self.checkbox_dark_subtraction,
        )

        self.edit_dark_n_samples = QLineEdit(
            str(self.processor.dark_n_samples)
        )
        self.edit_dark_n_samples.editingFinished.connect(
            lambda: self.update_processing_value(
                self.edit_dark_n_samples,
                self.processor.set_dark_n_samples,
                "dark_n_samples",
            )
        )
        processing_form.addRow(
            "Dark samples:",
            self.edit_dark_n_samples,
        )

        # ---------------------------------------------------------------------
        # Spike correction
        # ---------------------------------------------------------------------
        self.checkbox_spike_correction = QCheckBox()
        self.checkbox_spike_correction.setChecked(
            self.processor.enable_spike_correction
        )
        self.checkbox_spike_correction.toggled.connect(
            lambda checked: self.update_processing_toggle(
                self.processor.set_enable_spike_correction,
                checked,
            )
        )
        processing_form.addRow(
            "Spike correction:",
            self.checkbox_spike_correction,
        )

        self.edit_spike_window = QLineEdit(
            str(self.processor.spike_window)
        )
        self.edit_spike_window.editingFinished.connect(
            lambda: self.update_processing_value(
                self.edit_spike_window,
                self.processor.set_spike_window,
                "spike_window",
            )
        )
        processing_form.addRow(
            "Spike window:",
            self.edit_spike_window,
        )

        self.edit_spike_multiplier = QLineEdit(
            str(self.processor.spike_T_multiplier)
        )
        self.edit_spike_multiplier.editingFinished.connect(
            lambda: self.update_processing_value(
                self.edit_spike_multiplier,
                self.processor.set_spike_T_multiplier,
                "spike_T_multiplier",
            )
        )
        processing_form.addRow(
            "Spike threshold:",
            self.edit_spike_multiplier,
        )

        # ---------------------------------------------------------------------
        # Spectrum averaging
        # ---------------------------------------------------------------------
        self.edit_n_spectra = QLineEdit(
            str(self.processor.n_spectra)
        )
        self.edit_n_spectra.editingFinished.connect(
            lambda: self.update_processing_value(
                self.edit_n_spectra,
                self.processor.set_n_spectra,
                "n_spectra",
            )
        )
        processing_form.addRow(
            "Spectra to average:",
            self.edit_n_spectra,
        )

        # ---------------------------------------------------------------------
        # Savitzky-Golay filtering
        # ---------------------------------------------------------------------
        self.checkbox_filtering = QCheckBox()
        self.checkbox_filtering.setChecked(
            self.processor.enable_filtering
        )
        self.checkbox_filtering.toggled.connect(
            lambda checked: self.update_processing_toggle(
                self.processor.set_enable_filtering,
                checked,
            )
        )
        processing_form.addRow(
            "Filtering:",
            self.checkbox_filtering,
        )

        self.edit_filter_window = QLineEdit(
            str(self.processor.filter_window)
        )
        self.edit_filter_window.editingFinished.connect(
            lambda: self.update_processing_value(
                self.edit_filter_window,
                self.processor.set_filter_window,
                "filter_window",
            )
        )
        processing_form.addRow(
            "Filter window:",
            self.edit_filter_window,
        )

        self.edit_filter_poly_order = QLineEdit(
            str(self.processor.filter_poly_order)
        )
        self.edit_filter_poly_order.editingFinished.connect(
            lambda: self.update_processing_value(
                self.edit_filter_poly_order,
                self.processor.set_filter_poly_order,
                "filter_poly_order",
            )
        )
        processing_form.addRow(
            "Polynomial order:",
            self.edit_filter_poly_order,
        )

        # ---------------------------------------------------------------------
        # Baseline correction
        # ---------------------------------------------------------------------
        self.checkbox_baseline_correction = QCheckBox()
        self.checkbox_baseline_correction.setChecked(
            self.processor.enable_baseline_correction
        )
        self.checkbox_baseline_correction.toggled.connect(
            lambda checked: self.update_processing_toggle(
                self.processor.set_enable_baseline_correction,
                checked,
            )
        )
        processing_form.addRow(
            "Baseline correction:",
            self.checkbox_baseline_correction,
        )

        self.edit_baseline_lambda = QLineEdit(
            f"{self.processor.baseline_lambda:.2e}"
        )
        self.edit_baseline_lambda.editingFinished.connect(
            lambda: self.update_processing_value(
                self.edit_baseline_lambda,
                self.processor.set_baseline_lambda,
                "baseline_lambda",
                lambda value: f"{value:.2e}",
            )
        )
        processing_form.addRow(
            "Baseline lambda:",
            self.edit_baseline_lambda,
        )

        self.edit_baseline_diff_order = QLineEdit(
            str(self.processor.baseline_diff_order)
        )
        self.edit_baseline_diff_order.editingFinished.connect(
            lambda: self.update_processing_value(
                self.edit_baseline_diff_order,
                self.processor.set_baseline_diff_order,
                "baseline_diff_order",
            )
        )
        processing_form.addRow(
            "Difference order:",
            self.edit_baseline_diff_order,
        )

        self.edit_baseline_iterations = QLineEdit(
            str(self.processor.baseline_iterations)
        )
        self.edit_baseline_iterations.editingFinished.connect(
            lambda: self.update_processing_value(
                self.edit_baseline_iterations,
                self.processor.set_baseline_iterations,
                "baseline_iterations",
            )
        )
        processing_form.addRow(
            "Iterations:",
            self.edit_baseline_iterations,
        )

        self.edit_baseline_tolerance = QLineEdit(
            f"{self.processor.baseline_tolerance:.2e}"
        )
        self.edit_baseline_tolerance.editingFinished.connect(
            lambda: self.update_processing_value(
                self.edit_baseline_tolerance,
                self.processor.set_baseline_tolerance,
                "baseline_tolerance",
                lambda value: f"{value:.2e}",
            )
        )
        processing_form.addRow(
            "Tolerance:",
            self.edit_baseline_tolerance,
        )

        # ---------------------------------------------------------------------
        # Normalization
        # ---------------------------------------------------------------------
        self.checkbox_normalization = QCheckBox()
        self.checkbox_normalization.setChecked(
            self.processor.enable_normalization
        )
        self.checkbox_normalization.toggled.connect(
            lambda checked: self.update_processing_toggle(
                self.processor.set_enable_normalization,
                checked,
            )
        )
        processing_form.addRow(
            "Normalization:",
            self.checkbox_normalization,
        )

        processing_layout.addLayout(processing_form)

        # ---------------------------------------------------------------------
        # Peak visualization
        # ---------------------------------------------------------------------
        self.btn_find_peaks = QPushButton("Show peaks")
        self.btn_find_peaks.clicked.connect(self.toggle_find_peaks)
        processing_layout.addWidget(self.btn_find_peaks)

        self.btn_peak_labels = QPushButton("Show peak labels")
        self.btn_peak_labels.clicked.connect(self.toggle_peak_labels)
        self.btn_peak_labels.setEnabled(False)
        processing_layout.addWidget(self.btn_peak_labels)

        self.btn_restore_processing = QPushButton(
            "Restore processing defaults"
        )
        self.btn_restore_processing.clicked.connect(
            self.restore_processing_defaults
        )
        processing_layout.addWidget(self.btn_restore_processing)

        group_processing.setLayout(processing_layout)

        ########################################################################
        # CALIBRATION GROUP
        group_calibration = QGroupBox("Calibration")
        calibration_layout = QVBoxLayout()

        self.lbl_calibration_status = QLabel(
            "Scale: pixels"
        )
        calibration_layout.addWidget(
            self.lbl_calibration_status
        )

        self.btn_calibration = QPushButton(
            "Wavelength calibration..."
        )
        self.btn_calibration.clicked.connect(
            self.open_calibration_dialog
        )
        calibration_layout.addWidget(
            self.btn_calibration
        )

        group_calibration.setLayout(
            calibration_layout
        )

        ########################################################################
        # DATA GROUP
        group_data = QGroupBox("Data")
        data_layout = QVBoxLayout()

        self.btn_record = QPushButton("Start recording")
        self.btn_record.setEnabled(False)
        self.btn_record.clicked.connect(
            self.toggle_recording
        )
        data_layout.addWidget(self.btn_record)

        self.lbl_recording_status = QLabel(
            "Not recording"
        )
        data_layout.addWidget(
            self.lbl_recording_status
        )

        self.btn_import_raw = QPushButton(
            "Import raw data..."
        )
        self.btn_import_raw.clicked.connect(
            self.import_raw_data
        )
        data_layout.addWidget(
            self.btn_import_raw
        )

        self.slider_imported = QSlider(
            Qt.Horizontal
        )

        self.slider_imported.setMinimum(0)
        self.slider_imported.setMaximum(0)
        self.slider_imported.setValue(0)
        self.slider_imported.setEnabled(False)

        # Flechas: de a 1
        self.slider_imported.setSingleStep(1)

        # Page Up / Page Down: de a 10
        self.slider_imported.setPageStep(10)

        self.slider_imported.valueChanged.connect(
            self.show_imported_spectrum
        )

        data_layout.addWidget(
            self.slider_imported
        )

        self.lbl_imported_position = QLabel(
            "No imported data"
        )

        data_layout.addWidget(
            self.lbl_imported_position
        )
        self.btn_return_live = QPushButton(
            "Return to live data"
        )
        self.btn_return_live.clicked.connect(
            self.return_to_live_data
        )
        self.btn_return_live.setEnabled(False)
        data_layout.addWidget(
            self.btn_return_live
        )

        group_data.setLayout(data_layout)

        ########################################################################
        # Construct the left panel
        control_layout.addWidget(group_conn)
        control_layout.addWidget(group_cmds)
        control_layout.addWidget(group_acq)
        control_layout.addWidget(group_processing)
        control_layout.addWidget(group_calibration)
        control_layout.addWidget(group_data)
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
        self.plot_widget.setXRange(0, USEFUL_CCD_PIXELS)
        self.plot_widget.showGrid(x=True, y=True)
        
        self.curve = self.plot_widget.plot(pen=pg.mkPen('b', width=2)) # Curva azul

        self.peaks_curve = self.plot_widget.plot(
            pen=None,
            symbol='o',
            symbolSize=8,
            symbolBrush='r'
        )

        control_scroll = QScrollArea()
        control_scroll.setWidgetResizable(True)
        control_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        control_scroll.setWidget(control_widget)
        control_scroll.setFixedWidth(270)

        main_layout.addWidget(control_scroll)
        main_layout.addWidget(self.plot_widget)

    def show_imported_spectrum(self, index):
        if self.imported_raw_spectra is None:
            return

        total = len(
            self.imported_raw_spectra
        )

        if total == 0:
            return

        index = max(
            0,
            min(
                int(index),
                total - 1,
            ),
        )

        self.imported_spectrum_index = index

        raw_spectrum = (
            self.imported_raw_spectra[index]
        )

        processed = (
            self.processor.process_single_spectrum(
                raw_spectrum
            )
        )

        processed, _, _, _ = (
            self.processor.process_spectrum_batch(
                [processed]
            )
        )

        self.update_plot(
            processed
        )

        self.lbl_imported_position.setText(
            f"Spectrum {index + 1} / {total}"
        )

        if self.slider_imported.value() != index:
            self.slider_imported.blockSignals(True)
            self.slider_imported.setValue(index)
            self.slider_imported.blockSignals(False)

    def open_calibration_dialog(self):
        dialog = CalibrationDialog(
            coefficients=self.wavelength_coefficients,
            parent=self,
        )

        if dialog.exec() != QDialog.Accepted:
            return

        if dialog.coefficients is None:
            self.clear_wavelength_calibration()
        else:
            self.set_wavelength_calibration(
                dialog.coefficients
            )

    def return_to_live_data(self):
        self.data_source = "live"

        self.imported_raw_spectra = None
        self.imported_spectrum_index = 0

        self.btn_return_live.setEnabled(False)

        self.slider_imported.setEnabled(False)

        self.slider_imported.blockSignals(True)

        self.slider_imported.setMinimum(0)
        self.slider_imported.setMaximum(0)
        self.slider_imported.setValue(0)

        self.slider_imported.blockSignals(False)

        self.lbl_imported_position.setText(
            "No imported data"
        )

        self.lbl_recording_status.setText(
            "Live data"
        )

        self.processor.spectra_buffer.clear()

    def update_processing_value(
        self,
        widget,
        setter,
        attribute_name,
        formatter=str,
    ):
        """
        Applies a processing parameter entered by the user.

        The setter performs validation and range limiting. After applying the
        value, the field is rewritten with the actual accepted value.
        """
        try:
            setter(widget.text())

        except (ValueError, TypeError):
            QMessageBox.warning(
                self,
                "Invalid value",
                f"The entered value for {attribute_name} is invalid.",
            )

        actual_value = getattr(
            self.processor,
            attribute_name,
        )

        widget.setText(
            formatter(actual_value)
        )

        # Avoid combining spectra processed with different configurations.
        self.processor.spectra_buffer.clear()

        self.processor.save_config()

        if (self.data_source == "imported" and self.imported_raw_spectra is not None):
            self.show_imported_spectrum(self.imported_spectrum_index)


    def update_processing_toggle(self, setter, checked):
        setter(checked)

        # Avoid mixing spectra acquired using different configurations.
        self.processor.spectra_buffer.clear()

        self.processor.save_config()

        if (self.data_source == "imported" and self.imported_raw_spectra is not None):
            self.show_imported_spectrum(self.imported_spectrum_index)


    def restore_processing_defaults(self):
        response = QMessageBox.question(
            self,
            "Restore defaults",
            "Restore all processing parameters to their default values?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if response != QMessageBox.Yes:
            return

        self.processor.delete_config()

        self.refresh_processing_controls()

        self.processor.spectra_buffer.clear()


    def refresh_processing_controls(self):
        self.edit_dark_n_samples.setText(
            str(self.processor.dark_n_samples)
        )

        self.edit_spike_window.setText(
            str(self.processor.spike_window)
        )

        self.edit_spike_multiplier.setText(
            str(self.processor.spike_T_multiplier)
        )

        self.edit_n_spectra.setText(
            str(self.processor.n_spectra)
        )

        self.edit_filter_window.setText(
            str(self.processor.filter_window)
        )

        self.edit_filter_poly_order.setText(
            str(self.processor.filter_poly_order)
        )

        self.edit_baseline_lambda.setText(
            f"{self.processor.baseline_lambda:.2e}"
        )

        self.edit_baseline_diff_order.setText(
            str(self.processor.baseline_diff_order)
        )

        self.edit_baseline_iterations.setText(
            str(self.processor.baseline_iterations)
        )

        self.edit_baseline_tolerance.setText(
            f"{self.processor.baseline_tolerance:.2e}"
        )

        self.checkbox_dark_subtraction.setChecked(
            self.processor.enable_dark_subtraction
        )

        self.checkbox_spike_correction.setChecked(
            self.processor.enable_spike_correction
        )

        self.checkbox_filtering.setChecked(
            self.processor.enable_filtering
        )

        self.checkbox_baseline_correction.setChecked(
            self.processor.enable_baseline_correction
        )

        self.checkbox_normalization.setChecked(
            self.processor.enable_normalization
        )

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

    def set_wavelength_calibration(self, coefficients, save=True,):
        coefficients = np.asarray(
            coefficients,
            dtype=float,
        )

        if coefficients.shape != (3,):
            raise ValueError(
                "Calibration must contain exactly "
                "three coefficients."
            )

        self.wavelength_coefficients = coefficients

        self.update_calibration_status()
        self.update_x_axis()

        if self.processor.last_processed_data is not None:
            self.update_plot(
                self.processor.last_processed_data
            )

        if save:
            self.save_wavelength_calibration()

    
    def clear_wavelength_calibration(self, save=True,):
        self.wavelength_coefficients = None

        self.update_calibration_status()
        self.update_x_axis()

        if self.processor.last_processed_data is not None:
            self.update_plot(
                self.processor.last_processed_data
            )

        if save:
            self.save_wavelength_calibration()

    def update_calibration_status(self):
        if self.wavelength_coefficients is None:
            self.lbl_calibration_status.setText(
                "Scale: pixels"
            )
            return

        a2, a1, a0 = self.wavelength_coefficients

        if a2 == 0.0:
            calibration_type = "linear"
        else:
            calibration_type = "quadratic"

        self.lbl_calibration_status.setText(
            f"Scale: wavelength ({calibration_type})"
        )

        self.lbl_calibration_status.setToolTip(
            (
                f"a₂ = {a2:.8g}\n"
                f"a₁ = {a1:.8g}\n"
                f"a₀ = {a0:.8g}"
            )
        )

    def save_wavelength_calibration(self):
        if self.wavelength_coefficients is None:
            calibration = {
                "enabled": False,
                "coefficients": None,
            }

        else:
            calibration = {
                "enabled": True,
                "coefficients": (
                    self.wavelength_coefficients.tolist()
                ),
            }

        try:
            with open(
                self.calibration_path,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    calibration,
                    file,
                    indent=4,
                )

            print(
                "Calibration saved to "
                f"{self.calibration_path}"
            )

        except OSError as exc:
            QMessageBox.warning(
                self,
                "Calibration error",
                (
                    "The calibration could not be saved.\n\n"
                    f"{exc}"
                ),
            )

    def get_x_axis(self, data_length):
        pixel_axis = np.arange(data_length, dtype=float)

        if self.wavelength_coefficients is None:
            return pixel_axis

        return np.polyval(
            self.wavelength_coefficients,
            pixel_axis,
        )


    def update_x_axis(self):
        if self.wavelength_coefficients is None:
            self.plot_widget.setLabel(
                "bottom",
                "Pixel",
                units="",
            )
            self.plot_widget.setXRange(
                0,
                USEFUL_CCD_PIXELS - 1,
            )
            return

        wavelength_axis = self.get_x_axis(
            USEFUL_CCD_PIXELS
        )

        self.plot_widget.setLabel(
            "bottom",
            "Wavelength",
            units="nm",
        )

        self.plot_widget.setXRange(
            float(np.min(wavelength_axis)),
            float(np.max(wavelength_axis)),
        )

    def load_wavelength_calibration(self):
        if not self.calibration_path.exists():
            self.clear_wavelength_calibration(
                save=False
            )
            return

        try:
            with open(
                self.calibration_path,
                "r",
                encoding="utf-8",
            ) as file:
                calibration = json.load(file)

        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            QMessageBox.warning(
                self,
                "Calibration error",
                (
                    "The calibration file could not be loaded. "
                    "Pixel scale will be used.\n\n"
                    f"{exc}"
                ),
            )

            self.clear_wavelength_calibration(
                save=False
            )
            return

        enabled = calibration.get(
            "enabled",
            False,
        )

        coefficients = calibration.get(
            "coefficients"
        )

        if not enabled or coefficients is None:
            self.clear_wavelength_calibration(
                save=False
            )
            return

        try:
            coefficients = np.asarray(
                coefficients,
                dtype=float,
            )

            if coefficients.shape != (3,):
                raise ValueError(
                    "Invalid coefficient count."
                )

        except (TypeError, ValueError) as exc:
            QMessageBox.warning(
                self,
                "Calibration error",
                (
                    "The stored calibration is invalid. "
                    "Pixel scale will be used.\n\n"
                    f"{exc}"
                ),
            )

            self.clear_wavelength_calibration(
                save=False
            )
            return

        self.set_wavelength_calibration(
            coefficients,
            save=False,
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
            self.btn_record.setEnabled(True)
            
            # Inicializar el hilo (pero no arrancarlo aún)
            self.worker = AcquisitionThread(
                driver=self.dev,
                processor=self.processor,
            )

            self.worker.data_ready.connect(self.update_plot)
            self.worker.raw_data_ready.connect(self.receive_raw_data)
            self.worker.dark_progress.connect(self.update_dark_progress)
            self.worker.dark_finished.connect(self.dark_capture_finished)
            self.worker.acquisition_error.connect(self.show_acquisition_error)
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"Could not connect to {port}.\n\n{str(e)}")

    @Slot(np.ndarray)
    def receive_raw_data(self, raw_data):
        if not self.is_recording:
            return

        self.recorded_raw_spectra.append(
            np.asarray(
                raw_data,
                dtype=np.uint16,
            ).copy()
        )

        self.lbl_recording_status.setText(
            (
                "Recording: "
                f"{len(self.recorded_raw_spectra)} spectra"
            )
    )
        
    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording_and_save()

    def start_recording(self):
        if self.worker is None or not self.worker.isRunning():
            QMessageBox.warning(
                self,
                "Recording",
                "Start the acquisition before recording data.",
            )
            return

        if self.worker.capturing_dark:
            QMessageBox.warning(
                self,
                "Recording",
                (
                    "Wait until the dark acquisition "
                    "is complete."
                ),
            )
            return

        self.recorded_raw_spectra.clear()
        self.is_recording = True

        self.btn_record.setText(
            "Stop and save"
        )
        self.btn_record.setStyleSheet(
            "background-color: #ffcccc;"
        )

        self.lbl_recording_status.setText(
            "Recording: 0 spectra"
        )


    def stop_recording_and_save(self):
        self.is_recording = False

        self.btn_record.setText(
            "Start recording"
        )
        self.btn_record.setStyleSheet("")

        number_of_spectra = len(
            self.recorded_raw_spectra
        )

        if number_of_spectra == 0:
            self.lbl_recording_status.setText(
                "No spectra recorded"
            )

            QMessageBox.warning(
                self,
                "Recording",
                "No spectra were recorded.",
            )
            return

        default_name = (
            "raman_raw_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            + ".npz"
        )

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save raw Raman data",
            str(Path.home() / default_name),
            "NumPy compressed file (*.npz)",
        )

        if not filename:
            self.lbl_recording_status.setText(
                (
                    f"Recording discarded: "
                    f"{number_of_spectra} spectra"
                )
            )

            self.recorded_raw_spectra.clear()
            return

        if not filename.lower().endswith(".npz"):
            filename += ".npz"

        try:
            self.save_raw_recording(filename)

        except (OSError, ValueError) as exc:
            QMessageBox.critical(
                self,
                "Recording error",
                (
                    "The recording could not be saved."
                    f"\n\n{exc}"
                ),
            )

            self.lbl_recording_status.setText(
                "Save failed"
            )
            return

        self.lbl_recording_status.setText(
            f"Saved: {number_of_spectra} spectra"
        )

        self.recorded_raw_spectra.clear()


    def save_raw_recording(self, filename):
        raw_spectra = np.asarray(
            self.recorded_raw_spectra,
            dtype=np.uint16,
        )

        if raw_spectra.ndim != 2:
            raise ValueError(
                "Recorded spectra have an invalid shape."
            )

        processing_config = {
            "dark_n_samples": self.processor.dark_n_samples,
            "spike_window": self.processor.spike_window,
            "spike_T_multiplier": (
                self.processor.spike_T_multiplier
            ),
            "n_spectra": self.processor.n_spectra,
            "filter_window": self.processor.filter_window,
            "filter_poly_order": (
                self.processor.filter_poly_order
            ),
            "baseline_lambda": (
                self.processor.baseline_lambda
            ),
            "baseline_diff_order": (
                self.processor.baseline_diff_order
            ),
            "baseline_iterations": (
                self.processor.baseline_iterations
            ),
            "baseline_tolerance": (
                self.processor.baseline_tolerance
            ),
            "enable_dark_subtraction": (
                self.processor.enable_dark_subtraction
            ),
            "enable_spike_correction": (
                self.processor.enable_spike_correction
            ),
            "enable_filtering": (
                self.processor.enable_filtering
            ),
            "enable_baseline_correction": (
                self.processor.enable_baseline_correction
            ),
            "enable_normalization": (
                self.processor.enable_normalization
            ),
        }

        if self.processor.dark_average is None:
            dark_spectrum = np.array(
                [],
                dtype=float,
            )
        else:
            dark_spectrum = np.asarray(
                self.processor.dark_average,
                dtype=float,
            )

        if self.wavelength_coefficients is None:
            calibration = np.array(
                [],
                dtype=float,
            )
        else:
            calibration = np.asarray(
                self.wavelength_coefficients,
                dtype=float,
            )

        integration_time_us = getattr(
            self.dev,
            "int_time_us",
            -1,
        )

        skip_counter = getattr(
            self.dev,
            "skip_count",
            -1,
        )

        np.savez_compressed(
            filename,
            raw_spectra=raw_spectra,
            dark_spectrum=dark_spectrum,
            wavelength_coefficients=calibration,
            integration_time_us=np.asarray(
                integration_time_us
            ),
            skip_counter=np.asarray(
                skip_counter
            ),
            processing_config=np.asarray(
                json.dumps(processing_config)
            ),
            acquisition_datetime=np.asarray(
                datetime.now().isoformat(
                    timespec="seconds"
                )
            ),
        )
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
        self.btn_dark.setEnabled(True)
        self.btn_start.setEnabled(True)

        if self.processor.dark_average is None:
            self.lbl_dark_status.setText("Dark acquisition failed")

            QMessageBox.warning(
                self,
                "Dark acquisition",
                "The dark spectrum could not be calculated.",
            )
            return

        self.lbl_dark_status.setText(
            f"Dark acquired: {self.processor.dark_n_samples} samples averaged"
        )

        QMessageBox.information(
            self,
            "Dark acquisition",
            (
                "Dark spectrum acquired successfully.\n\n"
                f"Samples averaged: {self.processor.dark_n_samples}"
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

        else:
            if self.is_recording:
                self.stop_recording_and_save()
            self.worker.stop()

            self.processor.spectra_buffer.clear()

            self.btn_start.setText("Start Reading")
            self.btn_start.setStyleSheet("background-color: #ccffcc;")

    def import_raw_data(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import raw Raman data",
            str(Path.home()),
            "NumPy compressed file (*.npz)",
        )

        if not filename:
            return

        try:
            with np.load(
                filename,
                allow_pickle=False,
            ) as data:
                if "raw_spectra" not in data:
                    raise ValueError(
                        "The selected file does not contain raw_spectra."
                    )

                raw_spectra = np.asarray(
                    data["raw_spectra"],
                    dtype=np.uint16,
                )

                if raw_spectra.ndim == 1:
                    raw_spectra = raw_spectra[np.newaxis, :]

                if raw_spectra.ndim != 2:
                    raise ValueError(
                        "Raw spectra must have shape (spectra, pixels)."
                    )

                self.imported_raw_spectra = raw_spectra.copy()

                if "dark_spectrum" in data:
                    dark = np.asarray(
                        data["dark_spectrum"],
                        dtype=float,
                    )

                    if dark.size == raw_spectra.shape[1]:
                        self.processor.dark_average = dark.copy()

                if "wavelength_coefficients" in data:
                    coefficients = np.asarray(
                        data["wavelength_coefficients"],
                        dtype=float,
                    )

                    if coefficients.shape == (3,):
                        self.set_wavelength_calibration(
                            coefficients,
                            save=False,
                        )

        except (
            OSError,
            ValueError,
            KeyError,
        ) as exc:
            QMessageBox.critical(
                self,
                "Import error",
                (
                    "The raw data file could not be loaded."
                    f"\n\n{exc}"
                ),
            )
            return

        self.data_source = "imported"

        self.btn_return_live.setEnabled(True)

        total = len(self.imported_raw_spectra)

        self.lbl_recording_status.setText(
            f"Imported: {total} spectra"
        )

        self.imported_spectrum_index = 0

        self.slider_imported.blockSignals(True)

        self.slider_imported.setMinimum(0)
        self.slider_imported.setMaximum(
            max(0, total - 1)
        )
        self.slider_imported.setValue(0)

        self.slider_imported.blockSignals(False)

        self.slider_imported.setEnabled(
            total > 0
        )

        if total > 0:
            self.lbl_imported_position.setText(
                f"Spectrum 1 / {total}"
            )

            self.show_imported_spectrum(0)

        else:
            self.lbl_imported_position.setText(
                "No imported data"
            )


    def reprocess_imported_data(self):
        if self.imported_raw_spectra is None:
            return

        if len(self.imported_raw_spectra) == 0:
            return

        processed_single_spectra = []

        for raw_spectrum in self.imported_raw_spectra:
            processed_single = (
                self.processor.process_single_spectrum(
                    raw_spectrum
                )
            )

            processed_single_spectra.append(
                processed_single
            )

        processed_single_spectra = np.asarray(
            processed_single_spectra,
            dtype=float,
        )

        processed, _, _, _ = (
            self.processor.process_spectrum_batch(
                processed_single_spectra
            )
        )

        self.update_plot(processed)

    @Slot(str)
    def on_acquisition_error(self, message):
        self.btn_start.setText("Start Reading")
        self.btn_start.setStyleSheet("background-color: #ccffcc;")
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
            self.btn_peak_labels.setEnabled(True)
            self.find_and_plot_peaks()
        else:
            self.btn_find_peaks.setText("Show peaks")
            self.btn_peak_labels.setEnabled(False)

            self.peaks_curve.setData([], [])
            self.clear_peak_labels()

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

        sender = self.sender()

        if (
            sender is self.worker
            and self.data_source == "imported"
        ):
            return

        self.processor.last_processed_data = processed_data

        x_axis = self.get_x_axis(
            len(processed_data)
        )

        self.curve.setData(
            x_axis,
            processed_data,
        )

        if self.processor.enable_normalization:
            self.plot_widget.setYRange(
                -0.05,
                1.05,
            )
        else:
            self.plot_widget.setYRange(
                -50,
                4200,
            )

        if self.peaks_enabled:
            self.find_and_plot_peaks()

    # FIND AND PLOT PEAKS
    def find_and_plot_peaks(self):
        if self.processor.last_processed_data is None:
            return

        data = self.processor.last_processed_data
        peaks = self.processor.detect_peaks(data)

        self.clear_peak_labels()

        if len(peaks) == 0:
            self.peaks_curve.setData([], [])
            return

        full_x_axis = self.get_x_axis(len(data))

        x_peaks = full_x_axis[peaks]
        y_peaks = data[peaks]

        self.peaks_curve.setData(
            x_peaks,
            y_peaks,
        )

        if self.peak_labels_enabled:
            for peak_index, x, y in zip(
                peaks,
                x_peaks,
                y_peaks,
            ):
                if self.wavelength_coefficients is None:
                    label_text = f"{peak_index}, {y:.0f}"
                else:
                    label_text = f"{x:.3f} nm, {y:.0f}"

                label = pg.TextItem(
                    text=label_text,
                    color=(30, 30, 30),
                    fill=pg.mkBrush(255, 255, 255, 255),
                    border=pg.mkPen((120, 120, 120)),
                    anchor=(0.5, 1.2),
                )

                label.setPos(x, y)
                self.plot_widget.addItem(label)
                self.peak_labels.append(label)

    # REFRESH PORTS
    def refresh_ports(self):
        current = self.port_input.currentData()
        self.port_input.clear()

        ports = list(list_ports.comports())

        for port in ports:
            self.port_input.addItem(f"{port.device} ({port.description})", port.device)
        
        # The mock must always be available, even with no serial hardware.
        self.port_input.addItem("Mock (synthetic spectrum)", "__MOCK__")

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