@echo off
title Test RVC Pitch Sweep

if not exist rvc_env\RVC\assets\weights\jarvis.pth (
    echo Model not trained yet.
    pause
    exit /b 1
)

echo Generating base phrase with Silero...
rvc_env\Scripts\python.exe test_pitch.py


if not exist rvc_env\RVC\rvc_infer.py copy /Y rvc_infer.py rvc_env\RVC\rvc_infer.py >nul

cd rvc_env\RVC

echo.
echo Converting with pitch -6...
..\Scripts\python.exe rvc_infer.py _silero_out.wav _jarvis_pitch_minus6.wav -6
echo Converting with pitch -3...
..\Scripts\python.exe rvc_infer.py _silero_out.wav _jarvis_pitch_minus3.wav -3
echo Converting with pitch 0...
..\Scripts\python.exe rvc_infer.py _silero_out.wav _jarvis_pitch_0.wav 0
echo Converting with pitch +3...
..\Scripts\python.exe rvc_infer.py _silero_out.wav _jarvis_pitch_plus3.wav 3
echo Converting with pitch +6...
..\Scripts\python.exe rvc_infer.py _silero_out.wav _jarvis_pitch_plus6.wav 6

cd ..\..

echo.
echo ========================================
echo Done! 
echo Now open the folder: rvc_env\RVC\
echo And listen to these files:
echo   - _jarvis_pitch_minus6.wav
echo   - _jarvis_pitch_minus3.wav
echo   - _jarvis_pitch_0.wav
echo   - _jarvis_pitch_plus3.wav
echo   - _jarvis_pitch_plus6.wav
echo.
echo Find the one that sounds exactly like Jarvis!
echo Then open config.yaml and set rvc_pitch_shift to that number.
echo ========================================
pause
