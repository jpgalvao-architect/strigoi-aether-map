# SPDX-License-Identifier: GPL-3.0-only
# Folder distribution preserves Qt DLLs, plugins and license notices.
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

# Do not collect unrelated DLLs from tools installed elsewhere on the build host.
# Windows 10/11 supply UCRT and ICU; old copies on PATH can break modern Qt.
windows = Path(os.environ.get('WINDIR', 'C:/Windows'))
os.environ['PATH'] = os.pathsep.join([str(Path(sys.executable).parent), sys.base_prefix,
                                   str(windows / 'System32'), str(windows)])

data = collect_data_files('app', includes=['assets/**/*.svg', 'assets/*.png', 'assets/maps/*.webp', 'assets/*.ico', 'assets/*.json', 'data/*.json', 'data/profiles/*.json', 'config/*.json'])
data += collect_data_files('tzdata')
data += collect_data_files('app', includes=['assets/i18n/*.json', 'assets/i18n/*.qm', 'assets/legal/*.txt'])
data += collect_data_files('app', includes=['assets/sonar/*.npz', 'assets/sonar/*.json'])
a = Analysis(['launcher.py'], pathex=['.'], binaries=[('app/assets/sonar/sonar-capture.exe', 'app/assets/sonar')], datas=data,
             hiddenimports=['cv2', 'mss', 'numpy', 'PySide6.QtSvg', 'PySide6.QtSvgWidgets'],
             excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtPdf', 'pytest'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='StrigoiAetherMap',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False,
          icon='app/assets/aether.ico')
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='StrigoiAetherMap')
