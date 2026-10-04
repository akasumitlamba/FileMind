"""Capture the real UI using synthetic fixtures, never personal files."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from grok.ui import Window
from grok.storage import Settings

root = Path(__file__).resolve().parents[1]
app = QApplication([])
from PySide6.QtGui import QFontDatabase
QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeuib.ttf")
with tempfile.TemporaryDirectory(prefix='GROK-preview-') as temp:
    folder = Path(temp) / 'Projects'
    folder.mkdir()
    for name in ['Brand assets', 'Client work', 'Documents', 'Research', 'Screenshots']:
        (folder / name).mkdir()
    for name, content in {'Getting started.txt':'Welcome to GROK.', 'Project notes.md':'# Notes', 'Resources.csv':'Name,Type', 'Weekly plan.txt':'Monday: review'}.items():
        (folder / name).write_text(content)
    settings = Settings(Path(temp) / 'settings')
    settings.data['default_path'] = str(folder)
    settings.data['minimized'] = False
    window = Window(settings, test_mode=True)
    for _ in range(25):
        app.processEvents()
        QTest.qWait(40)
    # The path remains truthful; fixture name is shortened only in the path display
    # to avoid irrelevant temporary directory noise in product artwork.
    window.address.setText('Projects · demonstration files')
    window.make_crumbs(str(folder))
    window.resize(420, 820)
    app.processEvents()
    out = root / 'website/assets'
    out.mkdir(parents=True, exist_ok=True)
    window.grab().save(str(out / 'app-panel.png'))
    window.set_view_mode('grid', persist=False)
    app.processEvents()
    window.grab().save(str(out / 'app-grid.png'))
    window.set_view_mode('list', persist=False)
    window.toggle_wide()
    app.processEvents()
    window.grab().save(str(out / 'app-workspace.png'))
    window.toggle_wide()
    window.queue_attachments([str(folder / 'Getting started.txt'), str(folder / 'Project notes.md')])
    window.open_chat()
    window.prompt.setPlainText("Help me organize these notes.")
    app.processEvents()
    window.grab().save(str(out / 'app-chat.png'))
    window.set_expanded(False, False)
    app.processEvents()
    window.grab().save(str(out / 'app-dock.png'))
    window.pool.waitForDone()
    window.hide()
    window.model.setRootPath('')
    window.deleteLater()
    app.processEvents()
