# Empaquetado para Windows — PyInstaller + NSIS

Plan para generar **un solo instalador** (`Gestos-Setup-1.0.exe`) que incluya ambas aplicaciones del proyecto.

> **¿Solo quieres compilarlo?** → ve directo a
> **[`como-compilar-windows.md`](como-compilar-windows.md)**, la guía práctica
> paso a paso (requisitos, comandos, troubleshooting). Este archivo es el
> plan/original con el análisis completo, el porqué de cada decisión y el
> progreso.

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

## Fase 1 — Preparación del código — ✅ LISTO (1.4 omitido a propósito)

### 1.1 Ruta de `gestos.json` (crítico) — ✅ HECHO

`CONFIG_FILE = "gestos.json"` era relativo al directorio de trabajo actual. Lanzando desde un accesos directo **fallaba**, porque el CWD no es la carpeta del `.exe`.

Solución implementada en **`gestos_util.py`** (módulo compartido por ambos entry points):

- `ruta_config()` → en desarrollo usa el propio repo (igual que antes);
  en el `.exe` congelado usa `%APPDATA%\Gestos\gestos.json`
- Primer arranque: copia el `gestos.json` empaquetado (`sys._MEIPASS`) a ese destino
- Si ya existe, **no se sobreescribe** (conserva la config del usuario)
- El desinstalador **conserva** ese archivo

```python
# gestos_util.py — resumen
def es_congelado():
    return bool(getattr(sys, "frozen", False))

def dir_datos():
    if es_congelado():
        base = os.environ.get("APPDATA") or os.path.dirname(sys.executable)
        carpeta = os.path.join(base, NOMBRE_APP)   # %APPDATA%\Gestos
    else:
        carpeta = dir_recursos()                   # el repo, en desarrollo
    os.makedirs(carpeta, exist_ok=True)
    return carpeta

def ruta_config():
    destino = os.path.join(dir_datos(), "gestos.json")
    if not os.path.exists(destino):
        origen = os.path.join(dir_recursos(), "gestos.json")   # sys._MEIPASS si frozen
        if os.path.abspath(origen) != os.path.abspath(destino) and os.path.exists(origen):
            shutil.copyfile(origen, destino)
    return destino
```

### 1.2 Logs (`console=False`) — ✅ HECHO

Como los `.exe` van **sin consola**, todos los `print()` eran invisibles (y el `exit(1)` por cámara fallida se perdía sin rastro).

- `configurar_logging()` redirige `stdout`/`stderr` a `%APPDATA%\Gestos\gestos.log` (1 MB máx., se recorta solo)
- En desarrollo escribe en `gestos.log` de la raíz del repo (ignorado por git)
- `aviso_consola()` muestra un `MessageBoxW` **solo** si no hay consola visible → para errores fatales como cámara no detectada

### 1.3 Dependencias (`requirements.txt`) — ✅ HECHO

```txt
mediapipe==0.10.9
numpy<2
opencv-contrib-python==4.11.0.86
pyautogui
mouse
pyinstaller
```

> **Tres trampas verificadas en PyPI:**
>
> 1. **`mediapipe==0.10.9` solo tiene wheel para cp38–cp311** → usar Python **3.10** (3.12+ no instala).
> 2. **`numpy<2` es obligatorio**: mediapipe 0.10.9 está compilado contra NumPy 1.x; con NumPy 2 revienta con *"module compiled using NumPy 1.x cannot be run in NumPy 2.x"*.
> 3. **No instalar `opencv-python`**: mediapipe ya depende de `opencv-contrib-python` y tener los dos deja dos `cv2` en pelea. Y **tampoco el `-headless`**, porque el código usa `cv2.imshow`.
>    Además se pinea `==4.11.0.86`: a partir de **4.12 el paquete exige `numpy>=2`**, que contradice el punto 2.

### 1.4 Icono

- Crear `assets/icono.ico` (256x256, 128, 64, 48, 32, 16 px)
- Se usa tanto para los `.exe` como para el instalador

---

## Fase 2 — PyInstaller (2 binarios) — ✅ LISTO

### Entorno — ✅ LISTO

```powershell
py -3.10 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

> **Instalado y verificado en la PC de desarrollo:**
> - **Python 3.10.11** (`winget install Python.Python.3.10` → `py -3.10`)
> - **NSIS 3.12** (`winget install NSIS.NSIS` → `C:\Program Files (x86)\NSIS\makensis.exe`)
> - **venv en `venv\`** ya creado con `requirements.txt` instalado
>
> Prueba de humo pasada: `mediapipe 0.10.9` + `numpy 1.26.4` +
> `opencv-contrib-python 4.11.0.86` + `protobuf 3.20.3` + `pyinstaller 6.22.3`,
> `mp.solutions.hands.Hands()` carga los modelos TFLite sin error y
> `cv2.imshow` está disponible (no es el headless).

### Archivos `.spec` — ✅ HECHO (uno por entry point)

`build/prototipo.spec` → `dist\prototipo\Gestos.exe`
`build/gestos_gui.spec` → `dist\gestos_gui\Configurador.exe`

Puntos clave de ambos:

- **`console=False`** (decisión #3) — sin consola, logs a `gestos.log`
- **`datas=[('gestos.json', '.')]`** en ambos: es la default que
  `gestos_util.ruta_config()` copia al `%APPDATA%` en el primer arranque ✅ verificado
- **`SPECPATH`** (variable que inyecta PyInstaller) para resolver rutas relativas al `.spec`
- **Sin `icon=`** — se omite el ícono por ahora (decisión del autor)
- `--collect-all mediapipe` → `collect_all("mediapipe")` dentro del spec: MediaPipe
  trae módulos internos, modelos TFLite y el `.pyd` de bindings que PyInstaller
  **no detecta solo**

#### Trampas encontradas compilando (todas verificadas en runtime)

| # | Error | Causa | Solución |
|---|---|---|---|
| 1 | `ModuleNotFoundError: No module named 'secrets'` | `numpy/random/bit_generator.pyx` hace `import secrets` **compilado en Cython** → invisible al análisis estático de PyInstaller | `hiddenimports=['secrets']` en `prototipo.spec` |
| 2 | `ModuleNotFoundError: No module named 'unittest'` | `excludes=['unittest']` rompe `pyparsing.testing` (lo trae matplotlib) | **no excluir** `unittest`/`doctest`/`pydoc` |
| 3 | `import matplotlib.pyplot` falla | `mp.solutions.hands` → `drawing_styles` → `drawing_utils` lo importa **a nivel de módulo** | **no se puede excluir** matplotlib |
| 4 | fallos de calculators / módulos mediapipe | modelos TFLite y bindings no detectados por análisis estático | `collect_all("mediapipe")` |
| 5 | `NameError: name 'exit' is not defined` | `exit`/`quit` los inyecta el módulo **`site`**, que **no existe** dentro de un `.exe` congelado | usar **`sys.exit()`** — en runtime, no en análisis estático |

#### Tamaño real medido

```
dist\prototipo\   303.8 MB   ← Gestos.exe
    _internal\cv2\         112.8 MB
    _internal\mediapipe\    93.8 MB
    _internal\numpy.libs\   36.4 MB
    _internal\PIL\          12.8 MB
    _internal\matplotlib\   11.8 MB
dist\gestos_gui\   76.2 MB   ← Configurador.exe  (sin cv2/mediapipe/matplotlib)
```

- **`opencv_world3410.dll` (53.3 MB) es obligatorio**: verifiqué con `pefile` que
  `_framework_bindings.pyd` **linka directo** contra él → no se puede excluir.
- `gestos_gui.spec` pone `excludes=['mediapipe','cv2','matplotlib']` → ahorra
  ~150 MB porque el Configurador no toca cámara.
- **Pendiente de optimizar** (Fase 5): `cv2` empaqueta OpenCV completo aunque
  mediapipe trae el suyo, y `mediapipe\modules\` incluye modelos de pose/face/iris
  que no usamos (~20 MB). NSIS con `lzma` comprime bastante, pero hay margen.

### Comandos

```powershell
# ⚠️ --workpath OBLIGATORIO: por defecto PyInstaller usa build\ y
#    mezclaría su caché con tus .spec (que también viven en build\)
pyinstaller build\prototipo.spec --distpath dist --workpath build_tmp --noconfirm
pyinstaller build\gestos_gui.spec --distpath dist --workpath build_tmp --noconfirm
```

Salida esperada:

```
dist/
├── prototipo/     → Gestos.exe        (name='Gestos')
└── gestos_gui/    → Configurador.exe  (name='Configurador')
```

> **Nota sobre el exit code:** PyInstaller escribe su log a **stderr**, así que
> PowerShell puede reportar `Exited with code 1` **aunque el build salió bien**.
> Verificar con `$LASTEXITCODE` redirigiendo `2>$null`, o directamente comprobando
> que exista el `.exe`.

> **Decisión #5 resuelta → dos `onedir` separados, NO fusionados.** Motivos:
> el Configurador no lleva mediapipe (fusionar solo lo inflaría) y así cada exe se
> prueba por separado. NSIS hace dos `File /r` hacia `$INSTDIR`. Si al final los
> dos tamaños pesan, se puede migrar a un `.spec` único con dos `EXE()` + un
> `COLLECT()`.

### Prueba intermedia — ✅ PASADA

```powershell
Remove-Item $env:APPDATA\Gestos\gestos.log   # arrancar limpio
.\dist\prototipo\Gestos.exe
Get-Content $env:APPDATA\Gestos\gestos.log
```

Log real obtenido:

```
2026-10-05 14:19:05  inicio  Gestos.exe
[GESTOS] 4 gesto(s) activos cargados. Umbral: 0.04
[CONFIG] C:\Users\djmin\AppData\Roaming\Gestos\gestos.json
[LOG]    C:\Users\djmin\AppData\Roaming\Gestos\gestos.log
Error: no se pudo abrir la cámara (índice 1, CAP_DSHOW). Ver gestos.log
```

✅ Importa todo (mediapipe/opencv/numpy/matplotlib), **copia `gestos.json` al
`%APPDATA%` en el primer arranque** y carga los 4 gestos. El `MessageBox` de
error de cámara salió tal como se diseñó.

⚠️ **La cámara no se pudo probar:** esta PC **no tiene webcam** (índices 0–3
cerrados, sin dispositivos PnP de imagen). Queda para la Fase 5 en VM.

#### Bugs de diseño corregidos al probar

1. **El logging tenía que ir ANTES que todos los imports.** Originalmente
   `import mediapipe` estaba arriba de `configurar_logging()`, así que un fallo
   de import se perdía en el vacío. Hoy `prototipo.py` y `gestos_gui.py`
   arrancan con `gestos_util` (solo stdlib) y después los imports pesados.
2. **`_Tee` no hacía `flush()` por escritura** → al morir el proceso se perdía
   el buffer y el log salía vacío. Ahora flushea en cada `write()`.
3. **`sys.excepthook` instalado**: una excepción no capturada en una app sin
   consola es **invisible**. Ahora se loguea completa + `MessageBox` si está
   congelado. Fue lo que permitió diagnosticar los errores 1, 2 y 5 de la tabla.

---

## Fase 3 — NSIS (el instalador) — ✅ LISTO

### Instalar

- ~~Descargar **NSIS** → <https://nsis.sourceforge.io>~~ ✅ ya instalado
  (`winget install NSIS.NSIS` → **NSIS 3.12**, `C:\Program Files (x86)\NSIS\makensis.exe`,
  con `Spanish.nlf` y `MUI2.nsh` incluidos)

> **Dos gotchas de NSIS verificados compilando un script de prueba:**
>
> 1. El include correcto es **`!include "MUI2.nsh"`** — `MUI2.nsi` **no existe** y
>    `makensis` aborta con *"could not find"*.
> 2. `$TEMP` es constante de **runtime**. En el script (compile time) hay que usar
>    **`$%TEMP%`**. Rutas relativas a la carpeta del script funcionan sin problema
>    (por eso `OutFile "dist\Gestos-Setup-1.0.exe"` está bien).
>
> Verificado: un esqueleto con `MUI2` + `Spanish` + páginas + secciones
> `Programas`/`Uninstall` **compila OK** con NSIS 3.12.

### Script `build/installer.nsi` — ✅ HECHO y probado

| Elemento | Valor |
|---|---|
| Asistente | `MUI2` (bienvenida → ruta → componentes → instalar → finalizar) |
| Ruta instalación | `%LOCALAPPDATA%\Programs\Gestos` (por usuario, **sin admin**) |
| Archivos | `File /r "..\dist\Gestos\*.*"` |
| Accesos directos | Escritorio + Menú Inicio (submenu "Gestos": Gestos y Configurador) |
| Autoarranque | **`Section` con checkbox** en la página de componentes → `HKCU\...\Run` |
| Desinstalador | Borra atajos, registro y carpeta; **conserva** `%APPDATA%\Gestos\` |
| Compresión | `SetCompressor /SOLID lzma` → **92.5 MB** (de 307 MB, 30%) |
| Salida | `dist\Gestos-Setup-1.0.exe` |
| Iconos | **omitidos** — no hay `.ico`, usan los por defecto |

> **Autoarranque (decisión #2) — resuelto sin `nsDialogs`.** El checkbox no necesita
> una página custom: basta una `Section` opcional, que MUI2 **ya dibuja como casilla**
> en la página de componentes. Truco importante: `SecMain` debe **borrar** la clave
> `Run` al instalar, para que desmarcar la casilla en una *actualización* sí la quite
> (si no, queda pegada de la instalación anterior).

#### Bugs encontrados (todos verificados en instalación real)

| # | Error | Causa | Solución |
|---|---|---|---|
| 6 | `command SetShellVarContext not valid outside Section or Function` | NSIS solo lo admite dentro de `Section`/`Function`, no a nivel global | mover a `Function .onInit` y `Function un.onInit` |
| 7 | **Accesos directos del Menú Inicio no aparecían** (silencioso) | `CreateShortCut` **no crea el directorio destino** y falla sin avisar | `CreateDirectory "$SMPROGRAMS\Gestos"` antes |
| 8 | El desinstalador borraba `%APPDATA%` | — | `Section "Uninstall"` sin tocar esa ruta (ya estaba bien) |

> ⚠️ **Rutas relativas en NSIS son relativas al `.nsi`, no al CWD.** Por eso el
> script vive en `build\` y usa `..\dist\...`. Un `dist\Gestos\*.*` directo
> fallaría con *"can't open file"*.
>
> ⚠️ `$DESKTOP` puede estar **redirigido por OneDrive** (así pasó aquí:
> `C:\Users\...\OneDrive\Desktop`). `$DESKTOP` lo resuelve bien; lo que hay que
> tener claro al *verificar* es mirar la ruta real, no `%USERPROFILE%\Desktop`.

### Prueba completa del ciclo — ✅ PASADA

```
instalar (/S)  → 1768 archivos (1767 origen + Uninstall.exe), 307.4 MB
              → 3 accesos directos OK (Escritorio + Menú Inicio ×2)
              → autoarranque HKCU\Run OK
              → "Aplicaciones instaladas" OK
              → ambos .exe arrancan VÍA ACCESO DIRECTO con CWD=%TEMP%
                 (config leída por ruta absoluta en %APPDATA%)
desinstalar (/S) → INSTDIR borrado, .lnk borrados, Run borrado, ARP borrado
                → %APPDATA%\Gestos\gestos.json CONSERVADO (1476 bytes, idéntico)
```

---

## Fase 4 — Build automatizado — ✅ HECHO

`build.bat` en la raíz (5 pasos: venv → 2 specs → fusionar → NSIS → verificar):

```bat
py -3.10 -m venv venv                         (solo si no existe)
venv\Scripts\pyinstaller.exe build\prototipo.spec  --distpath dist --workpath build_tmp --noconfirm
venv\Scripts\pyinstaller.exe build\gestos_gui.spec --distpath dist --workpath build_tmp --noconfirm
xcopy dist\prototipo → dist\Gestos\  +  copy Configurador.exe
"C:\Program Files (x86)\NSIS\makensis.exe" build\installer.nsi
verifica dist\Gestos-Setup-1.0.exe
```

> ⚠️ **`build.bat` debe ir en ASCII puro y con fin de línea CRLF.** cmd.exe lo
> parsea con la **codepage OEM** de la consola (no con UTF-8): un `.bat` con
> acentos o caracteres de caja (`═`, `→`) corrompe el parseo y sale un festín de
> *"no se reconoce como un comando interno o externo"* con los comandos partidos
> a la mitad. Descubierto a la mala: el primer intento reventó así.
>
> `build.bat --no-pause` omite el `pause` final (para CI/automatización).

> ⚠️ PyInstaller **no puede cross-compilar**: todo el proceso corre en **Windows**.
> La misma receta correría en un runner de GitHub Actions (`windows-latest`)
> si se quisiera (decisión #4 resuelta a favor de PC local).

**Verificado:** `build.bat --no-pause` → `BUILD OK`, `dist\Gestos-Setup-1.0.exe` [97040885 bytes].

---

## Fase 5 — Verificación

### ✅ Ya verificado en la PC de desarrollo (no requiere VM)

- [x] Instalación silenciosa: 1768 archivos, 3 accesos directos, autoarranque, ARP
- [x] Ambos `.exe` arrancan **vía acceso directo** con `CWD=%TEMP%` → la config se
      resuelve por ruta absoluta en `%APPDATA%` (era el bug #1 de todo el plan)
- [x] `Configurador` guarda y **Gestos lo lee** (mismo `gestos.json` compartido)
- [x] `%APPDATA%\Gestos\gestos.log` recoge `print()` + trazas de excepciones
- [x] Desinstalación: borra INSTDIR, `.lnk`, `Run`, ARP **y conserva** `gestos.json`
- [x] Autoarranque: casilla en la página de componentes, marca/desmarca la clave `Run`

### ⬜ Pendiente — requiere VM limpia y webcam

- [ ] Probar en una **VM de Windows limpia** (no la de desarrollo)
- [ ] **Cámara**: `prototipo.py` usa índice **1** (`VideoCapture(1, CAP_DSHOW)`), y esta PC
      **no tiene webcam** (índices 0–3 cerrados) → decidir si se auto-deteca (probar 0, 1)
      o se expone en `gestos.json`
- [ ] Cámara, hotkeys (`win`, `alt`), clicks izq/der
- [ ] Guardar cambios desde el Configurador y reiniciar Gestos (en VM)
- [ ] Autoarranque real al entrar a Windows
- [ ] Que `%LOCALAPPDATA%\Programs\Gestos` funcione en una cuenta **sin** OneDrive
      (aquí `$DESKTOP` estaba redirigido a `OneDrive\Desktop`)

### SmartScreen / antivirus

Sin firma de código, Windows mostrará *"App no reconocida"* al abrir el instalador. Opciones:

1. **Aceptar** y compartir con "Más información → Ejecutar de todos modos" (gratis)
2. **Firma de código** con certificado (de pago, ~$70–400/año)

---

## Decisiones pendientes

| # | Decisión | Opciones | Decisión |
|---|---|---|---|
| 1 | Ruta de instalación | Por usuario (`%LOCALAPPDATA%`) vs Program Files (pide admin) | **Por usuario** — sin UAC ✅ |
| 2 | Autoarranque | Incluir checkbox "Ejecutar al iniciar Windows" | **Incluir** ✅ — `Section` opcional (MUI2 la dibuja como casilla) → `HKCU\...\Run` |
| 3 | Consola de `Gestos.exe` | `console=False` (oculta) vs visible | **Oculta + logs a archivo** ✅ (Fase 1.2) |
| 4 | Dónde compilar | PC Windows local vs GitHub Actions | **PC local** ✅ |
| 5 | Estructura PyInstaller | Dos `onedir` fusionados / dos separados con 2×`File /r` / un `.spec` con 2 `EXE` + 1 `COLLECT` | **Fusionados en `dist\Gestos\`** ✅ — verificado por hash que `_internal` del Configurador es subconjunto exacto (967/968 idénticos) → ahorra **73.5 MB** |
| 6 | Índice de cámara | Fijo en 1 / auto-detectar 0→1 / configurable en `gestos.json` | *Pendiente — sin webcam en la PC de desarrollo no se pudo probar* |

---

## Progreso

- [x] **Fase 1 — Preparación del código**
  - [x] 1.1 Ruta de `gestos.json` → `gestos_util.py` (`%APPDATA%\Gestos` en el exe)
  - [x] 1.2 Logging sin consola → `gestos_util.configurar_logging()` + `aviso_consola()`
  - [x] 1.3 `requirements.txt` con los pines verificados en PyPI
  - [x] `.gitignore` ampliado (`dist/`, `build_tmp/`, `gestos.log`, `__pycache__/`)
  - [x] Doc actualizado con las correcciones
  - [x] 1.4 `assets/icono.ico` — *omitido a propósito (lo de menos), iconos por defecto*
- [x] **Fase 2 — PyInstaller** (2 binarios compilando y corriendo)
  - [x] Entorno: Python 3.10.11 + NSIS 3.12 + venv
  - [x] `build/prototipo.spec` → `Gestos.exe` (303.8 MB)
  - [x] `build/gestos_gui.spec` → `Configurador.exe` (76.2 MB)
  - [x] Prueba intermedia: arranca, copia config al `%APPDATA%`, carga gestos
  - [ ] Cámara — *no hay webcam en esta PC*
- [x] **Fase 3 — NSIS** (`build/installer.nsi` → `Gestos-Setup-1.0.exe`, 92.5 MB)
  - [x] Instalación silenciosa: 1768 archivos, 3 accesos directos, autoarranque, ARP
  - [x] Ambos `.exe` arrancan **vía acceso directo** (CWD = `%TEMP%`)
  - [x] Desinstalación limpia **conservando** `%APPDATA%\Gestos\gestos.json`
- [x] **Fase 4 — `build.bat`** (5 pasos, probado con `--no-pause` → `BUILD OK`)
- [ ] Fase 5 — Verificación en VM (**única pendiente**)

> **Entorno:** ✅ resuelto. Python 3.10.11 + NSIS 3.12 instalados con winget,
> `venv\` creado y `requirements.txt` instalado.
>
> **1.4 (ícono) se omitió a propósito** — el autor decidió que es lo de menos.
> Sin `.ico` no hay `icon=` en los specs ni `MUI_ICON` en NSIS, así que los `.exe`
> y el instalador usan los iconos por defecto. Si algún día se quiere, basta con
> crear `assets/icono.ico` y agregar `icon=` a ambos specs + `MUI_ICON`/`MUI_UNICON`
> al `.nsi`.

---

## Estructura del repo al terminar

```
Tesis-Proyecto/
├── prototipo.py        → Gestos.exe
├── gestos_gui.py       → Configurador.exe
├── gestos_util.py      ← ruta de config + logging (compartido por ambos)
├── gestos.json         (config default, empaquetada y copiada al %APPDATA%)
├── requirements.txt    ✅
├── build.bat           ✅  (ASCII + CRLF)
├── build/
│   ├── prototipo.spec  ✅
│   ├── gestos_gui.spec ✅
│   └── installer.nsi   ✅
├── docs/
│   ├── como-compilar-windows.md   ← guía práctica: cómo compilarlo
│   └── empaquetado-windows.md     plan, análisis y progreso (este archivo)
│
├── dist/               (generado, en .gitignore)
│   ├── prototipo\          Gestos.exe + _internal\
│   ├── gestos_gui\         Configurador.exe + _internal\
│   ├── Gestos\             ← los dos fusionados (lo que instala NSIS)
│   └── Gestos-Setup-1.0.exe   ✅ 92.5 MB
│
├── build_tmp/          (workpath de PyInstaller, en .gitignore)
└── venv/               (Python 3.10, en .gitignore)
```

> **No hay `assets/icono.ico`** — se omitió a propósito. Si se quiere agregar,
> crear el `.ico` y poner `icon='assets\\icono.ico'` en ambos specs + `MUI_ICON`
> y `MUI_UNICON` en `installer.nsi`.

> `modelo.py` y `b.py` son pruebas/sandboxes → **no** entran al empaquetado.
