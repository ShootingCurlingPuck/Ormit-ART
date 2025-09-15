from PyQt6.QtCore import QObject, pyqtSignal


class GlobalSignals(QObject):
    update_message = pyqtSignal(str)


# Create a global instance of the signals
global_signals = GlobalSignals()
