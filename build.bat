@echo off
setlocal enabledelayedexpansion
title Gestos - Build

REM =================================================================
REM  build.bat - encadena Fase 2 (PyInstaller) + Fase 3 (NSIS)
REM
REM  Requisitos (instalados con winget):
REM     Python 3.10  -> py -3.10
REM     NSIS 3.12    -> C:\Program Files (x86)\NSIS\makensis.exe
REM
REM  Uso, desde la RAIZ del repo:
REM     build.bat              (con pausa al final)
REM     build.bat --no-pause   (para CI / automatizacion)
REM
REM  Salida: dist\Gestos-Setup-1.0.exe
REM
REM  NOTA: este archivo va en ASCII puro y con fin de linea CRLF.
REM  cmd.exe lo parsea con la codepage OEM de la consola, asi que un
REM  UTF-8 con acentos/caja lo corrompe y sale "no se reconoce ...".
REM =================================================================

cd /d "%~dp0"

set VENV=venv
set DIST=dist
set WORK=build_tmp
set MAKENSIS=C:\Program Files (x86)\NSIS\makensis.exe
set SETUP=%DIST%\Gestos-Setup-1.0.exe

echo.
echo [1/5] Entorno virtual...
if not exist "%VENV%\Scripts\python.exe" (
    echo       Creando %VENV% con Python 3.10...
    py -3.10 -m venv "%VENV%"
    if errorlevel 1 goto :error
    "%VENV%\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 goto :error
    "%VENV%\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :error
) else (
    echo       Ya existe.
)

echo.
echo [2/5] PyInstaller: Gestos.exe y Configurador.exe...
REM --workpath es OBLIGATORIO: por defecto PyInstaller usa build\ y
REM mezclaria su cache con los .spec que viven en build\
"%VENV%\Scripts\pyinstaller.exe" build\prototipo.spec --distpath %DIST% --workpath %WORK% --noconfirm
if errorlevel 1 goto :error
"%VENV%\Scripts\pyinstaller.exe" build\gestos_gui.spec --distpath %DIST% --workpath %WORK% --noconfirm
if errorlevel 1 goto :error

echo.
echo [3/5] Fusionando los dos onedir en %DIST%\Gestos\...
REM   Los dos .exe comparten _internal. Verificado por hash que
REM   gestos_gui\_internal es subconjunto exacto de prototipo\_internal
REM   (967/968 identicos). Fusionar ahorra ~73 MB de instalacion.
if exist "%DIST%\Gestos" rmdir /s /q "%DIST%\Gestos"
xcopy "%DIST%\prototipo" "%DIST%\Gestos\" /E /I /Q /Y >nul
if errorlevel 1 goto :error
copy /Y "%DIST%\gestos_gui\Configurador.exe" "%DIST%\Gestos\" >nul
if errorlevel 1 goto :error

echo.
echo [4/5] NSIS: instalador...
if not exist "%MAKENSIS%" (
    echo       ERROR: no se encontro NSIS en "%MAKENSIS%"
    echo       Instalar con: winget install NSIS.NSIS
    goto :error
)
"%MAKENSIS%" build\installer.nsi
if errorlevel 1 goto :error

echo.
echo [5/5] Verificando salida...
if not exist "%SETUP%" (
    echo       ERROR: no se genero %SETUP%
    goto :error
)
for %%A in ("%SETUP%") do echo       %SETUP%  [%%~zA bytes]

echo.
echo ============================================================
echo  BUILD OK
echo  Instalador: %SETUP%
echo  Probar en una VM limpia (Fase 5 del doc)
echo ============================================================
echo.
if /I "%~1"=="--no-pause" exit /b 0
pause
exit /b 0

:error
echo.
echo ============================================================
echo  BUILD FALLIDO - revisa el error de arriba
echo  Logs en ejecucion:  %%APPDATA%%\Gestos\gestos.log
echo ============================================================
echo.
if /I "%~1"=="--no-pause" exit /b 1
pause
exit /b 1
