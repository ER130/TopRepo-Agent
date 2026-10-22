@echo off
setlocal

set "HEREDIR=%~dp0.."
for %%I in ("%HEREDIR%") do set "HEREDIR=%%~fI"

rem Translate the project folder's Windows path to its WSL path once,
rem as its own small command -- doing this inline inside a bigger
rem start/wsl/bash line would need a double quote inside a double
rem quote, which cmd.exe's tokenizer does not handle the way bash does.
for /f "usebackq delims=" %%P in (`wsl.exe wslpath -a "%HEREDIR%"`) do set "WSLDIR=%%P"
if "%WSLDIR%"=="" (
    echo Could not resolve the WSL path for %HEREDIR%.
    echo Is WSL installed? Try running "wsl.exe wslpath -a ." yourself to check.
    exit /b 1
)

rem First run on this machine? Run the venv/dependency setup in its own
rem visible console window so you can see it happen (and see the error
rem if something's missing, like python3 itself). Everything else --
rem starting the server, waiting for it to come up, opening the browser
rem -- is the same cross-platform logic launch.py uses on macOS/Linux,
rem just run here inside WSL.
wsl.exe bash -lc "test -d '%WSLDIR%/.venv'"
if %errorlevel% neq 0 (
    echo First run detected -- setting up a Python virtual environment and
    echo installing dependencies inside the project folder. This happens
    echo once and may take a minute; a console window will show progress.
    start "TopRepo Agent - first-time setup" /wait wsl.exe bash -lc "cd '%WSLDIR%' && python3 launch/launch.py --setup-only"
    if %errorlevel% neq 0 (
        echo Setup failed -- see the window above for the error, fix it,
        echo then run this again.
        exit /b 1
    )
)

wsl.exe bash -lc "cd '%WSLDIR%' && python3 launch/launch.py"
