import sys
import ctypes
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QLockFile, QStandardPaths
from grok.ui import Window


def main():
    ctypes.windll.ole32.CoInitialize(None)
    app = QApplication(sys.argv)
    app.setApplicationName("GROK")
    app.setOrganizationName("akasumitlamba")
    app.setQuitOnLastWindowClosed(False)
    if '--smoke-test' in sys.argv:
        from grok.diagnostics import smoke_test
        index = sys.argv.index('--smoke-test')
        if index + 1 >= len(sys.argv):
            return 2
        return smoke_test(app, sys.argv[index + 1])
    lock = QLockFile(QStandardPaths.writableLocation(QStandardPaths.TempLocation) + "/grok-desktop.lock")
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        return 0
    window = Window()
    if "--minimized" in sys.argv:
        window.set_expanded(False, False)
    window.show()
    result = app.exec()
    lock.unlock()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
