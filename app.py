import sys
from PyQt5.QtWidgets import QApplication
from gui.window import MainWindow
import time

def main():
    app = QApplication(sys.argv)
    
    # Allow time for Qt's event loop to initialize first
    window = MainWindow()
    window.show()
    
    # Make sure the WebUIManager is created after the QApplication
    # but before the event loop starts
    
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())