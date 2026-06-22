import sys
import os
from pathlib import Path
from xmlrpc.server import SimpleXMLRPCServer
import traceback

def main():
    if len(sys.argv) < 3:
        print("Missing args")
        sys.exit(1)
        
    rvc_dir = os.path.abspath(sys.argv[1])
    port = int(sys.argv[2])
    
    rmvpe_root = os.path.join(rvc_dir, "assets", "rmvpe")
    index_root = os.path.join(rvc_dir, "logs")
    os.makedirs(rmvpe_root, exist_ok=True)
    os.makedirs(index_root, exist_ok=True)
    os.environ["rmvpe_root"] = rmvpe_root
    os.environ["index_root"] = index_root
    
    os.chdir(rvc_dir)
    sys.path.insert(0, rvc_dir)
    
    original_argv = sys.argv.copy()
    sys.argv = [sys.argv[0]]
    
    try:
        import torch
        import soundfile as sf
        import numpy as np
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

        config = Config()
        model_path = "assets/weights/jarvis.pth"
        index_path = "logs/jarvis/added_jarvis_v2.index"
        
        cpt = torch.load(model_path, map_location="cpu", weights_only=False)
        tgt_sr = cpt["config"][-1]
        cpt["config"][-3] = cpt["weight"]["emb_g.weight"].shape[0]
        version = cpt.get("version", "v2")
        if_f0 = cpt.get("f0", 1)
        
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
        
        file_index = index_path if Path(index_path).exists() else ""
        
        # Pre-load RMVPE model to prevent hanging during inference
        if if_f0 == 1:
            try:
                from infer.lib.rmvpe import RMVPE
                pipeline.model_rmvpe = RMVPE(
                    "%s/rmvpe.pt" % os.environ["rmvpe_root"],
                    is_half=config.is_half,
                    device=config.device,
                )
            except Exception as e:
                print(f"RMVPE pre-load error: {e}")
                
        def infer(input_wav, output_wav, pitch_shift):
            try:
                audio = load_audio(input_wav, 16000)
                audio_max = np.abs(audio).max() / 0.95
                if audio_max > 1:
                    audio /= audio_max
                    
                audio_converted = pipeline.pipeline(
                    hubert_model,
                    net_g,
                    0,
                    audio,
                    input_wav,
                    [0, 0, 0],
                    pitch_shift,
                    "rmvpe",
                    file_index,
                    0.75,
                    if_f0,
                    3,
                    tgt_sr,
                    0,
                    0.25,
                    version,
                    0.33,
                    None,
                )
                
                sf.write(output_wav, audio_converted, tgt_sr)
                return {"status": "ok", "sr": tgt_sr}
            except Exception as e:
                return {"status": "error", "message": str(e), "trace": traceback.format_exc()}
        
        server = SimpleXMLRPCServer(("127.0.0.1", port), allow_none=True, logRequests=False)
        server.register_function(infer, "infer")
        print("READY", flush=True)
        server.serve_forever()

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        sys.argv = original_argv

if __name__ == "__main__":
    main()
