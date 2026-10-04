"""Download canonical license texts to bundle with dynamically linked Qt."""
from pathlib import Path
from urllib.request import urlopen
root = Path(__file__).resolve().parents[1] / 'assets/licenses'
root.mkdir(parents=True, exist_ok=True)
urls = {
    'LGPL-3.0.txt': 'https://www.gnu.org/licenses/lgpl-3.0.txt',
    'GPL-3.0.txt': 'https://www.gnu.org/licenses/gpl-3.0.txt',
    'Qt-third-party.html': 'https://doc.qt.io/qt-6/licenses-used-in-qt.html',
}
for name, url in urls.items():
    with urlopen(url, timeout=30) as response:
        data = response.read()
    (root / name).write_bytes(data)
