; ══════════════════════════════════════════════════════════════
;  build/installer.nsi  →  dist\Gestos-Setup-1.0.exe
;
;  Instalador por usuario (sin UAC) con Gestos.exe + Configurador.exe.
;
;  Compilar desde la RAÍZ del repo:
;      "C:\Program Files (x86)\NSIS\makensis.exe" build\installer.nsi
;
;  ⚠️ NSIS resuelve las rutas RELATIVAS al archivo .nsi (build\),
;     NO al directorio de trabajo actual → por eso van "..\dist".
;
;  ⚠️ El include es MUI2.nsh (MUI2.nsi NO existe y makensis aborta).
; ══════════════════════════════════════════════════════════════

!include "MUI2.nsh"

!define APP_NAME    "Gestos"
!define APP_VERSION "1.0"
!define PUBLISHER   "Tesis — Control de gestos"

; Rutas relativas a ESTE archivo (build\)
!define SRCDIR  "..\dist\Gestos"
!define OUTFILE "..\dist\Gestos-Setup-${APP_VERSION}.exe"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "${OUTFILE}"

; Por usuario → sin ventana de UAC (decisión #1)
InstallDir "$LOCALAPPDATA\Programs\${APP_NAME}"
InstallDirRegKey HKCU "Software\${APP_NAME}" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma

; Instalador y desinstalador: atajos del usuario actual, no de Todos.
; ⚠️ SetShellVarContext SOLO es válido dentro de una Section/Function:
;    a nivel global makensis aborta con "not valid outside Section or Function".
Function .onInit
  SetShellVarContext current
FunctionEnd

Function un.onInit
  SetShellVarContext current
FunctionEnd

ShowInstDetails show
ShowUninstDetails show

; ── Páginas de instalación ──────────────────────────────────
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; ── Páginas de desinstalación ───────────────────────────────
; ⚠️ SIN ESTAS el desinstalador no tiene páginas y no arranca.
;    Los defines MUI_ICON/MUI_UNICON se omiten a propósito: no hay .ico.
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "Spanish"

; ══════════════════════════════════════════════════════════════
;  Sección principal — obligatoria (SectionIn RO)
; ══════════════════════════════════════════════════════════════
Section "Gestos (programas y accesos directos)" SecMain
  SectionIn RO

  SetOutPath "$INSTDIR"

  ; Resetea el autoarranque ANTES de instalar: si la casilla de abajo está
  ; marcada, SecAutostart lo vuelve a escribir. Así, desmarcarla en una
  ; actualización sí la quita.
  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME}"

  ; dist\Gestos\ contiene Gestos.exe + Configurador.exe + _internal\
  ; (los dos .exe comparten _internal: es un subconjunto exacto, verificado por hash)
  File /r "${SRCDIR}\*.*"

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; ── Accesos directos ──
  ; ⚠️ CreateShortCut NO crea el directorio destino: si falta, falla en
  ;    silencio y el acceso directo no aparece. Hay que CreateDirectory.
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"

  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" \
                 "$INSTDIR\Gestos.exe" \
                 "Control de mouse por gestos"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\Gestos.lnk" \
                 "$INSTDIR\Gestos.exe" \
                 "Control de mouse por gestos"
  CreateShortCut "$SMPROGRAMS\${APP_NAME}\Configurador.lnk" \
                 "$INSTDIR\Configurador.exe" \
                 "Configurar gestos"

  ; ── "Aplicaciones instaladas" de Windows ──
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
              "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
              "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
              "Publisher" "${PUBLISHER}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
              "DisplayIcon" "$INSTDIR\Gestos.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
              "InstallLocation" "$INSTDIR"
  ; ${NSISDIR}\.. es el desinstalador; con / _ y "" para rutas con espacios
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
              "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" \
              "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'

  WriteRegStr HKCU "Software\${APP_NAME}" "InstallDir" "$INSTDIR"
SectionEnd

; ══════════════════════════════════════════════════════════════
;  Autoarranque — casilla en la página de componentes (decisión #2)
;  Marcada por defecto: es una app de control de mouse.
; ══════════════════════════════════════════════════════════════
Section "Ejecutar al iniciar Windows" SecAutostart
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" \
              "${APP_NAME}" "$INSTDIR\Gestos.exe"
SectionEnd

; ══════════════════════════════════════════════════════════════
;  Desinstalador
;  ⚠️ El nombre debe ser EXACTAMENTE "Uninstall" para que NSIS lo
;     compile dentro de Uninstall.exe. Cualquier otro nombre hace que
;     se ejecute DURANTE LA INSTALACIÓN (borraría lo recién instalado).
; ══════════════════════════════════════════════════════════════
Section "Uninstall"
  Delete    "$DESKTOP\${APP_NAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APP_NAME}"

  DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME}"
  DeleteRegKey   HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
  DeleteRegKey   HKCU "Software\${APP_NAME}"

  RMDir /r "$INSTDIR"

  ; %APPDATA%\Gestos\ (gestos.json + gestos.log) se CONSERVA a propósito:
  ; es la configuración del usuario.
SectionEnd

; ══════════════════════════════════════════════════════════════
;  Descripciones en la página de componentes
; ══════════════════════════════════════════════════════════════
LangString DESC_SecMain ${LANG_SPANISH} \
  "Archivos de Gestos y Configurador, accesos directos y desinstalador. (Obligatorio)"
LangString DESC_SecAutostart ${LANG_SPANISH} \
  "Gestos se ejecuta cada vez que inicias Windows. Recomendado: es el control de mouse."

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain}      $(DESC_SecMain)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecAutostart} $(DESC_SecAutostart)
!insertmacro MUI_FUNCTION_DESCRIPTION_END
