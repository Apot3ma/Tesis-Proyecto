# Cómo compilar el instalador de Windows — Guía paso a paso

Guía **práctica** para generar `Gestos-Setup-1.0.exe` desde una máquina Windows
nueva, de cero. El por qué de cada decisión y el análisis completo están en
[`empaquetado-windows.md`](empaquetado-windows.md); aquí solo lo que hay que hacer.

---

## 0. Qué se obtiene

```
dist\Gestos-Setup-1.0.exe     ~92 MB   ← único archivo para repartir
   ├── Gestos.exe             (prototipo.py:  control de mouse + gestos)
   ├── Configurador.exe       (gestos_gui.py: interfaz de configuración)
   ├── _internal\             (Python + dependencias, compartido por ambos)
   ├── Uninstall.exe
   ├── Accesos directos       (Escritorio + Menú Inicio)
   ├── Autoarranque           (casilla al instalar)
   └── Desinstalador
```

Se instala en `%LOCALAPPDATA%\Programs\Gestos` → **sin pedir administrador**.

---

## 1. Requisitos previos

Solo dos cosas. Con `winget` (viene con Windows 10/11):

```powershell
winget install Python.Python.3.10
winget install NSIS.NSIS
```

### ⚠️ Python 3.10 o 3.11, NADA más nuevo

`mediapipe==0.10.9` solo publicó wheels para **cp38 – cp311**. Con Python 3.12+
`pip install` falla con *no matching distribution found*.

Comprueba qué tienes instalado:

```powershell
py -0p
```

Debe aparecer algo como `-V:3.10`:

```
 -V:3.14 *        C:\...\Python\pythoncore-3.14-64\python.exe   ← no vale
 -V:3.10          C:\...\Programs\Python\Python310\python.exe   ← este
```

Si `py -3.10` no responde, vuelve a instalar la versión correcta:
`winget install Python.Python.3.10 --force`.

### Comprobar NSIS

```powershell
& "C:\Program Files (x86)\NSIS\makensis.exe" /VERSION     # → v3.12
```

También debe existir `C:\Program Files (x86)\NSIS\Include\MUI2.nsh`
(y `Contrib\Language files\Spanish.nlf` para el instalador en español).

---

## 2. Clonar e instalar dependencias

```powershell
git clone https://github.com/Apot3ma/Tesis-Proyecto.git
cd Tesis-Proyecto
git checkout docs/empaquetado-windows

py -3.10 -m venv venv
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt
```

### Comprobar que todo importa

```powershell
venv\Scripts\python -c "import mediapipe as mp, cv2, numpy; print(mp.__version__, cv2.__version__, numpy.__version__)"
```

Debe salir: `0.10.9 4.11.0 1.26.4`.

### Pines obligatorios (no quitarlos de `requirements.txt`)

| Paquete | Por qué va pineado |
|---|---|
| `mediapipe==0.10.9` | Versión requerida; solo tiene wheels para cp38–cp311 |
| `numpy<2` | mediapipe 0.10.9 está compilado contra NumPy 1.x. Con NumPy 2 revienta con *"module compiled using NumPy 1.x cannot be run in NumPy 2.x"* |
| `opencv-contrib-python==4.11.0.86` | A partir de **4.12 exige `numpy>=2`**, que contradice lo anterior. Y **no** usar `opencv-python`: mediapipe ya depende del `contrib`, tener los dos deja dos `cv2` en pelea. Tampoco `-headless`, porque el código usa `cv2.imshow` |

---

## 3. Compilar

### Opción A — automatizado (recomendado)

```powershell
build.bat
```

o, si no quieres la pausa final (CI, scripts):

```powershell
build.bat --no-pause
```

Al final debe decir `BUILD OK`.

### Opción B — manual

```powershell
venv\Scripts\pyinstaller.exe build\prototipo.spec  --distpath dist --workpath build_tmp --noconfirm
venv\Scripts\pyinstaller.exe build\gestos_gui.spec --distpath dist --workpath build_tmp --noconfirm

# fusionar: el Configurador comparte _internal con Gestos
robocopy dist\prototipo dist\Gestos /E
copy dist\gestos_gui\Configurador.exe dist\Gestos\

& "C:\Program Files (x86)\NSIS\makensis.exe" build\installer.nsi
```

> ⚠️ **`robocopy` devuelve `1` cuando COPIÓ ARCHIVOS** — no es error. Su códigos
> 0–7 son éxito; 8 o más, fallo. Si lo metes en un `.bat` con
> `if errorlevel 1 goto :error` lo marcará como error **aunque haya ido bien**
> (por eso `build.bat` usa `xcopy`, que sí devuelve 0 en éxito).

### ⚠️ `--workpath build_tmp` es obligatorio

Por defecto PyInstaller escribe su caché en `build\`, que es donde están tus
`.spec` → los mezcla y ensucia el repo.

---

## 4. Resultado

```
dist\
├── prototipo\          Gestos.exe + _internal\      (303.8 MB)
├── gestos_gui\         Configurador.exe + _internal\ (76.2 MB)
├── Gestos\             ← los dos fusionados         (307.4 MB)
└── Gestos-Setup-1.0.exe   ✅ 92.5 MB
```

> **`dist\` está en `.gitignore`.** El instalador **no** se sube al repo: si
> necesitas llevártelo a otra máquina, cópialo aparte (USB, Drive, etc.).

### Prueba rápida antes de distribuir

```powershell
.\dist\Gestos\Gestos.exe
Get-Content $env:APPDATA\Gestos\gestos.log
```

Si arranca y el log muestra los gestos cargados, la cadena funciona.

---

## 5. Probar en una máquina con cámara

```powershell
# 1. copiar dist\Gestos-Setup-1.0.exe a la otra máquina y ejecutarlo
#    SmartScreen dirá "app no reconocida" → Más información → Ejecutar de todos modos

# 2. tras instalar, revisar el log ante cualquier duda:
notepad $env:APPDATA\Gestos\gestos.log
```

### Checklist

- [ ] **Cámara** abre y se ve el frame
- [ ] Mano **derecha**: mueve el cursor, clic izq (pulgar+índice), clic der (pulgar+medio)
- [ ] Mano **izquierda**: los 4 gestos (Alt+Tab, Win+D, captura, explorador)
- [ ] Guardar cambios en el **Configurador** → cerrar y reabrir **Gestos** → aplicados
- [ ] Autoarranque: desmarcar la casilla → no debe quedar en `HKCU\...\Run`
- [ ] Desinstalar → `%APPDATA%\Gestos\gestos.json` **debe conservarse**
- [ ] `%APPDATA%\Gestos\gestos.log` sin trazas

### 🐛 Problema previsible: índice de cámara

`prototipo.py` está hardcodeado a:

```python
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)   # línea ~95
```

**1** suele ser una webcam USB; la webcam integrada de una laptop suele ser **0**.
Si sale el mensaje *"No se pudo abrir la cámara"*, cambia el `1` por `0` y
recompila con `build.bat`.

Pendiente de mejora: auto-detectar (probar 0, luego 1) o exponerlo en `gestos.json`.

---

## 6. Dónde mirar si algo falla

| Síntoma | Qué mirar |
|---|---|
| El `.exe` no arranca o muere raro | `%APPDATA%\Gestos\gestos.log` ← traza completa |
| No encuentra la configuración | `%APPDATA%\Gestos\gestos.json` |
| Errores en pantalla (ventana *Unhandled exception*) | misma traza en el log |

**Los `.exe` van sin consola** (`console=False`), así que todos los `print()` y
las excepciones van a ese log. Fue diseñado así: sin él, cualquier fallo es
invisible. El log se trunca solo al pasar de 1 MB.

---

## 7. Troubleshooting durante el build

Errores que aparecen **solo** al compilar o ejecutar el `.exe` congelado,
resueltos y documentados:

| Error | Causa | Solución |
|---|---|---|
| `No module named 'secrets'` | `numpy.random` lo importa compilado en Cython → invisible al análisis estático | `hiddenimports=['secrets']` en `prototipo.spec` |
| `No module named 'unittest'` | `excludes=['unittest']` rompe `pyparsing.testing` (lo trae matplotlib) | no excluir `unittest`/`doctest`/`pydoc` |
| `import matplotlib.pyplot` falla | `mp.solutions.hands` → `drawing_utils` lo importa a nivel de módulo | matplotlib **no** se puede excluir |
| `NameError: name 'exit' is not defined` | `exit`/`quit` los inyecta el módulo `site`, que **no existe** en un exe congelado | usar `sys.exit()` |
| `SetShellVarContext not valid outside Section` | NSIS solo lo admite dentro de `Section`/`Function` | mover a `.onInit` / `un.onInit` |
| Los accesos directos del Menú Inicio **no aparecen** (sin error) | `CreateShortCut` **no crea** el directorio destino | `CreateDirectory "$SMPROGRAMS\Gestos"` antes |
| `!include: could not find: "MUI2.nsi"` | ese archivo no existe | usar **`MUI2.nsh`** |
| `build.bat`: *"no se reconoce como un comando"* con comandos partidos | cmd.exe parsea con la **codepage OEM**; un `.bat` UTF-8 con acentos o caracteres de caja (`═`) corrompe las líneas | `build.bat` en **ASCII puro + CRLF** |
| PowerShell reporta *"Exited with code 1"* pero el build salió bien | PyInstaller escribe su log a **stderr** | comprobar `$LASTEXITCODE` con `2>$null`, o que exista el `.exe` |

### Trampas de NSIS

- Las **rutas relativas en `.nsi` son relativas al archivo `.nsi`**, no al CWD.
  Por eso el script vive en `build\` y usa `..\dist\...`.
- `$TEMP` es constante de **runtime**; en compile time se usa `$%TEMP%`.
- La sección del desinstalador se llama **exactamente** `Section "Uninstall"`.
  Con otro nombre NSIS la compila en el *instalador* y borrará lo recién
  instalado.
- Sin `!insertmacro MUI_UNPAGE_CONFIRM` + `MUI_UNPAGE_INSTFILES` el
  desinstalador no tiene páginas y no arranca.
- `$DESKTOP` puede estar redirigido por **OneDrive**
  (`C:\Users\...\OneDrive\Desktop`).

---

## 8. Decisiones tomadas

| # | Decisión | Elección |
|---|---|---|
| 1 | Ruta de instalación | `%LOCALAPPDATA%\Programs\Gestos` — por usuario, **sin UAC** |
| 2 | Autoarranque | **Sí**, como casilla en la página de componentes |
| 3 | Consola de `Gestos.exe` | **Oculta** + logs en `%APPDATA%\Gestos\gestos.log` |
| 4 | Dónde compilar | **PC local** |
| 5 | Estructura PyInstaller | Dos `onedir` **fusionados** en `dist\Gestos\` (−73.5 MB) |
| 6 | Índice de cámara | ⬜ **Pendiente** — ahora fijo en `1` |
| — | Icono `assets/icono.ico` | ⬜ **Omitido a propósito** — iconos por defecto |

### Sobre la fusión (decisión #5)

`gestos_gui\_internal` es **subconjunto exacto** de `prototipo\_internal`
(967/968 archivos idénticos por hash; solo difiere `base_library.zip`).
Por eso se puede fusionar en una sola carpeta y ambos `.exe` comparten
`_internal`, ahorrando 73.5 MB. Si algún día se cambian las dependencias de
uno de los dos, **volver a verificar el hash antes de fusionar**.

---

## 9. Estructura del repo

```
Tesis-Proyecto/
├── prototipo.py              → Gestos.exe
├── gestos_gui.py             → Configurador.exe
├── gestos_util.py            ← ruta de config + logging (compartido)
├── gestos.json               config default
├── requirements.txt          pines obligatorios (ver §2)
├── build.bat                 ASCII + CRLF (ver §3)
├── build/
│   ├── prototipo.spec        PyInstaller → Gestos.exe
│   ├── gestos_gui.spec       PyInstaller → Configurador.exe
│   └── installer.nsi         NSIS → instalador
├── docs/
│   ├── como-compilar-windows.md   ← este archivo
│   └── empaquetado-windows.md     plan, análisis y progreso
│
├── dist/                     (generado, ignorado por git)
├── build_tmp/                (caché de PyInstaller, ignorado)
└── venv/                     (Python 3.10, ignorado)
```

`modelo.py` y `b.py` son pruebas/sandboxes → **no** entran al empaquetado.

---

## 10. Pendiente

- [ ] **Fase 5**: probar en una VM Windows limpia **con webcam** (la de
      desarrollo no tiene ninguna: índices 0–3 cerrados)
- [ ] Índice de cámara configurable o auto-detectado (decisión #6)
- [ ] Icono `assets/icono.ico`
- [ ] Reducir tamaño: `cv2` empaqueta OpenCV completo y `mediapipe` trae
      modelos de pose/face/iris que no se usan (~20 MB)
- [ ] SmartScreen: sin firma de código aparecerá *"App no reconocida"*.
      Opciones: asumirlo (gratis) o certificado de firma (~$70–400/año)
