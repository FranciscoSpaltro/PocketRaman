import numpy as np

def gaussian(x, center, amplitude, sigma):
    """
    Gaussian peak.
    """
    return amplitude * np.exp(-0.5 * ((x - center) / sigma) ** 2)


def generate_fake_raman_raw(
    n_pixels=3694,
    peaks=None,
    baseline_offset=800,
    baseline_slope=0.08,
    baseline_curve=300,
    noise_std=20,
    adc_max=4095,
    seed=None,
):
    """
    Generate a fake raw Raman-like CCD spectrum.

    Returns
    -------
    pixels : np.ndarray
        Pixel axis.
    raw_counts : np.ndarray
        Simulated raw ADC counts.
    clean_signal : np.ndarray
        Signal without noise.
    baseline : np.ndarray
        Simulated baseline.
    """

    rng = np.random.default_rng(seed)

    pixels = np.arange(n_pixels)

    # Normalize x from 0 to 1 to make baseline shape easier
    x_norm = pixels / (n_pixels - 1)

    # Baseline: offset + slope + broad curved background
    baseline = (
        baseline_offset
        + baseline_slope * pixels
        + baseline_curve * np.exp(-3.0 * x_norm)
    )

    # Default fake Raman peaks
    if peaks is None:
        peaks = [
            # center_pixel, amplitude, sigma_pixels
            (600, 300, 8),
            (950, 700, 12),
            (1450, 450, 10),
            (2100, 900, 18),
            (2800, 500, 14),
            (3300, 250, 10),
        ]

    signal = baseline.copy()

    for center, amplitude, sigma in peaks:
        signal += gaussian(pixels, center, amplitude, sigma)

    noise = rng.normal(loc=0, scale=noise_std, size=n_pixels)

    raw_counts = signal + noise

    # Simulate ADC clipping
    raw_counts = np.clip(raw_counts, 0, adc_max)

    # Simulate integer ADC output
    raw_counts = raw_counts.astype(np.uint16)

    return pixels, raw_counts, signal, baseline