# Empaquetado para Windows — PyInstaller + NSIS

Plan para generar **un solo instalador** (`Gestos-Setup-1.0.exe`) que incluya ambas aplicaciones del proyecto.

## Objetivo

```
Gestos-Setup-1.0.exe          ← único archivo instalador
   ├── Gestos.exe             (prototipo.py: control de mouse + gestos)
   ├── Configurador.exe       (gestos_gui.py)
   ├── gestos.json            (configuración default)
   ├── Accesos directos       (Escritorio + Menú Inicio)
   ├── [opcional] Ejecutar al iniciar Windows
   └── Desinstalador
```

## Stack elegido

| Componente | Herramienta | Por qué |
|---|---|---|
| Binarios | **PyInstaller** (modo `onedir`) | Estándar de facto; buena compatibilidad con mediapipe/opencv |
| Instalador | **NSIS** | Genera un único `.exe` instalador, gratis y muy configurable |
| Python | **3.10** (venv) | Versión requerida por `mediapipe==0.10.9` |

> **Por qué `onedir` y no `onefile`:** `onefile` extrae todo a temp en cada arranque (lento) y tiene alta tasa de falsos positivos de antivirus. Con `onedir`, NSIS empaqueta la carpeta en el instalador igual → **el usuario final igual recibe un solo archivo**.

---

## Fase 1 — Preparación del código

### 1.1 Ruta de `gestos.json` (crítico)

Hoy `CONFIG_FILE = "gestos.json"` es relativo al directorio de trabajo actual. Lanzando desde un accesos directo **fallará**. Plan:

- Primer arranque: copiar el `gestos.json` empaquetado a `%APPDATA%\Gestos\gestos.json`
- Ambos `.exe` leen y escriben en esa ruta (archivo compartido)
- Si ya existe, no se sobreescribe (conserva la config del usuario)
- El desinstalador **conserva** ese archivo

Ejemplo de helper a agregar en ambos entry points:

```python
import sys, os, shutil

def ruta_config():
    if getattr(sys, "frozen", False):
        base = os.environ["APPDATA"] / ...  # %APPDATA%\Gestos
        dir_ = os.path.join(os.environ["APPDATA"], "Gestos")
    else:
        dir_ = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(dir_, exist_ok=True)
    destino = os.path.join(dir_, "gestos.json")
    if not os.path.exists(destino):
        origen = os.path.join(getattr(sys, "_MEIPASS", dir_), "gestos.json")
        if os.path.exists(origen):
            shutil.copy(origen, destino)
    return destino
```

### 1.2 Dependencias (`requirements.txt`)

```txt
mediapipe==0.10.9
opencv-python
pyautogui
mouse
pyinstaller
```

> **Importante:** usar `opencv-python` y **no** `opencv-python-headless`, porque el código usa `cv2.imshow`.

### 1.3 Icono

- Crear `assets/icono.ico` (256x256, 128, 64, 48, 32, 16 px)
- Se usa tanto para los `.exe` como para el instalador

---

## Fase 2 — PyInstaller (2 binarios)

### Entorno

```powershell
py -3.10 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Archivos `.spec` (uno por entry point)

`build/prototipo.spec` y `build/gestos_gui.spec`, con:

- `icon='assets\\icono.ico'`
- `console=False` (ver decisión #3 abajo)
- **`--collect-all mediapipe`**: MediaPipe trae módulos internos, modelos TFLite y archivos `.task`/`.solutionpackaged` que PyInstaller **no detecta solo** → error clásico en runtime
- Excluir módulos innecesarios para bajar tamaño (`tkinter.dev`, tests, etc.)

### Comandos

```powershell
pyinstaller build\prototipo.spec --distpath dist
pyinstaller build\gestos_gui.spec --distpath dist
```

Salida esperada:

```
dist/
├── prototipo/     → Gestos.exe        (renombrar en spec name='Gestos')
└── gestos_gui/    → Configurador.exe  (renombrar en spec name='Configurador')
```

> **Nota:** los dos `onedir` se fusionan en **una sola carpeta** `dist\Gestos\` antes de pasársela a NSIS (mismo `gestos.json` empaquetado en ambos; basta copiar los DLLs/exe de cada uno sin duplicar).

### Prueba intermedia

Ejecutar `dist\Gestos\Gestos.exe` en la misma máquina antes de armar el instalador.

---

## Fase 3 — NSIS (el instalador)

### Instalar

- Descargar **NSIS** → <https://nsis.sourceforge.io> (incluye `makensis.exe`)

### Script `build/installer.nsi` — elementos clave

| Elemento | Valor |
|---|---|
| Asistente | `MUI2` (bienvenida → ruta → instalar → finalizar) |
| Ruta instalación | `%LOCALAPPDATA%\Programs\Gestos` (por usuario, **sin admin**) |
| Archivos | `File /r dist\Gestos\*` |
| Accesos directos | Escritorio + Menú Inicio (submenu "Gestos": Gestos y Configurador) |
| Autoarranque | Checkbox → clave `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` |
| Desinstalador | Borra atajos, registro y carpeta; **conserva** `%APPDATA%\Gestos\` |
| Compresión | `SetCompressor /SOLID lzma` |
| Salida | `dist\Gestos-Setup-1.0.exe` |
| Iconos | `MUI_ICON` / `MUI_UNICON` = `assets\icono.ico` |

Esqueleto base:

```nsis
!include "MUI2.nsi"
Name "Gestos"
OutFile "dist\Gestos-Setup-1.0.exe"
InstallDir "$LOCALAPPDATA\Programs\Gestos"
RequestExecutionLevel user
SetCompressor /SOLID lzma

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "Spanish"

Section "Programas" SecMain
  SetOutPath "$INSTDIR"
  File /r "dist\Gestos\*.*"
  CreateShortCut "$DESKTOP\Gestos.lnk" "$INSTDIR\Gestos.exe"
  CreateShortCut "$SMPROGRAMS\Gestos\Gestos.lnk" "$INSTDIR\Gestos.exe"
  CreateShortCut "$SMPROGRAMS\Gestos\Configurador.lnk" "$INSTDIR\Configurador.exe"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstaller"
  Delete "$DESKTOP\Gestos.lnk"
  RMDir /r "$SMPROGRAMS\Gestos"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir /r "$INSTDIR"
  ; %APPDATA%\Gestos se conserva a propósito
SectionEnd
```

---

## Fase 4 — Build automatizado

`build.bat` en la raíz:

```bat
@echo off
call venv\Scripts\activate
pyinstaller build\prototipo.spec --distpath dist --noconfirm
pyinstaller build\gestos_gui.spec --distpath dist --noconfirm
makensis build\installer.nsi
echo Listo: dist\Gestos-Setup-1.0.exe
```

> ⚠️ PyInstaller **no puede cross-compilar**: todo el proceso corre en **Windows**. Si no se quiere usar la PC local, la misma receta corre en un runner de GitHub Actions (`windows-latest`).

---

## Fase 5 — Verificación

- [ ] Probar en una **VM de Windows limpia** (no la de desarrollo)
- [ ] Cámara, hotkeys (`win`, `alt`), clicks izq/der
- [ ] Guardar cambios desde el Configurador y reiniciar Gestos
- [ ] Desinstalar y verificar que `%APPDATA%\Gestos\gestos.json` se conserva
- [ ] Autoarranque (si se incluye)

### SmartScreen / antivirus

Sin firma de código, Windows mostrará *"App no reconocida"* al abrir el instalador. Opciones:

1. **Aceptar** y compartir con "Más información → Ejecutar de todos modos" (gratis)
2. **Firma de código** con certificado (de pago, ~$70–400/año)

---

## Decisiones pendientes

| # | Decisión | Opciones | Recomendación |
|---|---|---|---|
| 1 | Ruta de instalación | Por usuario (`%LOCALAPPDATA%`) vs Program Files (pide admin) | **Por usuario** — sin UAC |
| 2 | Autoarranque | Incluir checkbox "Ejecutar al iniciar Windows" | Incluir (es una app de control de mouse) |
| 3 | Consola de `Gestos.exe` | `console=False` (oculta) vs visible | **Oculta + logs a archivo** |
| 4 | Dónde compilar | PC Windows local vs GitHub Actions | Definir según disponibilidad |

---

## Estructura del repo al terminar

```
Tesis-Proyecto/
├── prototipo.py
├── gestos_gui.py
├── gestos.json
├── requirements.txt
├── build.bat
├── assets/
│   └── icono.ico
├── build/
│   ├── prototipo.spec
│   ├── gestos_gui.spec
│   └── installer.nsi
├── docs/
│   └── empaquetado-windows.md   ← este archivo
└── dist/                         (generado, en .gitignore)
```
