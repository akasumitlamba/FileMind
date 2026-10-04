"""Original 24px line icons, sharing stroke and optical alignment."""
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

PATHS = {
    'select': '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="m7 12 3 3 7-7"/>',
    'chat': '<path d="M4 4h16v12H9l-5 4Z"/><path d="M8 8h8M8 12h5"/>',
    'grid': '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    'list': '<path d="M8 5h13M8 12h13M8 19h13M3 5h1M3 12h1M3 19h1"/>',
    'sort': '<path d="M4 4v16m-3-3 3 3 3-3M11 5h10M11 12h7M11 19h4"/>',
    'columns': '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M15 4v16"/>',
    'folder': '<path d="M3 7V5h7l2 3h9v12H3Z"/>',
    'back': '<path d="m14 5-7 7 7 7M7 12h13"/>',
    'forward': '<path d="m10 5 7 7-7 7M17 12H4"/>',
    'up': '<path d="m5 11 7-7 7 7M12 4v16"/>',
    'refresh': '<path d="M20 10a8 8 0 1 0-2 8M20 3v7h-7"/>',
    'star': '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9Z"/>',
    'search': '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    'settings': '<path d="M5 3v18M12 3v18M19 3v18"/><rect x="2.5" y="6" width="5" height="4" rx="1" fill="#111"/><rect x="9.5" y="14" width="5" height="4" rx="1" fill="#111"/><rect x="16.5" y="7" width="5" height="4" rx="1" fill="#111"/>',
    'collapse': '<path d="m9 5 7 7-7 7"/>',
    'expand': '<path d="m15 5-7 7 7 7"/>',
    'new': '<path d="M3 7V5h7l2 3h9v12H3Z M12 11v6M9 14h6"/>',
    'copy': '<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
    'cut': '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="m8 8 12 12M8 16 20 4"/>',
    'paste': '<path d="M8 5H4v16h16V5h-4"/><rect x="8" y="3" width="8" height="4" rx="1"/><path d="M8 12h8M8 16h6"/>',
    'trash': '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7"/>',
    'pin': '<path d="m8 3 8 0-1 6 4 4v2H5v-2l4-4ZM12 15v7"/>',
    'more': '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    'send': '<path d="m3 3 18 9-18 9 4-9ZM7 12h14"/>',
    'attach': '<path d="m8 13 7-7a3 3 0 0 1 4 4L9 20a5 5 0 0 1-7-7L13 2M6 15l10-10"/>',
    'close': '<path d="m6 6 12 12M6 18 18 6"/>',
}


def icon(name, color='#dedede'):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g fill="none" stroke="{color}" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</g></svg>'
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)


BUTTON_ICONS = {'Chat':'chat', 'Grid':'grid', 'List':'list', 'Sort':'sort', 'Columns':'columns', 'G':'folder', '‹':'expand', '›':'collapse', '☆':'star', '⌕':'search',
                '⚙':'settings', '←':'back', '→':'forward', '↑':'up', '↻':'refresh',
                '＋':'new', 'Pin':'pin', 'Pinned':'pin', 'Paste':'paste', 'Copy':'copy',
                'Cut':'cut', 'Delete':'trash', 'Actions':'more', 'Send ↑':'send',
                'Attach…':'attach', 'Clear':'trash', 'Cancel':'close'}
