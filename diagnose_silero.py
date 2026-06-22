"""
Диагностика Silero TTS - изолирует причину искажения голоса.
Генерирует одну и ту же фразу на CPU и на CUDA отдельно,
сохраняет оба файла, чтобы сравнить и понять, виновата ли CUDA.

Запуск:
    rvc_env\\Scripts\\python.exe diagnose_silero.py
"""
import torch
import pathlib
import soundfile as sf
import warnings
warnings.filterwarnings("ignore")

TEXT = "Все системы онлайн, сэр. Джарвис готов к работе."
SPEAKER = "aidar"
SR = 24000


def find_silero_pt():
    hub_dir = pathlib.Path(torch.hub.get_dir())
    for silero_dir in hub_dir.glob("snakers4_silero*"):
        exact = silero_dir / "src" / "silero" / "model" / "v4_ru.pt"
        if exact.exists():
            return exact
    for silero_dir in hub_dir.glob("snakers4_silero*"):
        for pt in silero_dir.rglob("v4_ru.pt"):
            return pt
    return None


def generate(device_name, out_path):
    print(f"\n=== Generating on {device_name} ===")
    pt_path = find_silero_pt()
    if not pt_path:
        print("ERROR: v4_ru.pt not found")
        return None

    importer = torch.package.PackageImporter(str(pt_path))
    model = importer.load_pickle("tts_models", "model")
    print("Model type:", type(model))
    print("Model dtype before .to():",
          next(model.parameters()).dtype if hasattr(model, "parameters") else "N/A")

    result = model.to(device_name)
    if result is not None:
        model = result

    if hasattr(model, "eval"):
        model.eval()

    print("Model dtype after .to():",
          next(model.parameters()).dtype if hasattr(model, "parameters") else "N/A")

    with torch.no_grad():
        audio = model.apply_tts(
            text=TEXT,
            speaker=SPEAKER,
            sample_rate=SR,
            put_accent=True,
            put_yo=True,
        )

    arr = audio.detach().cpu().numpy() if hasattr(audio, "detach") else audio
    print("Audio shape:", arr.shape, "dtype:", arr.dtype,
          "min:", arr.min(), "max:", arr.max())

    sf.write(str(out_path), arr, SR)
    print(f"Saved: {out_path}")
    return arr


if __name__ == "__main__":
    out_dir = pathlib.Path(__file__).parent
    cpu_path = out_dir / "_diag_cpu.wav"
    generate("cpu", cpu_path)

    if torch.cuda.is_available():
        cuda_path = out_dir / "_diag_cuda.wav"
        generate("cuda", cuda_path)
        print(f"\nCompare {cpu_path} and {cuda_path} by ear.")
        print("If CPU sounds clean and CUDA sounds garbled -> CUDA is the cause.")
        print("If BOTH sound garbled -> the problem is elsewhere (model loading / text / speaker).")
    else:
        print("\nNo CUDA available, only CPU test ran.")
