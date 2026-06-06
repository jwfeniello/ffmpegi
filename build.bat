@echo off
setlocal

echo Building ffmpegi.exe with PyInstaller...

pyinstaller ^
    --onefile ^
    --name ffmpegi ^
    --add-data "vocabulary.py;." ^
    --add-data "src;src" ^
    --hidden-import shlex ^
    --hidden-import dataclasses ^
    --hidden-import argparse ^
    --hidden-import platform ^
    --collect-all rapidfuzz ^
    src\main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo Build failed.
    exit /b %ERRORLEVEL%
)

echo.
echo Done. Binary is at dist\ffmpegi.exe
echo Drop it somewhere on your PATH, e.g.:
echo   copy dist\ffmpegi.exe C:\Windows\System32\ffmpegi.exe
endlocal
