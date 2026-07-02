import numpy as np
from pybaselines import Baseline
from scipy.signal import savgol_filter
from scipy.signal import find_peaks

BASELINE_LAMBDA_DEFAULT = 10000
SMOOTHING_WD_DEFAULT = 2
SMOOTHING_POLY_DEFAULT = 1
PEAK_HEIGHT_FACTOR_DEFAULT = 1
PEAK_MIN_DISTANCE_DEFAULT = 1
PEAK_WIDTH_DEFAULT = 1
PEAK_PROMINENCE_DEFAULT = 1

class SignalProcessor:
    ################################################################################
    # CONSTRUCTOR AND INITIALIZATION
    ################################################################################
    def __init__(self):
        self.baseline_lambda = BASELINE_LAMBDA_DEFAULT
        self.smoothing_wd = SMOOTHING_WD_DEFAULT
        self.smoothing_poly = SMOOTHING_POLY_DEFAULT
        self.peak_height_factor = PEAK_HEIGHT_FACTOR_DEFAULT
        self.peak_min_distance = PEAK_MIN_DISTANCE_DEFAULT
        self.peak_width = PEAK_WIDTH_DEFAULT
        self.peak_prominence = PEAK_PROMINENCE_DEFAULT
        self.processing_enabled = False
        self.last_processed_data = None
        self.last_noise = 0

    ####################################################################################
    # SETTERS
    ####################################################################################
    def set_baseline_lambda(self, value):
        val = min(max(value, 0), 1e14)
        self.baseline_lambda = val
        print(f"Baseline lambda = {val:.1e}")

    def set_smoothing_wd(self, value):
        val = value
        if val < 2:
            val = 2
        elif val > 3694:
            val = 3694
        self.smoothing_wd = val
        print(f"Smoothing window length = {val}")

    def set_smoothing_poly(self, value):
        val = value
        if val < 1:
            val = 1
        elif val > self.smoothing_wd - 1:
            val = self.smoothing_wd - 1
        self.smoothing_poly = val
        print(f"Smoothing polynomial order = {val}")

    def set_peak_height_factor(self, value):
        val = value
        if val < 0:
            val = 0
        self.peak_height_factor = val
        print(f"Peak height = {val:.2f}")

    def set_peak_prominence(self, value):
        val = value
        if val < 0:
            val = 0
        self.peak_prominence = val
        print(f"Peak prominence = {val:.2f}")

    def set_peak_min_distance(self, value):
        val = value
        if val < 1:
            val = 1
        elif val > 3693:
            val = 3693
        self.peak_min_distance = val
        print(f"Min peak distance = {val:.2f}")

    def set_enable_processing(self, enabled):
        self.processing_enabled = enabled
        print(f"Enable processing = {enabled}")

    ####################################################################################
    # PROCESSING
    ####################################################################################
    def process(self, data):
        processed = data.copy()
        peaks = None

        if self.processing_enabled:
            processed = self.apply_baseline_correction(processed)
            processed = self.apply_smoothing(processed)

            self.last_processed_data = processed
            self.update_noise(processed)

            # peaks = self.find_peaks(processed)    # Optional: Uncomment this line to find peaks during processing

        return processed, peaks
    
    def update_noise(self, data):
        data_ = data.astype(float)
        self.last_noise = 1.4826 * np.median(
            np.abs(data_ - np.median(data_))
        )
        return self.last_noise

    ##################################################################################
    # APLIERS
    ##################################################################################
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

        noise = self.update_noise(data_)

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