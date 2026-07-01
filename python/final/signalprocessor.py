import numpy as np
from pybaselines import Baseline
from scipy.signal import savgol_filter
from scipy.signal import find_peaks

class SignalProcessor:
    def __init__(self):
        self.baseline_lambda = 10000
        self.smoothing_wd = 2
        self.smoothing_poly = 1
        self.peak_height_factor = 1
        self.peak_min_distance = 1
        self.peak_width = 1
        self.peak_prominence = 1
        self.processing_enabled = False
        self.last_processed_data = None
        self.last_noise = 0

    def set_baseline_lambda(self, value):
        self.baseline_lambda = value
        print(f"Baseline lambda = {value}")

    def set_smoothing_wd(self, value):
        self.smoothing_wd = value
        print(f"Smoothing window length = {value}")

    def set_smoothing_poly(self, value):
        self.smoothing_poly = value
        print(f"Smoothing polynomial order = {value}")

    def set_peak_height_factor(self, value):
        self.peak_height_factor = value
        print(f"Peak height = {value}")

    def set_peak_min_distance(self, value):
        self.peak_min_distance = value
        print(f"Min peak distance = {value}")

    def set_peak_prominence(self, value):
        self.peak_prominence = value
        print(f"Peak prominence = {value}")

    def set_enable_processing(self, enabled):
        self.processing_enabled = enabled
        print(f"Enable processing = {enabled}")

    def process(self, data):
        """
        Esta función recibe el espectro crudo y devuelve el espectro procesado.
        Por ahora devuelve lo mismo.
        """
        processed = data.copy()
        peaks = None
        if(self.processing_enabled):
            processed = self.apply_baseline_correction(processed)
            processed = self.apply_smoothing(processed)
            peaks = self.find_peaks(processed)

        return processed, peaks

    def apply_baseline_correction(self, data):
        if self.baseline_lambda <= 0:
            return data.astype(float)
        
        data_ = data.astype(float)
        baseline_fitter = Baseline(x_data=np.arange(len(data)))
        estimated_baseline, params = baseline_fitter.arpls(data_, lam=self.baseline_lambda)
        corrected = data_ - estimated_baseline

        return corrected

    def apply_smoothing(self, data):
        data_ = data.astype(float)
        smoothed = savgol_filter(
            data_,
            window_length=self.smoothing_wd,   # Cuantos puntos usa para suavizar. Debe ser impar y mayor que polyorder.
            polyorder=self.smoothing_poly,        # Orden del polinomio usado para suavizar. Debe ser menor que window_length.
        )

        return smoothed

    def find_peaks(self, data):
        data_ = data.astype(float)
        self.last_noise = 1.4826 * np.median(np.abs(data_ - np.median(data_)))
        noise = self.last_noise
        height_threshold = self.peak_height_factor * noise
        prominence_threshold = self.peak_prominence * noise
        peaks, props = find_peaks(
            data_,
            height=height_threshold,
            prominence=prominence_threshold,
            distance=self.peak_min_distance,
            width=self.peak_width,
        )
        return peaks