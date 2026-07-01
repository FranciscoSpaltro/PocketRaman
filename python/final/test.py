from fake_spectra import generate_fake_raman_raw
import matplotlib.pyplot as plt
from pybaselines import Baseline
from scipy.signal import savgol_filter
from scipy.signal import find_peaks
import numpy as np

if __name__ == "__main__":
    pixels, raw_counts, clean_signal, true_baseline = generate_fake_raman_raw(
        n_pixels=3694,                  # Cantidad de muestras del CCD
        peaks=None,                     # [(centro, amplitud, sigma), ...] Si None, se usan picos por defecto
        baseline_offset=800,            # Nivel medio del detector
        baseline_slope=0.1,            # Hace que el baseline tenga una pendiente de izquierda a derecha igual a slope * n_pixels
        baseline_curve=150,             # Agrega una curva de fondo al baseline (simula fluorescencia)
        noise_std=20,                   # Ruido gaussiano agregado a la señal
        adc_max=4095,                   # Clip de la señal
        seed=None,                      # Con None, cada ejecución genera un ruido diferente
    )

    raw_counts = raw_counts.astype(float)

    baseline_fitter = Baseline(x_data=pixels)
    estimated_baseline, params = baseline_fitter.arpls(raw_counts, lam=1e6)

    corrected = raw_counts - estimated_baseline
    smoothed = savgol_filter(
        corrected,
        window_length=21,   # Cuantos puntos usa para suavizar. Debe ser impar y mayor que polyorder.
        polyorder=3,        # Orden del polinomio usado para suavizar. Debe ser menor que window_length.
    )

    noise = 1.4826 * np.median(np.abs(smoothed - np.median(smoothed)))
    height_threshold = 5 * noise
    prominence_threshold = 3 * noise
    peaks, props = find_peaks(
        smoothed,
        height=height_threshold,
        prominence=prominence_threshold,
        distance=20,
        width=2,
    )

    print(f"Detected peaks at pixels: {peaks}")
    print(f"Peak heights: {props['peak_heights']}")
    
    plt.figure(figsize=(12, 6))
    plt.plot(pixels, raw_counts, label="Raw Counts", alpha=0.7)
    #plt.plot(pixels, clean_signal, label="Clean Signal", alpha=0.7)
    #plt.plot(pixels, true_baseline, label="True Fake Baseline", alpha=0.7)
    plt.plot(pixels, estimated_baseline, label="Estimated Baseline", alpha=0.7)
    #plt.plot(pixels, corrected, label="Corrected")
    plt.plot(pixels, smoothed, label="Smoothed")
    plt.xlabel("Pixel")
    plt.ylabel("ADC Counts")
    plt.title("Fake Raman-like CCD Spectrum")
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.show()

    