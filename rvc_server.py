import sys
import os
import json
from pathlib import Path

def log_debug(msg):
    with open("c:/Jarvis-assistant/server_log.txt", "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def main():
    log_debug("Starting server")
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "Missing rvc_dir"}), flush=True)
        sys.exit(1)
        
    rvc_dir = os.path.abspath(sys.argv[1])
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
        
        if not Path(model_path).exists():
            print(json.dumps({"status": "error", "message": f"Model not found: {model_path}"}), flush=True)
            sys.exit(1)
        
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
        
        # Signal ready
        log_debug("Sending ready signal")
        print(json.dumps({"status": "ready"}), flush=True)
        
        while True:
            log_debug("Waiting for input...")
            line = sys.stdin.readline()
            log_debug(f"Got line: {repr(line)}")
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
                
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                print(json.dumps({"status": "error", "message": "Invalid JSON format"}), flush=True)
                continue
                
            if req.get("command") == "exit":
                break
                
            input_wav = req.get("input_wav")
            output_wav = req.get("output_wav")
            pitch_shift = req.get("pitch_shift", 0)
            
            if not input_wav or not output_wav:
                print(json.dumps({"status": "error", "message": "input_wav and output_wav are required"}), flush=True)
                continue
                
            log_debug(f"Processing input_wav={input_wav}")
            try:
                log_debug("load_audio...")
                audio = load_audio(input_wav, 16000)
                log_debug("audio max...")
                audio_max = np.abs(audio).max() / 0.95
                if audio_max > 1:
                    audio /= audio_max
                    
                log_debug("pipeline.pipeline...")
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
                
                log_debug("sf.write...")
                sf.write(output_wav, audio_converted, tgt_sr)
                log_debug("sending ok")
                print(json.dumps({"status": "ok", "sr": tgt_sr}), flush=True)
                
            except Exception as e:
                import traceback
                log_debug(f"Error in inference: {e}")
                print(json.dumps({"status": "error", "message": str(e), "trace": traceback.format_exc()}), flush=True)

    except Exception as e:
        import traceback
        log_debug(f"Global error: {e}")
        print(json.dumps({"status": "error", "message": str(e), "trace": traceback.format_exc()}), flush=True)
    finally:
        sys.argv = original_argv

if __name__ == "__main__":
    main()
