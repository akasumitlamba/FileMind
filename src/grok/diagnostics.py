"""Explicit --smoke-test only: isolated fixtures, no keys or personal files."""
import json
import tempfile
from pathlib import Path
from PySide6.QtCore import QTimer
from .storage import Settings
from .ui import Window


def smoke_test(app, output):
    fixture = tempfile.TemporaryDirectory(prefix='GROK-smoke-')
    folder = Path(fixture.name) / 'Files'
    folder.mkdir()
    (folder / 'smoke.txt').write_text('GROK disposable package test')
    settings = Settings(Path(fixture.name) / 'settings')
    settings.data['default_path'] = str(folder)
    window = Window(settings, test_mode=True)
    window.setWindowTitle('GROK package smoke test')
    results = {}
    def expanded():
        results['dock_width'] = window.width()
        results['folder_loaded'] = window.current == str(folder)
        results['file_count'] = window.proxy.rowCount(window.view.rootIndex())
        window.set_expanded(True, False)
        QTimer.singleShot(250, finish)
    def finish():
        results['panel_width'] = window.width()
        results['inside_work_area'] = window.target_screen().availableGeometry().contains(window.geometry())
        results['icon_loaded'] = not window.windowIcon().isNull()
        results['item_count_visible'] = window.empty.isVisible() and window.empty.width() > 0
        results['passed'] = (results['dock_width'] == 42 and results['panel_width'] == 420 and results['folder_loaded']
                             and results['file_count'] == 1 and results['inside_work_area'] and results['icon_loaded'] and results['item_count_visible'])
        target = Path(output).absolute()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(results, indent=2), 'utf-8')
        window.grab().save(str(target.with_suffix('.png')))
        window.pool.waitForDone()
        window.hide()
        app.exit(0 if results['passed'] else 1)
    QTimer.singleShot(1800, expanded)
    result = app.exec()
    # Qt releases the model's directory handle when the process exits.
    window.model.setRootPath('')
    window.deleteLater()
    app.processEvents()
    fixture.cleanup()
    return result
