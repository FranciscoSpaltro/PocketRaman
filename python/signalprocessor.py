import numpy as np
from pybaselines import Baseline
from scipy.signal import savgol_filter
from scipy.ndimage import median_filter
from pathlib import Path
import json
from scipy.signal import find_peaks

CCD_PIXELS = 3694
USEFUL_CCD_PIXELS = 3694
ADC_MAX = 4095

DARK_N_SAMPLES_MAX = 1000
DARK_N_SAMPLES_MIN = 1
DARK_N_SAMPLES_DEFAULT = 100

SPIKE_WINDOW_MAX = 51
SPIKE_WINDOW_MIN = 3
SPIKE_WINDOW_DEFAULT = 5

SPIKE_T_MULTIPLIER_MAX = 1
SPIKE_T_MULTIPLIER_MIN = 1
SPIKE_T_MULTIPLIER_DEFAULT = 1

N_SPECTRA_MAX = 1000
N_SPECTRA_MIN = 1
N_SPECTRA_DEFAULT = 100

# Values from SAVGOL filtering method
FILTER_WINDOW_MAX = USEFUL_CCD_PIXELS # fixed
FILTER_WINDOW_MIN = 3
FILTER_WINDOW_DEFAULT = 3

FILTER_POLY_ORDER_MAX = FILTER_WINDOW_MAX - 1 # fixed
FILTER_POLY_ORDER_MIN = 1
FILTER_POLY_ORDER_DEFAULT = 1

# Values from ARPLS baseline correction method
BASELINE_LAMBDA_MAX = 1e14
BASELINE_LAMBDA_MIN = 1
BASELINE_LAMBDA_DEFAULT = 1e5 # fixed

BASELINE_DIFF_ORDER_MAX = 2
BASELINE_DIFF_ORDER_MIN = 1 # fixed
BASELINE_DIFF_ORDER_DEFAULT = 2 # fixed

BASELINE_ITERATIONS_MAX = 100
BASELINE_ITERATIONS_MIN = 1
BASELINE_ITERATIONS_DEFAULT = 50 # fixed

BASELINE_TOLERANCE_MAX = 1
BASELINE_TOLERANCE_MIN = 1e-9
BASELINE_TOLERANCE_DEFAULT = 1e-3 # fixed

ENABLE_DARK_SUBTRACTION_DEFAULT = False
ENABLE_SPIKE_CORRECTION_DEFAULT = False
ENABLE_FILTERING_DEFAULT = False
ENABLE_BASELINE_CORRECTION_DEFAULT = False
ENABLE_NORMALIZATION_DEFAULT = False

class SignalProcessor:
    ################################################################################
    # CONSTRUCTOR AND INITIALIZATION
    ################################################################################
    def __init__(self):
        # Individual spectrum
        self.dark_n_samples = DARK_N_SAMPLES_DEFAULT
        self.spike_window = SPIKE_WINDOW_DEFAULT
        self.spike_T_multiplier = SPIKE_T_MULTIPLIER_DEFAULT

        # N spectra
        self.n_spectra = N_SPECTRA_DEFAULT
        self.filter_window = FILTER_WINDOW_DEFAULT
        self.filter_poly_order = FILTER_POLY_ORDER_DEFAULT
        self.baseline_lambda = BASELINE_LAMBDA_DEFAULT
        self.baseline_diff_order = BASELINE_DIFF_ORDER_DEFAULT
        self.baseline_iterations = BASELINE_ITERATIONS_DEFAULT
        self.baseline_tolerance = BASELINE_TOLERANCE_DEFAULT

        self.enable_dark_subtraction = ENABLE_DARK_SUBTRACTION_DEFAULT
        self.enable_spike_correction = ENABLE_SPIKE_CORRECTION_DEFAULT
        self.enable_filtering = ENABLE_FILTERING_DEFAULT
        self.enable_baseline_correction = ENABLE_BASELINE_CORRECTION_DEFAULT
        self.enable_normalization = ENABLE_NORMALIZATION_DEFAULT

        self.load_config()

        self.dark_buffer = []
        self.spectra_buffer = []
        self.last_processed_data = None

    ####################################################################################
    # SETTERS
    ####################################################################################
    def set_dark_n_samples(self, value):
        val = int(value)
        val = min(max(val, DARK_N_SAMPLES_MIN), DARK_N_SAMPLES_MAX)
        self.dark_n_samples = val
        print(f"Dark samples = {val}")

    def set_spike_window(self, value):
        val = int(value)
        if val % 2 == 0:
            val += 1 
        val = min(max(val, SPIKE_WINDOW_MIN), SPIKE_WINDOW_MAX)
        self.spike_window = val
        print(f"Spike window = {val}")

    def set_spike_T_multiplier(self, value):
        val = float(value)
        val = min(max(val, SPIKE_T_MULTIPLIER_MIN), SPIKE_T_MULTIPLIER_MAX)
        self.spike_T_multiplier = val
        print(f"Spike threshold T = {val:.2f}")

    def set_n_spectra(self, value):
        val = int(value)
        val = min(max(val, N_SPECTRA_MIN), N_SPECTRA_MAX)
        self.n_spectra = val
        print(f"N spectra = {val}")

    def set_filter_window(self, value):
        val = int(value)
        if val % 2 == 0:
            val += 1 
        val = min(max(val, FILTER_WINDOW_MIN), FILTER_WINDOW_MAX)
        self.filter_window = val
        print(f"Filter window = {val}")

    def set_filter_poly_order(self, value):
        val = int(value)
        val = min(max(val, FILTER_POLY_ORDER_MIN), FILTER_POLY_ORDER_MAX)
        val = min(val, self.filter_window - 1)
        self.filter_poly_order = val
        print(f"Filter polynomial order = {val}")

    def set_baseline_lambda(self, value):
        val = float(value)
        val = min(max(val, BASELINE_LAMBDA_MIN), BASELINE_LAMBDA_MAX)
        self.baseline_lambda = val
        print(f"Baseline lambda = {val:.1e}")

    def set_baseline_diff_order(self, value):
        val = int(value)
        val = min(max(val, BASELINE_DIFF_ORDER_MIN), BASELINE_DIFF_ORDER_MAX)
        self.baseline_diff_order = val
        print(f"Baseline difference order = {val}")

    def set_baseline_iterations(self, value):
        val = int(value)
        val = min(max(val, BASELINE_ITERATIONS_MIN), BASELINE_ITERATIONS_MAX)
        self.baseline_iterations = val
        print(f"Baseline iterations = {val}")

    def set_baseline_tolerance(self, value):
        val = float(value)
        val = min(max(val, BASELINE_TOLERANCE_MIN), BASELINE_TOLERANCE_MAX)
        self.baseline_tolerance = val
        print(f"Baseline tolerance = {val:.2e}")

    def set_enable_dark_subtraction(self, value):
        self.enable_dark_subtraction = bool(value)
        print(f"Enable dark subtraction = {self.enable_dark_subtraction}")

    def set_enable_spike_correction(self, value):
        self.enable_spike_correction = bool(value)
        print(f"Enable spike correction = {self.enable_spike_correction}")

    def set_enable_filtering(self, value):
        self.enable_filtering = bool(value)
        print(f"Enable filtering = {self.enable_filtering}")

    def set_enable_baseline_correction(self, value):
        self.enable_baseline_correction = bool(value)
        print(f"Enable baseline correction = {self.enable_baseline_correction}")

    def set_enable_normalization(self, value):
        self.enable_normalization = bool(value)
        print(f"Enable normalization = {self.enable_normalization}")

    def save_config(self, filename="config.json"):
        config = {
            "dark_n_samples": self.dark_n_samples,
            "spike_window": self.spike_window,
            "spike_T_multiplier": self.spike_T_multiplier,
            "n_spectra": self.n_spectra,
            "filter_window": self.filter_window,
            "filter_poly_order": self.filter_poly_order,
            "baseline_lambda": self.baseline_lambda,
            "baseline_diff_order": self.baseline_diff_order,
            "baseline_iterations": self.baseline_iterations,
            "baseline_tolerance": self.baseline_tolerance,
            "enable_dark_subtraction": self.enable_dark_subtraction,
            "enable_spike_correction": self.enable_spike_correction,
            "enable_filtering": self.enable_filtering,
            "enable_baseline_correction": self.enable_baseline_correction,
            "enable_normalization": self.enable_normalization,
        }

        path = Path(__file__).parent / filename

        with open(path, "w") as f:
            json.dump(config, f, indent=4)

        print(f"Configuration saved to {path}")

    ####################################################################################
    # PROCESSING
    ####################################################################################
    def process_single_spectrum(self, data):
        processed = ADC_MAX - data.copy()

        if self.enable_dark_subtraction:
            processed = self.subtract_dark(processed)

        if self.enable_spike_correction:
            processed = self.correct_spikes(processed)

        return processed
    
    def process_spectrum_batch(self, spectra):
        # spectra: array/list con forma (n_spectra, n_pixels)
        
        spectra = np.asarray(spectra)

        avg = np.mean(spectra, axis=0)

        if spectra.shape[0] > 1:
            std = np.std(spectra, axis=0, ddof=1)
        else:
            std = np.zeros_like(avg)

        processed = avg.copy()

        if self.enable_filtering:
            processed = self.apply_smoothing(processed)

        if self.enable_baseline_correction:
            processed = self.apply_baseline_correction(processed)

        # Peak detection is requested explicitly by the GUI, not here.
        peaks = None

        if self.enable_normalization:
            processed = self.normalize(processed)

        return processed, peaks, avg, std

    def process(self, data):
        single = self.process_single_spectrum(data)

        self.spectra_buffer.append(single)

        if len(self.spectra_buffer) < self.n_spectra:
            return None, None, None, None

        spectra = np.array(self.spectra_buffer)
        self.spectra_buffer.clear()

        processed, peaks, avg, std = self.process_spectrum_batch(spectra)

        return processed, peaks, avg, std
    
    ##################################################################################
    # APLIERS
    ##################################################################################
    def subtract_dark(self, data):
        if len(self.dark_buffer) == 0:
            return np.asarray(data, dtype=float).copy()

        dark = np.mean(
            np.asarray(self.dark_buffer, dtype=float),
            axis=0,
        )

        corrected = (
            np.asarray(data, dtype=float)
            - dark
        )

        return np.clip(corrected, 0, None)
    
    def correct_spikes(self, data):
        y = np.asarray(data, dtype=float)
        # median_filter returns an array of the same shape as the input, with the median value computed over a local window defined by 'size'.
        # "nearest" mode means that for positions outside the array, the nearest edge value is used ([? ? 10 ...] == [10 10 10 ...]).
        local_median = median_filter(y, size=self.spike_window, mode="nearest")

        # Compute the residual (difference between the original signal and the local median)
        residual = y - local_median

        abs_residual = np.abs(residual)
        # MAD = median(|r - median(r)|)
        local_mad = median_filter(abs_residual, size=self.spike_window, mode="nearest")
        sigma = 1.4826 * local_mad

        # Calculate threshold as defined (T * sigma)
        threshold = self.spike_T_multiplier * sigma

        # Mark the positions where the absolute residual exceeds the threshold and sigma is greater than zero
        mask = (sigma > 0) & (abs_residual > threshold)

        corrected = y.copy()
        # Only replace the values at the positions marked by the mask with the local median values
        corrected[mask] = local_median[mask]
        return corrected

    def apply_smoothing(self, data):
        data_ = data.astype(float)
        smoothed = savgol_filter(
            data_,
            window_length=self.filter_window,
            polyorder=self.filter_poly_order,
        )

        return smoothed
    
    def normalize(self, data):
        data_ = np.asarray(data, dtype=float)
        minimum = np.min(data_)
        maximum = np.max(data_)
        span = maximum - minimum
        if span == 0:
            return np.zeros_like(data_)
        return (data_ - minimum) / span

    def apply_baseline_correction(self, data):        
        data_ = data.astype(float)

        baseline_fitter = Baseline(x_data=np.arange(len(data)))
        estimated_baseline, params = baseline_fitter.arpls(data_, lam=self.baseline_lambda, diff_order=self.baseline_diff_order, max_iter=self.baseline_iterations, tol=self.baseline_tolerance)

        corrected = data_ - estimated_baseline

        return corrected

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
    
    def load_config(self, filename="config.json"):
        path = Path(__file__).parent / filename

        if not path.exists():
            print("Configuration file not found. Using defaults.")
            return

        with open(path, "r") as f:
            config = json.load(f)

        self.dark_n_samples = config.get("dark_n_samples", self.dark_n_samples)
        self.spike_window = config.get("spike_window", self.spike_window)
        self.spike_T_multiplier = config.get("spike_T_multiplier", self.spike_T_multiplier)
        self.n_spectra = config.get("n_spectra", self.n_spectra)

        self.filter_window = config.get("filter_window", self.filter_window)
        self.filter_poly_order = config.get("filter_poly_order", self.filter_poly_order)

        self.baseline_lambda = config.get("baseline_lambda", self.baseline_lambda)
        self.baseline_diff_order = config.get("baseline_diff_order", self.baseline_diff_order)
        self.baseline_iterations = config.get("baseline_iterations", self.baseline_iterations)
        self.baseline_tolerance = config.get("baseline_tolerance", self.baseline_tolerance)

        self.enable_dark_subtraction = config.get("enable_dark_subtraction", self.enable_dark_subtraction)
        self.enable_spike_correction = config.get("enable_spike_correction", self.enable_spike_correction)
        self.enable_filtering = config.get("enable_filtering", self.enable_filtering)
        self.enable_baseline_correction = config.get("enable_baseline_correction", self.enable_baseline_correction)
        self.enable_normalization = config.get("enable_normalization", self.enable_normalization)

        print(f"Configuration loaded from {path}")

    def delete_config(self, filename="config.json"):
        path = Path(__file__).parent / filename

        if path.exists():
            path.unlink()
            print(f"Configuration file {path} deleted.")
        else:
            print(f"Configuration file {path} does not exist.")

        self.__init__()

        