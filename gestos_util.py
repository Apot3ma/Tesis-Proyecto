r"""
Utilidades compartidas por prototipo.py (Gestos.exe)
y gestos_gui.py (Configurador.exe).

Resuelve dos problemas del empaquetado con PyInstaller:

  1. `gestos.json` no puede ser una ruta relativa: el directorio de trabajo
     actual NO es la carpeta del .exe cuando se lanza desde un acceso
     directo. Se usa siempre una ruta absoluta en %APPDATA%\Gestos.

  2. Los .exe se compilan con `console=False`, así que `print()` no se ve
     en ninguna parte. stdout/stderr se redirigen a gestos.log para poder
     depurar en la máquina del usuario.

En desarrollo (sin compilar) todo sigue funcionando igual que antes:
la configuración se lee/escribe del propio repo y el log se escribe
en gestos.log de la raíz (ignorado por git).
"""

import io
import os
import shutil
import sys
from datetime import datetime

NOMBRE_APP = "Gestos"
ARCHIVO_CONFIG = "gestos.json"
ARCHIVO_LOG = "gestos.log"

_log_configurado = False


def es_congelado():
    """True cuando corre como .exe compilado por PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def dir_recursos():
    """Carpeta con los archivos empaquetados junto al código."""
    if es_congelado():
        # PyInstaller extrae los datos a sys._MEIPASS (...\_internal en onedir)
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def dir_datos():
    """Carpeta de datos de la app: aquí viven gestos.json y gestos.log."""
    if es_congelado():
        base = os.environ.get("APPDATA") or os.path.dirname(sys.executable)
        carpeta = os.path.join(base, NOMBRE_APP)
    else:
        # En desarrollo todo queda en el repo, como hasta ahora
        carpeta = dir_recursos()
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


def ruta_config():
    """Ruta absoluta de gestos.json.

    Primer arranque: copia la configuración default que viene empaquetada.
    Si ya existe no se toca (conserva la configuración del usuario), y el
    desinstalador tampoco la borra.
    """
    destino = os.path.join(dir_datos(), ARCHIVO_CONFIG)
    if not os.path.exists(destino):
        origen = os.path.join(dir_recursos(), ARCHIVO_CONFIG)
        # En desarrollo origen y destino son el mismo archivo
        if os.path.abspath(origen) != os.path.abspath(destino) and os.path.exists(origen):
            shutil.copyfile(origen, destino)
    return destino


class _Tee:
    """Escribe en la consola (si hay) y en el archivo de log a la vez."""

    def __init__(self, *streams):
        self._streams = [s for s in streams if s is not None]

    def write(self, texto):
        for s in self._streams:
            try:
                s.write(texto)
                # Log de diagnóstico: se fuerza el flush en cada escritura
                # porque si el proceso muere el buffer se pierde y dejamos
                # de ver justo lo que necesitamos para depurar.
                s.flush()
            except Exception:
                pass
        return len(texto)

    def flush(self):
        for s in self._streams:
            try:
                s.flush()
            except Exception:
                pass

    def isatty(self):
        for s in self._streams:
            if hasattr(s, "isatty"):
                try:
                    return s.isatty()
                except Exception:
                    pass
        return False

    def fileno(self):
        for s in self._streams:
            if hasattr(s, "fileno"):
                try:
                    return s.fileno()
                except Exception:
                    pass
        raise io.UnsupportedOperation("sin fileno (app sin consola)")


def configurar_logging():
    """Redirige stdout/stderr a gestos.log. Devuelve la ruta del archivo."""
    global _log_configurado

    ruta = os.path.join(dir_datos(), ARCHIVO_LOG)
    if _log_configurado:
        return ruta
    _log_configurado = True

    try:
        # Evita un log que crezca sin límite
        if os.path.getsize(ruta) > 1_000_000:  # 1 MB
            os.remove(ruta)
    except OSError:
        pass

    log = open(ruta, "a", encoding="utf-8", errors="replace")
    log.write("\n" + "=" * 60 + "\n")
    log.write(
        "{}  inicio  {}\n".format(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            os.path.basename(sys.argv[0]) or NOMBRE_APP,
        )
    )
    log.write("=" * 60 + "\n")
    log.flush()

    sys.stdout = _Tee(sys.stdout, log)
    sys.stderr = _Tee(sys.stderr, log)

    # En una app sin consola una excepción no capturada no se ve en NINGÚN
    # lado: se loguea y se avisa con un MessageBox (solo si está congelado,
    # en desarrollo ya revienta en la terminal).
    def _excepthook(tipo, valor, tb):
        import traceback

        traceback.print_exception(tipo, valor, tb, file=sys.stderr)
        sys.stderr.flush()
        aviso_consola(
            "Gestos se cerró por un error inesperado.\n\n"
            f"{tipo.__name__}: {valor}\n\n"
            f"Detalle completo en:\n{ruta}",
            titulo=f"{NOMBRE_APP} — error",
        )

    sys.excepthook = _excepthook
    return ruta


def aviso_consola(texto, titulo=None):
    """Muestra un MessageBox solo si no hay consola visible (exe sin consola)."""
    if not es_congelado():
        return None
    try:
        import ctypes

        print(f"[AVISO] Mostrando MessageBox: {titulo or NOMBRE_APP}")
        # MB_ICONERROR (0x10) + MB_OK por defecto → bloquea hasta que el
        # usuario lo cierre. Si retorna, se registra el valor: 0 = falló,
        # 1 = IDOK, 2 = IDCANCEL, 3 = IDABORT, etc.
        r = ctypes.windll.user32.MessageBoxW(
            0, texto, titulo or NOMBRE_APP, 0x10  # MB_ICONERROR
        )
        print(f"[AVISO] MessageBoxW retornó {r}" + ("  ← FALLO (0)" if r == 0 else ""))
        return r
    except Exception as e:
        # Nunca en silencio: esto era exactamente lo que nos estaba tapando
        print(f"[ERROR] No se pudo mostrar el MessageBox: {e!r}")
        return None
