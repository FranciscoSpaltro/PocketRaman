from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Callable

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QElapsedTimer, QTimer, Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from serial.tools import list_ports

from adquisition import AcquisitionThread
from signalprocessor import SignalProcessor, USEFUL_CCD_PIXELS
from spectrometer import SpectrometerDriver, SpectrometerDriverMock

try:
    from gpiozero import OutputDevice
except ImportError:
    OutputDevice = None


# Reference wavelengths can be edited or moved to a JSON/CSV file later.
# The intensity value is only used to choose which lines are shown first.
NEON_REFERENCE_LINES = [
    (540.056, 0.30),
    (556.277, 0.20),
    (565.666, 0.35),
    (571.922, 0.45),
    (574.830, 0.30),
    (576.442, 0.35),
    (580.445, 0.45),
    (585.249, 1.00),
    (588.190, 0.55),
    (594.483, 0.75),
    (597.553, 0.40),
    (602.999, 0.65),
    (607.434, 0.50),
    (609.616, 0.45),
    (614.306, 0.80),
    (616.359, 0.55),
    (621.728, 0.70),
    (626.650, 0.65),
    (630.479, 0.35),
    (633.443, 0.60),
    (638.299, 0.65),
    (640.225, 0.45),
]


class NeonCalibrationDialog(QDialog):
    """Interactive wavelength calibration using draggable neon lines."""

    DEFAULT_ANCHOR_PIXEL = 1615.0
    DEFAULT_ANCHOR_WAVELENGTH = 585.249
    DEFAULT_DISPERSION_NM_PER_PIXEL = 0.030

    def __init__(
        self,
        spectrum: np.ndarray,
        coefficients: np.ndarray | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.spectrum = np.asarray(spectrum, dtype=float).copy()
        self.initial_coefficients = (
            None if coefficients is None else np.asarray(coefficients, dtype=float).copy()
        )
        self.coefficients: np.ndarray | None = None
        self.line_items: list[pg.InfiniteLine] = []
        self.assigned_points: dict[float, float] = {}

        self.setWindowTitle("Interactive neon calibration")
        self.resize(1050, 720)

        self._build_ui()
        self._create_reference_lines()
        self._refresh_table_and_fit()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        instructions = QLabel(
            "Drag an orange neon line near the matching measured peak. "
            "When released, it snaps to the local maximum and becomes green."
        )
        instructions.setWordWrap(True)
        main_layout.addWidget(instructions)

        self.plot_widget = pg.PlotWidget(title="Measured spectrum and neon reference")
        self.plot_widget.setLabel("left", "Intensity")
        self.plot_widget.setLabel("bottom", "Pixel")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)
        self.plot_widget.plot(
            np.arange(self.spectrum.size),
            self.spectrum,
            pen=pg.mkPen("b", width=2),
        )
        main_layout.addWidget(self.plot_widget, stretch=1)

        controls = QHBoxLayout()

        self.spin_snap_radius = QSpinBox()
        self.spin_snap_radius.setRange(1, 100)
        self.spin_snap_radius.setValue(15)
        controls.addWidget(QLabel("Snap radius (pixels):"))
        controls.addWidget(self.spin_snap_radius)

        self.combo_degree = QComboBox()
        self.combo_degree.addItem("Linear", 1)
        self.combo_degree.addItem("Quadratic", 2)
        controls.addWidget(QLabel("Fit:"))
        controls.addWidget(self.combo_degree)

        self.btn_reset_positions = QPushButton("Reset line positions")
        self.btn_reset_positions.clicked.connect(self._reset_line_positions)
        controls.addWidget(self.btn_reset_positions)

        self.btn_clear_assignments = QPushButton("Clear assignments")
        self.btn_clear_assignments.clicked.connect(self._clear_assignments)
        controls.addWidget(self.btn_clear_assignments)

        controls.addStretch()
        main_layout.addLayout(controls)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Neon wavelength (nm)", "Pixel", "Calculated (nm)", "Residual (nm)"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMaximumHeight(190)
        main_layout.addWidget(self.table)

        self.lbl_fit = QLabel("Assign at least two lines to calculate a calibration.")
        self.lbl_fit.setWordWrap(True)
        main_layout.addWidget(self.lbl_fit)

        button_row = QHBoxLayout()

        self.btn_manual = QPushButton("Enter coefficients manually...")
        self.btn_manual.clicked.connect(self._enter_coefficients_manually)
        button_row.addWidget(self.btn_manual)

        self.btn_pixel_scale = QPushButton("Use pixel scale")
        self.btn_pixel_scale.clicked.connect(self._use_pixel_scale)
        button_row.addWidget(self.btn_pixel_scale)

        button_row.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        button_row.addWidget(buttons)

        main_layout.addLayout(button_row)

    def _create_reference_lines(self) -> None:
        for wavelength, relative_intensity in NEON_REFERENCE_LINES:
            pixel = self._initial_pixel_for_wavelength(wavelength)
            if not 0 <= pixel < self.spectrum.size:
                continue

            line = pg.InfiniteLine(
                pos=pixel,
                angle=90,
                movable=True,
                pen=pg.mkPen((255, 140, 0), width=1.5, style=Qt.DashLine),
                hoverPen=pg.mkPen((255, 100, 0), width=3),
                label=f"{wavelength:.3f}",
                labelOpts={"position": min(0.95, 0.68 + 0.25 * relative_intensity)},
            )
            line.neon_wavelength = wavelength
            line.initial_pixel = pixel
            line.assigned = False
            line.sigPositionChangeFinished.connect(
                lambda moved_line=line: self._on_line_released(moved_line)
            )

            self.plot_widget.addItem(line)
            self.line_items.append(line)

    def _initial_pixel_for_wavelength(self, wavelength: float) -> float:
        if self.initial_coefficients is not None:
            pixel = self._invert_calibration(wavelength, self.initial_coefficients)
            if pixel is not None:
                return pixel

        return self.DEFAULT_ANCHOR_PIXEL + (
            wavelength - self.DEFAULT_ANCHOR_WAVELENGTH
        ) / self.DEFAULT_DISPERSION_NM_PER_PIXEL

    def _invert_calibration(
        self,
        wavelength: float,
        coefficients: np.ndarray,
    ) -> float | None:
        a2, a1, a0 = coefficients

        if np.isclose(a2, 0.0):
            if np.isclose(a1, 0.0):
                return None
            return float((wavelength - a0) / a1)

        roots = np.roots([a2, a1, a0 - wavelength])
        valid = [
            float(root.real)
            for root in roots
            if abs(root.imag) < 1e-8 and 0 <= root.real < self.spectrum.size
        ]
        return valid[0] if valid else None

    def _on_line_released(self, line: pg.InfiniteLine) -> None:
        snapped_pixel = self._find_local_maximum(
            line.value(),
            self.spin_snap_radius.value(),
        )
        line.setValue(snapped_pixel)
        line.setPen(pg.mkPen((0, 150, 70), width=2.5))
        line.assigned = True

        self.assigned_points[line.neon_wavelength] = snapped_pixel
        self._refresh_table_and_fit()

    def _find_local_maximum(self, approximate_pixel: float, radius: int) -> float:
        center = int(round(approximate_pixel))
        left = max(0, center - radius)
        right = min(self.spectrum.size, center + radius + 1)

        if right <= left:
            return float(np.clip(center, 0, self.spectrum.size - 1))

        local = self.spectrum[left:right]
        return float(left + int(np.argmax(local)))

    def _fit_coefficients(self) -> np.ndarray | None:
        degree = int(self.combo_degree.currentData())
        minimum_points = degree + 1

        if len(self.assigned_points) < minimum_points:
            return None

        wavelengths = np.asarray(list(self.assigned_points.keys()), dtype=float)
        pixels = np.asarray(list(self.assigned_points.values()), dtype=float)
        fitted = np.polyfit(pixels, wavelengths, degree)

        if degree == 1:
            a1, a0 = fitted
            return np.asarray([0.0, a1, a0], dtype=float)

        return np.asarray(fitted, dtype=float)

    def _refresh_table_and_fit(self) -> None:
        self.coefficients = self._fit_coefficients()
        points = sorted(self.assigned_points.items())
        self.table.setRowCount(len(points))

        residuals = []
        for row, (wavelength, pixel) in enumerate(points):
            calculated = np.nan
            residual = np.nan

            if self.coefficients is not None:
                calculated = float(np.polyval(self.coefficients, pixel))
                residual = calculated - wavelength
                residuals.append(residual)

            values = [
                f"{wavelength:.3f}",
                f"{pixel:.1f}",
                "—" if np.isnan(calculated) else f"{calculated:.4f}",
                "—" if np.isnan(residual) else f"{residual:+.4f}",
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, column, item)

        degree = int(self.combo_degree.currentData())
        minimum_points = degree + 1

        if self.coefficients is None:
            self.lbl_fit.setText(
                f"Assigned lines: {len(points)}. "
                f"A {self.combo_degree.currentText().lower()} fit requires "
                f"at least {minimum_points}."
            )
            return

        a2, a1, a0 = self.coefficients
        rms = float(np.sqrt(np.mean(np.square(residuals)))) if residuals else 0.0
        self.lbl_fit.setText(
            f"λ(x) = {a2:.6g}·x² + {a1:.6g}·x + {a0:.6g}    "
            f"RMS residual: {rms:.5f} nm"
        )

    def _reset_line_positions(self) -> None:
        self.assigned_points.clear()
        for line in self.line_items:
            line.setValue(line.initial_pixel)
            line.setPen(pg.mkPen((255, 140, 0), width=1.5, style=Qt.DashLine))
            line.assigned = False
        self._refresh_table_and_fit()

    def _clear_assignments(self) -> None:
        self.assigned_points.clear()
        for line in self.line_items:
            line.setPen(pg.mkPen((255, 140, 0), width=1.5, style=Qt.DashLine))
            line.assigned = False
        self._refresh_table_and_fit()

    def _enter_coefficients_manually(self) -> None:
        dialog = ManualCalibrationDialog(self.initial_coefficients, self)
        if dialog.exec() == QDialog.Accepted:
            self.coefficients = dialog.coefficients
            super().accept()

    def _use_pixel_scale(self) -> None:
        self.coefficients = None
        super().accept()

    def accept(self) -> None:
        self.coefficients = self._fit_coefficients()
        if self.coefficients is None:
            QMessageBox.warning(
                self,
                "Calibration",
                "There are not enough assigned neon lines for the selected fit.",
            )
            return
        super().accept()


class ManualCalibrationDialog(QDialog):
    """Small fallback dialog for direct coefficient entry."""

    def __init__(
        self,
        coefficients: np.ndarray | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.coefficients: np.ndarray | None = None
        self.setWindowTitle("Manual wavelength calibration")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.edits = [QLineEdit(), QLineEdit(), QLineEdit()]
        for label, edit in zip(("a₂:", "a₁:", "a₀:"), self.edits):
            form.addRow(label, edit)

        if coefficients is not None:
            for edit, value in zip(self.edits, coefficients):
                edit.setText(f"{value:.12g}")

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        try:
            values = [float(edit.text().strip() or 0.0) for edit in self.edits]
        except ValueError:
            QMessageBox.warning(self, "Calibration", "Coefficients must be numbers.")
            return

        if np.isclose(values[0], 0.0) and np.isclose(values[1], 0.0):
            QMessageBox.warning(self, "Calibration", "a₁ or a₂ must be non-zero.")
            return

        self.coefficients = np.asarray(values, dtype=float)
        super().accept()


class RamanGUI(QMainWindow):
    """Main Raman spectrometer window."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Spectrometer Raman - Control Panel")
        self.resize(1100, 680)

        self.processor = SignalProcessor()
        self.dev = None
        self.worker = None
        self.laser = self._create_laser_output()

        self.peaks_enabled = False
        self.peak_labels_enabled = False
        self.peak_labels: list[pg.TextItem] = []

        self.is_recording = False
        self.recorded_raw_spectra: list[np.ndarray] = []

        self.data_source = "live"
        self.imported_raw_spectra: np.ndarray | None = None
        self.imported_spectrum_index = 0

        self.frame_counter = 0
        self.packet_timer = QElapsedTimer()
        self.acquisition_ui_timer = QTimer(self)
        self.acquisition_ui_timer.setInterval(100)
        self.acquisition_ui_timer.timeout.connect(self.update_acquisition_status)

        self.wavelength_coefficients: np.ndarray | None = None
        self.calibration_path = Path(__file__).parent / "calibration.json"

        self._build_ui()
        self.load_wavelength_calibration()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        control_panel = QWidget()
        control_panel.setMinimumWidth(245)
        controls = QVBoxLayout(control_panel)

        for group in (
            self._build_connection_group(),
            self._build_device_group(),
            self._build_acquisition_group(),
            self._build_processing_group(),
            self._build_calibration_group(),
            self._build_data_group(),
        ):
            controls.addWidget(group)
        controls.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(control_panel)
        scroll.setFixedWidth(285)

        layout.addWidget(scroll)
        layout.addWidget(self._build_plot_widget(), stretch=1)

    def _build_connection_group(self) -> QGroupBox:
        group = QGroupBox("Connection")
        layout = QVBoxLayout(group)

        port_row = QHBoxLayout()
        self.port_input = QComboBox()
        self.btn_refresh_ports = QPushButton("Refresh")
        self.btn_refresh_ports.clicked.connect(self.refresh_ports)
        port_row.addWidget(self.port_input)
        port_row.addWidget(self.btn_refresh_ports)

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clicked.connect(self.connect_device)

        layout.addWidget(QLabel("Serial port:"))
        layout.addLayout(port_row)
        layout.addWidget(self.btn_connect)
        self.refresh_ports()
        return group

    def _build_device_group(self) -> QGroupBox:
        group = QGroupBox("STM32 configuration")
        layout = QVBoxLayout(group)

        self.spin_time = QDoubleSpinBox()
        self.spin_time.setRange(0.001, 100000.0)
        self.spin_time.setDecimals(3)
        self.spin_time.setValue(100.0)
        self.spin_time.setSuffix(" ms")
        layout.addWidget(self.spin_time)
        layout.addWidget(self._button("Set integration time", lambda: self.send_cmd("time")))

        self.spin_skip = QSpinBox()
        self.spin_skip.setRange(0, 1000)
        layout.addWidget(self.spin_skip)
        layout.addWidget(self._button("Set skip counter", lambda: self.send_cmd("skip")))

        btn_reset = self._button("Reset device", lambda: self.send_cmd("reset"))
        btn_reset.setStyleSheet("background-color: #ffcccc;")
        layout.addWidget(btn_reset)
        layout.addWidget(self._button("Toggle LED", lambda: self.send_cmd("toggle_led")))

        self.btn_laser = QPushButton("Laser OFF")
        self.btn_laser.setCheckable(True)
        self.btn_laser.toggled.connect(self.set_laser_state)
        layout.addWidget(self.btn_laser)
        return group

    def _build_acquisition_group(self) -> QGroupBox:
        group = QGroupBox("Continuous acquisition")
        layout = QVBoxLayout(group)

        self.btn_start = QPushButton("Start reading")
        self.btn_start.setStyleSheet("background-color: #ccffcc;")
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.toggle_acquisition)

        self.btn_dark = QPushButton("Capture dark")
        self.btn_dark.setEnabled(False)
        self.btn_dark.clicked.connect(self.start_dark_capture)

        self.frame_label = QLabel("Frame: 0")
        self.frame_time_label = QLabel("Since last frame: 0.00 s")
        self.lbl_dark_status = QLabel("Dark: not acquired")

        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_dark)
        layout.addWidget(self._button("Reset frame counter", self.reset_frame_counter))
        layout.addWidget(self.lbl_dark_status)
        layout.addWidget(self.frame_label)
        layout.addWidget(self.frame_time_label)
        return group

    def _build_processing_group(self) -> QGroupBox:
        group = QGroupBox("Processing")
        layout = QVBoxLayout(group)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.checkbox_dark_subtraction = self._add_toggle(
            form,
            "Dark subtraction:",
            self.processor.enable_dark_subtraction,
            self.processor.set_enable_dark_subtraction,
        )
        self.edit_dark_n_samples = self._add_processing_edit(
            form, "Dark samples:", "dark_n_samples", self.processor.set_dark_n_samples
        )

        self.checkbox_spike_correction = self._add_toggle(
            form,
            "Spike correction:",
            self.processor.enable_spike_correction,
            self.processor.set_enable_spike_correction,
        )
        self.edit_spike_window = self._add_processing_edit(
            form, "Spike window:", "spike_window", self.processor.set_spike_window
        )
        self.edit_spike_multiplier = self._add_processing_edit(
            form,
            "Spike threshold:",
            "spike_T_multiplier",
            self.processor.set_spike_T_multiplier,
        )

        self.edit_n_spectra = self._add_processing_edit(
            form, "Spectra to average:", "n_spectra", self.processor.set_n_spectra
        )

        self.checkbox_filtering = self._add_toggle(
            form,
            "Filtering:",
            self.processor.enable_filtering,
            self.processor.set_enable_filtering,
        )
        self.edit_filter_window = self._add_processing_edit(
            form, "Filter window:", "filter_window", self.processor.set_filter_window
        )
        self.edit_filter_poly_order = self._add_processing_edit(
            form,
            "Polynomial order:",
            "filter_poly_order",
            self.processor.set_filter_poly_order,
        )

        self.checkbox_baseline_correction = self._add_toggle(
            form,
            "Baseline correction:",
            self.processor.enable_baseline_correction,
            self.processor.set_enable_baseline_correction,
        )
        self.edit_baseline_lambda = self._add_processing_edit(
            form,
            "Baseline lambda:",
            "baseline_lambda",
            self.processor.set_baseline_lambda,
            lambda value: f"{value:.2e}",
        )
        self.edit_baseline_diff_order = self._add_processing_edit(
            form,
            "Difference order:",
            "baseline_diff_order",
            self.processor.set_baseline_diff_order,
        )
        self.edit_baseline_iterations = self._add_processing_edit(
            form,
            "Iterations:",
            "baseline_iterations",
            self.processor.set_baseline_iterations,
        )
        self.edit_baseline_tolerance = self._add_processing_edit(
            form,
            "Tolerance:",
            "baseline_tolerance",
            self.processor.set_baseline_tolerance,
            lambda value: f"{value:.2e}",
        )

        self.checkbox_normalization = self._add_toggle(
            form,
            "Normalization:",
            self.processor.enable_normalization,
            self.processor.set_enable_normalization,
        )

        self.edit_peak_prominence = self._add_processing_edit(
            form,
            "Peak prominence (σ):",
            "peak_prominence_factor",
            self.processor.set_peak_prominence_factor,
        )
        self.edit_peak_min_distance = self._add_processing_edit(
            form,
            "Peak distance:",
            "peak_min_distance",
            self.processor.set_peak_min_distance,
        )
        self.edit_peak_min_width = self._add_processing_edit(
            form,
            "Peak width:",
            "peak_min_width",
            self.processor.set_peak_min_width,
        )

        layout.addLayout(form)

        self.btn_find_peaks = self._button("Show peaks", self.toggle_find_peaks)
        self.btn_peak_labels = self._button("Show peak labels", self.toggle_peak_labels)
        self.btn_peak_labels.setEnabled(False)
        layout.addWidget(self.btn_find_peaks)
        layout.addWidget(self.btn_peak_labels)
        layout.addWidget(self._button("Restore processing defaults", self.restore_processing_defaults))
        return group

    def _build_calibration_group(self) -> QGroupBox:
        group = QGroupBox("Calibration")
        layout = QVBoxLayout(group)
        self.lbl_calibration_status = QLabel("Scale: pixels")
        self.btn_calibration = self._button(
            "Interactive neon calibration...", self.open_calibration_dialog
        )
        layout.addWidget(self.lbl_calibration_status)
        layout.addWidget(self.btn_calibration)
        return group

    def _build_data_group(self) -> QGroupBox:
        group = QGroupBox("Data")
        layout = QVBoxLayout(group)

        self.btn_record = self._button("Start recording", self.toggle_recording)
        self.btn_record.setEnabled(False)
        self.lbl_recording_status = QLabel("Not recording")

        self.btn_import_raw = self._button("Import raw data...", self.import_raw_data)

        self.slider_imported = QSlider(Qt.Horizontal)
        self.slider_imported.setRange(0, 0)
        self.slider_imported.setSingleStep(1)
        self.slider_imported.setPageStep(10)
        self.slider_imported.setEnabled(False)
        self.slider_imported.valueChanged.connect(self.show_imported_spectrum)

        self.lbl_imported_position = QLabel("No imported data")
        self.btn_return_live = self._button("Return to live data", self.return_to_live_data)
        self.btn_return_live.setEnabled(False)

        for widget in (
            self.btn_record,
            self.lbl_recording_status,
            self.btn_import_raw,
            self.slider_imported,
            self.lbl_imported_position,
            self.btn_return_live,
        ):
            layout.addWidget(widget)
        return group

    def _build_plot_widget(self) -> pg.PlotWidget:
        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")

        self.plot_widget = pg.PlotWidget(title="Spectrum in real time")
        self.plot_widget.setLabel("left", "Intensity (ADC)")
        self.plot_widget.setLabel("bottom", "Pixel")
        self.plot_widget.setYRange(-50, 4200)
        self.plot_widget.setXRange(0, USEFUL_CCD_PIXELS - 1)
        self.plot_widget.showGrid(x=True, y=True)

        self.curve = self.plot_widget.plot(pen=pg.mkPen("b", width=2))
        self.peaks_curve = self.plot_widget.plot(
            pen=None,
            symbol="o",
            symbolSize=8,
            symbolBrush="r",
        )
        return self.plot_widget

    @staticmethod
    def _button(text: str, callback: Callable) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(callback)
        return button

    def _add_toggle(
        self,
        form: QFormLayout,
        label: str,
        current_value: bool,
        setter: Callable[[bool], None],
    ) -> QCheckBox:
        checkbox = QCheckBox()
        checkbox.setChecked(current_value)
        checkbox.toggled.connect(
            lambda checked, selected_setter=setter: self.update_processing_toggle(
                selected_setter, checked
            )
        )
        form.addRow(label, checkbox)
        return checkbox

    def _add_processing_edit(
        self,
        form: QFormLayout,
        label: str,
        attribute_name: str,
        setter: Callable,
        formatter: Callable = str,
    ) -> QLineEdit:
        edit = QLineEdit(formatter(getattr(self.processor, attribute_name)))
        edit.editingFinished.connect(
            lambda selected_edit=edit,
            selected_setter=setter,
            selected_attribute=attribute_name,
            selected_formatter=formatter: self.update_processing_value(
                selected_edit,
                selected_setter,
                selected_attribute,
                selected_formatter,
            )
        )
        form.addRow(label, edit)
        return edit

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------
    def open_calibration_dialog(self) -> None:
        spectrum = self.processor.last_processed_data
        if spectrum is None:
            QMessageBox.warning(
                self,
                "Wavelength calibration",
                "Acquire or import a spectrum before calibrating.",
            )
            return

        dialog = NeonCalibrationDialog(
            spectrum=np.asarray(spectrum, dtype=float),
            coefficients=self.wavelength_coefficients,
            parent=self,
        )

        if dialog.exec() != QDialog.Accepted:
            return

        if dialog.coefficients is None:
            self.clear_wavelength_calibration()
        else:
            self.set_wavelength_calibration(dialog.coefficients)

    def set_wavelength_calibration(self, coefficients, save: bool = True) -> None:
        coefficients = np.asarray(coefficients, dtype=float)
        if coefficients.shape != (3,):
            raise ValueError("Calibration must contain [a2, a1, a0].")

        self.wavelength_coefficients = coefficients
        self.update_calibration_status()
        self.update_x_axis()
        self._redraw_last_spectrum()

        if save:
            self.save_wavelength_calibration()

    def clear_wavelength_calibration(self, save: bool = True) -> None:
        self.wavelength_coefficients = None
        self.update_calibration_status()
        self.update_x_axis()
        self._redraw_last_spectrum()

        if save:
            self.save_wavelength_calibration()

    def _redraw_last_spectrum(self) -> None:
        if self.processor.last_processed_data is not None:
            self.update_plot(self.processor.last_processed_data, count_frame=False)

    def update_calibration_status(self) -> None:
        if self.wavelength_coefficients is None:
            self.lbl_calibration_status.setText("Scale: pixels")
            self.lbl_calibration_status.setToolTip("")
            return

        a2, a1, a0 = self.wavelength_coefficients
        kind = "linear" if np.isclose(a2, 0.0) else "quadratic"
        self.lbl_calibration_status.setText(f"Scale: wavelength ({kind})")
        self.lbl_calibration_status.setToolTip(
            f"a₂ = {a2:.8g}\na₁ = {a1:.8g}\na₀ = {a0:.8g}"
        )

    def get_x_axis(self, data_length: int) -> np.ndarray:
        pixels = np.arange(data_length, dtype=float)
        if self.wavelength_coefficients is None:
            return pixels
        return np.polyval(self.wavelength_coefficients, pixels)

    def update_x_axis(self) -> None:
        if self.wavelength_coefficients is None:
            self.plot_widget.setLabel("bottom", "Pixel")
            self.plot_widget.setXRange(0, USEFUL_CCD_PIXELS - 1)
            return

        wavelength_axis = self.get_x_axis(USEFUL_CCD_PIXELS)
        self.plot_widget.setLabel("bottom", "Wavelength", units="nm")
        self.plot_widget.setXRange(
            float(np.min(wavelength_axis)),
            float(np.max(wavelength_axis)),
        )

    def save_wavelength_calibration(self) -> None:
        payload = {
            "enabled": self.wavelength_coefficients is not None,
            "coefficients": (
                None
                if self.wavelength_coefficients is None
                else self.wavelength_coefficients.tolist()
            ),
        }

        try:
            self.calibration_path.write_text(
                json.dumps(payload, indent=4),
                encoding="utf-8",
            )
        except OSError as exc:
            QMessageBox.warning(self, "Calibration error", str(exc))

    def load_wavelength_calibration(self) -> None:
        if not self.calibration_path.exists():
            self.clear_wavelength_calibration(save=False)
            return

        try:
            payload = json.loads(self.calibration_path.read_text(encoding="utf-8"))
            coefficients = payload.get("coefficients")

            if not payload.get("enabled", False) or coefficients is None:
                self.clear_wavelength_calibration(save=False)
                return

            self.set_wavelength_calibration(
                np.asarray(coefficients, dtype=float),
                save=False,
            )
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            QMessageBox.warning(
                self,
                "Calibration error",
                f"Stored calibration is invalid. Pixel scale will be used.\n\n{exc}",
            )
            self.clear_wavelength_calibration(save=False)

    # ------------------------------------------------------------------
    # Processing controls
    # ------------------------------------------------------------------
    def update_processing_value(
        self,
        widget: QLineEdit,
        setter: Callable,
        attribute_name: str,
        formatter: Callable = str,
    ) -> None:
        try:
            setter(widget.text())
        except (ValueError, TypeError):
            QMessageBox.warning(
                self,
                "Invalid value",
                f"The entered value for {attribute_name} is invalid.",
            )

        widget.setText(formatter(getattr(self.processor, attribute_name)))
        self._processing_configuration_changed()

    def update_processing_toggle(self, setter: Callable, checked: bool) -> None:
        setter(checked)
        self._processing_configuration_changed()

    def _processing_configuration_changed(self) -> None:
        self.processor.spectra_buffer.clear()
        self.processor.save_config()

        if self.data_source == "imported" and self.imported_raw_spectra is not None:
            self.show_imported_spectrum(self.imported_spectrum_index)

    def restore_processing_defaults(self) -> None:
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

    def refresh_processing_controls(self) -> None:
        field_map = {
            self.edit_dark_n_samples: ("dark_n_samples", str),
            self.edit_spike_window: ("spike_window", str),
            self.edit_spike_multiplier: ("spike_T_multiplier", str),
            self.edit_n_spectra: ("n_spectra", str),
            self.edit_filter_window: ("filter_window", str),
            self.edit_filter_poly_order: ("filter_poly_order", str),
            self.edit_baseline_lambda: ("baseline_lambda", lambda value: f"{value:.2e}"),
            self.edit_baseline_diff_order: ("baseline_diff_order", str),
            self.edit_baseline_iterations: ("baseline_iterations", str),
            self.edit_baseline_tolerance: (
                "baseline_tolerance",
                lambda value: f"{value:.2e}",
            ),
            self.edit_peak_prominence: ("peak_prominence_factor", str),
            self.edit_peak_min_distance: ("peak_min_distance", str),
            self.edit_peak_min_width: ("peak_min_width", str),
        }

        for widget, (attribute, formatter) in field_map.items():
            widget.setText(formatter(getattr(self.processor, attribute)))

        toggle_map = {
            self.checkbox_dark_subtraction: "enable_dark_subtraction",
            self.checkbox_spike_correction: "enable_spike_correction",
            self.checkbox_filtering: "enable_filtering",
            self.checkbox_baseline_correction: "enable_baseline_correction",
            self.checkbox_normalization: "enable_normalization",
        }

        for checkbox, attribute in toggle_map.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(bool(getattr(self.processor, attribute)))
            checkbox.blockSignals(False)

    # ------------------------------------------------------------------
    # Device and acquisition
    # ------------------------------------------------------------------
    def _create_laser_output(self):
        if OutputDevice is None:
            return None
        try:
            return OutputDevice(17, active_high=False, initial_value=False)
        except Exception:
            return None

    def connect_device(self) -> None:
        port = self.port_input.currentData()
        if port is None:
            QMessageBox.warning(self, "Connection error", "No serial port selected.")
            return

        try:
            self.dev = (
                SpectrometerDriverMock()
                if port == "__MOCK__"
                else SpectrometerDriver(port=port, timeout=10.0)
            )
            self.worker = AcquisitionThread(driver=self.dev, processor=self.processor)
            self.worker.data_ready.connect(self.update_plot)
            self.worker.raw_data_ready.connect(self.receive_raw_data)
            self.worker.dark_progress.connect(self.update_dark_progress)
            self.worker.dark_finished.connect(self.dark_capture_finished)
            self.worker.acquisition_error.connect(self.show_acquisition_error)

            self.btn_connect.setText("Connected")
            self.btn_connect.setStyleSheet("background-color: #ccffcc;")
            self.btn_connect.setEnabled(False)
            self.port_input.setEnabled(False)
            self.btn_start.setEnabled(True)
            self.btn_dark.setEnabled(True)
            self.btn_record.setEnabled(True)

            self.packet_timer.start()
            self.acquisition_ui_timer.start()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Connection error",
                f"Could not connect to {port}.\n\n{exc}",
            )

    def toggle_acquisition(self) -> None:
        if self.worker is None:
            return

        if not self.worker.isRunning():
            self.processor.spectra_buffer.clear()
            self.worker.start()
            self.btn_start.setText("Stop reading")
            self.btn_start.setStyleSheet("background-color: #ffcccc;")
            return

        if self.is_recording:
            self.stop_recording_and_save()
        self.worker.stop()
        self.processor.spectra_buffer.clear()
        self.btn_start.setText("Start reading")
        self.btn_start.setStyleSheet("background-color: #ccffcc;")

    def update_acquisition_status(self) -> None:
        if not self.packet_timer.isValid():
            return
        elapsed_s = self.packet_timer.elapsed() / 1000.0
        self.frame_time_label.setText(f"Since last frame: {elapsed_s:.2f} s")

    def reset_frame_counter(self) -> None:
        self.frame_counter = 0
        self.frame_label.setText("Frame: 0")

    def send_cmd(self, command: str) -> None:
        if self.dev is None:
            return

        commands = {
            "reset": self.dev.reset_device,
            "time": lambda: self.dev.set_integration_time(self.spin_time.value() * 1000.0),
            "skip": lambda: self.dev.set_skip_counter(self.spin_skip.value()),
            "toggle_led": self.dev.toggle_led,
        }
        action = commands.get(command)
        if action is not None:
            action()

    def set_laser_state(self, enabled: bool) -> None:
        if self.laser is not None:
            self.laser.on() if enabled else self.laser.off()
        self.btn_laser.setText("Laser ON" if enabled else "Laser OFF")

    def start_dark_capture(self) -> None:
        if self.worker is None or not self.worker.isRunning():
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
        self.lbl_dark_status.setText(f"Dark: 0 / {self.processor.dark_n_samples}")

    def update_dark_progress(self, current: int, total: int) -> None:
        self.lbl_dark_status.setText(f"Dark: {current} / {total}")

    def dark_capture_finished(self) -> None:
        self.btn_dark.setEnabled(True)
        self.btn_start.setEnabled(True)

        if self.processor.dark_average is None:
            self.lbl_dark_status.setText("Dark acquisition failed")
            QMessageBox.warning(self, "Dark acquisition", "Dark spectrum could not be calculated.")
            return

        self.lbl_dark_status.setText(
            f"Dark acquired: {self.processor.dark_n_samples} samples averaged"
        )

    def show_acquisition_error(self, message: str) -> None:
        self.btn_start.setText("Start reading")
        self.btn_start.setStyleSheet("background-color: #ccffcc;")
        QMessageBox.critical(self, "Acquisition error", message)

    # ------------------------------------------------------------------
    # Recording and imported data
    # ------------------------------------------------------------------
    @Slot(np.ndarray)
    def receive_raw_data(self, raw_data: np.ndarray) -> None:
        if not self.is_recording:
            return
        self.recorded_raw_spectra.append(np.asarray(raw_data, dtype=np.uint16).copy())
        self.lbl_recording_status.setText(
            f"Recording: {len(self.recorded_raw_spectra)} spectra"
        )

    def toggle_recording(self) -> None:
        self.start_recording() if not self.is_recording else self.stop_recording_and_save()

    def start_recording(self) -> None:
        if self.worker is None or not self.worker.isRunning():
            QMessageBox.warning(self, "Recording", "Start acquisition before recording.")
            return
        if self.worker.capturing_dark:
            QMessageBox.warning(self, "Recording", "Wait for dark acquisition to finish.")
            return

        self.recorded_raw_spectra.clear()
        self.is_recording = True
        self.btn_record.setText("Stop and save")
        self.btn_record.setStyleSheet("background-color: #ffcccc;")
        self.lbl_recording_status.setText("Recording: 0 spectra")

    def stop_recording_and_save(self) -> None:
        self.is_recording = False
        self.btn_record.setText("Start recording")
        self.btn_record.setStyleSheet("")

        count = len(self.recorded_raw_spectra)
        if count == 0:
            self.lbl_recording_status.setText("No spectra recorded")
            return

        default_name = "raman_raw_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".npz"
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save raw Raman data",
            str(Path.home() / default_name),
            "NumPy compressed file (*.npz)",
        )
        if not filename:
            self.recorded_raw_spectra.clear()
            self.lbl_recording_status.setText("Recording discarded")
            return

        if not filename.lower().endswith(".npz"):
            filename += ".npz"

        try:
            self.save_raw_recording(filename)
            self.lbl_recording_status.setText(f"Saved: {count} spectra")
            self.recorded_raw_spectra.clear()
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Recording error", str(exc))

    def save_raw_recording(self, filename: str) -> None:
        raw_spectra = np.asarray(self.recorded_raw_spectra, dtype=np.uint16)
        if raw_spectra.ndim != 2:
            raise ValueError("Recorded spectra have an invalid shape.")

        processing_config = {
            name: getattr(self.processor, name)
            for name in (
                "dark_n_samples",
                "spike_window",
                "spike_T_multiplier",
                "n_spectra",
                "filter_window",
                "filter_poly_order",
                "baseline_lambda",
                "baseline_diff_order",
                "baseline_iterations",
                "baseline_tolerance",
                "enable_dark_subtraction",
                "enable_spike_correction",
                "enable_filtering",
                "enable_baseline_correction",
                "enable_normalization",
            )
        }

        dark = (
            np.array([], dtype=float)
            if self.processor.dark_average is None
            else np.asarray(self.processor.dark_average, dtype=float)
        )
        calibration = (
            np.array([], dtype=float)
            if self.wavelength_coefficients is None
            else self.wavelength_coefficients
        )

        np.savez_compressed(
            filename,
            raw_spectra=raw_spectra,
            dark_spectrum=dark,
            wavelength_coefficients=calibration,
            integration_time_us=np.asarray(getattr(self.dev, "int_time_us", -1)),
            skip_counter=np.asarray(getattr(self.dev, "skip_count", -1)),
            processing_config=np.asarray(json.dumps(processing_config)),
            acquisition_datetime=np.asarray(datetime.now().isoformat(timespec="seconds")),
        )

    def import_raw_data(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import raw Raman data",
            str(Path.home()),
            "NumPy compressed file (*.npz)",
        )
        if not filename:
            return

        try:
            with np.load(filename, allow_pickle=False) as data:
                if "raw_spectra" not in data:
                    raise ValueError("The file does not contain raw_spectra.")

                raw = np.asarray(data["raw_spectra"], dtype=np.uint16)
                if raw.ndim == 1:
                    raw = raw[np.newaxis, :]
                if raw.ndim != 2:
                    raise ValueError("raw_spectra must have shape (spectra, pixels).")

                self.imported_raw_spectra = raw.copy()

                dark = np.asarray(data.get("dark_spectrum", []), dtype=float)
                if dark.size == raw.shape[1]:
                    self.processor.dark_average = dark.copy()

                calibration = np.asarray(data.get("wavelength_coefficients", []), dtype=float)
                if calibration.shape == (3,):
                    self.set_wavelength_calibration(calibration, save=False)
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.critical(self, "Import error", str(exc))
            return

        self.data_source = "imported"
        self.imported_spectrum_index = 0
        total = len(self.imported_raw_spectra)

        self.btn_return_live.setEnabled(True)
        self.slider_imported.setRange(0, max(0, total - 1))
        self.slider_imported.setEnabled(total > 0)
        self.slider_imported.setValue(0)
        self.lbl_recording_status.setText(f"Imported: {total} spectra")

        if total:
            self.show_imported_spectrum(0)

    def show_imported_spectrum(self, index: int) -> None:
        if self.imported_raw_spectra is None or len(self.imported_raw_spectra) == 0:
            return

        index = int(np.clip(index, 0, len(self.imported_raw_spectra) - 1))
        self.imported_spectrum_index = index

        processed = self.processor.process_single_spectrum(self.imported_raw_spectra[index])
        processed, _, _, _ = self.processor.process_spectrum_batch([processed])
        self.update_plot(processed, count_frame=False)

        self.lbl_imported_position.setText(
            f"Spectrum {index + 1} / {len(self.imported_raw_spectra)}"
        )

    def return_to_live_data(self) -> None:
        self.data_source = "live"
        self.imported_raw_spectra = None
        self.imported_spectrum_index = 0
        self.slider_imported.setRange(0, 0)
        self.slider_imported.setEnabled(False)
        self.lbl_imported_position.setText("No imported data")
        self.btn_return_live.setEnabled(False)
        self.lbl_recording_status.setText("Live data")
        self.processor.spectra_buffer.clear()

    # ------------------------------------------------------------------
    # Plot and peaks
    # ------------------------------------------------------------------
    @Slot(np.ndarray)
    def update_plot(self, processed_data: np.ndarray, count_frame: bool = True) -> None:
        if processed_data is None:
            return

        if self.sender() is self.worker and self.data_source == "imported":
            return

        if count_frame:
            self.frame_counter += 1
            self.frame_label.setText(f"Frame: {self.frame_counter}")
            self.packet_timer.restart()

        data = np.asarray(processed_data, dtype=float)
        self.processor.last_processed_data = data
        self.curve.setData(self.get_x_axis(data.size), data)

        self.plot_widget.setYRange(
            -0.05 if self.processor.enable_normalization else -50,
            1.05 if self.processor.enable_normalization else 4200,
        )

        if self.peaks_enabled:
            self.find_and_plot_peaks()

    def toggle_find_peaks(self) -> None:
        self.peaks_enabled = not self.peaks_enabled
        self.btn_find_peaks.setText("Hide peaks" if self.peaks_enabled else "Show peaks")
        self.btn_peak_labels.setEnabled(self.peaks_enabled)

        if self.peaks_enabled:
            self.find_and_plot_peaks()
        else:
            self.peaks_curve.setData([], [])
            self.clear_peak_labels()

    def toggle_peak_labels(self) -> None:
        self.peak_labels_enabled = not self.peak_labels_enabled
        self.btn_peak_labels.setText(
            "Hide peak labels" if self.peak_labels_enabled else "Show peak labels"
        )
        self.find_and_plot_peaks() if self.peak_labels_enabled else self.clear_peak_labels()

    def find_and_plot_peaks(self) -> None:
        data = self.processor.last_processed_data
        if data is None:
            return

        peaks = self.processor.detect_peaks(data)
        self.clear_peak_labels()

        if len(peaks) == 0:
            self.peaks_curve.setData([], [])
            return

        x_axis = self.get_x_axis(len(data))
        x_peaks = x_axis[peaks]
        y_peaks = data[peaks]
        self.peaks_curve.setData(x_peaks, y_peaks)

        if not self.peak_labels_enabled:
            return

        for pixel, x, y in zip(peaks, x_peaks, y_peaks):
            text = f"{pixel}, {y:.0f}" if self.wavelength_coefficients is None else f"{x:.3f} nm, {y:.0f}"
            label = pg.TextItem(
                text=text,
                color=(30, 30, 30),
                fill=pg.mkBrush(255, 255, 255, 255),
                border=pg.mkPen((120, 120, 120)),
                anchor=(0.5, 1.2),
            )
            label.setPos(x, y)
            self.plot_widget.addItem(label)
            self.peak_labels.append(label)

    def clear_peak_labels(self) -> None:
        for label in self.peak_labels:
            self.plot_widget.removeItem(label)
        self.peak_labels.clear()

    # ------------------------------------------------------------------
    # Miscellaneous
    # ------------------------------------------------------------------
    def refresh_ports(self) -> None:
        current = self.port_input.currentData()
        self.port_input.clear()

        for port in list_ports.comports():
            self.port_input.addItem(f"{port.device} ({port.description})", port.device)
        self.port_input.addItem("Mock (synthetic spectrum)", "__MOCK__")

        for index in range(self.port_input.count()):
            if self.port_input.itemData(index) == current:
                self.port_input.setCurrentIndex(index)
                break

    def closeEvent(self, event) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
        if self.dev is not None:
            self.dev.close()
        if self.laser is not None:
            self.laser.off()
            self.laser.close()
        event.accept()