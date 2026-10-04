import importlib.metadata
import shutil
import sys
from pathlib import Path
out = Path(__file__).resolve().parents[1] / 'dist/GROK/_internal/licenses'
out.mkdir(parents=True, exist_ok=True)
for package in ['PySide6_Essentials', 'PySide6_Addons', 'shiboken6', 'pyinstaller']:
    dist = importlib.metadata.distribution(package)
    for file in dist.files or []:
        if 'license' in str(file).lower() and dist.locate_file(file).is_file():
            dest = out / package / Path(str(file)).name
            dest.parent.mkdir(exist_ok=True)
            shutil.copy2(dist.locate_file(file), dest)
license_file = Path(sys.base_prefix) / 'LICENSE.txt'
if license_file.exists():
    shutil.copy2(license_file, out / 'Python-LICENSE.txt')
