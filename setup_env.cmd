@echo off

where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR CRITICO] No se detecta 'conda'. Asegurate de tenerlo instalado y en el PATH.
    echo Tip: Reinicia la terminal si lo acabas de instalar.
    exit /b 1
)

if not exist requirements.txt (
    echo [ERROR] No se encuentra el archivo 'requirements.txt' en este directorio.
    exit /b 1
)

echo [INFO] Comprobaciones pasadas. Iniciando...

echo --- Limpiando entorno 'bits' antiguo ---
call conda remove --name bits --all -y

echo --- Creando entorno 'bits' con Python 3.13 ---
call conda create --name bits python=3.13 -y 

echo --- Instalando dependencias desde requirements.txt ---
call conda run -n bits pip install -r requirements.txt

echo --- Activando entorno 'bits' ---
call conda activate bits

echo [EXITO] Entorno configurado y activado.