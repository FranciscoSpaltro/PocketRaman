from PySide6.QtCore import QThread, Signal
import numpy as np
from spectrometer import SpectrometerDriverMock

# ==========================================
# HILO DE ADQUISICIÓN
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
                if isinstance(self.dev, SpectrometerDriverMock):
                    self.msleep(100) # Para fake data
            else:
                # Si hay timeout o error, se espera un poco antes de intentar leer de nuevo
                self.msleep(10)

    def stop(self):
        self.running = False
        # cuando sea SpectrometerDriver (pongo if instance)
        if not isinstance(self.dev, SpectrometerDriverMock):
            self.wait()
        else:
            if self.isRunning():
                self.quit()
                self.wait(2000)