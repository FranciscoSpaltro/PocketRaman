from PySide6.QtWidgets import QMessageBox

def show_smoothing_help(self):
    QMessageBox.information(
        self,
        "Smoothing help",
        """
        <b>Window</b><br>
        Length of the Savitzky-Golay filter window.<br>
        It must be an odd integer.<br><br>

        <b>Poly</b><br>
        Polynomial order used by the filter.<br>
        It must be lower than Window.
        """
    )

def show_baseline_help(self):
    QMessageBox.information(
        self,
        "Baseline λ",
        """
        Controls the smoothness of the baseline estimated by the arPLS algorithm. <br><br>
        Higher values produce a smoother baseline that follows only slow intensity variations.<br>
        Lower values allow the baseline to follow faster changes in the spectrum.<br><br>

        Typical values range from 10⁴ to 10⁸ depending on the spectrum
        """
    )

def show_height_factor_help(self):
    QMessageBox.information(
        self,
        "Height factor",
        """
        Multiplier applied to the estimated noise level (MAD) to define the minimum peak height.<br><br>
        Larger values detect only stronger peaks.<br>
        Smaller values increase sensitivity but may detect noise.
        """
    )

def show_prominence_factor_help(self):
    QMessageBox.information(
        self,
        "Prominence factor",
        """
        Multiplier applied to the estimated noise level (MAD) to define the minimum peak prominence.<br><br>
        Larger values detect only well-defined peaks.<br>
        Smaller values increase sensitivity but may detect noise.
        """
    )

def show_minmum_peak_distance_help(self):
    QMessageBox.information(
        self,
        "Minimum peak distance",
        """
        Minimum distance, in samples, allowed between two detected peaks.<br><br>
        Larger values merge nearby peaks.<br>
        Smaller values allow closely spaced peaks to be detected separately.<br><br>
        Interval: 1 - 3693
        """
    )

def show_peak_width_help(self):
    QMessageBox.information(
        self,
        "Peak width",
        """
        Minimum peak width, in samples.<br><br>
        Larger values reject narrow peaks and spikes.<br>
        Smaller values allow narrower peaks to be detected.<br><br>
        Interval: 1 - 3694
        """
    )