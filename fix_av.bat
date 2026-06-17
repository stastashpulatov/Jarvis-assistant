@echo off
title Fix av dependency

echo Installing av (PyAV) for audio loading...
rvc_env\Scripts\python.exe -m pip install "av<17" -q
if errorlevel 1 (
    echo FAILED installing av
    pause
    exit /b 1
)

echo OK - verifying...
rvc_env\Scripts\python.exe -c "import av; print('av version:', av.__version__)"
if errorlevel 1 (
    echo av still not working
    pause
    exit /b 1
)

echo.
echo Done! Now run train_voice.bat again.
pause
