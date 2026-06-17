"""
RVC inference - converts input WAV to JARVIS voice using trained model.
Run from inside rvc_env/RVC/ directory:
  rvc_env\\Scripts\\python.exe rvc_infer.py input.wav output.wav [pitch_shift]

pitch_shift: integer semitones, 0 = no shift, negative = lower pitch
"""
import sys, os, traceback
import numpy as np
import soundfile as sf
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from configs.config import Config
from infer.lib.audio import load_audio
from infer.lib.infer_pack.models import (
    SynthesizerTrnMs256NSFsid,
    SynthesizerTrnMs256NSFsid_nono,
    SynthesizerTrnMs768NSFsid,
    SynthesizerTrnMs768NSFsid_nono,
)
from infer.modules.vc.pipeline import Pipeline
from infer.modules.vc.utils import load_hubert


def main():
    if len(sys.argv) < 3:
        print("Usage: rvc_infer.py input.wav output.wav [pitch_shift]")
        sys.exit(1)

    input_path  = sys.argv[1]
    output_path = sys.argv[2]
    f0_up_key   = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    model_path = "assets/weights/jarvis.pth"
    index_path = "logs/jarvis/added_jarvis_v2.index"

    if not os.path.exists(model_path):
        print(f"ERROR: model not found: {model_path}")
        sys.exit(2)

    config = Config()

    cpt = torch.load(model_path, map_location="cpu", weights_only=False)
    tgt_sr = cpt["config"][-1]
    cpt["config"][-3] = cpt["weight"]["emb_g.weight"].shape[0]
    version = cpt.get("version", "v2")
    if_f0   = cpt.get("f0", 1)

    synth_class = {
        ("v1", 1): SynthesizerTrnMs256NSFsid,
        ("v1", 0): SynthesizerTrnMs256NSFsid_nono,
        ("v2", 1): SynthesizerTrnMs768NSFsid,
        ("v2", 0): SynthesizerTrnMs768NSFsid_nono,
    }[(version, if_f0)]

    net_g = synth_class(*cpt["config"], is_half=config.is_half)
    del net_g.enc_q
    net_g.load_state_dict(cpt["weight"], strict=False)
    net_g.eval().to(config.device)
    net_g = net_g.half() if config.is_half else net_g.float()

    pipeline = Pipeline(tgt_sr, config)
    hubert_model = load_hubert(config)

    audio = load_audio(input_path, 16000)
    audio_max = np.abs(audio).max() / 0.95
    if audio_max > 1:
        audio /= audio_max

    file_index = index_path if os.path.exists(index_path) else ""

    audio_opt = pipeline.pipeline(
        hubert_model,
        net_g,
        0,                  # sid
        audio,
        input_path,
        [0, 0, 0],          # times
        f0_up_key,
        "rmvpe",            # f0_method
        file_index,
        0.75,               # index_rate
        if_f0,
        3,                  # filter_radius
        tgt_sr,
        0,                  # resample_sr (0 = no resample)
        0.25,               # rms_mix_rate
        0.33,               # protect
        None,               # f0_file
    )

    sf.write(output_path, audio_opt, tgt_sr)
    print(f"OK: wrote {output_path} ({tgt_sr} Hz, {len(audio_opt)} samples)")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
