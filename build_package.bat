@echo off
echo Starting build process...

call venv\Scripts\activate.bat

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

python -m PyInstaller --onefile --windowed --name=app --add-data=questions.db;. --add-data=config.py;. --exclude-module=PyQt5.Qt main.py

if %errorlevel% equ 0 (
    echo Build successful!
    echo exe location: dist\app.exe
) else (
    echo Build failed!
)

pause