@echo off
title Test RVC Voice

if not exist rvc_env\RVC\assets\weights\jarvis.pth (
    echo Model not trained yet. Run train_voice.bat first.
    pause
    exit /b 1
)

echo Copying rvc_infer.py into RVC folder...
copy /Y rvc_infer.py rvc_env\RVC\rvc_infer.py >nul

echo Generating test phrase with Silero...
rvc_env\Scripts\python.exe -c "import torch,pathlib,sounddevice as sd,soundfile as sf; hub=pathlib.Path(torch.hub.get_dir()); pt=None; [pt:=p for d in hub.glob('snakers4_silero*') for p in d.rglob('v4_ru.pt')]; imp=torch.package.PackageImporter(str(pt)); m=imp.load_pickle('tts_models','model'); r=m.to('cuda' if torch.cuda.is_available() else 'cpu'); m=r if r is not None else m; audio=m.apply_tts(text='Все системы онлайн, сэр. Джарвис готов к работе.', speaker='aidar', sample_rate=40000, put_accent=True, put_yo=True); sf.write('rvc_env/RVC/_silero_out.wav', audio.detach().cpu().numpy(), 40000); print('Silero output saved')"

echo.
echo Converting to JARVIS voice with RVC...
cd rvc_env\RVC
..\Scripts\python.exe rvc_infer.py _silero_out.wav _jarvis_out.wav 0
if errorlevel 1 (
    echo RVC conversion FAILED - see error above
    cd ..\..
    pause
    exit /b 1
)
cd ..\..

echo.
echo Playing ORIGINAL Silero voice...
rvc_env\Scripts\python.exe -c "import soundfile as sf, sounddevice as sd; d,sr=sf.read('rvc_env/RVC/_silero_out.wav'); sd.play(d,sr); sd.wait()"

echo.
echo Playing CONVERTED JARVIS voice...
rvc_env\Scripts\python.exe -c "import soundfile as sf, sounddevice as sd; d,sr=sf.read('rvc_env/RVC/_jarvis_out.wav'); sd.play(d,sr); sd.wait()"

echo.
echo Done! Compare the two voices above.
pause
