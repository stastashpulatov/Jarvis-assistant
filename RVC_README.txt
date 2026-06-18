========================================
 RVC - JARVIS Voice Cloning Setup
========================================

Pipeline: Silero (Russian TTS) -> RVC (voice conversion to JARVIS) -> playback

Everything runs in an ISOLATED venv (rvc_env/) so the main
Jarvis assistant (Silero + Gemini + commands) keeps working
no matter what happens here.

STEPS:

1. setup_rvc.bat
   - Creates rvc_env/ (separate Python environment)
   - Installs torch+cuda, fairseq-fixed (has Python 3.12 wheel!),
     faiss, pyworld, parselmouth, etc.
   - Automatically continues into setup_rvc2.bat, which:
       - Clones RVC-WebUI into rvc_env/RVC
       - Downloads pretrained models (~600MB):
           hubert_base.pt, rmvpe.pt, f0G40k.pth, f0D40k.pth, ffmpeg.exe
       - Verifies all imports work + checks CUDA

   Run this FIRST (just setup_rvc.bat, it chains into part 2).
   If it fails, main Jarvis is untouched.
   To remove: rmdir /s rvc_env

2. train_voice.bat
   - Copies voices/jarvis_sample.wav + jarvis_sample1.wav as dataset
   - Preprocesses (slices audio into ~3s chunks)
   - Extracts pitch (RMVPE) + HuBERT features (v2, 768-dim)
   - Trains for 200 epochs (GPU-heavy, expect 20-40 min on RTX 4060)
   - Builds FAISS retrieval index
   - Output: rvc_env/RVC/assets/weights/jarvis.pth

3. test_rvc.bat
   - Generates a test phrase with Silero
   - Converts it through the trained JARVIS model
   - Plays BOTH versions so you can compare

4. Once jarvis.pth exists, core/tts.py automatically uses RVC.
   No further changes needed - just run: python main.py

TUNING:
  In config.yaml, under "voice:", you can add:
    rvc_pitch_shift: 0     # negative = lower pitch (e.g. -2, -4)

  If voice sounds off, try retraining with more epochs (edit
  train_voice.bat: -te 200 -> -te 400) or adjust index_rate /
  protect values inside rvc_wrapper.py (used by core/tts.py at
  runtime) and rvc_infer.py (used by test_rvc.bat).

TROUBLESHOOTING:
  - If fairseq-fixed fails to install: main Jarvis still works,
    just delete rvc_env and run python main.py as before.
  - If training OOMs (out of memory): edit train_voice.bat,
    change "-bs 4" to "-bs 2".
  - rvc_infer.py timeout (90s) can be increased in core/tts.py
    if your GPU is slower.
