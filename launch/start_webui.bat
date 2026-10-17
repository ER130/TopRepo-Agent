@echo off
setlocal

set "PORT=8000"
set "HEREDIR=%~dp0.."
for %%I in ("%HEREDIR%") do set "HEREDIR=%%~fI"

rem Already running (e.g. from an earlier double-click)? Just open the
rem browser -- don't start a second server on the same port.
powershell -NoProfile -Command "try { $c = New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1', %PORT%); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 goto :open

rem Translate the project folder's Windows path to its WSL path once,
rem as its own small command -- doing this inline inside the big
rem start/wsl/bash line below would need a double quote inside a double
rem quote, which cmd.exe's tokenizer does not handle the way bash does.
for /f "usebackq delims=" %%P in (`wsl.exe wslpath -a "%HEREDIR%"`) do set "WSLDIR=%%P"
if "%WSLDIR%"=="" (
    echo Could not resolve the WSL path for %HEREDIR%.
    echo Is WSL installed? Try running "wsl.exe wslpath -a ." yourself to check.
    pause
    exit /b 1
)

rem First run on this machine? Set up this project's own venv instead of
rem assuming one exists anywhere -- a hardcoded path to some specific
rem machine's venv would work on that one machine and nowhere else for
rem anyone who clones this repo fresh. This makes the project
rem self-contained: no manual venv setup, no path to edit.
wsl.exe bash -lc "test -d '%WSLDIR%/.venv'"
if %errorlevel% neq 0 (
    echo First run detected -- setting up a Python virtual environment and
    echo installing dependencies inside the project folder. This happens
    echo once and may take a minute; a console window will show progress.
    start "TopRepo Agent - first-time setup" /wait wsl.exe bash -lc "cd '%WSLDIR%' && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    if %errorlevel% neq 0 (
        echo Setup failed -- see the window above for the error, fix it,
        echo then double-click this again.
        pause
        exit /b 1
    )
)

echo Starting TopRepo Agent web server in WSL -- first launch can take a
echo few seconds while the model client and skills load...
start "TopRepo Agent server" /min wsl.exe bash -lc "cd '%WSLDIR%' && source .venv/bin/activate && exec uvicorn server:app --host 0.0.0.0 --port %PORT%"

set tries=0
:wait
set /a tries=tries+1
if %tries% gtr 30 (
    echo Server did not come up within 30 seconds -- opening the browser
    echo anyway; reload the page once it finishes starting.
    goto :open
)
timeout /t 1 /nobreak >nul
powershell -NoProfile -Command "try { $c = New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1', %PORT%); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% neq 0 goto :wait

:open
start "" "http://localhost:%PORT%/"
