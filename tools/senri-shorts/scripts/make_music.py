#!/usr/bin/env python3
"""Compon una pista instrumental original per als shorts de Senri (lo-fi tranquil amb koto).

Tot es genera aquí per síntesi, així que no hi ha drets de tercers. Decisions de so
(vegeu references/musica.md per al perquè):
- Lo-fi a 70-84 bpm: calmat però no somnolent; sense veu, perquè el text del vídeo mani.
- Acords de 7a en piano elèctric (FM, tipus Rhodes) i koto pinçat sobre l'escala yo,
  que sona japonesa i alegre alhora.
- Bateria escassa (bombo, aro, xarleston), una mica fora de quadrícula i filtrada a ~2 kHz;
  la resta «s'aparta» quan sona el bombo (sidechain).
- Calidesa: saturació suau, lleuger vaivé de cinta, cruixit de vinil, reverberació de sala.
- Mescla pensada per a altaveus de mòbil: res per sota de 90 Hz, una mica de presència a 2 kHz,
  i -16 LUFS / -1 dBTP, el nivell recomanat per a vídeos de text amb música de fons.

Ús:
  python3 make_music.py sortida.m4a --seed 3 --seconds 30
  python3 make_music.py sortida.m4a --seed 7 --bpm 76 --no-drums
"""
import argparse
import subprocess
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
YO = [0, 2, 5, 7, 9]  # escala yo (民謡): graus 1 2 4 5 6
KEYS = {"C": 60, "D": 62, "Eb": 63, "F": 65, "G": 67, "A": 57}
# Progressions de 4 compassos en semitons sobre la tònica, amb la qualitat de l'acord.
PROGS = [
    [(0, "maj7"), (9, "m7"), (5, "maj7"), (7, "sus")],   # I – vi – IV – V
    [(5, "maj7"), (7, "sus"), (4, "m7"), (9, "m7")],     # IV – V – iii – vi (la «royal road» japonesa)
    [(0, "maj7"), (5, "maj7"), (9, "m7"), (7, "sus")],
    [(9, "m7"), (5, "maj7"), (0, "maj7"), (7, "sus")],
]
SHAPES = {"maj7": [0, 4, 7, 11], "m7": [0, 3, 7, 10], "sus": [0, 5, 7, 10]}


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x)


# ---------- instruments ----------

def koto(freq, dur, rng):
    """Corda pinçada (Karplus-Strong per blocs) amb un atac una mica brillant."""
    n = int(dur * SR)
    period = max(2, int(round(SR / freq)))
    buf = lp(rng.uniform(-1, 1, period * 2), min(6000, freq * 8))[-period:]
    blocks = []
    for _ in range(n // period + 1):
        blocks.append(buf.copy())
        buf = 0.997 * 0.5 * (buf + np.roll(buf, -1))
    out = np.concatenate(blocks)[:n]
    out *= np.minimum(1, np.arange(n) / (0.002 * SR))
    return out / (np.abs(out).max() + 1e-9)


def epiano(freq, dur, vel=1.0):
    """Piano elèctric per FM (modulador 1:1 que s'apaga ràpid, com un Rhodes)."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    index = 1.6 * vel * np.exp(-t * 6)
    tone = np.sin(2 * np.pi * freq * t + index * np.sin(2 * np.pi * freq * t))
    tone += 0.25 * np.sin(2 * np.pi * freq * 2.0 * t) * np.exp(-t * 3)  # «tine»
    env = np.minimum(1, t / 0.006) * np.exp(-t * 0.9) * np.minimum(1, (dur - t) / 0.25).clip(0)
    return tone * env * vel


def kick():
    t = np.arange(int(0.35 * SR)) / SR
    f = 95 * np.exp(-t * 22) + 52
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    click = lp(np.random.default_rng(1).normal(0, 1, len(t)), 3000) * np.exp(-t * 200) * 0.15
    return np.tanh(1.6 * (body + click)) * 0.7


def rim(rng):
    t = np.arange(int(0.12 * SR)) / SR
    tone = np.sin(2 * np.pi * 1700 * t) * np.exp(-t * 60) * 0.25
    noise = bp(rng.normal(0, 1, len(t)), 900, 4000) * np.exp(-t * 35) * 0.35
    return (tone + noise) * 0.5


def hat(rng, open_=False):
    t = np.arange(int((0.18 if open_ else 0.05) * SR)) / SR
    n = hp(rng.normal(0, 1, len(t)), 6000)
    return n * np.exp(-t * (25 if open_ else 110)) * 0.12


def add(track, sig, start):
    i = int(round(start * SR))
    if i < 0 or i >= len(track):
        return
    e = min(len(track), i + len(sig))
    track[i:e] += sig[: e - i]


# ---------- efectes ----------

def reverb(x, seconds=1.6, damp=3500, seed=0):
    """Reverberació de convolució amb una resposta sintètica (soroll que s'apaga i s'enfosqueix)."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.normal(0, 1, n) * np.exp(-t * 6.9 / seconds)
    ir = lp(ir, damp)
    ir[: int(0.012 * SR)] = 0  # predelay
    ir /= np.sqrt((ir ** 2).sum())
    return fftconvolve(x, ir)[: len(x)]


def wobble(x, depth=0.0018, rate=0.45):
    """Vaivé de cinta: el to puja i baixa molt poc."""
    n = len(x)
    t = np.arange(n) / SR
    pos = np.arange(n) + depth * SR * np.sin(2 * np.pi * rate * t) / (2 * np.pi * rate)
    return np.interp(pos, np.arange(n), x)


def duck(n, hits, floor=0.6, release=0.22):
    g = np.ones(n)
    k = int(release * SR)
    shape = 1 - (1 - floor) * np.exp(-5 * np.arange(k) / k)
    for h in hits:
        i = int(h * SR)
        e = min(n, i + k)
        g[i:e] = np.minimum(g[i:e], shape[: e - i])
    return g


def vinyl(n, rng):
    hiss = hp(rng.normal(0, 1, n), 2000) * 0.004
    crackle = np.zeros(n)
    idx = rng.integers(0, n, int(n / SR * 9))
    crackle[idx] = rng.uniform(-1, 1, len(idx)) * 0.12
    crackle = bp(crackle, 1500, 7000)
    return hiss + crackle


# ---------- composició ----------

def compose(seed, seconds, bpm=None, key=None, drums=True):
    rng = np.random.default_rng(seed)
    bpm = bpm or int(rng.choice([72, 76, 80, 84]))
    key = key or str(rng.choice(list(KEYS)))
    root = KEYS[key]
    beat = 60 / bpm
    bar = 4 * beat
    swing = 0.06 * beat  # les corxeres de part feble una mica endarrerides
    prog = PROGS[seed % len(PROGS)]
    n = int((seconds + 2) * SR)  # +2 s de cua per a la reverberació
    keys_, kot, bass, drm = (np.zeros(n) for _ in range(4))
    kicks = []

    scale = [root + d + o for o in (0, 12) for d in YO]
    # Motiu de 2 compassos: frases curtes amb silencis, que és el que fa que una melodia respiri.
    motif, pos, t = [], int(rng.integers(3, 7)), 0.0
    while t < 2 * bar - 1e-6:
        dur = min(float(rng.choice([0.5, 0.5, 1, 1, 1.5, 2])) * beat, 2 * bar - t)
        pos = int(np.clip(pos + rng.choice([-2, -1, -1, 0, 1, 1, 2]), 0, len(scale) - 1))
        motif.append((t, dur, None if rng.random() < 0.22 else scale[pos]))
        t += dur
    # La frase acaba en una nota de l'acord (la tònica), perquè «resolgui».
    last = max(i for i, m in enumerate(motif) if m[2] is not None)
    motif[last] = (motif[last][0], motif[last][1], root + 12)

    bars = int(np.ceil(seconds / bar))
    for b in range(bars):
        t0 = b * bar
        deg, q = prog[b % len(prog)]
        chord_root = root - 12 + deg
        notes = [chord_root + iv for iv in SHAPES[q]]
        notes = [m + 12 if m < root - 7 else m for m in notes]  # veus tancades al registre mig
        # Acord: un cop al temps 1 i un altre de suau a l'«i» del 3, amb les notes una mica escampades.
        for hit, vel in ((0.0, 0.9), (2.5 * beat + swing, 0.55)):
            for k, m in enumerate(notes):
                add(keys_, epiano(hz(m), bar - hit + 0.3, vel) * 0.22, t0 + hit + k * 0.012 + rng.normal(0, 0.004))
        # Baix: fonamental a l'1 i a l'«i» del 2 (al registre mig, perquè se senti al mòbil).
        for hit in (0.0, 1.5 * beat + swing):
            add(bass, epiano(hz(chord_root - 12), beat * 1.2, 0.8) * 0.45, t0 + hit)
        # Koto: entra al segon compàs i va alternant motiu i variació, amb compassos de descans.
        if b >= 1 and b % 2 == 1:
            vary = (b // 2) % 2 == 1
            for mt, md, m in motif:
                if m is None:
                    continue
                if vary and rng.random() < 0.3:
                    m = scale[int(np.clip(scale.index(m) + rng.choice([-1, 1]), 0, len(scale) - 1))]
                st = t0 + mt + (swing if (mt / beat) % 1 else 0)
                add(kot, koto(hz(m), md + 1.2, rng) * 0.5, st)
        if drums and b >= 1:
            for qb in range(4):
                bt = t0 + qb * beat
                if qb == 0 or (qb == 2 and rng.random() < 0.6):
                    kk = bt + rng.normal(0.008, 0.006)  # el bombo, una mica fora de quadrícula
                    add(drm, kick(), kk)
                    kicks.append(kk)
                if qb in (1, 3):
                    add(drm, rim(rng), bt + rng.normal(0, 0.004))
                add(drm, hat(rng) * 0.9, bt)
                if rng.random() < 0.8:
                    add(drm, hat(rng, open_=rng.random() < 0.1) * 0.55, bt + beat / 2 + swing)

    g = duck(n, kicks) if kicks else np.ones(n)
    keys_ = wobble(lp(keys_, 4200)) * g
    kot = lp(kot, 6000) * (0.6 + 0.4 * g)
    bass = lp(bass, 900) * g
    drm = lp(drm, 2200, 1)  # bateria apagada, com de disc vell

    wet = reverb(keys_ * 0.6 + kot, 1.8, 3200, seed)
    left = keys_ * 0.95 + kot * 0.8 + bass + drm + wet * 0.35
    right = keys_ * 0.85 + kot * 1.0 + bass + drm + reverb(keys_ * 0.6 + kot, 1.8, 3200, seed + 1) * 0.35
    st = np.stack([left, right], axis=1)
    st += vinyl(n, rng)[:, None]

    # Mescla per a mòbil: fora greus que l'altaveu no reprodueix, una mica de presència.
    for c in range(2):
        x = hp(st[:, c], 90)
        x = x + 0.18 * bp(x, 1500, 3500)
        st[:, c] = np.tanh(1.3 * x / (np.abs(x).max() + 1e-9)) / np.tanh(1.3)
    st = st[: int(seconds * SR)]
    t = np.arange(len(st)) / SR
    st *= (np.minimum(1, t / 0.3) * np.minimum(1, (seconds - t) / 2.0).clip(0))[:, None]
    st /= np.abs(st).max() + 1e-9
    return st * 0.8, dict(seed=seed, bpm=bpm, key=key)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=30)
    ap.add_argument("--bpm", type=int)
    ap.add_argument("--key", choices=list(KEYS))
    ap.add_argument("--no-drums", action="store_true")
    ap.add_argument("--lufs", type=float, default=-16, help="sonoritat objectiu (per defecte -16)")
    a = ap.parse_args()
    audio, info = compose(a.seed, a.seconds, a.bpm, a.key, not a.no_drums)
    out = Path(a.out)
    wav = out.with_name(out.stem + ".tmp.wav")
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((audio * 32767).astype("<i2").tobytes())
    codec = ["-c:a", "pcm_s16le"] if out.suffix.lower() == ".wav" else ["-c:a", "aac", "-b:a", "192k"]
    tmp = out.with_name(out.stem + ".tmp" + out.suffix)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                    "-af", f"loudnorm=I={a.lufs}:TP=-1:LRA=7", "-ar", str(SR), *codec, str(tmp)], check=True)
    wav.unlink()
    tmp.rename(out)
    print(f"{out} · llavor {info['seed']} · {info['bpm']} bpm · {info['key']} yo")


if __name__ == "__main__":
    main()
