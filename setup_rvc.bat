@echo off
chcp 65001 > nul
title RVC Setup - Part 1

echo ============================================
echo  RVC Setup Part 1 - JARVIS Voice Cloning
echo  Creates an ISOLATED environment - rvc_env
echo  Main JARVIS assistant is NOT touched.
echo ============================================
echo.

set "PYTHON_EXE="

if exist "rvc_env\Scripts\python.exe" (
    echo rvc_env already exists.
    set /p REDO="Delete and recreate it? y or n: "
    if /i "%REDO%"=="y" (
        rmdir /s /q rvc_env
    ) else (
        echo Skipping venv creation, continuing with existing rvc_env...
        goto torch
    )
)

echo Step 1: Locating a Python interpreter for rvc_env...
python --version > nul 2>&1
if not errorlevel 1 set "PYTHON_EXE=python"

if "%PYTHON_EXE%"=="" (
    py -3 --version > nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=py -3"
)

if "%PYTHON_EXE%"=="" (
    echo Python not found! Install Python 3.12 from python.org
    echo Python 3.12 is recommended for RVC.
    echo Make sure to enable "Add Python to PATH" during install.
    pause
    exit /b 1
)

echo Step 2: Creating isolated venv at rvc_env ...
%PYTHON_EXE% -m venv rvc_env
if errorlevel 1 (
    echo FAILED creating venv
    pause
    exit /b 1
)
echo OK

:torch
echo.
echo Step 3: Installing PyTorch with CUDA 12.1 - for RTX 4060 etc...
rvc_env\Scripts\python.exe -m pip install --upgrade pip -q
rvc_env\Scripts\python.exe -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121 -q
if errorlevel 1 (
    echo FAILED installing torch+cuda. Trying CPU-only torch as fallback...
    rvc_env\Scripts\python.exe -m pip install torch torchaudio -q
    if errorlevel 1 (
        echo FAILED installing torch entirely.
        pause
        exit /b 1
    )
    echo WARNING: Installed CPU-only torch. RVC will work but be much slower.
)
echo OK

echo.
echo Step 4: Installing fairseq-fixed - has a Python 3.12 wheel...
rvc_env\Scripts\python.exe -m pip install fairseq-fixed -q
if errorlevel 1 (
    echo FAILED installing fairseq-fixed.
    echo Main JARVIS assistant is untouched - you can delete rvc_env and
    echo continue using JARVIS with Silero voice only, no RVC conversion.
    pause
    exit /b 1
)
echo OK

echo.
echo Step 5: Installing remaining RVC dependencies...
rvc_env\Scripts\python.exe -m pip install faiss-cpu pyworld praat-parselmouth ^
    librosa soundfile sounddevice torchcrepe numpy scipy "av<17" ffmpeg-python ^
    tqdm tensorboard tensorboardX "matplotlib<3.8" gradio==3.34.0 -q
if errorlevel 1 (
    echo Some optional dependencies failed - continuing anyway.
    echo You can retry individually, e.g. fix_av.bat for the av package.
)
echo OK

echo.
echo ============================================
echo  Part 1 complete! Continuing with Part 2...
echo ============================================
echo.
call setup_rvc2.bat
