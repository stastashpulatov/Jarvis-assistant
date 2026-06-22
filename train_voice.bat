@echo off
title RVC Train JARVIS Voice

set RVC=rvc_env\RVC
set PY=..\..\rvc_env\Scripts\python.exe
set EXP=jarvis

echo ============================================
echo  Training JARVIS voice model
echo  This will use the GPU heavily for a while
echo ============================================
echo.

if not exist rvc_env\RVC\infer-web.py (
    echo RVC not set up. Run setup_rvc.bat first.
    pause
    exit /b 1
)

dir /b voices\*.wav >nul 2>nul
if errorlevel 1 (
    echo ERROR: no WAV files found in voices\
    echo Put at least one WAV sample of the target voice into voices\ first.
    pause
    exit /b 1
)

echo Step 1: Preparing dataset folder...
if exist dataset_raw rmdir /s /q dataset_raw
mkdir dataset_raw
for %%F in (voices\*.wav) do (
    if /i not "%%~nxF"=="jarvis_sample.wav" copy /Y "%%F" "dataset_raw\%%~nxF" >nul
)
echo OK - copied WAV files to dataset_raw\, see below:
dir /b dataset_raw\*.wav
echo NOTE: jarvis_sample.wav is intentionally skipped if present - it was
echo detected as a music or vocal track, kupigolos.ru metadata, no speech
echo pauses, not clean speech, and would degrade the trained voice.

if not exist rvc_env\RVC\rvc_infer.py copy /Y rvc_infer.py rvc_env\RVC\rvc_infer.py >nul

cd %RVC%
if exist logs\%EXP% (
    echo Removing previous logs\%EXP% to avoid mixing old music-contaminated data...
    rmdir /s /q logs\%EXP%
)
mkdir logs\%EXP%

echo.
echo Step 2: Preprocessing audio (slicing)...
%PY% infer/modules/train/preprocess.py "..\..\dataset_raw" 40000 4 logs\%EXP% False 3.0
if errorlevel 1 (echo FAILED at preprocess & cd ..\.. & pause & exit /b 1)
echo OK

echo.
echo Step 3: Extracting pitch (F0) with RMVPE...
%PY% infer/modules/train/extract/extract_f0_rmvpe.py 1 0 0 logs\%EXP% False
if errorlevel 1 (echo FAILED at f0 extraction & cd ..\.. & pause & exit /b 1)
echo OK

echo.
echo Step 4: Extracting HuBERT features (v2, 768-dim)...
%PY% infer/modules/train/extract_feature_print.py cuda:0 1 0 logs\%EXP% v2 False
if errorlevel 1 (echo FAILED at feature extraction & cd ..\.. & pause & exit /b 1)
echo OK

echo.
echo Step 5: Generating filelist and config...
%PY% -c "import os,json,random; exp='logs/%EXP%'; gt=exp+'/0_gt_wavs'; feat=exp+'/3_feature768'; f0=exp+'/2a_f0'; f0n=exp+'/2b-f0nsf'; names=set(n.split('.')[0] for n in os.listdir(gt)) & set(n.split('.')[0] for n in os.listdir(feat)) & set(n.split('.')[0] for n in os.listdir(f0)) & set(n.split('.')[0] for n in os.listdir(f0n)); opt=[]; [opt.append('%%s/%%s.wav|%%s/%%s.npy|%%s/%%s.wav.npy|%%s/%%s.wav.npy|0' %% (gt,n,feat,n,f0,n,f0n,n)) for n in names]; now=os.getcwd(); [opt.append('%%s/logs/mute/0_gt_wavs/mute40k.wav|%%s/logs/mute/3_feature768/mute.npy|%%s/logs/mute/2a_f0/mute.wav.npy|%%s/logs/mute/2b-f0nsf/mute.wav.npy|0' %% (now,now,now,now)) for _ in range(2)]; random.shuffle(opt); open(exp+'/filelist.txt','w').write('\n'.join(opt)); cfg=json.load(open('configs/v1/40k.json')); json.dump(cfg, open(exp+'/config.json','w'), indent=2); print('Filelist entries:', len(opt))"
if errorlevel 1 (echo FAILED generating filelist & cd ..\.. & pause & exit /b 1)
echo OK

echo.
echo Step 6: Training (500 epochs, batch 2, save every 100)...
echo This is the GPU-heavy part. Please wait - this will take a while.
set USE_LIBUV=0
set PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
%PY% infer/modules/train/train.py -e %EXP% -sr 40k -f0 1 -bs 2 -te 500 -se 100 -pg assets/pretrained_v2/f0G40k.pth -pd assets/pretrained_v2/f0D40k.pth -l 0 -c 0 -sw 1 -v v2
if errorlevel 1 (echo FAILED at training & cd ..\.. & pause & exit /b 1)
echo OK

if not exist assets\weights\%EXP%.pth (
    echo.
    echo WARNING: assets\weights\%EXP%.pth not found after training.
    echo Trying to export weights from the last checkpoint...
    if not exist assets\weights mkdir assets\weights
    %PY% -c "import torch,glob,os; ckpts=sorted(glob.glob('logs/%EXP%/G_*.pth'), key=os.path.getmtime); src=ckpts[-1] if ckpts else None; print('Using checkpoint:', src); cpt=torch.load(src, map_location='cpu') if src else None; torch.save(cpt, 'assets/weights/%EXP%.pth') if cpt else print('NO CHECKPOINT FOUND')"
    if not exist assets\weights\%EXP%.pth (
        echo FAILED - could not produce assets\weights\%EXP%.pth automatically.
        echo Check logs\%EXP%\ for G_*.pth checkpoints and export manually.
        cd ..\..
        pause 
        exit /b 1
    )
    echo OK - exported weights to assets\weights\%EXP%.pth
)

echo.
echo Step 7: Building retrieval index...
%PY% -c "import os,numpy as np,faiss; exp='logs/%EXP%'; feat='%%s/3_feature768'%%exp; npys=[np.load(os.path.join(feat,f)) for f in sorted(os.listdir(feat))]; big=np.concatenate(npys,0); idx=np.arange(big.shape[0]); np.random.shuffle(idx); big=big[idx]; n_ivf=max(1,min(int(16*np.sqrt(big.shape[0])), big.shape[0]//39 if big.shape[0]>=39 else 1)); index=faiss.index_factory(768,'IVF%%s,Flat'%%n_ivf); index_ivf=faiss.extract_index_ivf(index); index_ivf.nprobe=1; index.train(big); index.add(big); faiss.write_index(index, exp+'/added_jarvis_v2.index'); print('Index saved with', big.shape[0], 'vectors, n_ivf=', n_ivf)"
if errorlevel 1 (echo FAILED building index & cd ..\.. & pause & exit /b 1)
echo OK

cd ..\..

echo.
echo ============================================
echo  TRAINING COMPLETE!
echo  Model: rvc_env\RVC\logs\jarvis\
echo  Weights: rvc_env\RVC\assets\weights\jarvis.pth
echo  Index:   rvc_env\RVC\logs\jarvis\added_jarvis_v2.index
echo ============================================
echo Next step: run test_rvc.bat to hear the voice,
echo then run start.bat or python main.py - JARVIS
echo will automatically use the trained voice.
pause
