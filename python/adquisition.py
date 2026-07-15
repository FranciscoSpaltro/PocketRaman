from PySide6.QtCore import QThread, Signal
import numpy as np

from spectrometer import SpectrometerDriverMock
from signalprocessor import FIRST_USEFUL_PIXEL, TRAILING_UNUSED_PIXELS

class AcquisitionThread(QThread):
    raw_data_ready = Signal(np.ndarray)
    data_ready = Signal(np.ndarray)

    dark_progress = Signal(int, int)
    dark_finished = Signal()
    acquisition_error = Signal(str)

    def __init__(self, driver, processor):
        super().__init__()

        self.dev = driver
        self.processor = processor
        self.running = False

        self.capturing_dark = False
        self.dark_samples_acquired = 0

    def start_dark_capture(self):
        self.processor.dark_buffer.clear()
        self.processor.dark_average = None
        self.dark_samples_acquired = 0
        self.capturing_dark = True

    def cancel_dark_capture(self):
        self.capturing_dark = False
        self.dark_samples_acquired = 0
        self.processor.dark_buffer.clear()
        self.processor.dark_average = None

    def run(self):
        self.running = True
        self.processor.spectra_buffer.clear()

        while self.running:
            try:
                pixels = self.dev.read_frame()

                if not self.running:
                    break

                if pixels is None:
                    self.msleep(10)
                    continue
                    
                pixels = np.asarray(pixels[FIRST_USEFUL_PIXEL:-TRAILING_UNUSED_PIXELS])
                
                # -------------------------------------------------------------
                # DARK CAPTURE
                # -------------------------------------------------------------
                if self.capturing_dark:
                    self.processor.dark_buffer.append(
                        np.asarray(pixels, dtype=float).copy()
                    )

                    self.dark_samples_acquired += 1

                    self.dark_progress.emit(
                        self.dark_samples_acquired,
                        self.processor.dark_n_samples,
                    )

                    if self.dark_samples_acquired >= self.processor.dark_n_samples:
                        self.capturing_dark = False
                        self.processor.compute_dark_average()
                        self.dark_finished.emit()

                    # Este frame no entra al procesamiento normal
                    continue

                # -------------------------------------------------------------
                # NORMAL ACQUISITION
                # -------------------------------------------------------------
                
                self.raw_data_ready.emit(np.asarray(pixels, dtype=np.uint16).copy())
                processed_data, _, _, _ = self.processor.process(pixels)

                if processed_data is not None:
                    self.data_ready.emit(processed_data)

                if isinstance(self.dev, SpectrometerDriverMock):
                    self.msleep(100)

            except Exception as exc:
                self.acquisition_error.emit(str(exc))
                self.msleep(50)

        self.running = False

    def stop(self):
        self.running = False
        self.capturing_dark = False

        if hasattr(self.dev, "cancel_read"):
            self.dev.cancel_read()

        self.wait(2000)