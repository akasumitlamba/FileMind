import os
import struct
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QMimeData, QUrl, QSortFilterProxyModel, QSize, QEvent, QRect, QItemSelectionModel
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QTreeView, QAbstractItemView, QApplication, QListView, QStyledItemDelegate, QStyleOptionViewItem, QStyleOptionButton, QStyle


class SelectionDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        show = index.column() == 0 and getattr(self.parent(), "selection_mode", False)
        if show:
            opt.rect.adjust(22, 0, 0, 0)
        super().paint(painter, opt, index)
        if show:
            check = QStyleOptionButton()
            check.rect = QRect(option.rect.left() + 3, option.rect.center().y() - 7, 14, 14)
            check.state = QStyle.State_Enabled | (QStyle.State_On if option.state & QStyle.State_Selected else QStyle.State_Off)
            QApplication.style().drawControl(QStyle.CE_CheckBox, check, painter)



class FileFilter(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.query = ""
        self.root = ""
        self.extensions = True
        self.setDynamicSortFilter(True)

    def hasChildren(self, parent):
        if parent.isValid():
            return self.sourceModel().rowCount(self.mapToSource(parent)) > 0
        return super().hasChildren(parent)

    def filterAcceptsRow(self, row, parent):
        model = self.sourceModel()
        index = model.index(row, 0, parent)
        if os.path.normcase(os.path.normpath(model.filePath(parent))) != os.path.normcase(os.path.normpath(self.root)):
            return True
        return self.query.casefold() in model.fileName(index).casefold()

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and index.column() == 0 and not self.extensions:
            source = self.mapToSource(index)
            if not self.sourceModel().isDir(source):
                return Path(self.sourceModel().fileName(source)).stem
        return super().data(index, role)

    def lessThan(self, left, right):
        model = self.sourceModel()
        if model.isDir(left) != model.isDir(right):
            return model.isDir(left)
        if left.column() == 0:
            return model.fileName(left).casefold() < model.fileName(right).casefold()
        if left.column() == 1:
            return model.size(left) < model.size(right)
        if left.column() == 3:
            return model.lastModified(left) < model.lastModified(right)
        return super().lessThan(left, right)


def file_mime(paths, cut=False):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
    mime.setData('application/x-qt-windows-mime;value="Preferred DropEffect"', struct.pack("<I", 2 if cut else 1))
    return mime


class FileView(QTreeView):
    transferRequested = Signal(list, str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.folder = ""
        self.selection_mode = False
        self.setAccessibleName("Files in current folder")
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setRootIsDecorated(True)
        self.setItemsExpandable(True)
        self.setExpandsOnDoubleClick(False)
        self.setAnimated(True)
        self.setIndentation(18)
        self.setMouseTracking(True)
        self.setItemDelegateForColumn(0, SelectionDelegate(self))
        self.setUniformRowHeights(True)
        self.setSortingEnabled(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.CopyAction)

    def mousePressEvent(self, event):
        index = self.indexAt(event.position().toPoint())
        rect = self.visualRect(index)
        if self.selection_mode and event.button() == Qt.LeftButton and index.isValid() and index.column() == 0 and rect.left() <= event.position().x() < rect.left() + 22:
            self.selectionModel().select(index, QItemSelectionModel.Toggle | QItemSelectionModel.Rows)
            event.accept()
            return
        (QTreeView if isinstance(self, QTreeView) else QListView).mousePressEvent(self, event)

    def paths(self):
        proxy = self.model()
        return [proxy.sourceModel().filePath(proxy.mapToSource(i)) for i in self.selectionModel().selectedRows(0)]

    def startDrag(self, actions):
        paths = self.paths()
        if paths:
            drag = QDrag(self)
            drag.setMimeData(file_mime(paths))
            drag.exec(Qt.CopyAction | Qt.MoveAction, Qt.CopyAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and all(u.isLocalFile() for u in event.mimeData().urls()):
            event.acceptProposedAction()

    def destination(self, point):
        index = self.indexAt(point)
        if index.isValid():
            model = self.model().sourceModel()
            source = self.model().mapToSource(index)
            if model.isDir(source):
                return model.filePath(source)
        return self.folder

    def dragMoveEvent(self, event):
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        dest = self.destination(event.position().toPoint())
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if not dest or not paths:
            event.ignore()
            return
        mods = event.modifiers()
        move = bool(mods & Qt.ShiftModifier) or (not mods & Qt.ControlModifier and all(Path(p).drive.casefold() == Path(dest).drive.casefold() for p in paths))
        event.setDropAction(Qt.MoveAction if move else Qt.CopyAction)
        event.accept()
        self.setToolTip(f"{'Move' if move else 'Copy'} into {Path(dest).name or dest}. Ctrl: copy · Shift: move")

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        dest = self.destination(event.position().toPoint())
        if paths and dest:
            # Acknowledge Copy to OLE; GROK performs the entire move itself.
            # This prevents an external source from deleting before async completion.
            move = event.dropAction() == Qt.MoveAction
            self.transferRequested.emit(paths, dest, move)
            event.setDropAction(Qt.CopyAction)
            event.accept()


class GridView(QListView):
    transferRequested = Signal(list, str, bool)
    mousePressEvent = FileView.mousePressEvent
    startDrag = FileView.startDrag
    dragEnterEvent = FileView.dragEnterEvent
    destination = FileView.destination
    dragMoveEvent = FileView.dragMoveEvent
    dropEvent = FileView.dropEvent

    def __init__(self, parent=None):
        super().__init__(parent)
        self.folder = ""
        self.selection_mode = False
        self.setAccessibleName("Files in grid view")
        self.setMouseTracking(True)
        self.setItemDelegate(SelectionDelegate(self))
        self.setViewMode(QListView.IconMode)
        self.setResizeMode(QListView.Adjust)
        self.setMovement(QListView.Static)
        self.setIconSize(QSize(40, 40))
        self.setGridSize(QSize(108, 98))
        self.setSpacing(5)
        self.setWordWrap(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.CopyAction)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)

    def paths(self):
        proxy = self.model()
        return [proxy.sourceModel().filePath(proxy.mapToSource(i)) for i in self.selectedIndexes() if i.column() == 0]
