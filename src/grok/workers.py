import threading
import ctypes
from PySide6.QtCore import QObject, QRunnable, Signal


class Signals(QObject):
    done = Signal(object)
    failed = Signal(str)
    progress = Signal(str)


class Job(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.signals = Signals()
        self.cancel = threading.Event()

    def run(self):
        initialized = ctypes.windll.ole32.CoInitializeEx(None, 2) in (0, 1)
        try:
            self.signals.done.emit(self.fn(self))
        except PermissionError:
            self.signals.failed.emit("Windows denied access. Check permissions or close apps using this item.")
        except (FileExistsError, FileNotFoundError, InterruptedError) as exc:
            self.signals.failed.emit(str(exc))
        except OSError as exc:
            self.signals.failed.emit(f"Windows could not finish the operation (error {exc.winerror if hasattr(exc, 'winerror') else exc.errno}). Completed items are retained; refresh before retrying.")
        except Exception as exc:
            self.signals.failed.emit(str(exc) if isinstance(exc, ValueError) else "The operation could not finish. Check your settings and try again.")
        finally:
            if initialized:
                ctypes.windll.ole32.CoUninitialize()
