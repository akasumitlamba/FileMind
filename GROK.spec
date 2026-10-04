# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

site_data = [(str(p), str(p.parent)) for p in Path('website').rglob('*') if p.is_file() and p.suffix.lower() not in ('.msix', '.cer')]


a = Analysis(
    ['src\\main.py'],
    pathex=['src'],
    binaries=[],
    datas=[('assets', 'assets'), ('docs/THIRD-PARTY-NOTICES.md', '.')] + site_data,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6', 'PyQt5', 'tkinter', 'numpy', 'matplotlib'],
    noarchive=False,
    optimize=0,
)
# Qt's Windows build imports the Windows ICU API. A PATH-installed ICU (for
# example another developer tool's versioned ICU) is ABI-incompatible here.
# Windows 10 19041+ supplies icuuc.dll/icu.dll; do not shadow these system DLLs.
a.binaries = [entry for entry in a.binaries if Path(entry[0]).name.lower() not in ('icuuc.dll', 'icuin.dll', 'icudt78.dll')]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GROK',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='packaging\\version.txt',
    icon=['assets\\grok.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='GROK',
)
