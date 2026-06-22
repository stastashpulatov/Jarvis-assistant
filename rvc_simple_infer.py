я#!/usr/bin/env python3
"""
Simple RVC inference wrapper - avoids argparse conflicts by running in isolated subprocess.
Usage: python rvc_simple_infer.py <input_wav> <output_wav> <pitch_shift> <rvc_dir>
"""
import sys
import os
import json

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("ERROR: Usage: rvc_simple_infer.py <input> <output> <pitch> <rvc_dir>")
        sys.exit(1)
    
    input_wav = sys.argv[1]
    #!/usr/bin/env python3
    """
    Minimal RVC inference wrapper - avoids argparse conflicts.
    Usage: python rvc_simple_infer.py <input_wav> <output_wav> <pitch_shift> <rvc_dir>
    """
    import sys
    import os

    # Suppress argv parsing issues by using bare minimum imports
    if __name__ == "__main__":
        if len(sys.argv) < 5:
            print("ERROR: Usage: rvc_simple_infer.py <input> <output> <pitch> <rvc_dir>")
            sys.exit(1)
    



    
        input_wav = sys.argv[1]
        output_wav = sys.argv[2]
        pitch_shift = int(sys.argv[3])
        rvc_dir = sys.argv[4]
    
        try:
            os.chdir(rvc_dir)
            sys.path.insert(0, rvc_dir)
        
            # Import after chdir
            import torch
            import soundfile as sf
            from configs.config import Config
            from infer.lib.audio import load_audio
            from infer.lib.infer_pack.models import (
                SynthesizerTrnMs256NSFsid,
                SynthesizerTrnMs256NSFsid_nono,
                SynthesizerTrnMs768NSFsid,
                SynthesizerTrnMs768NSFsid_nono,
            )
            from infer.modules.vc.pipeline import Pipeline
            from infer.modules.vc.utils import load_hubert as rvc_load_hubert
        
            model_path = "assets/weights/jarvis.pth"
            index_path = "logs/jarvis/added_jarvis_v2.index"
        
            if not os.path.exists(model_path):
                print(f"ERROR: Model not found: {model_path}")
                sys.exit(1)
        
            # Load config
            config = Config()
        
            # Load checkpoint
            cpt = torch.load(model_path, map_location="cpu", weights_only=False)
            tgt_sr = cpt["config"][-1]
            cpt["config"][-3] = cpt["weight"]["emb_g.weight"].shape[0]
            version = cpt.get("version", "v2")
            if_f0 = cpt.get("f0", 1)
        
            # Select model class
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
        
            # Create pipeline
            pipeline = Pipeline(tgt_sr, config)
            hubert_model = rvc_load_hubert(config)
        
            # Load input audio
            audio = load_audio(input_wav, 16000)
        
            # Normalize
            import numpy as np
            audio_max = np.abs(audio).max() / 0.95
            if audio_max > 1:
                audio /= audio_max
        
            # Prepare index
            file_index = index_path if os.path.exists(index_path) else ""
        
            # Run pipeline
            audio_opt = pipeline.pipeline(
                hubert_model,
                net_g,
                0,                  # sid (speaker id)
                audio,
                input_wav,
                [0, 0, 0],          # times
                pitch_shift,        # f0_up_key
                "rmvpe",            # f0_method
                file_index,
                0.75,               # index_rate
                if_f0,
                3,                  # filter_radius
                tgt_sr,
                0,                  # resample_sr
                0.25,               # rms_mix_rate
                0.33,               # protect
                None,               # f0_file
            )
        
            # Save output
            sf.write(output_wav, audio_opt, tgt_sr)
            print("OK")
            sys.exit(0)
        
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
