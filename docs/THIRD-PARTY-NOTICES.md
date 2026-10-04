# Third-party notices

GROK is made by akasumitlamba. Its original resource mark and line icons are project artwork.

The distributable includes Python (PSF License), PySide6 / Shiboken6 and Qt 6 (LGPLv3 / GPLv3 / commercial options, with third-party components under their respective licenses). GROK uses dynamically linked Qt libraries. Users may replace compatible Qt/PySide libraries in the portable distribution for debugging modified library versions. Do not restrict reverse engineering required for LGPL compliance. MSIX package integrity requires repackaging after modifications.

Source and license information:
- https://www.python.org/downloads/source/
- https://doc.qt.io/qtforpython-6/licenses.html
- https://code.qt.io/cgit/pyside/pyside-setup.git/
- https://code.qt.io/cgit/qt/
- https://www.gnu.org/licenses/lgpl-3.0.html

PyInstaller's bootloader exception permits distribution of bundled applications. See https://pyinstaller.org/en/stable/license.html.

Build tools (not app runtime): Pillow and pytest. Windows shell file icons belong to their respective owners and are obtained through Windows/Qt system integration. Provider names identify independent services, not endorsements.

The release must retain the collected third-party license texts in `_internal/licenses`. Review licensing and Microsoft Store requirements before public release.
