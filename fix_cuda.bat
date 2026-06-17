@echo off
chcp 65001 > nul
title Install CUDA PyTorch for RTX 4060

echo Uninstalling CPU PyTorch...
pip uninstall torch torchaudio torchvision -y -q

echo Installing PyTorch with CUDA 12.1 for RTX 4060...
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

echo Done! Now run: python test_voice.py
pause
