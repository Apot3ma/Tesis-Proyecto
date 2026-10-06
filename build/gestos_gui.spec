# -*- mode: python ; coding: utf-8 -*-
# build/gestos_gui.spec → dist\gestos_gui\Configurador.exe
#
# Compilar desde la RAÍZ del repo:
#   pyinstaller build\gestos_gui.spec --distpath dist --workpath build_tmp --noconfirm
#
# ⚠️ --workpath es obligatorio: sin él PyInstaller usa build\ y mezclaría
#    su caché con los .spec que viven en build\.

import os

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis

# SPECPATH = carpeta del .spec (build\). La raíz del repo es un nivel arriba.
ROOT = os.path.dirname(SPECPATH)

block_cipher = None

a = Analysis(
    [os.path.join(ROOT, "gestos_gui.py")],
    pathex=[ROOT],
    binaries=[],
    # gestos.json es la default que gestos_util.ruta_config() copia
    # a %APPDATA%\Gestos\ en el primer arranque.
    datas=[(os.path.join(ROOT, "gestos.json"), ".")],
    # pyautogui se importa dentro de _probar() — PyInstaller lo detecta,
    # pero su stack (pyscreeze/PIL/pytweening) conviene declararlo.
    hiddenimports=[
        "pyautogui",
        "pygetwindow",
        "pyscreeze",
        "pytweening",
        "mouseinfo",
        "pymsgbox",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # El Configurador NO toca cámara ni visión: fuera todo el stack
        # pesado que sí necesita Gestos.exe. Ahorra ~150 MB de instalación.
        "mediapipe",
        "cv2",
        "matplotlib",
        # ⚠️ NO excluir unittest/doctest/pydoc: pyparsing.testing (traído
        # por matplotlib/pyautogui) los importa y rompe el arranque.
        "tkinter.test",
        "lib2to3",
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Configurador",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # decisión #3: sin consola, logs a gestos.log
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="gestos_gui",       # → dist\gestos_gui\
)
