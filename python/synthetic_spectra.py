import numpy as np


def gaussian(x, center, amplitude, sigma):
    return amplitude * np.exp(-0.5 * ((x - center) / sigma) ** 2)


def generate_synthetic_raman_raw(
    n_pixels=3694,
    peaks=None,
    adc_max=4095,
    baseline_offset=700,
    fluorescence_amp=1800,
    read_noise_std=18,
    shot_noise_scale=1.0,
    fixed_pattern_std=0.025,
    dark_current_level=40,
    hot_pixel_prob=0.003,
    dead_pixel_prob=0.001,
    cosmic_ray_prob=0.001,
    ripple_amp=25,
    ripple_period_px=95,
    seed=None,
):
    rng = np.random.default_rng(seed)
    px = np.arange(n_pixels)
    x = px / (n_pixels - 1)

    if peaks is None:
        peaks = [
            (620, 180, 7),
            (980, 420, 11),
            (1430, 240, 9),
            (2080, 620, 16),
            (2810, 300, 13),
            (3260, 120, 8),
        ]

    # Fluorescencia / baseline no simpática
    baseline = (
        baseline_offset
        + fluorescence_amp * np.exp(-2.8 * x)
        + 250 * x
        + 120 * np.sin(2 * np.pi * x * 0.7 + 1.2)
    )

    signal = baseline.copy()

    for center, amplitude, sigma in peaks:
        signal += gaussian(px, center, amplitude, sigma)

    # Dark current con estructura lenta
    dark = (
        dark_current_level
        + 15 * np.sin(2 * np.pi * px / n_pixels * 3.0)
        + rng.normal(0, 4, n_pixels)
    )

    signal += dark

    # Fixed pattern noise: ganancia distinta por pixel
    pixel_gain = rng.normal(1.0, fixed_pattern_std, n_pixels)
    signal *= pixel_gain

    # Ripple electrónico
    ripple = ripple_amp * np.sin(2 * np.pi * px / ripple_period_px)
    signal += ripple

    # Shot noise aproximado
    shot_noise = rng.normal(0, np.sqrt(np.maximum(signal, 0)) * shot_noise_scale)

    # Ruido de lectura
    read_noise = rng.normal(0, read_noise_std, n_pixels)

    raw = signal + shot_noise + read_noise

    # Hot pixels
    hot_mask = rng.random(n_pixels) < hot_pixel_prob
    raw[hot_mask] += rng.uniform(300, 2500, hot_mask.sum())

    # Dead pixels
    dead_mask = rng.random(n_pixels) < dead_pixel_prob
    raw[dead_mask] *= rng.uniform(0.0, 0.15, dead_mask.sum())

    # Cosmic rays / spikes finitos
    cosmic_mask = rng.random(n_pixels) < cosmic_ray_prob
    raw[cosmic_mask] += rng.uniform(800, 3500, cosmic_mask.sum())

    # Saturación ADC
    raw = np.clip(raw, 0, adc_max)

    return px, raw.astype(np.uint16), signal, baseline