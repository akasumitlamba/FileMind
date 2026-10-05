import ctypes
from ctypes import wintypes
import html
import json
import os
from pathlib import Path
import re
import struct
import sys

from PySide6.QtCore import Qt, QDir, QTimer, QThreadPool, QPropertyAnimation, QEasingCurve, QEvent, QUrl, QSize, QRect
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut, QDesktopServices, QCursor, QRegion
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QStackedWidget, QTabWidget, QComboBox, QMenu, QInputDialog,
    QMessageBox, QDialog, QFormLayout, QCheckBox, QSpinBox, QScrollArea, QTextBrowser,
    QTextEdit, QDialogButtonBox, QSystemTrayIcon, QProgressBar, QHeaderView, QFileDialog, QFileSystemModel,
    QSizePolicy, QLayout, QFrame, QSplitter)

from . import __version__
from .storage import Settings, History
from . import windows, files
from .workers import Job
from .dock import geometry
from .browser import FileFilter, FileView, GridView, file_mime
from .ai import PROVIDERS
from .icons import icon, BUTTON_ICONS


def asset(name):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base / "assets" / name


def button(text, tip, fn):
    b = QPushButton(text)
    b.setToolTip(tip)
    b.setAccessibleName(tip)
    if text in BUTTON_ICONS:
        b.setIcon(icon(BUTTON_ICONS[text]))
        b.setIconSize(QSize(18, 18))
        b.setText("")
        b.setFixedSize(30, 30)
        b.setProperty("iconButton", True)
    b.clicked.connect(fn)
    return b


PRIVACY = """GROK's file-management features run locally. No GROK backend, account, analytics or telemetry is used.

Settings and favorites are stored in your Windows user profile. API keys are stored in Windows Credential Manager. Keys are not included in settings or logs.

When you enable AI and press Send, your message and the current conversation go directly to your selected provider. Attaching a text file or folder listing requires a separate preview and confirmation. Provider retention and processing policies apply. No requests are proxied by GROK.

Conversations, including sent attachment text, are saved as unencrypted local JSON in your GROK settings folder, separately per provider. They survive restarting, switching providers and disabling AI. Clear chat deletes the selected provider’s saved conversation. No chat is uploaded except when you send a provider request. GROK does not create crash reports. Windows or third-party security software may collect their own diagnostics.

The bundled static website has no analytics, external fonts or cookies. A future hosting provider may process request logs. No public site is configured in this build.

Remove keys individually before uninstalling; Windows Credential Manager entries may survive uninstall. Local settings can be removed from %LOCALAPPDATA%\\GROK (packaged Windows may redirect this location).

Made by akasumitlamba. Independent of Microsoft, OpenAI, Google and xAI."""


class Window(QWidget):
    def __init__(self, settings=None, test_mode=False):
        super().__init__()
        self.settings = settings or Settings()
        self.s = self.settings.data
        self.test_mode = test_mode
        self.history = History()
        self.pool = QThreadPool(self)
        self.jobs = set()
        self.operation = None
        self.nav_token = 0
        self.expanded = False
        self.wide = False
        self.current = ""
        self.vault = windows.Vault("GROK-test" if test_mode else "GROK")
        self.chat_messages = []
        self.attachments = []
        self.chat_generation = 0
        self.ai_busy = False
        self.setWindowTitle("GROK · Graphical Resource Organization Kit")
        self.setObjectName("grokWindow")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(QIcon(str(asset("grok.ico"))))
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | (Qt.WindowStaysOnTopHint if self.s["topmost"] else Qt.Widget))
        self.outer = QVBoxLayout(self)
        self.outer.setSizeConstraint(QLayout.SetNoConstraint)
        self.outer.setContentsMargins(1, 1, 1, 1)
        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.outer.addWidget(self.stack)
        self.make_dock()
        self.make_panel()
        self.anim = QPropertyAnimation(self, b"geometry", self)
        self.anim.finished.connect(self.finish_transition)
        self.anim.setDuration(210)
        self.anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        menu = QMenu()
        menu.addAction("Open GROK", lambda: self.set_expanded(True))
        menu.addAction("Settings", self.show_settings)
        menu.addSeparator()
        menu.addAction("Quit GROK", self.quit)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("GROK · Your files, one click away")
        self.tray.activated.connect(lambda reason: self.set_expanded(not self.expanded) if reason == QSystemTrayIcon.Trigger else None)
        if not test_mode:
            self.tray.show()
        self.apply_style()
        self.load_chat()
        self.bind_shortcuts()
        app = QApplication.instance()
        app.screenAdded.connect(self.screen_added)
        app.screenRemoved.connect(lambda _: self.reposition())
        for screen in app.screens():
            self.screen_added(screen)
        self.navigate(self.s["default_path"])
        self.set_expanded(not self.s["minimized"], False)
        if not test_mode:
            QTimer.singleShot(200, self.hotkey)
        if self.settings.recovered:
            self.status.setText("Settings could not be read; defaults restored.")

    def make_dock(self):
        self.dock = QFrame()
        self.dock.setObjectName("dockSurface")
        layout = QVBoxLayout(self.dock)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.dock_files = button("G", "Open files", self.open_files)
        layout.addWidget(self.dock_files)
        self.dock_fav = button("☆", "Favorite folders", self.favorites_menu)
        self.dock_search = button("⌕", "Search current folder", self.focus_search)
        self.dock_chat = button("Chat", "Open AI chat", lambda: self.open_chat(False))
        layout.addWidget(self.dock_chat)
        self.dock_fav.hide()
        self.dock_search.hide()
        for control in self.dock.findChildren(QPushButton):
            control.setFixedSize(40, 40)
            control.setIconSize(QSize(22, 22))
            control.setFocusPolicy(Qt.NoFocus)
        self.dock.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dock.customContextMenuRequested.connect(lambda _: self.dock_menu())
        self.stack.addWidget(self.dock)

    def make_panel(self):
        self.panel = QWidget()
        self.panel.setObjectName("panelSurface")
        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(8)
        header = QHBoxLayout()
        brand = QLabel("GROK")
        brand.setObjectName("brand")
        header.addWidget(brand)
        header.addStretch()
        self.pin = button("Pin", "Keep panel open", self.toggle_pin)
        
        header.addWidget(self.pin)
        header.addWidget(button("⚙", "Settings", self.show_settings))
        header.addWidget(button("›", "Collapse (Escape)", lambda: self.set_expanded(False)))
        layout.addLayout(header)
        subtitle = QLabel("YOUR FILES. WITHIN REACH.")
        subtitle.setObjectName("eyebrow")
        layout.addWidget(subtitle)
        self.tabs = QTabWidget()
        self.workspace = QSplitter(Qt.Horizontal)
        self.workspace.addWidget(self.tabs)
        layout.addWidget(self.workspace, 1)
        self.side_arrow = button("‹", "Expand to full workspace", self.toggle_wide)
        self.side_arrow.setFixedSize(30, 30)
        header.insertWidget(1, self.side_arrow)
        page = QWidget()
        self.files_page = page
        fl = QVBoxLayout(page)
        fl.setContentsMargins(0, 10, 0, 0)
        nav_line = QHBoxLayout()
        nav_line.setSpacing(8)
        nav_frame = QFrame()
        nav_frame.setObjectName("navigation")
        nav = QHBoxLayout(nav_frame)
        nav.setContentsMargins(3, 3, 3, 3)
        nav.setSpacing(0)
        self.back = button("←", "Back (Alt+Left)", lambda: self.go_history(-1))
        self.forward = button("→", "Forward (Alt+Right)", lambda: self.go_history(1))
        for b in [self.back, self.forward, button("↑", "Parent folder (Alt+Up)", self.up), button("↻", "Refresh (F5)", self.refresh)]:
            nav.addWidget(b)
        nav_line.addWidget(nav_frame)
        self.path_stack = QStackedWidget()
        self.path_stack.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.path_stack.setFixedHeight(38)
        nav_line.addWidget(self.path_stack, 1)
        fl.addLayout(nav_line)
        self.address = QLineEdit()
        self.address.setAccessibleName("Folder path")
        self.address.setPlaceholderText("Enter a folder path")
        self.address.returnPressed.connect(lambda: self.navigate(self.address.text()))
        self.address.editingFinished.connect(lambda: self.path_stack.setCurrentIndex(0))
        self.breadcrumb_frame = QFrame()
        self.breadcrumb_frame.setObjectName("navigation")
        self.crumbs = QHBoxLayout(self.breadcrumb_frame)
        self.crumbs.setContentsMargins(3, 3, 3, 3)
        self.crumbs.setSpacing(2)
        self.path_stack.addWidget(self.breadcrumb_frame)
        self.path_stack.addWidget(self.address)
        self.locations = QComboBox()
        self.locations.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.locations.setMinimumContentsLength(12)
        self.locations.setAccessibleName("Quick locations")
        self.populate_locations()
        self.locations.activated.connect(lambda _: self.navigate(self.locations.currentData()))
        self.locations.hide()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search this folder…")
        self.search.setAccessibleName("Search this folder")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter_changed)
        self.search.addAction(icon("search"), QLineEdit.LeadingPosition)
        
        self.select_action = self.search.addAction(icon("select"), QLineEdit.TrailingPosition)
        self.select_action.setCheckable(True)
        self.select_action.setToolTip("Select files: show checkboxes")
        self.select_action.toggled.connect(self.toggle_selection_mode)
        fl.addWidget(self.search)
        self.model = QFileSystemModel(self)
        self.model.setReadOnly(True)
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | (QDir.Hidden if self.s["hidden"] else QDir.Filter(0)))
        self.model.setRootPath("")
        self.proxy = FileFilter(self)
        self.proxy.extensions = self.s["extensions"]
        self.proxy.setSourceModel(self.model)
        self.view = FileView()
        self.view.setModel(self.proxy)
        self.view.sortByColumn(self.s["sort"] if self.s["sort"] in range(4) else 0, Qt.AscendingOrder)
        self.view.doubleClicked.connect(lambda _: self.open_selected())
        self.view.transferRequested.connect(self.transfer)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.context_menu)
        self.view.header().setStretchLastSection(False)
        self.view.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.view.header().moveSection(2, 1)
        self.view.setColumnWidth(1, 72)
        self.view.setColumnWidth(2, 95)
        self.view.setColumnWidth(3, 125)
        self.model.directoryLoaded.connect(self.list_loaded)
        self.grid = GridView()
        self.grid.setModel(self.proxy)
        self.grid.setSelectionModel(self.view.selectionModel())
        self.grid.doubleClicked.connect(lambda _: self.open_selected())
        self.grid.transferRequested.connect(self.transfer)
        self.grid.setContextMenuPolicy(Qt.CustomContextMenu)
        self.grid.customContextMenuRequested.connect(self.context_menu)
        self.view_stack = QStackedWidget()
        self.view_stack.addWidget(self.view)
        self.view_stack.addWidget(self.grid)
        self.column_button = button("Columns", "Choose visible file columns", self.column_menu)
        self.column_button.setParent(self.view)
        self.model.directoryLoaded.connect(self.folder_loaded)
        self.view.expanded.connect(self.preload_children)
        self.view.installEventFilter(self)
        self.view.header().setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.header().customContextMenuRequested.connect(lambda _: self.column_menu())
        fl.addWidget(self.view_stack, 1)
        self.empty = QLabel("Loading folder…")
        self.empty.setWordWrap(True)
        self.empty.setMinimumWidth(0)
        self.empty.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.empty.setObjectName("muted")
        self.footer_frame = QFrame()
        self.footer_frame.setObjectName("navigation")
        footer = QHBoxLayout(self.footer_frame)
        footer.setContentsMargins(6, 6, 6, 6)
        footer.setSpacing(5)
        footer.addWidget(self.empty, 1)
        self.list_button = button("List", "List view", lambda: self.set_view_mode("list"))
        self.grid_button = button("Grid", "Grid view", lambda: self.set_view_mode("grid"))
        footer.addWidget(self.list_button)
        footer.addWidget(self.grid_button)
        self.sort_button = button("Sort", "Sort files", lambda: self.search_options(self.sort_button))
        footer.addWidget(self.sort_button)
        layout.addWidget(self.footer_frame)
        self.tabs.addTab(page, "Files")
        self.make_chat()
        footer.insertWidget(0, button("Files", "Show files", lambda: self.tabs.setCurrentWidget(self.files_page)))
        self.chat_switch = button("AI Chat", "Open chat; attach selected files", lambda: self.open_chat(True))
        footer.insertWidget(1, self.chat_switch)
        self.view.selectionModel().selectionChanged.connect(self.selection_changed)
        self.status = QLabel("Ready · No account needed")
        self.status.setWordWrap(True)
        self.status.setObjectName("muted")
        self.status.hide()
        layout.addWidget(self.status)
        busy = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(4)
        self.progress.hide()
        self.cancel_op = button("Cancel", "Cancel file transfer", self.cancel_transfer)
        self.cancel_op.hide()
        busy.addWidget(self.progress)
        busy.addWidget(self.cancel_op)
        layout.addLayout(busy)
        self.stack.addWidget(self.panel)

    def populate_locations(self):
        self.locations.clear()
        for name, path in windows.locations().items():
            self.locations.addItem(name, path)
        self.locations.addItem("This PC · Drives", "")
        for path in QDir.drives():
            self.locations.addItem(path.absoluteFilePath(), path.absoluteFilePath())

    def active_view(self):
        return self.grid if self.view_stack.currentIndex() == 1 else self.view

    def set_view_mode(self, mode, persist=True):
        mode = mode if mode in ("list", "grid") else "list"
        self.s["view_mode"] = mode
        self.view_stack.setCurrentIndex(1 if mode == "grid" else 0)
        for control, selected in [(self.list_button, mode == "list"), (self.grid_button, mode == "grid")]:
            control.setStyleSheet("background:#303030; border:1px solid #555; border-radius:4px;" if selected else "")
        if persist:
            self.save()

    def set_sort(self, column, descending=None):
        self.s["sort"] = column
        if descending is not None:
            self.s["descending"] = descending
        self.view.sortByColumn(column, Qt.DescendingOrder if self.s["descending"] else Qt.AscendingOrder)
        self.save()

    def column_limit(self):
        return 3 if self.wide or self.width() >= 600 else 2 if self.width() >= 480 else 1

    def update_columns(self):
        key = "wide_columns" if self.wide else "columns"
        chosen = [c for c in self.s[key] if c in (1, 2, 3)][:self.column_limit()]
        for col in (1, 2, 3):
            self.view.setColumnHidden(col, col not in chosen)
        self.view.setColumnWidth(1, 80)
        self.view.setColumnWidth(2, 110)
        self.view.setColumnWidth(3, 180)
        self.view.setViewportMargins(0, 0, 0, 0)

    def column_menu(self):
        key = "wide_columns" if self.wide else "columns"
        chosen = [c for c in self.s[key] if c in (1, 2, 3)][:self.column_limit()]
        menu = QMenu(self)
        menu.addAction(f"Name + up to {self.column_limit()} details").setEnabled(False)
        for label, col in [("Type", 2), ("Size", 1), ("Date modified", 3)]:
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(col in chosen)
            action.setEnabled(col in chosen or len(chosen) < self.column_limit())
            def change(checked, c=col):
                selected = list(chosen)
                if checked and c not in selected:
                    selected.append(c)
                elif not checked and c in selected:
                    selected.remove(c)
                self.s[key] = selected
                self.update_columns()
                self.save()
            action.triggered.connect(change)
        menu.exec(self.column_button.mapToGlobal(self.column_button.rect().bottomLeft()))

    def open_files(self):
        self.tabs.setCurrentWidget(self.files_page)
        self.set_expanded(True)

    def toggle_selection_mode(self, enabled):
        for view in (self.view, self.grid):
            view.selection_mode = enabled
            view.viewport().update()
        self.select_action.setToolTip("Finish selecting" if enabled else "Select files: show checkboxes")

    def preload_children(self, index):
        source = self.proxy.mapToSource(index)
        for row in range(self.model.rowCount(source)):
            child = self.model.index(row, 0, source)
            if self.model.isDir(child) and self.model.canFetchMore(child):
                self.model.fetchMore(child)

    def folder_loaded(self, path):
        index = self.proxy.mapFromSource(self.model.index(path))
        if index == self.view.rootIndex() or self.view.isExpanded(index):
            self.preload_children(index)
        self.view.viewport().update()

    def open_chat(self, attach_selection=True):
        if attach_selection:
            self.queue_attachments(self.active_view().paths())
        self.view.selectionModel().clearSelection()
        self.set_expanded(True)
        if not self.wide:
            self.tabs.setCurrentWidget(self.chat_page)
        self.prompt.setFocus()

    def toggle_wide(self):
        self.wide = not self.wide
        if self.wide:
            self.tabs.removeTab(self.tabs.indexOf(self.chat_page))
            self.workspace.addWidget(self.chat_page)
            self.chat_page.show()
            self.workspace.setSizes([900, 440])
            self.tabs.setCurrentWidget(self.files_page)
        else:
            self.chat_page.setParent(None)
            self.tabs.addTab(self.chat_page, "AI Chat")
        self.tabs.tabBar().hide()
        self.side_arrow.setIcon(icon("collapse" if self.wide else "expand"))
        self.side_arrow.setToolTip("Return to sidebar" if self.wide else "Expand to full workspace")
        self.set_expanded(True)
        self.update_columns()

    def apply_style(self):
        accent = self.s["accent"] if re.fullmatch(r"#[0-9a-fA-F]{6}", self.s["accent"]) else "#dddddd"
        self.setStyleSheet(f"""
            QWidget {{ background:#0b0b0b; color:#ededed; font: 10pt 'Segoe UI'; }}
            QWidget#grokWindow, QStackedWidget {{ background:transparent; }}
            QWidget#panelSurface {{ background:#0b0b0b; border-left:1px solid #292929; }}
            QFrame#dockSurface {{ background:transparent; border:0; }}
            QFrame#dockSurface QPushButton {{ background:#141414; border:1px solid #3a3a3a; border-radius:9px; padding:0; min-height:38px; max-height:38px; min-width:38px; max-width:38px; }}
            QFrame#dockSurface QPushButton:hover {{ background:#292929; }}
            QFrame#dockSurface QPushButton:focus {{ background:#232323; border:1px solid #666666; }}
            QLabel#brand {{ font-size:18pt; font-weight:700; letter-spacing:2px; }}
            QLabel#eyebrow {{ color:#a0a0a0; font-size:7pt; letter-spacing:1.4px; }}
            QFrame#navigation {{ background:#121212; border:1px solid #242424; border-radius:6px; }}
            QLabel#muted {{ color:#a3a3a3; font-size:9pt; }}
            QPushButton {{ background:#191919; border:1px solid #303030; border-radius:4px; padding:6px 8px; min-height:16px; }}
            QPushButton[iconButton="true"] {{ padding:0; background:transparent; border:1px solid transparent; }}
            QPushButton:hover {{ background:#292929; border-color:#505050; }}
            QPushButton[iconButton="true"]:hover {{ background:#262626; border-color:#404040; }}
            QPushButton:focus, QLineEdit:focus, QComboBox:focus, QTreeView:focus, QTextEdit:focus {{ border:1px solid {accent}; }}
            QPushButton:disabled {{ color:#686868; }}
            QLineEdit, QTextEdit, QTextBrowser, QComboBox, QSpinBox {{ background:#171717; border:1px solid #343434; border-radius:4px; padding:7px; selection-background-color:#454545; }}
            QTreeView {{ background:#101010; border:1px solid #242424; border-radius:6px; outline:0; alternate-background-color:#131313; }}
            QTreeView::item {{ padding:{3 if self.s['compact'] else 6}px 3px; border-bottom:1px solid #1d1d1d; }}
            QTreeView::item:selected {{ background:#333333; color:white; }}
            QTreeView::item:hover {{ background:#222222; }}
            QListView {{ background:#101010; border:1px solid #242424; border-radius:6px; padding:8px; }}
            QListView::item {{ border-radius:5px; padding:5px; }}
            QListView::item:selected {{ background:#343434; }}
            QListView::item:hover {{ background:#242424; }}
            QSplitter::handle {{ background:#2c2c2c; width:1px; }}
            QHeaderView::section {{ background:#101010; color:#a3a3a3; border:0; border-bottom:1px solid #303030; padding:8px 3px; font-size:8pt; text-align:left; }}
            QTabWidget::pane {{ border:0; }}
            QTabBar::tab {{ padding:8px 18px; color:#a3a3a3; border-bottom:2px solid #272727; }}
            QTabBar::tab:selected {{ color:white; border-bottom:2px solid {accent}; }}
            QScrollBar:vertical {{ background:transparent; width:5px; margin:3px 0; }}
            QScrollBar::handle:vertical {{ background:#393939; min-height:28px; border-radius:2px; }}
            QScrollBar::handle:vertical:hover {{ background:#707070; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:transparent; }}
            QScrollBar:horizontal {{ background:transparent; height:5px; margin:0 3px; }}
            QScrollBar::handle:horizontal {{ background:#393939; min-width:28px; border-radius:2px; }}
            QScrollBar::handle:horizontal:hover {{ background:#707070; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width:0; }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background:transparent; }}
            QMenu {{ background:#1b1b1b; border:1px solid #464646; padding:5px; }}
            QMenu::item {{ padding:7px 22px; }} QMenu::item:selected {{ background:#333333; }}
            QProgressBar::chunk {{ background:{accent}; }}
        """)
        self.dock_fav.hide()
        self.dock_search.hide()
        self.pin.setIcon(icon("pin", "#ffffff" if self.s["pinned"] else "#999999"))
        self.pin.setToolTip("Unpin panel" if self.s["pinned"] else "Keep panel open")
        self.tabs.tabBar().hide()
        self.chat_notice.setVisible(not self.s["ai_enabled"])
        self.set_view_mode(self.s["view_mode"], persist=False)
        self.update_columns()

    def run_job(self, fn, done, failure=None):
        job = Job(fn)
        self.jobs.add(job)
        job.signals.done.connect(lambda result: self.finish_job(job, done, result))
        job.signals.failed.connect(lambda error: self.finish_job(job, failure or self.error, error))
        job.signals.progress.connect(self.status.setText)
        self.pool.start(job)
        return job

    def finish_job(self, job, callback, result):
        self.jobs.discard(job)
        callback(result)

    def error(self, message):
        self.status.setText(message)
        if not self.test_mode:
            QMessageBox.warning(self, "GROK", message)

    def guard(self, fn):
        try:
            return fn()
        except (ValueError, OSError) as exc:
            self.error(str(exc))

    def save(self):
        self.guard(self.settings.save)

    def navigate(self, path, history_index=None):
        self.nav_token += 1
        token = self.nav_token
        self.status.setText("Opening folder…")
        def ready(folder):
            if token != self.nav_token:
                return
            self.current = folder
            self.address.setText(folder)
            self.proxy.root = folder
            self.view.folder = folder
            self.grid.folder = folder
            self.search.clear()
            self.model.setRootPath(folder)
            self.view.selectionModel().clearSelection()
            self.view.setRootIndex(self.proxy.mapFromSource(self.model.index(folder)))
            self.grid.setRootIndex(self.view.rootIndex())
            self.preload_children(self.view.rootIndex())
            if history_index is None:
                self.history.push(folder)
            else:
                self.history.index = history_index
            self.back.setEnabled(self.history.index > 0)
            self.forward.setEnabled(self.history.index < len(self.history.paths) - 1)
            self.make_crumbs(folder)
            self.status.setText("Ready · Files stay on this PC")
            QTimer.singleShot(200, self.update_count)
        self.run_job(lambda _: files.validate_folder(path) if path else "", ready,
                     lambda msg: self.error(msg) if token == self.nav_token else None)

    def make_crumbs(self, path):
        while self.crumbs.count():
            item = self.crumbs.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        location_button = button("G", "Locations: Home, known folders and drives", self.locations_menu)
        self.crumbs.addWidget(location_button)
        if path:
            p = Path(path)
            chain = list(reversed(p.parents)) + [p]
            for part in chain[-2:]:
                label = part.name or part.drive
                b = button(label[:12], str(part), lambda checked=False, x=str(part): self.navigate(x))
                b.setMinimumWidth(0)
                b.setMaximumHeight(25)
                b.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
                b.setStyleSheet("QPushButton {border:0; background:transparent; padding:2px; font-size:8pt;}")
                b.setMaximumWidth(150)
                self.crumbs.addWidget(b)
                chevron = QLabel("›")
                chevron.setStyleSheet("color:#666; background:transparent;")
                self.crumbs.addWidget(chevron)
        else:
            self.crumbs.addWidget(QLabel("This PC"))
        self.crumbs.addStretch()
        edit_path = button("Actions", "Edit or paste folder path (Ctrl+L)", self.edit_path)
        edit_path.setFixedWidth(24)
        self.crumbs.addWidget(edit_path)
        self.path_stack.setCurrentIndex(0)
        self.search.setPlaceholderText(f"Search in {Path(path).name if path else 'This PC'}…")

    def edit_path(self):
        self.path_stack.setCurrentIndex(1)
        self.address.setFocus()
        self.address.selectAll()

    def locations_menu(self):
        menu = QMenu(self)
        for name, path in windows.locations().items():
            menu.addAction(name, lambda p=path: self.navigate(p))
        menu.addSeparator()
        menu.addAction("This PC", lambda: self.navigate(""))
        for drive in QDir.drives():
            path = drive.absoluteFilePath()
            menu.addAction(path, lambda p=path: self.navigate(p))
        menu.addSeparator()
        menu.addAction("Favorites…", self.favorites_menu)
        menu.exec(self.breadcrumb_frame.mapToGlobal(self.breadcrumb_frame.rect().bottomLeft()))

    def search_options(self, anchor=None):
        menu = QMenu(self)
        menu.addAction("Search current folder only").setEnabled(False)
        for label, column in [("Sort by name", 0), ("Sort by type", 2), ("Sort by size", 1), ("Sort by modified date", 3)]:
            action = menu.addAction(label, lambda c=column: self.set_sort(c))
            action.setCheckable(True)
            action.setChecked(column == self.proxy.sortColumn())
        menu.addSeparator()
        ascending = menu.addAction("Ascending", lambda: self.set_sort(self.s["sort"], False))
        descending = menu.addAction("Descending", lambda: self.set_sort(self.s["sort"], True))
        for action, checked in [(ascending, not self.s["descending"]), (descending, self.s["descending"])]:
            action.setCheckable(True)
            action.setChecked(checked)
        menu.addSeparator()
        menu.addAction("Favorites…", self.favorites_menu)
        menu.addAction("New folder", self.new_folder)
        anchor = anchor if isinstance(anchor, QWidget) else self.search
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def go_history(self, offset):
        path = self.history.step(offset)
        if path is not None:
            self.navigate(path, self.history.index + offset)

    def up(self):
        if self.current:
            self.navigate(str(Path(self.current).parent))

    def refresh(self):
        self.populate_locations()
        self.model.setRootPath("")
        self.navigate(self.current, self.history.index)

    def filter_changed(self, query):
        self.proxy.query = query
        self.proxy.invalidate()
        self.update_count()

    def list_loaded(self, path):
        if os.path.normcase(os.path.normpath(path)) == os.path.normcase(os.path.normpath(self.current)):
            self.update_count()

    def update_count(self):
        count = self.proxy.rowCount(self.view.rootIndex())
        label = f"{count} item" if count == 1 else f"{count} items"
        self.empty.setText("No matches" if self.search.text() and count == 0 else label)
        self.empty.setStyleSheet("color:#888; background:transparent; font-size:8pt; padding-left:5px;")
        self.empty.setToolTip("Clear search to see all files." if self.search.text() and not count else "Current folder item count; updates as the directory loads.")

    def focus_search(self):
        self.set_expanded(True)
        self.tabs.setCurrentIndex(0)
        self.search.setFocus()
        self.search.selectAll()

    def open_selected(self):
        paths = self.active_view().paths()
        if not paths:
            return
        path = paths[0]
        if self.model.isDir(self.model.index(path)):
            self.navigate(path)
        elif not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            self.error("Windows could not open this file. Try Open with.")

    def clipboard(self, cut=False):
        paths = self.active_view().paths()
        if paths:
            QApplication.clipboard().setMimeData(file_mime(paths, cut))
            self.status.setText(f"{len(paths)} items {'cut' if cut else 'copied'} to the Windows clipboard")

    def paste(self):
        mime = QApplication.clipboard().mimeData()
        if not mime or not mime.hasUrls():
            self.status.setText("Copy files in GROK or Explorer first.")
            return
        paths = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]
        effect = bytes(mime.data('application/x-qt-windows-mime;value="Preferred DropEffect"'))
        cut = len(effect) >= 4 and struct.unpack("<I", effect[:4])[0] == 2
        self.transfer(paths, self.current, cut, clipboard_cut=cut)

    def transfer(self, paths, dest, move=False, clipboard_cut=False):
        if self.operation:
            self.error("Wait for the current file operation to finish.")
            return
        if not dest or not paths:
            self.error("Open a destination folder first.")
            return
        self.status.show()
        self.progress.show()
        self.cancel_op.show()
        def finish(result, failed=False):
            self.operation = None
            self.status.hide()
            self.progress.hide()
            self.cancel_op.hide()
            if clipboard_cut and not failed:
                mime = QApplication.clipboard().mimeData()
                if mime and [u.toLocalFile() for u in mime.urls()] == paths:
                    QApplication.clipboard().clear()
            self.refresh()
            self.status.setText(result if failed else f"Completed {len(result)} items")
            if failed:
                self.error(result)
        self.operation = self.run_job(lambda job: files.transfer(paths, dest, move, job.cancel, job.signals.progress.emit),
                                     finish, lambda msg: finish(msg, True))

    def cancel_transfer(self):
        if self.operation:
            self.operation.cancel.set()
            self.status.setText("Cancel requested; finishing the current safe step…")

    def new_folder(self):
        if not self.current:
            return self.error("Open a folder first.")
        name, ok = QInputDialog.getText(self, "New folder", "Folder name")
        if ok:
            self.run_job(lambda _: files.create_folder(self.current, name), lambda _: self.refresh())

    def rename_selected(self):
        paths = self.active_view().paths()
        if len(paths) != 1:
            return self.error("Select one item to rename.")
        name, ok = QInputDialog.getText(self, "Rename", "New name (including extension)", text=Path(paths[0]).name)
        if ok and name != Path(paths[0]).name:
            self.run_job(lambda _: files.rename(paths[0], name), lambda _: self.refresh())

    def delete_selected(self):
        paths = self.active_view().paths()
        if not paths or self.operation:
            return
        if self.s["confirm_delete"] and QMessageBox.question(self, "Recycle selected items?", f"Send {len(paths)} selected items to the Windows Recycle Bin? Windows may warn if the destination cannot recycle.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.operation = self.run_job(lambda _: windows.recycle(paths), lambda _: self.delete_done(), lambda msg: self.delete_done(msg))
        self.status.setText("Waiting for Windows to finish recycling…")

    def delete_done(self, error=None):
        self.operation = None
        self.refresh()
        if error:
            self.error(error)

    def context_menu(self, point):
        menu = QMenu(self)
        paths = self.active_view().paths()
        if paths:
            menu.addAction("Open", self.open_selected)
            if len(paths) == 1:
                menu.addAction("Open with…", lambda: self.guard(lambda: windows.open_with(paths[0], int(self.winId()))))
            menu.addSeparator()
            menu.addAction("Copy    Ctrl+C", lambda: self.clipboard(False))
            menu.addAction("Cut       Ctrl+X", lambda: self.clipboard(True))
            menu.addAction("Move to…", self.move_to)
            menu.addAction("Rename    F2", self.rename_selected)
            menu.addAction("Delete     Del", self.delete_selected)
            menu.addSeparator()
            menu.addAction("Open containing folder", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(paths[0]).parent))))
            if Path(paths[0]).is_dir():
                menu.addAction("Open folder in Explorer", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(paths[0])))
            menu.addAction("Properties", lambda: self.guard(lambda: windows.properties(paths[0], int(self.winId()))))
        menu.addAction("Paste    Ctrl+V", self.paste)
        menu.addAction("New folder", self.new_folder)
        menu.exec(self.active_view().viewport().mapToGlobal(point) if point is not None else QCursor.pos())

    def move_to(self):
        paths = self.active_view().paths()
        if paths:
            dest = QFileDialog.getExistingDirectory(self, "Move selected items to")
            if dest:
                self.transfer(paths, dest, True)

    def favorites_menu(self):
        self.set_expanded(True)
        menu = QMenu(self)
        for path in self.s["favorites"]:
            menu.addAction(Path(path).name or path, lambda p=path: self.navigate(p)).setToolTip(path)
        menu.addSeparator()
        if self.current:
            menu.addAction("Unpin current folder" if self.current in self.s["favorites"] else "Pin current folder", self.toggle_favorite)
        if not self.s["favorites"]:
            menu.addAction("No favorite folders yet").setEnabled(False)
        menu.exec(QCursor.pos())

    def toggle_favorite(self):
        if self.current in self.s["favorites"]:
            self.s["favorites"].remove(self.current)
        else:
            self.s["favorites"].append(self.current)
        self.save()

    def dock_menu(self):
        menu = QMenu(self)
        menu.addAction("Settings", self.show_settings)
        menu.addAction("Quit GROK", self.quit)
        menu.exec(QCursor.pos())

    def bind_shortcuts(self):
        bindings = {"Escape": lambda: self.set_expanded(False), "Alt+Left": lambda: self.go_history(-1),
                    "Alt+Right": lambda: self.go_history(1), "Alt+Up": self.up,
                    "F5": self.refresh, "Ctrl+L": self.edit_path, "Ctrl+F": self.focus_search}
        for key, fn in bindings.items():
            QShortcut(QKeySequence(key), self, activated=fn)
        # File shortcuts are scoped to the view: typing in chat/path never deletes files.
        for key, fn in {"Return": self.open_selected, "Ctrl+C": lambda: self.clipboard(),
                        "Ctrl+X": lambda: self.clipboard(True), "Ctrl+V": self.paste,
                        "Delete": self.delete_selected, "F2": self.rename_selected,
                        "Ctrl+Shift+N": self.new_folder}.items():
            for target in [self.view, self.grid]:
                shortcut = QShortcut(QKeySequence(key), target, activated=fn)
                shortcut.setContext(Qt.WidgetWithChildrenShortcut)

    def screen_added(self, screen):
        screen.availableGeometryChanged.connect(lambda _: self.reposition())
        screen.logicalDotsPerInchChanged.connect(lambda _: self.reposition())
        self.reposition()

    def target_screen(self):
        app = QApplication.instance()
        return next((x for x in app.screens() if x.name() == self.s["monitor"]), app.primaryScreen())

    def reposition(self):
        self.anim.stop() if hasattr(self, "anim") else None
        area = self.target_screen().availableGeometry()
        self.setGeometry(geometry(area, (area.width() if self.wide else self.s["width"]), self.expanded, self.s["position"]))

    def finish_transition(self):
        self.stack.setCurrentWidget(self.panel if self.expanded else self.dock)
        if not self.expanded:
            self.setFixedSize(42, 86)
            self.outer.activate()
            self.dock.layout().activate()
            # Use the dock's fixed local bounds, never pre-show widget positions.
            self.setMask(QRegion(QRect(1, 1, 40, 40)) | QRegion(QRect(1, 45, 40, 40)))
            QTimer.singleShot(0, self.settle_dock_bounds)

    def settle_dock_bounds(self):
        if not self.expanded:
            self.setGeometry(geometry(self.target_screen().availableGeometry(), self.s["width"], False, self.s["position"]))

    def set_expanded(self, value, animate=True):
        self.clearMask()
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        self.expanded = value
        if value:
            self.stack.setCurrentWidget(self.panel)
        area = self.target_screen().availableGeometry()
        rect = geometry(area, area.width() if self.wide else self.s["width"], value, self.s["position"])
        self.anim.stop()
        if animate and self.s["animation"] and not self.test_mode and QApplication.isEffectEnabled(Qt.UI_AnimateMenu):
            self.anim.setStartValue(self.geometry())
            self.anim.setEndValue(rect)
            self.anim.start()
        else:
            self.setGeometry(rect)
            self.finish_transition()
        self.show()
        if value:
            self.raise_()
            self.activateWindow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "column_button"):
            self.update_columns()
            self.column_button.move(max(0, self.view.width() - 32), 2)
            self.column_button.raise_()
        if hasattr(self, "side_arrow"):
            pass

    def eventFilter(self, watched, event):
        if watched is getattr(self, "view", None) and event.type() == QEvent.Resize and hasattr(self, "column_button"):
            self.column_button.move(max(0, self.view.width() - 34), 2)
            self.column_button.raise_()
        return super().eventFilter(watched, event)

    def event(self, event):
        if event.type() == QEvent.WindowDeactivate and getattr(self, "expanded", False):
            if self.s["auto_hide"] and not self.s["pinned"]:
                QTimer.singleShot(250, self.auto_collapse)
        return super().event(event)

    def auto_collapse(self):
        if not self.isActiveWindow() and not QApplication.activeModalWidget() and not QApplication.activePopupWidget() and not self.operation:
            self.set_expanded(False)

    def toggle_pin(self):
        self.s["pinned"] = not self.s["pinned"]
        self.apply_style()
        self.save()

    def hotkey(self):
        self.guard(lambda: windows.register_hotkey(int(self.winId()), self.s["hotkey"]))

    def nativeEvent(self, event_type, message):
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == 0x0312 and msg.wParam == 71:
            self.set_expanded(not self.expanded)
            return True, 0
        if msg.message in (0x007E, 0x02E0):
            QTimer.singleShot(100, self.reposition)
        return super().nativeEvent(event_type, message)

    def closeEvent(self, event):
        event.ignore()
        self.set_expanded(False)

    def quit(self):
        if self.jobs:
            self.error("Wait for pending operations to finish before quitting. You can cancel a file transfer.")
            return
        ctypes.windll.user32.UnregisterHotKey(wintypes.HWND(int(self.winId())), 71)
        self.save()
        self.tray.hide()
        QApplication.instance().quit()

    def make_chat(self):
        page = QWidget()
        self.chat_page = page
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 10, 12, 0)
        self.provider = QComboBox()
        self.provider.addItems(PROVIDERS)
        self.provider.setCurrentText(self.s["provider"])
        self.provider.setAccessibleName("AI provider")
        self.provider.currentTextChanged.connect(self.change_provider)
        layout.addWidget(QLabel("AI ASSISTANT"))
        layout.addWidget(self.provider)
        self.chat_notice = button("Connect a provider", "Configure and enable optional AI", self.show_settings)
        layout.addWidget(self.chat_notice)
        note = QLabel("Optional AI · Requests go directly to your provider.\nAPI access and billing are separate from consumer chat subscriptions.")
        note.setWordWrap(True)
        note.setObjectName("muted")
        layout.addWidget(note)
        self.chat = QTextBrowser()
        self.chat.setPlaceholderText("Your files, with an assistant.\n\nConnect your own provider to start a conversation. Select a text file in Files, then use Attach to review what you share.\n\nFile-editing and conversion tools are planned. This version does not execute AI commands.")
        self.chat.setOpenExternalLinks(False)
        self.chat.setAccessibleName("AI conversation")
        layout.addWidget(self.chat, 1)
        self.prompt = QTextEdit()
        self.prompt.setPlaceholderText("Ask your provider…")
        self.prompt.setAccessibleName("Message to selected AI provider")
        self.prompt.setMaximumHeight(100)
        composer = QFrame()
        composer.setObjectName("navigation")
        compose_layout = QVBoxLayout(composer)
        compose_layout.setContentsMargins(8, 8, 8, 8)
        self.attachment_box = QVBoxLayout()
        compose_layout.addLayout(self.attachment_box)
        self.prompt.setStyleSheet("border:0; background:transparent;")
        compose_layout.addWidget(self.prompt)
        layout.addWidget(composer)
        row = QHBoxLayout()
        row.addWidget(button("Attach…", "Preview a text file or folder listing for AI", self.attach_context))
        row.addWidget(button("Clear", "Delete this provider’s local chat history", self.clear_chat))
        row.addStretch()
        self.send = button("Send ↑", "Send message to selected external provider", self.send_chat)
        row.addWidget(self.send)
        compose_layout.addLayout(row)
        self.tabs.addTab(page, "AI Chat")

    def change_provider(self, provider):
        self.s["provider"] = provider
        self.chat_generation += 1
        self.load_chat()
        self.save()

    def clear_chat(self):
        if self.ai_busy:
            return self.error("Wait for the current reply before clearing history.")
        self.chat_generation += 1
        self.chat_messages = []
        self.chat.clear()
        self.prompt.clear()
        self.save_chat()

    def history_path(self):
        return self.settings.root / ("chat-" + self.provider.currentText() + ".json")

    def save_chat(self):
        try:
            self.settings.root.mkdir(parents=True, exist_ok=True)
            path = self.history_path()
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.chat_messages, ensure_ascii=False), "utf-8")
            tmp.replace(path)
        except OSError:
            self.status.setText("Could not save local chat history.")

    def load_chat(self):
        try:
            data = json.loads(self.history_path().read_text("utf-8"))
            self.chat_messages = [m for m in data if isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)]
        except (OSError, ValueError, TypeError):
            self.chat_messages = []
        self.chat.clear()
        for m in self.chat_messages:
            self.chat.append("<p><b>" + ("You" if m["role"] == "user" else self.provider.currentText()) + "</b><br>" + html.escape(m["content"]).replace("\n", "<br>") + "</p>")

    def selection_changed(self):
        count = len(self.active_view().paths())
        self.chat_switch.setText(f"AI Chat ({count})" if count else "AI Chat")
        self.chat_switch.setStyleSheet("border:1px solid #aaa; background:#303030;" if count else "")

    def queue_attachments(self, paths):
        for path in paths:
            if path not in self.attachments and len(self.attachments) < 10:
                self.attachments.append(path)
        self.render_attachments()

    def render_attachments(self):
        while self.attachment_box.count():
            item = self.attachment_box.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        for path in self.attachments:
            chip = button(Path(path).name + "  ×", "Remove attachment: " + path, lambda checked=False, p=path: self.remove_attachment(p))
            self.attachment_box.addWidget(chip)

    def remove_attachment(self, path):
        self.attachments.remove(path)
        self.render_attachments()

    def attach_context(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Attach files for review", self.current)
        self.queue_attachments(paths)

    def reviewed_attachment_text(self):
        chunks = []
        for filename in self.attachments:
            path = Path(filename)
            if path.is_dir():
                with os.scandir(path) as entries:
                    import itertools
                    content = "\n".join(e.name for e in itertools.islice(entries, 500))
            else:
                if path.suffix.lower() not in {".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".html", ".css", ".xml", ".log", ".yaml", ".yml"}:
                    raise ValueError(f"{path.name}: only text attachments are supported currently. Remove it to send.")
                with path.open("rb") as source:
                    data = source.read(100001)
                if len(data) > 100000:
                    raise ValueError(f"{path.name}: attachment exceeds 100 KB.")
                try:
                    content = data.decode("utf-8-sig")
                except UnicodeDecodeError:
                    raise ValueError(f"{path.name}: this is not UTF-8 text.") from None
            chunks.append("Attachment: " + path.name + "\n" + content)
        return "\n\n".join(chunks)

    def send_chat(self):
        if not self.s["ai_enabled"]:
            return self.error("Enable AI and add a provider key in Settings → AI providers.")
        if self.ai_busy:
            return
        text = self.prompt.toPlainText().strip()
        if not text and not self.attachments:
            return
        if self.attachments:
            try:
                content = self.reviewed_attachment_text()
            except (ValueError, OSError) as exc:
                return self.error(str(exc))
            review = QDialog(self)
            review.setWindowTitle("Review attachments before sending")
            review.resize(540, 500)
            review_layout = QVBoxLayout(review)
            label = QLabel(f"Send the following content to {self.provider.currentText()}? It will also be retained in local chat history.")
            label.setWordWrap(True)
            review_layout.addWidget(label)
            preview = QTextEdit(); preview.setReadOnly(True); preview.setPlainText(content)
            review_layout.addWidget(preview)
            actions = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            actions.button(QDialogButtonBox.Ok).setText("Send to provider")
            actions.accepted.connect(review.accept); actions.rejected.connect(review.reject)
            review_layout.addWidget(actions)
            if review.exec() != QDialog.Accepted:
                return
            text += "\n\n" + content
        if sum(len(m["content"]) for m in self.chat_messages) + len(text) > 200_000:
            return self.error("Conversation is too large. Clear it and start a new chat.")
        provider = self.provider.currentText()
        key = self.guard(lambda: self.vault.get(provider))
        if not key:
            return self.error("Add your API key and model in Settings → AI providers.")
        messages = self.chat_messages + [{"role": "user", "content": text}]
        generation = self.chat_generation
        self.ai_busy = True
        self.send.setEnabled(False)
        self.provider.setEnabled(False)
        self.status.setText(f"Sending directly to {provider}…")
        def finished(result, failed=False):
            self.ai_busy = False
            self.send.setEnabled(True)
            self.provider.setEnabled(True)
            if generation != self.chat_generation:
                return
            if failed:
                return self.error(result)
            self.chat_messages = messages + [{"role": "assistant", "content": result}]
            self.chat.append(f"<p><b>You</b><br>{html.escape(text).replace(chr(10), '<br>')}</p>")
            self.chat.append(f"<p><b>{provider}</b><br>{html.escape(result).replace(chr(10), '<br>')}</p>")
            self.prompt.clear()
            self.attachments.clear()
            self.render_attachments()
            self.save_chat()
            self.status.setText("Response received · History saved locally")
        model = self.s["models"][provider]
        self.run_job(lambda _: PROVIDERS[provider].request(key, model, messages), finished, lambda msg: finished(msg, True))

    def show_settings(self):
        self.set_expanded(True)
        dialog = QDialog(self)
        dialog.setWindowTitle("GROK Settings")
        dialog.resize(590, 660)
        layout = QVBoxLayout(dialog)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        controls = {}
        def page(title):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            w = QWidget()
            form = QFormLayout(w)
            form.setVerticalSpacing(15)
            scroll.setWidget(w)
            tabs.addTab(scroll, title)
            return form
        def check(form, key, label):
            control = QCheckBox(label)
            control.setChecked(self.s[key])
            controls[key] = control
            form.addRow(control)
        def combo(form, key, label, options):
            control = QComboBox()
            for text, value in options:
                control.addItem(text, value)
            index = control.findData(self.s[key])
            control.setCurrentIndex(max(index, 0))
            controls[key] = control
            form.addRow(label, control)
        def edit(form, key, label):
            control = QLineEdit(str(self.s[key]))
            controls[key] = control
            form.addRow(label, control)
        general = page("General")
        for key, label in [("startup", "Start with Windows"), ("minimized", "Start as a small dock"),
                           ("topmost", "Always on top"), ("auto_hide", "Collapse when focus leaves GROK"), ("pinned", "Keep panel open")]:
            check(general, key, label)
        combo(general, "width", "Panel width", [("Narrow · 380", 380), ("Medium · 420", 420), ("Wide · 640", 640)])
        combo(general, "monitor", "Monitor", [("Primary (automatic)", "")] + [(s.name(), s.name()) for s in QApplication.screens()])
        combo(general, "position", "Dock position", [("Top", 0.0), ("Center", 0.5), ("Bottom", 1.0)])
        general.addRow(QLabel("Compact dock: Files and AI Chat.\nFavorites and search are available inside the panel."))
        appearance = page("Appearance")
        appearance.addRow(QLabel("Dark theme · designed for quiet desktop use"))
        combo(appearance, "accent", "Accent", [("Neutral", "#dddddd"), ("White", "#ffffff"), ("Mint", "#67d5bc")])
        check(appearance, "compact", "Compact file rows")
        check(appearance, "animation", "Animate expansion (disable for reduced motion)")
        browser = page("Files")
        edit(browser, "default_path", "Default folder")
        combo(browser, "sort", "Default sort", [("Name", 0), ("Size", 1), ("Type", 2), ("Modified", 3)])
        check(browser, "hidden", "Show hidden files")
        check(browser, "extensions", "Show file extensions")
        check(browser, "confirm_delete", "Confirm before asking Windows to delete")
        shortcut = page("Shortcuts")
        edit(shortcut, "hotkey", "Global toggle")
        shortcut.addRow(QLabel("Ctrl+Alt+G by default. Use Ctrl/Alt/Shift + a letter.\n\nEscape — collapse\nAlt+Left / Right / Up — navigate\nCtrl+L — path\nCtrl+F — search\nF5 — refresh\n\nWhen the file list is focused:\nCtrl+C / X / V — copy / cut / paste\nF2 — rename\nDelete — recycle\nCtrl+Shift+N — new folder\nEnter — open"))
        ai = page("AI providers")
        check(ai, "ai_enabled", "Enable optional external AI")
        ai.addRow(QLabel("Keys are saved immediately in Windows Credential Manager.\nModels and other settings are saved with Save.\nConnection tests send ‘Reply with OK’ and may incur API charges."))
        model_controls = {}
        for provider in PROVIDERS:
            model = QLineEdit(self.s["models"].get(provider, ""))
            model.setPlaceholderText("Model ID from your provider")
            model_controls[provider] = model
            ai.addRow(f"{provider} model", model)
            secret = QLineEdit()
            secret.setEchoMode(QLineEdit.Password)
            secret.setPlaceholderText("New API key (never displayed again)")
            ai.addRow(f"{provider} key", secret)
            state = QLabel("Key saved" if self.guard(lambda p=provider: self.vault.get(p)) else "Disconnected")
            row = QHBoxLayout()
            def save_key(p=provider, field=secret, label=state):
                try:
                    self.vault.put(p, field.text().strip())
                    field.clear()
                    label.setText("Key saved · Not yet tested")
                except ValueError as exc:
                    self.error(str(exc))
            def remove_key(p=provider, label=state):
                self.guard(lambda: self.vault.remove(p))
                label.setText("Disconnected")
            def test_key(p=provider, field=model, label=state):
                key = self.guard(lambda: self.vault.get(p))
                if not key:
                    label.setText("Save an API key first")
                    return
                label.setText("Testing…")
                model_id = field.text().strip()
                self.run_job(lambda _: PROVIDERS[p].request(key, model_id, [{"role": "user", "content": "Reply with OK"}]),
                             lambda _: label.setText("Connected · Test succeeded"), label.setText)
            row.addWidget(button("Save key", f"Save {provider} credential", save_key))
            row.addWidget(button("Test", f"Test {provider} with a small external request", test_key))
            row.addWidget(button("Disconnect", f"Remove {provider} credential", remove_key))
            ai.addRow(row)
            ai.addRow(state)
        ai.addRow(button("Clear chat history", "Delete this provider’s saved local history", self.clear_chat))
        privacy = page("Privacy")
        label = QLabel(PRIVACY)
        label.setWordWrap(True)
        privacy.addRow(label)
        about = page("About")
        label = QLabel(f"GROK {__version__}\nGraphical Resource Organization Kit\nMade by akasumitlamba\n\nYour files. Your AI. All in one sidebar.\n\nGROK describes a graphical resource utility. It is independent software, not the official xAI Grok service.\n\nWebsite: bundled static site; public URL not configured.\nThird-party licenses are included with the application.")
        label.setWordWrap(True)
        about.addRow(label)
        about.addRow(button("Open website & privacy policy", "Open bundled GROK website", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(asset("grok.ico").parent.parent / "website" / "index.html")))))
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        def apply():
            updated = {}
            for key, control in controls.items():
                updated[key] = control.isChecked() if isinstance(control, QCheckBox) else control.currentData() if isinstance(control, QComboBox) else control.text().strip()
            if not re.fullmatch(r"(?i)(?:(?:Ctrl|Alt|Shift)\+)+[A-Z0-9]", updated["hotkey"]):
                return self.error("Use Ctrl, Alt or Shift plus one letter for the shortcut.")
            try:
                if updated["startup"] != self.s["startup"]:
                    windows.startup(updated["startup"])
                if not self.test_mode:
                    windows.register_hotkey(int(self.winId()), updated["hotkey"])
            except ValueError as exc:
                self.hotkey()
                return self.error(str(exc))
            self.s.update(updated)
            self.s["models"] = {p: c.text().strip() for p, c in model_controls.items()}
            # Disabling AI preserves the user-requested local history.
            self.save()
            self.setWindowFlag(Qt.WindowStaysOnTopHint, self.s["topmost"])
            self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | (QDir.Hidden if self.s["hidden"] else QDir.Filter(0)))
            self.proxy.extensions = self.s["extensions"]
            self.proxy.invalidate()
            self.view.sortByColumn(self.s["sort"], Qt.AscendingOrder)
            self.apply_style()
            self.set_expanded(True, False)
            if not self.test_mode:
                self.hotkey()
            dialog.accept()
        buttons.accepted.connect(apply)
        buttons.rejected.connect(dialog.reject)
        dialog.exec()
