# -*- mode: python ; coding: utf-8 -*-
# build/prototipo.spec → dist\prototipo\Gestos.exe
#
# Compilar desde la RAÍZ del repo:
#   pyinstaller build\prototipo.spec --distpath dist --workpath build_tmp --noconfirm
#
# ⚠️ --workpath es obligatorio: sin él PyInstaller usa build\ y mezclaría
#    su caché con los .spec que viven en build\.

import os

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import collect_all

# SPECPATH = carpeta del .spec (build\). La raíz del repo es un nivel arriba.
ROOT = os.path.dirname(SPECPATH)

# MediaPipe trae módulos internos, modelos TFLite (.binarypb / .tflite),
# los .task y el binding .pyd que PyInstaller NO detecta solo.
# Sin esto revienta en runtime con "Failed to load module ... calculator".
mp_datas, mp_binaries, mp_hiddenimports = collect_all("mediapipe")

# NO se puede excluir matplotlib: mp.solutions.hands → drawing_utils
# hace `import matplotlib.pyplot` a nivel de módulo.

block_cipher = None

a = Analysis(
    [os.path.join(ROOT, "prototipo.py")],
    pathex=[ROOT],
    binaries=mp_binaries,
    # gestos.json es la default que gestos_util.ruta_config() copia
    # a %APPDATA%\Gestos\ en el primer arranque.
    datas=[(os.path.join(ROOT, "gestos.json"), ".")] + mp_datas,
    hiddenimports=mp_hiddenimports + [
        # numpy.random (bit_generator.pyx) hace `import secrets` COMPIlado en
        # Cython → PyInstaller no lo ve en análisis estático y revienta con
        # "ModuleNotFoundError: No module named 'secrets'" al arrancar.
        "secrets",
        # Se tragan cuando cv2/numpy cargan por primera vez
        "hashlib",
        "hmac",
        "base64",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # No excluir unittest/doctest/pydoc: pyparsing.testing (traído por
        # matplotlib) los importa a nivel de módulo y rompe el arranque.
        "tkinter.test",
        "lib2to3",
        # mediapipe incluye ejemplos y otros frameworks que no usamos
        "mediapipe.examples",
        "mediapipe.model_maker",
        "mediapipe.tasks.python.metadata",
        "mediapipe.python.calculator_graph_test",
        "mediapipe.python.image_frame_test",
        "mediapipe.python.image_test",
        "mediapipe.python.packet_creator_test",
        "mediapipe.python.packet_getter_test",
        "mediapipe.python.packet_test",
        "mediapipe.python.solution_base_test",
        "mediapipe.python.timestamp_test",
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
    name="Gestos",
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
    name="prototipo",       # → dist\prototipo\
)
