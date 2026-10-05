import time
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from grok.ui import Window
from grok.storage import Settings


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def settle(app, window):
    deadline = time.monotonic() + 8
    while window.jobs and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(20)
    assert not window.jobs
    QTest.qWait(250)
    app.processEvents()


def test_window_workflows(app, tmp_path):
    folder = tmp_path / 'files'; folder.mkdir()
    (folder / 'alpha.txt').write_text('alpha')
    (folder / 'beta.txt').write_text('beta')
    (folder / 'sub').mkdir()
    s = Settings(tmp_path / 'settings')
    s.data['default_path'] = str(folder)
    w = Window(s, test_mode=True)
    settle(app, w)
    assert w.width() == 42
    w.set_expanded(True)
    assert w.width() == 420
    assert w.geometry().right() == w.target_screen().availableGeometry().right()
    w.search.setText('alpha')
    app.processEvents()
    assert w.proxy.rowCount(w.view.rootIndex()) == 1
    w.search.clear()
    w.navigate(str(folder / 'sub')); settle(app, w)
    w.go_history(-1); settle(app, w)
    assert w.current == str(folder)
    w.go_history(1); settle(app, w)
    assert w.current == str(folder / 'sub')
    w.up(); settle(app, w)
    w.toggle_favorite()
    assert str(folder) in Settings(s.root).data['favorites']
    w.address.setText(str(folder / 'sub'))
    w.edit_path()
    w.address.setText(str(folder / 'sub'))
    QTest.keyClick(w.address, Qt.Key_Return); settle(app, w)
    assert w.current == str(folder / 'sub')
    w.navigate(str(folder / 'missing')); settle(app, w)
    assert w.current == str(folder / 'sub')
    w.set_expanded(False)
    assert w.width() == 42
    w.hide()
    w.deleteLater()
    app.processEvents()


def test_clipboard_and_background_transfer(app, tmp_path):
    folder = tmp_path / 'files'; folder.mkdir()
    source = folder / 'source.txt'; source.write_text('fixture')
    dest = folder / 'dest'; dest.mkdir()
    s = Settings(tmp_path / 'settings')
    s.data['default_path'] = str(folder)
    w = Window(s, test_mode=True)
    settle(app, w)
    from grok.browser import file_mime
    QApplication.clipboard().setMimeData(file_mime([str(source)], cut=True))
    w.navigate(str(dest)); settle(app, w)
    w.paste(); settle(app, w)
    assert (dest / source.name).read_text() == 'fixture'
    assert not source.exists()
    assert w.operation is None
    assert not QApplication.clipboard().mimeData() or not QApplication.clipboard().mimeData().hasUrls()
    w.hide(); w.deleteLater(); app.processEvents()


def test_workspace_grid_columns_and_chat(app, tmp_path):
    folder = tmp_path / 'files'; folder.mkdir()
    (folder / 'a.txt').write_text('a')
    settings = Settings(tmp_path / 'prefs')
    settings.data['default_path'] = str(folder)
    w = Window(settings, test_mode=True)
    settle(app, w)
    assert w.width() == 42 and w.height() == 86
    assert not w.attachments
    w.open_chat(False)
    assert not w.attachments
    assert w.tabs.currentWidget() is w.chat_page
    assert w.chat_notice.isVisible()
    w.tabs.setCurrentWidget(w.files_page)
    w.set_view_mode('grid')
    assert w.active_view() is w.grid
    assert w.grid.model().rowCount(w.grid.rootIndex()) == 1
    w.set_sort(1, True)
    assert w.proxy.sortColumn() == 1
    assert w.proxy.sortOrder() == Qt.DescendingOrder
    w.set_view_mode('list')
    assert w.column_limit() == 1
    w.toggle_wide(); app.processEvents()
    assert w.geometry() == w.target_screen().availableGeometry()
    assert w.workspace.count() == 2
    assert all(not w.view.isColumnHidden(c) for c in [1, 2, 3])
    assert w.chat_page.isVisible()
    w.toggle_wide(); app.processEvents()
    assert w.width() == 420
    assert w.tabs.indexOf(w.chat_page) == 1
    assert sum(not w.view.isColumnHidden(c) for c in [1, 2, 3]) <= 1
    w.hide(); w.deleteLater(); app.processEvents()


def test_attachments_and_persistent_history(app, tmp_path):
    folder = tmp_path / 'files'; folder.mkdir()
    first = folder / 'first.txt'; first.write_text('First content', encoding='utf-8')
    second = folder / 'second.md'; second.write_text('Second content', encoding='utf-8')
    settings = Settings(tmp_path / 'prefs')
    settings.data['default_path'] = str(folder)
    w = Window(settings, test_mode=True); settle(app, w)
    w.queue_attachments([str(first), str(second), str(first)])
    assert w.attachments == [str(first), str(second)]
    assert w.attachment_box.count() == 2
    assert 'First content' in w.reviewed_attachment_text()
    assert 'Second content' in w.reviewed_attachment_text()
    assert not w.chat_messages  # Attaching does not submit or create history.
    w.remove_attachment(str(first))
    assert w.attachments == [str(second)]
    w.chat_messages = [{'role':'user', 'content':'Remember this'}, {'role':'assistant', 'content':'Saved fixture'}]
    w.save_chat()
    w.provider.setCurrentText('Gemini')
    assert w.chat_messages == []
    w.provider.setCurrentText('OpenAI')
    assert w.chat_messages[0]['content'] == 'Remember this'
    assert not w.tabs.tabBar().isVisible()
    w.hide(); w.deleteLater(); app.processEvents()
    restored = Window(Settings(tmp_path / 'prefs'), test_mode=True); settle(app, restored)
    assert restored.chat_messages[1]['content'] == 'Saved fixture'
    restored.clear_chat()
    restored.load_chat()
    assert restored.chat_messages == []
    restored.hide(); restored.deleteLater(); app.processEvents()


def test_selection_to_chat_and_sort_anchor(app, tmp_path, monkeypatch):
    from PySide6.QtCore import QItemSelectionModel
    from PySide6.QtWidgets import QMenu
    folder = tmp_path / 'files'; folder.mkdir()
    file = folder / 'note.txt'; file.write_text('fixture')
    settings = Settings(tmp_path / 'prefs'); settings.data['default_path'] = str(folder)
    w = Window(settings, test_mode=True); settle(app, w)
    w.set_expanded(True)
    index = w.proxy.mapFromSource(w.model.index(str(file)))
    w.view.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
    assert 'AI Chat (1)' in w.chat_switch.text()
    w.open_chat()
    assert w.attachments == [str(file).replace('\\', '/')] or w.attachments == [str(file)]
    assert w.tabs.currentWidget() is w.chat_page
    positions = []
    class CapturedMenu(QMenu):
        def exec(self, point):
            positions.append(point)
    monkeypatch.setattr('grok.ui.QMenu', CapturedMenu)
    w.search_options(w.sort_button)
    assert positions[-1] == w.sort_button.mapToGlobal(w.sort_button.rect().bottomLeft())
    w.hide(); w.deleteLater(); app.processEvents()


def test_tree_and_checkbox_selection(app, tmp_path):
    from PySide6.QtCore import QPoint
    folder = tmp_path / 'files'; folder.mkdir()
    sub = folder / 'Folder'; sub.mkdir()
    child = sub / 'child.txt'; child.write_text('fixture')
    settings = Settings(tmp_path / 'prefs'); settings.data['default_path'] = str(folder)
    w = Window(settings, test_mode=True); settle(app, w); w.set_expanded(True)
    index = w.proxy.mapFromSource(w.model.index(str(sub)))
    source = w.model.index(str(sub))
    if w.model.canFetchMore(source):
        w.model.fetchMore(source)
    deadline = time.monotonic() + 5
    while w.proxy.rowCount(index) != 1 and time.monotonic() < deadline:
        QTest.qWait(50); app.processEvents()
    index = w.proxy.mapFromSource(w.model.index(str(sub)))
    w.view.expand(index); app.processEvents()
    assert w.view.isExpanded(index)
    assert w.proxy.rowCount(index) == 1
    assert not w.view.selection_mode
    w.select_action.setChecked(True)
    assert w.view.selection_mode
    rect = w.view.visualRect(index)
    point = QPoint(rect.left() + 8, rect.center().y())
    QTest.mouseClick(w.view.viewport(), Qt.LeftButton, pos=point)
    assert len(w.view.paths()) == 1
    QTest.mouseClick(w.view.viewport(), Qt.LeftButton, pos=point)
    assert not w.view.paths()
    w.open_chat(False)
    assert not w.attachments
    w.hide(); w.deleteLater(); app.processEvents()

def test_empty_folders_and_independent_dock(app, tmp_path):
    folder = tmp_path / 'files'; folder.mkdir()
    empty = folder / 'Empty'; empty.mkdir()
    populated = folder / 'Populated'; populated.mkdir()
    (populated / 'note.txt').write_text('fixture')
    settings = Settings(tmp_path / 'prefs'); settings.data['default_path'] = str(folder)
    w = Window(settings, test_mode=True); settle(app, w)
    QTest.qWait(500)
    assert w.mask().boundingRect().getRect() == (1, 1, 40, 84)
    assert not w.proxy.hasChildren(w.proxy.mapFromSource(w.model.index(str(empty))))
    assert w.proxy.hasChildren(w.proxy.mapFromSource(w.model.index(str(populated))))
    assert not w.view.selection_mode and not w.grid.selection_mode
    for _ in range(3):
        w.dock_chat.click(); app.processEvents()
        assert w.tabs.currentWidget() is w.chat_page
        assert not w.attachments
        w.set_expanded(False, False); app.processEvents()
        assert w.size().width() == 42 and w.size().height() == 86
        assert w.mask().boundingRect().height() == 84
        assert w.dock_chat.geometry().bottom() <= w.dock.height()
        w.dock_files.click(); app.processEvents()
        assert w.tabs.currentWidget() is w.files_page
        assert w.mask().isEmpty()
        w.set_expanded(False, False)
    w.select_action.setChecked(True)
    assert w.view.selection_mode and w.grid.selection_mode
    w.select_action.setChecked(False)
    assert not w.view.selection_mode and not w.grid.selection_mode
    w.hide(); w.deleteLater(); app.processEvents()

def test_workspace_window_controls(app, tmp_path, monkeypatch):
    s = Settings(tmp_path / 'prefs'); s.data['default_path'] = str(tmp_path)
    w = Window(s, test_mode=True); settle(app, w)
    assert w.window_controls.isHidden()
    w.toggle_wide(); app.processEvents()
    assert w.window_controls.isVisible()
    area = w.target_screen().availableGeometry()
    assert w.geometry() == area
    w.maximize_button.click(); app.processEvents()
    assert area.contains(w.geometry()) and w.width() < area.width()
    assert w.maximize_button.toolTip() == 'Maximize'
    w.maximize_button.click(); app.processEvents()
    assert w.geometry() == area
    w.minimize_button.click(); app.processEvents()
    assert w.isMinimized()
    w.auto_collapse()
    assert w.expanded and w.wide
    w.showNormal(); app.processEvents()
    quit_calls = []
    monkeypatch.setattr(QApplication.instance(), 'quit', lambda: quit_calls.append(True))
    w.close_button.click()
    assert quit_calls == [True]
    w.toggle_wide(); app.processEvents()
    assert w.window_controls.isHidden()
    w.hide(); w.deleteLater(); app.processEvents()
