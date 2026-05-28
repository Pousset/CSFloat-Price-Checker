@echo off
title CSFloat Price Checker — Build EXE
color 0A

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     CSFloat Price Checker — Build EXE    ║
echo  ╚══════════════════════════════════════════╝
echo.

:: ── Vérifier Python ───────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERREUR] Python n'est pas installe ou pas dans le PATH.
    pause & exit /b 1
)

:: ── Installer les dépendances ─────────────────────────────────────────────────
echo  [1/3] Installation des dependances...
python -m pip install requests python-dotenv pyinstaller --quiet
if errorlevel 1 (
    echo  [ERREUR] Echec de pip install.
    pause & exit /b 1
)
echo         OK
echo.

:: ── Nettoyage build précédent ─────────────────────────────────────────────────
echo  [2/3] Nettoyage des anciens builds...
if exist "dist\CSFloat_Price_Checker.exe" del /f /q "dist\CSFloat_Price_Checker.exe"
if exist "build" rmdir /s /q "build"
if exist "CSFloat_Price_Checker.spec" del /f /q "CSFloat_Price_Checker.spec"
echo         OK
echo.

:: ── Compilation PyInstaller ───────────────────────────────────────────────────
echo  [3/3] Compilation en cours (peut prendre 1-2 minutes)...
echo.

python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "CSFloat_Price_Checker" ^
    --hidden-import "requests" ^
    --hidden-import "dotenv" ^
    --hidden-import "tkinter" ^
    --hidden-import "tkinter.ttk" ^
    --hidden-import "tkinter.messagebox" ^
    --hidden-import "tkinter.filedialog" ^
    csfloat_gui.py

if errorlevel 1 (
    echo.
    echo  [ERREUR] La compilation a echoue. Voir les messages ci-dessus.
    pause & exit /b 1
)

:: ── Copier le .env à côté du .exe ─────────────────────────────────────────────
if exist ".env" (
    echo.
    echo  Copie du fichier .env dans dist\...
    copy ".env" "dist\.env" >nul
    echo  Le .exe lira automatiquement la cle API depuis dist\.env
)

:: ── Succès ────────────────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║  BUILD REUSSI !                          ║
echo  ║                                          ║
echo  ║  Ton executable est dans :               ║
echo  ║  dist\CSFloat_Price_Checker.exe          ║
echo  ╚══════════════════════════════════════════╝
echo.
echo  Note : garde le fichier .env dans le meme dossier que le .exe
echo.
pause
