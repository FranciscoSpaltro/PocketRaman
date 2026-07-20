def raman_to_nm(raman_shift, laser_wavelength):
    """
    Convert Raman shift (in cm^-1) to wavelength (in nm).

    Parameters:
    - raman_shift: Raman shift in cm^-1
    - laser_wavelength: Laser wavelength in nm

    Returns:
    - Wavelength in nm corresponding to the given Raman shift.
    """
    return 1e7 / (1e7 / laser_wavelength - raman_shift)

# https://sdbs.db.aist.go.jp/RamanSpectralView.aspx?fname=RM29&sdbsno=2149
isopropyl_alcohol_raman_peaks = [820, 955, 1132, 1464, 2881, 2919, 2938, 2972]
laser_wavelength = 532 #nm

print("Isopropyl Alcohol Raman Peaks (cm^-1):", isopropyl_alcohol_raman_peaks)
print("Corresponding Wavelengths (nm):")
for peak in isopropyl_alcohol_raman_peaks:
    print(f"  {peak} cm^-1 -> {raman_to_nm(peak, laser_wavelength)} nm")