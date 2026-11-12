"""So dels shorts: tic-tac del compte enrere, campaneta de la resposta, transició suau i la
pronunciació japonesa de Senri (VOICEVOX:春日部つむぎ, audio/index.json del repositori), mesclats
amb la música. Els efectes es sintetitzen aquí: res de tercers.
"""
import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile

SR = 44100


def _env(n, attack, decay):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-t / decay)


def tick(last=False):
    """Bloc de fusta curt; l'últim (l'«1») una mica més agut."""
    n = int(SR * 0.09)
    t = np.arange(n) / SR
    f = 2100 if last else 1650
    body = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t)
    click = np.random.default_rng(1).normal(0, 1, n) * _env(n, 0.0005, 0.003)
    return 0.32 * (body * _env(n, 0.001, 0.018) + 0.4 * click)


def chime():
    """Campaneta de dues notes (sol i si agut) per a la resposta correcta."""
    n = int(SR * 1.4)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for start, f in [(0.0, 1567.98), (0.09, 1975.53)]:
        k = int(start * SR)
        tt = t[: n - k]
        tone = sum(a * np.sin(2 * np.pi * f * m * tt) for m, a in [(1, 1), (2.0, .25), (3.01, .12)])
        out[k:] += tone * _env(n - k, 0.002, 0.35)
    return 0.35 * out


def whoosh():
    """Transició d'escena: soroll filtrat que puja i baixa, molt discret."""
    n = int(SR * 0.35)
    noise = np.random.default_rng(2).normal(0, 1, n)
    k = 60
    smooth = np.convolve(noise, np.ones(k) / k, mode="same")
    shape = np.sin(np.linspace(0, np.pi, n)) ** 2
    return 0.18 * smooth * shape / (np.abs(smooth).max() + 1e-9)


def _decode(path, work, name):
    wav = Path(work) / f"{name}.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), str(wav)],
                   check=True)
    _, x = wavfile.read(wav)
    return x.astype(np.float32) / 32768.0


def _hira(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def build_track(events, total, work, music=None, senri=None, voice=True, sfx=True):
    """Torna (fitxer wav, si porta veu, textos sense àudio)."""
    n = int(SR * (total + 0.5))
    fx = np.zeros(n, np.float32)
    vo = np.zeros(n, np.float32)
    missing, used = [], False
    index, adir = {}, None
    if voice and senri and (Path(senri) / "audio/index.json").exists():
        adir = Path(senri) / "audio"
        index = json.loads((adir / "index.json").read_text())["files"]

    def put(buf, sig, t, gain=1.0):
        k = int(t * SR)
        if k >= n:
            return
        m = min(len(sig), n - k)
        buf[k:k + m] += gain * sig[:m]

    sounds = {"reveal": chime(), "whoosh": whoosh()}
    for i, (kind, t, kw) in enumerate(sorted(events, key=lambda e: e[1])):
        if kind == "tick" and sfx:
            put(fx, tick(kw.get("last")), t)
        elif kind in sounds and sfx:
            put(fx, sounds[kind], t)
        elif kind == "voice" and voice and kw.get("text"):
            txt = kw["text"]
            f = index.get(txt) or index.get(_hira(txt))
            if not f:
                missing.append(txt)
                continue
            v = _decode(adir / f, work, f"v{i}")
            # Els àudios de Senri són fluixos (≈ -28 LUFS): es porten a pic 0,9 perquè la veu mani.
            put(vo, v * (0.9 / (np.abs(v).max() + 1e-9)), t)
            used = True

    mix = fx + vo
    if music:
        m = _decode(music, work, "music")[:n]
        m = np.pad(m, (0, n - len(m)))
        # Quan parla la veu, la música baixa (com un locutor de ràdio) i torna a pujar.
        talking = (np.abs(vo) > 1e-3).astype(np.float32)
        k = int(SR * 0.25)
        talking = np.convolve(talking, np.ones(k) / k, mode="same").clip(0, 1)
        duck = 1 - 0.7 * talking
        fade = np.ones(n, np.float32)
        f0 = int(SR * max(total - 1.5, 0))
        fade[f0:] = np.linspace(1, 0, n - f0)
        mix = mix + m * duck * fade
    peak = np.abs(mix).max()
    if peak > 0.98:
        mix = mix * (0.98 / peak)
    raw = Path(work) / "mix-raw.wav"
    wavfile.write(raw, SR, (mix * 32767).astype(np.int16))
    out = Path(work) / "mix.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af",
                    "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", str(SR), "-ac", "2", str(out)], check=True)
    return out, used, sorted(set(missing))
