"""
RVC inference wrapper that blocks argv during imports to prevent argparse conflicts.
"""
import sys
import os
from pathlib import Path

def run_rvc_inference(input_wav: str, output_wav: str, pitch_shift: int, rvc_dir: str) -> bool:
    """
    Run RVC inference without argparse conflicts.
    """
    # MUST set environment variables FIRST, before any imports
    rvc_dir = os.path.abspath(rvc_dir)
    rmvpe_root = os.path.join(rvc_dir, "assets", "rmvpe")
    index_root = os.path.join(rvc_dir, "logs")
    
    os.makedirs(rmvpe_root, exist_ok=True)
    os.makedirs(index_root, exist_ok=True)
    
    os.environ["rmvpe_root"] = rmvpe_root
    os.environ["index_root"] = index_root
    
    try:
        os.chdir(rvc_dir)
        sys.path.insert(0, rvc_dir)
        
        # Block argv to prevent Config() from parsing arguments
        original_argv = sys.argv.copy()
        sys.argv = [sys.argv[0]]  # Keep only script name
        
        try:
            import torch
            import soundfile as sf
            import numpy as np

            # Now safe to import - Config won't see command-line args
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
            
            # Get configuration
            config = Config()
            
            # Load model checkpoint
            model_path = "assets/weights/jarvis.pth"
            index_path = "logs/jarvis/added_jarvis_v2.index"
            
            if not Path(model_path).exists():
                print(f"ERROR: Model not found: {model_path}")
                return False
            
            cpt = torch.load(model_path, map_location="cpu", weights_only=False)
            tgt_sr = cpt["config"][-1]
            cpt["config"][-3] = cpt["weight"]["emb_g.weight"].shape[0]
            version = cpt.get("version", "v2")
            if_f0 = cpt.get("f0", 1)
            
            # Select appropriate model class
            synth_class = {
                ("v1", 1): SynthesizerTrnMs256NSFsid,
                ("v1", 0): SynthesizerTrnMs256NSFsid_nono,
                ("v2", 1): SynthesizerTrnMs768NSFsid,
                ("v2", 0): SynthesizerTrnMs768NSFsid_nono,
            }[(version, if_f0)]
            
            # Build model
            net_g = synth_class(*cpt["config"], is_half=config.is_half)
            del net_g.enc_q
            net_g.load_state_dict(cpt["weight"], strict=False)
            net_g.eval().to(config.device)
            net_g = net_g.half() if config.is_half else net_g.float()
            
            # Load models for feature extraction
            pipeline = Pipeline(tgt_sr, config)
            hubert_model = load_hubert(config)
            
            # Load and preprocess input audio
            audio = load_audio(input_wav, 16000)
            audio_max = np.abs(audio).max() / 0.95
            if audio_max > 1:
                audio /= audio_max
            
            # Use FAISS index if available
            file_index = index_path if Path(index_path).exists() else ""
            
            # Run voice conversion pipeline
            audio_converted = pipeline.pipeline(
                hubert_model,
                net_g,
                0,                  # sid (speaker id)
                audio,
                input_wav,
                [0, 0, 0],          # times
                pitch_shift,        # f0_up_key
                "rmvpe",            # f0_method
                file_index,         # index path
                0.75,               # index_rate
                if_f0,              # use_f0
                3,                  # filter_radius
                tgt_sr,             # target sample rate
                0,                  # resample_sr (0 = don't resample)
                0.25,               # rms_mix_rate
                0.33,               # protect
                None,               # f0_file
            )
            
            # Save output
            sf.write(output_wav, audio_converted, tgt_sr)
            return True
            
        finally:
            # Restore argv
            sys.argv = original_argv
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python rvc_wrapper.py <input_wav> <output_wav> <pitch_shift> <rvc_dir>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    pitch = int(sys.argv[3])
    rvc_path = sys.argv[4]
    
    success = run_rvc_inference(input_file, output_file, pitch, rvc_path)
    sys.exit(0 if success else 1)
