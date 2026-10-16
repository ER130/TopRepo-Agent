@echo off
echo Stopping TopRepo Agent web server...
wsl.exe bash -lc "pkill -f 'uvicorn server:app'"
echo Done -- it's safe to leave this closed; the server also just stays
echo running quietly in the background if you'd rather not stop it.
pause
