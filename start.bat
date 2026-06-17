@echo off
chcp 65001 > nul
title JARVIS

set "PYTHON_EXE="

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe --version > nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=.venv\Scripts\python.exe"
)

if "%PYTHON_EXE%"=="" (
    python --version > nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=python"
)

if "%PYTHON_EXE%"=="" (
    py -3 --version > nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=py -3"
)

if "%PYTHON_EXE%"=="" (
    echo Python not found!
    echo Install Python 3.12 or 3.13 from python.org and enable "Add Python to PATH".
    pause
    exit /b 1
)

echo Installing dependencies...
%PYTHON_EXE% -m pip install --upgrade pip -q
%PYTHON_EXE% -m pip install -r requirements.txt -q

if errorlevel 1 (
    echo Dependencies failed. Trying pyaudio via pipwin...
    %PYTHON_EXE% -m pip install pipwin -q
    %PYTHON_EXE% -m pipwin install pyaudio
    %PYTHON_EXE% -m pip install -r requirements.txt -q
)

%PYTHON_EXE% -c "import torch; assert torch.cuda.is_available()" 2>nul
if errorlevel 1 (
    echo Installing PyTorch CUDA 12.1 for RTX 4060...
    %PYTHON_EXE% -m pip uninstall torch torchaudio -y -q 2>nul
    %PYTHON_EXE% -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121 -q
)

echo Starting JARVIS...
%PYTHON_EXE% main.py
pause
