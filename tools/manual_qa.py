"""Launch an isolated, labeled UI fixture for interactive acceptance testing."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from PySide6.QtWidgets import QApplication
from grok.storage import Settings
from grok.ui import Window
root = Path(__file__).resolve().parents[1] / 'build/qa-fixtures'
root.mkdir(parents=True, exist_ok=True)
folder = root / 'Files'
folder.mkdir(exist_ok=True)
(folder / 'Destination').mkdir(exist_ok=True)
(folder / 'Alpha.txt').write_text('Disposable GROK QA fixture.\n')
(folder / 'Beta.txt').write_text('Second disposable fixture.\n')
app = QApplication([])
settings = Settings(root / 'settings')
settings.data.update(default_path=str(folder), minimized=True, animation=False, auto_hide=False, hotkey='Ctrl+Alt+J')
window = Window(settings, test_mode=True)
window.setWindowTitle('GROK QA — disposable fixtures')
window.hotkey()
window.show()
app.exec()
