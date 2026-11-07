@echo off
setlocal enabledelayedexpansion
echo ========================================================
echo   Projet IA ENSI - Systemes Experts ^& Recherche
echo ========================================================

REM Se placer dans le dossier du script
cd /d "%~dp0"

REM 1. Verifier si l'environnement virtuel existe deja
if exist ".venv\Scripts\python.exe" (
    echo [INFO] Environnement virtuel .venv detecte.
    ".venv\Scripts\python.exe" main.py %*
    goto :eof
)

REM 2. Si absent, verifier la presence de Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe ou pas accessible dans le PATH.
    echo Veuillez installer Python 3.10 ou superieur depuis https://www.python.org/
    pause
    exit /b 1
)

REM 3. Creation du venv
echo [INFO] Creation de l'environnement virtuel .venv...
python -m venv .venv
if %errorlevel% neq 0 (
    echo [AVERTISSEMENT] Impossible de creer le venv. Tentative d'installation directe...
    python -m pip install -r requirements.txt
    python main.py %*
    goto :eof
)

REM 4. Installation des dependances
echo [INFO] Installation des dependances...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\pip.exe" install -r requirements.txt

REM 5. Lancement
echo [INFO] Lancement de l'application...
".venv\Scripts\python.exe" main.py %*
endlocal
