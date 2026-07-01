import sys
from PySide6.QtWidgets import (QApplication)
from gui import RamanGUI
   

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RamanGUI()
    window.show()
    sys.exit(app.exec())