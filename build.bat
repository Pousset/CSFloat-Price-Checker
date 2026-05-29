@echo off
title CSFloat Price Checker — Build EXE
color 0A

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     CSFloat Price Checker — Build EXE    ║
echo  ╚══════════════════════════════════════════╝
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERREUR] Python introuvable dans le PATH.
    pause & exit /b 1
)

echo  [1/3] Installation des dependances...
python -m pip install requests python-dotenv pillow pyinstaller --quiet
if errorlevel 1 (
    echo  [ERREUR] Echec pip install.
    pause & exit /b 1
)
echo         OK
echo.

echo  [2/3] Nettoyage anciens builds...
if exist "dist\CSFloat_Price_Checker.exe" del /f /q "dist\CSFloat_Price_Checker.exe"
if exist "build" rmdir /s /q "build"
if exist "CSFloat_Price_Checker.spec" del /f /q "CSFloat_Price_Checker.spec"
echo         OK
echo.

echo  [3/3] Compilation (1-2 minutes)...
echo.

python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "CSFloat_Price_Checker" ^
    --hidden-import "requests" ^
    --hidden-import "dotenv" ^
    --hidden-import "PIL" ^
    --hidden-import "PIL.Image" ^
    --hidden-import "PIL.ImageTk" ^
    --hidden-import "tkinter" ^
    --hidden-import "tkinter.ttk" ^
    --hidden-import "tkinter.messagebox" ^
    --hidden-import "tkinter.filedialog" ^
    csfloat_gui.py

if errorlevel 1 (
    echo.
    echo  [ERREUR] Compilation echouee.
    pause & exit /b 1
)

if exist ".env" (
    echo.
    echo  Copie .env dans dist\...
    copy ".env" "dist\.env" >nul
)

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║  BUILD REUSSI !                          ║
echo  ║  dist\CSFloat_Price_Checker.exe          ║
echo  ╚══════════════════════════════════════════╝
echo.
echo  Garde le .env dans le meme dossier que le .exe
echo.
pause
