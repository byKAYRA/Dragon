"""FreyaTTS test scripti — Dragon'a gömmeden önce sesi dene.

Kurulum (bir kez):
    pip install torch numpy einops soundfile librosa huggingface_hub safetensors voxcpm
    # + FreyaTTS reposu:
    #   git clone https://github.com/freyavoiceai/FreyaTTS.git _freyatts_src
    #   (veya freyatts paketini PYTHONPATH'e ekle)

Kullanım:
    python scripts/freya_test.py --text "Emredersiniz efendim, sistemler hazır."
    python scripts/freya_test.py --text "Merhaba efendim." --seed 0 --steps 32
    python scripts/freya_test.py --list-seeds  (farklı erkek sesleri dene)

Not: FreyaTTS varsayılan sesi kadın (Leyla). Erkek/JARVIS için farklı
seed'ler dene; seed sesi belirler. Beğendiğin seed'i not et, Dragon'a o
seed ile gömeriz.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FREYA_SRC = ROOT / "_freyatts_src"

# Klonlanmış repo varsa import yoluna ekle.
if FREYA_SRC.exists() and str(FREYA_SRC) not in sys.path:
    sys.path.insert(0, str(FREYA_SRC))

DEFAULT_TEXT = "Emredersiniz efendim. Tüm sistemler hazır, nasıl yardımcı olabilirim?"
DEFAULT_SEEDS = [1234, 42, 7, 2026, 999]


def _load_model(device: str):
    try:
        from freyatts import FreyaTTS
    except ImportError:
        print(
            "freyatts paketi bulunamadı.\n"
            "Kurmak için:\n"
            '  git clone https://github.com/freyavoiceai/FreyaTTS.git "_freyatts_src"\n'
            "  pip install torch numpy einops soundfile librosa huggingface_hub safetensors voxcpm\n",
            file=sys.stderr,
        )
        raise SystemExit(1)
    print(f"Model yükleniyor (device={device}) ...")
    tts = FreyaTTS.from_pretrained("freyavoice/freya-tts", device=device)
    return tts


def _play_wav(path: Path) -> None:
    """Üretilen wav'ı varsayılan oynatıcıyla çal (Windows)."""
    try:
        import os

        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        print(f"Oynatmak için dosyayı aç: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="FreyaTTS ses testi")
    parser.add_argument("--text", default=DEFAULT_TEXT, help="Seslendirilecek metin")
    parser.add_argument("--seed", type=int, default=1234, help="Ses tohumu (sesi belirler)")
    parser.add_argument("--steps", type=int, default=32, help="ODE adım sayısı")
    parser.add_argument("--out", default="freya_test.wav", help="Çıktı dosyası")
    parser.add_argument("--device", default="cpu", help="cpu veya cuda")
    parser.add_argument("--list-seeds", action="store_true", help="Birkaç seed ile örnek üret")
    args = parser.parse_args()

    tts = _load_model(args.device)

    if args.list_seeds:
        outdir = ROOT / "data" / "freya_samples"
        outdir.mkdir(parents=True, exist_ok=True)
        for seed in DEFAULT_SEEDS:
            wav = tts.synthesize(args.text, steps=args.steps, seed=seed)
            out = outdir / f"freya_seed{seed}.wav"
            tts.save_wav(wav, str(out))
            print(f"seed={seed} -> {out}")
        print("Hepsini dinleyip en tok erkeği seç, numarasını söyle.")
        return 0

    wav = tts.synthesize(args.text, steps=args.steps, seed=args.seed)
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    tts.save_wav(wav, str(out))
    print(f"Tamam: {out} (seed={args.seed})")
    _play_wav(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
