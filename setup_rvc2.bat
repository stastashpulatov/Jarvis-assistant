@echo off
title RVC Setup - Part 2

echo ============================================
echo  RVC Setup Part 2 (no git needed)
echo  rvc_env already has torch+cuda+fairseq - OK!
echo ============================================
echo.

echo Step 6: Downloading RVC-WebUI as ZIP (no git needed)...
if exist rvc_env\RVC\infer-web.py (
    echo RVC repo already exists, skipping download
    goto models
)

rvc_env\Scripts\python.exe -c "import urllib.request; print('Downloading...'); urllib.request.urlretrieve('https://codeload.github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI/zip/refs/heads/main', 'rvc_temp.zip'); print('Downloaded')"
if errorlevel 1 (
    echo FAILED downloading RVC zip
    pause
    exit /b 1
)

echo Extracting...
rvc_env\Scripts\python.exe -c "import zipfile; zipfile.ZipFile('rvc_temp.zip').extractall('rvc_env')"
if errorlevel 1 (
    echo FAILED extracting RVC zip
    pause
    exit /b 1
)

echo Renaming folder...
rvc_env\Scripts\python.exe -c "import os; d=[x for x in os.listdir('rvc_env') if x.startswith('Retrieval-based-Voice-Conversion-WebUI')][0]; os.rename(os.path.join('rvc_env',d), os.path.join('rvc_env','RVC')); print('Renamed', d, '-> RVC')"
if errorlevel 1 (
    echo FAILED renaming folder
    pause
    exit /b 1
)

del rvc_temp.zip

if not exist rvc_env\RVC\infer-web.py (
    echo FAILED - infer-web.py not found after extraction
    pause
    exit /b 1
)
echo OK - RVC repo ready

:models
echo.
echo Step 7: Downloading pretrained models (this is large, ~600MB)...
cd rvc_env\RVC
if not exist assets\hubert mkdir assets\hubert
if not exist assets\rmvpe mkdir assets\rmvpe
if not exist assets\pretrained_v2 mkdir assets\pretrained_v2

if not exist assets\hubert\hubert_base.pt (
    echo Downloading hubert_base.pt...
    ..\..\rvc_env\Scripts\python.exe -c "import urllib.request; urllib.request.urlretrieve('https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/hubert_base.pt', 'assets/hubert/hubert_base.pt')"
)
if not exist assets\rmvpe\rmvpe.pt (
    echo Downloading rmvpe.pt...
    ..\..\rvc_env\Scripts\python.exe -c "import urllib.request; urllib.request.urlretrieve('https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/rmvpe.pt', 'assets/rmvpe/rmvpe.pt')"
)
if not exist assets\pretrained_v2\f0G40k.pth (
    echo Downloading f0G40k.pth...
    ..\..\rvc_env\Scripts\python.exe -c "import urllib.request; urllib.request.urlretrieve('https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/pretrained_v2/f0G40k.pth', 'assets/pretrained_v2/f0G40k.pth')"
)
if not exist assets\pretrained_v2\f0D40k.pth (
    echo Downloading f0D40k.pth...
    ..\..\rvc_env\Scripts\python.exe -c "import urllib.request; urllib.request.urlretrieve('https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/pretrained_v2/f0D40k.pth', 'assets/pretrained_v2/f0D40k.pth')"
)
if not exist ffmpeg.exe (
    echo Downloading ffmpeg.exe...
    ..\..\rvc_env\Scripts\python.exe -c "import urllib.request; urllib.request.urlretrieve('https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/ffmpeg.exe', 'ffmpeg.exe')"
)
if not exist ffprobe.exe (
    echo Downloading ffprobe.exe...
    ..\..\rvc_env\Scripts\python.exe -c "import urllib.request; urllib.request.urlretrieve('https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/ffprobe.exe', 'ffprobe.exe')"
)

cd ..\..

echo.
echo Step 8: Verifying everything loads...
rvc_env\Scripts\python.exe -c "import torch; import fairseq; import faiss; import pyworld; import parselmouth; import tensorboard; import sounddevice; import torchcrepe; print('CUDA:', torch.cuda.is_available()); print('All imports OK')"
if errorlevel 1 (
    echo SOME IMPORT FAILED - see error above
    pause
    exit /b 1
)

echo.
echo ============================================
echo  SETUP COMPLETE!
echo ============================================
echo Next step: run train_voice.bat
pause
