#!/usr/bin/env python3
"""Genera la veu en castellà dels shorts (s'executa a GitHub Actions: .github/workflows/veu.yml).

Llegeix tools/veu/frases.json (llista de textos) i tools/veu/config.json (veus actives) i deixa,
per a cada veu, veus/<veu>/<hash>.mp3 i veus/<veu>/index.json {text: fitxer}. Només genera el
que falta. Motors amb llicència lliure:
  - kokoro:<veu>   Kokoro-82M (hexgrad, Apache 2.0) · ef_dora, em_alex, em_santa
  - piper:<model>  Piper (veus de rhasspy/piper-voices; cada una amb la llicència del seu MODEL_CARD)
  - chatterbox:<variant>  Chatterbox Multilingual (Resemble AI, MIT) · default, expressiu
  - melo:ES        MeloTTS (MyShell, MIT)
Amb --only <motor> només fa les veus d'aquell motor (cada motor té les seves dependències).
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "veus"
PIPER_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang}/{loc}/{name}/{q}/{model}"


def h(text):
    return hashlib.sha1(text.encode()).hexdigest()[:12]


def to_mp3(wav, mp3):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af",
                    "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
                    "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
                    "loudnorm=I=-16:TP=-1.5", "-ar", "44100", "-ac", "1", "-b:a", "96k", str(mp3)], check=True)


def kokoro_engine(voice):
    from kokoro import KPipeline
    import numpy as np
    import soundfile as sf
    pipe = KPipeline(lang_code="e")

    def say(text, wav):
        chunks = [a for _, _, a in pipe(text, voice=voice, speed=1.0)]
        sf.write(wav, np.concatenate(chunks), 24000)
    return say


def piper_engine(model):
    # model: es_ES-sharvard-medium
    lang_loc, name, q = model.split("-")
    lang = lang_loc.split("_")[0]
    d = Path(tempfile.gettempdir()) / "piper"
    d.mkdir(exist_ok=True)
    for ext in (".onnx", ".onnx.json"):
        f = d / (model + ext)
        if not f.exists():
            url = PIPER_URL.format(lang=lang, loc=lang_loc, name=name, q=q, model=model + ext)
            subprocess.run(["curl", "-sSL", "-o", str(f), url], check=True)

    def say(text, wav):
        subprocess.run(["piper", "--model", str(d / (model + ".onnx")), "--output_file", str(wav)],
                       input=text.encode(), check=True)
    return say


def chatterbox_engine(variant):
    import torchaudio as ta
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    kw = {"exaggeration": 0.7, "cfg_weight": 0.3} if variant == "expressiu" else {}

    def say(text, wav):
        ta.save(wav, model.generate(text, language_id="es", **kw), model.sr)
    return say


def melo_engine(lang):
    from melo.api import TTS
    model = TTS(language=lang, device="cpu")
    spk = model.hps.data.spk2id[lang]

    def say(text, wav):
        model.tts_to_file(text, spk, wav, speed=1.0, quiet=True)
    return say


ENGINES = {"kokoro": kokoro_engine, "piper": piper_engine, "chatterbox": chatterbox_engine, "melo": melo_engine}


def main():
    frases = json.loads((ROOT / "tools/veu/frases.json").read_text())
    voices = json.loads((ROOT / "tools/veu/config.json").read_text())["voices"]
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    for v in voices:
        if only and not v.startswith(only + ":"):
            continue
        engine, arg = v.split(":", 1)
        vdir = OUT / v.replace(":", "-")
        vdir.mkdir(parents=True, exist_ok=True)
        idx_f = vdir / "index.json"
        idx = json.loads(idx_f.read_text()) if idx_f.exists() else {}
        todo = [t for t in frases if t not in idx]
        if not todo:
            continue
        say = ENGINES[engine](arg)
        for t in todo:
            with tempfile.NamedTemporaryFile(suffix=".wav") as w:
                say(t, w.name)
                f = h(t) + ".mp3"
                to_mp3(w.name, vdir / f)
                idx[t] = f
            print(v, "→", t, flush=True)
        idx_f.write_text(json.dumps(idx, ensure_ascii=False, indent=1, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())
