import torch
import pathlib
import sounddevice as sd
import soundfile as sf
import os
import sys

text = 'Тестовая фраза для подбора тональности голоса. Раз два три.'
speaker = 'aidar'
sample_rate = 24000

print(f"Generating base phrase using Silero (Speaker: {speaker})...")

try:
    hub = pathlib.Path(torch.hub.get_dir())
    pt = None
    for d in hub.glob('snakers4_silero*'):
        for p in d.rglob('v4_ru.pt'):
            pt = p
            break
        if pt: break

    if not pt:
        print("Error: v4_ru.pt not found!")
        sys.exit(1)

    imp = torch.package.PackageImporter(str(pt))
    model = imp.load_pickle('tts_models', 'model')
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model_to_device = model.to(device)
    if model_to_device is not None:
        model = model_to_device

    with torch.no_grad():
        audio = model.apply_tts(
            text=text, 
            speaker=speaker, 
            sample_rate=sample_rate, 
            put_accent=True, 
            put_yo=True
        )
    
    audio_np = audio.detach().cpu().numpy()
    out_path = pathlib.Path('rvc_env/RVC/_silero_out.wav')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    sf.write(str(out_path), audio_np, sample_rate)
    print(f"Saved base audio to {out_path}")
except Exception as e:
    print(f"Silero TTS error: {e}")
    sys.exit(1)
