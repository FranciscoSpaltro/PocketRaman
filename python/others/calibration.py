import numpy as np

pixels = np.array([
    1615,
    1703,
    1779,
    1840,
    1884,
    1904,
    1950,
    1999,
    2032,
    2061,
    2126,
    2242,
    2306,
    2378,
    2412,
    2606,
    2701,
], dtype=float)

wavelengths = np.array([
    585.249,
    594.483,
    603.000,
    609.616,
    614.306,
    616.359,
    621.728,
    626.650,
    630.479,
    633.443,
    640.225,
    653.288,
    659.895,
    667.828,
    671.704,
    692.947,
    703.241,
], dtype=float)

coefficients = np.polyfit(pixels, wavelengths, deg=1)

slope, intercept = coefficients

print(f"Wavelength = {slope:.9f} · pixel + {intercept:.6f}")

estimated = np.polyval(coefficients, pixels)
residuals = wavelengths - estimated

for pixel, wavelength, estimated_wavelength, error in zip(
    pixels,
    wavelengths,
    estimated,
    residuals,
):
    print(
        f"Pixel {pixel:4.0f}: "
        f"reference={wavelength:8.3f} nm, "
        f"estimated={estimated_wavelength:8.3f} nm, "
        f"error={error:+.3f} nm"
    )

# For grade 1:
# wavelength_nm = 0.1083552 * pixel + 410.2815

# For grade 2:
# wavelength_nm = (1.79e-6 * pixel**2 + 0.10069 * pixel + 418.28)