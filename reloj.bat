@echo off
rem ---------------------------------------------------------------------
rem  Reloj de sobremesa. Doble clic y listo.
rem
rem  La primera vez instala lo que falte; a partir de ahi arranca directo.
rem  Todo lo interesante se elige ya con la ventana abierta (flechas para
rem  cambiar de esfera, g para guardar un PNG), asi que aqui solo hay lo
rem  que hay que decidir ANTES de abrirla.
rem ---------------------------------------------------------------------
setlocal
cd /d "%~dp0"
chcp 65001 >nul

where python >nul 2>&1
if errorlevel 1 (
    echo No encuentro Python. Instalalo desde python.org y marca
    echo "Add python.exe to PATH" durante la instalacion.
    pause
    exit /b 1
)

rem Comprobacion barata: si falta alguna dependencia, instalarlas todas.
python -c "import sdl2, numpy, PIL" >nul 2>&1
if errorlevel 1 (
    echo Primera vez: instalando dependencias...
    python -m pip install -q -r requirements.txt
    if errorlevel 1 (
        echo No se pudieron instalar. Mira el error de arriba.
        pause
        exit /b 1
    )
)

:menu
cls
echo.
echo   RELOJ DE SOBREMESA
echo   ==================
echo.
echo   1   Ventana         (empieza en disco, flechas para pasear)
echo   2   Pantalla completa
echo.
echo   3   Elegir una esfera concreta
echo   4   Ver las quince en un PNG
echo.
echo   5   Actualizar desde GitHub  (git pull)
echo   0   Salir
echo.
set "op="
set /p "op=  Que hago?  "

if "%op%"=="1" goto ventana
if "%op%"=="2" goto completa
if "%op%"=="3" goto elegir
if "%op%"=="4" goto hoja
if "%op%"=="5" goto actualizar
if "%op%"=="0" exit /b 0
goto menu

:ventana
python -m reloj --ventana
goto menu

:completa
python -m reloj
goto menu

:elegir
cls
echo.
python -m reloj --lista
echo.
set "cual="
set /p "cual=  Nombre de la esfera:  "
if "%cual%"=="" goto menu
python -m reloj --ventana --esfera %cual%
goto menu

:hoja
python -m reloj --lamina todas.png --esfera TODAS --lado 440
if exist todas.png start "" todas.png
goto menu

:actualizar
where git >nul 2>&1
if errorlevel 1 (
    echo No encuentro git. Instalalo desde git-scm.com
    pause
    goto menu
)
git pull
echo.
pause
goto menu
