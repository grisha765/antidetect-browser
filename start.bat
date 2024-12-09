@echo off
setlocal enabledelayedexpansion

set "current_dir=%~dp0"

set "found_folder="
for /d %%d in ("%current_dir%WPy64*") do (
    if exist "%%d" (
        set "found_folder=%%d"
        goto :folder_found
    )
)

:folder_found
if defined found_folder (
    echo The folder %found_folder% already exists.
    echo Activate %found_folder%\scripts\activate.bat
    call "%found_folder%\scripts\activate.bat"
    python main.py
    pause
    exit /b
)

set "DOWNLOAD_URL="
for /f "tokens=1,* delims=:" %%i in ('curl -s https://api.github.com/repos/winpython/winpython/releases/latest ^| findstr /i "browser_download_url"') do (
    set "line=%%j"
    set "line=!line:"=!"
    for /f "tokens=* delims= " %%x in ("!line!") do set "line=%%x"
    if "!line:~-1!"=="," set "line=!line:~0,-1!"
    echo !line!|findstr /i "Winpython64" >nul && (
        set "DOWNLOAD_URL=!line!"
    )
)

if not defined DOWNLOAD_URL (
    echo ERROR: Could not find browser_download_url for Winpython64 in the latest release.
    pause
    exit /b 1
)

echo DEBUG: Final URL is "%DOWNLOAD_URL%"

echo Downloading WinPython from: %DOWNLOAD_URL%
curl -L "%DOWNLOAD_URL%" -o "%current_dir%WinPython64.exe" --insecure

if not exist "%current_dir%WinPython64.exe" (
    echo ERROR: WinPython installer was not downloaded. Check URL and curl output.
    pause
    exit /b 1
)

"%current_dir%WinPython64.exe" -o"%current_dir%" -y

if errorlevel 1 (
    echo ERROR: WinPython installer failed.
    pause
    exit /b 1
)

echo WinPython is installed in the %current_dir% directory

set "installed_folder="
for /d %%d in ("%current_dir%WPy64*") do (
    set "installed_folder=%%d"
)

if not defined installed_folder (
    echo ERROR: Installed folder not found.
    pause
    exit /b 1
)

call "%installed_folder%\scripts\activate.bat"

pip install -r requirements.txt
python main.py
pause
