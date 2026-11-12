#!/usr/bin/env python3
"""Genera un vídeo vertical (1080x1920, 30 fps) amb l'estil de Senri a partir d'un guió JSON.

Cada escena és una plantilla HTML animada amb CSS. El script congela les animacions,
fa una captura per fotograma amb Chromium (Playwright) i ho codifica amb ffmpeg.
Quan una escena ja no es mou, reutilitza l'últim fotograma, així que les escenes
estàtiques són gairebé instantànies.

Ús:
  python3 render_short.py guio.json sortida.mp4            # vídeo complet + portada
  python3 render_short.py guio.json sortida.mp4 --stills   # només un fotograma per escena, per revisar
  python3 render_short.py guio.json sortida.mp4 --audio musica.mp3

Format del guió: vegeu references/spec.md.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

W, H, FPS = 1080, 1920, 30
HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
# Zona que cap plataforma tapa (TikTok, Reels i Shorts): x 60-960, y 210-1600.
SAFE = (80, 220, 940, 1580)

THEMES = {
    "light": dict(bg="#EDF0EA", surface="#FAFBF7", ink="#1D2A22", muted="#5B675E", line="#D4DAD1",
                  accent="#36563C", accent_soft="#DCE7DD", shu="#C8432B", shu_soft="#F4DED6",
                  gold="#B97A00", good="#2F7D4A", good_soft="#DCEEDF", wave="#CFD9CE", grid="#C9D3C6"),
    "dark": dict(bg="#111814", surface="#18221C", ink="#E5ECE4", muted="#96A59A", line="#283A2F",
                 accent="#8CC9A0", accent_soft="#1F3428", shu="#FF6E4E", shu_soft="#3A211C",
                 gold="#F0BE4A", good="#6FD49A", good_soft="#15301F", wave="#1E2D24", grid="#2C4034"),
}


def fmt(text):
    """Escapa el text i converteix **paraula** en èmfasi vermell i \\n en salt de línia."""
    t = html.escape(str(text or ""))
    t = re.sub(r"\*\*(.+?)\*\*", r"<em>\1</em>", t)
    return t.replace("\n", "<br>")


def jp(word, kana=None):
    """Japonès amb furigana per sobre quan la paraula porta kanji."""
    word = html.escape(word)
    if kana and kana != word and re.search(r"[一-鿿]", word):
        return f"<ruby>{word}<rt>{html.escape(kana)}</rt></ruby>"
    return word


def big_size(text, base=430, width=820):
    """Mida de lletra perquè els caràcters grans càpiguen en una sola línia."""
    n = max(1, len(text))
    # Amb més d'un caràcter, més petit: si no, no hi cap el text del ganxo a sobre.
    return min(base if n == 1 else 340, int(width / n))


def anim(name, delay, dur=0.45, extra=""):
    return f'style="animation:{name} {dur}s cubic-bezier(.2,.8,.2,1) {delay}s both;{extra}"'


# ---------- plantilles d'escena ----------
# Cada funció retorna (html, durada_mínima_suggerida). Les animacions comencen a t=0
# de l'escena; `both` fa que l'element estigui amagat abans del seu retard.

def scene_hook(s):
    big = s.get("big")
    big_html = (f'<div class="t big kana" style="font-size:{big_size(big)}px;animation:zoom {s.get("duration", 2.5)}s linear both">'
                f'{html.escape(big)}</div>') if big else ""
    sub = f'<div class="t sub" {anim("up", .5)}>{fmt(s["sub"])}</div>' if s.get("sub") else ""
    # El títol ja és visible al primer fotograma: és el que decideix si la gent s'atura.
    return f'''<div class="stack center">
      <div class="t hook">{fmt(s["text"])}</div>
      {big_html}{sub}
    </div>''', 2.5


def scene_kanji(s):
    paths = s.get("paths") or []
    per, gap = s.get("stroke_time", 0.45), 0.1
    # Amb «question», l'escena fa de ganxo: la pregunta ja és al fotograma 0 i el traç comença tot seguit.
    t0 = 0.05 if s.get("question") else 0.3
    strokes = "".join(
        f'<path d="{html.escape(p)}" pathLength="1" style="animation:draw {per}s ease-in-out {t0 + i * (per + gap):.2f}s both"/>'
        for i, p in enumerate(paths))
    t_end = t0 + len(paths) * (per + gap)
    # Amb «question», el kanji sencer ja es veu en gris des del fotograma 0: la pantalla mai surt buida.
    ghost = ('<g class="ghost">' + "".join(f'<path d="{html.escape(p)}"/>' for p in paths) + '</g>') if s.get("question") else ""
    if paths:
        glyph = f'''<svg class="t strokes" viewBox="0 0 109 109">
          <g class="guide"><line x1="54.5" y1="0" x2="54.5" y2="109"/><line x1="0" y1="54.5" x2="109" y2="54.5"/></g>
          {ghost}<g class="ink">{strokes}</g></svg>'''
    else:
        glyph = f'<div class="t big kana" {anim("pop", .2, .5)}>{html.escape(s["k"])}</div>'
        t_end = 0.8
    reading = " · ".join(x for x in [s.get("reading"), s.get("romaji")] if x)
    top = (f'<div class="t title">{fmt(s["question"])}</div>' if s.get("question")
           else f'<div class="t chip" {anim("up", 0)}>{fmt(s.get("label", "Kanji N5"))}</div>')
    parts = [top, glyph,
             f'<div class="t meaning" {anim("up", t_end)}>{fmt(s.get("meaning", ""))}</div>']
    if reading:
        parts.append(f'<div class="t reading kana" {anim("up", t_end + .35)}>{html.escape(reading)}</div>')
    if s.get("hint"):
        parts.append(f'<div class="t hint" {anim("up", t_end + .7)}>{fmt(s["hint"])}</div>')
    if s.get("teaser"):
        # Just quan surt la resposta és quan més gent marxa: deixa una porta oberta cap al que ve.
        parts.append(f'<div class="t tip" {anim("up", t_end + .3)}>{fmt(s["teaser"])}</div>')
    if s.get("question") and s.get("label"):
        parts.append(f'<div class="t chip" {anim("up", t_end + .9)}>{fmt(s["label"])}</div>')
    if s.get("strokes_label"):
        parts.insert(1, f'<div class="t small muted" {anim("up", .1)}>{fmt(s["strokes_label"])}</div>')
    return f'<div class="stack center">{"".join(parts)}</div>', t_end + 2.2


def scene_word(s):
    reveal = s.get("reveal_at", 1.2)
    parts = []
    if s.get("label"):
        parts.append(f'<div class="t chip" {anim("up", 0)}>{fmt(s["label"])}</div>')
    parts.append(f'<div class="t word kana" {anim("pop", .05, .5)}>{jp(s["jp"], s.get("kana"))}</div>')
    if s.get("romaji"):
        parts.append(f'<div class="t reading" {anim("up", .45)}>{html.escape(s["romaji"])}</div>')
    parts.append(f'<div class="t meaning" {anim("up", reveal)}>{fmt(s.get("meaning", ""))}</div>')
    if s.get("note"):
        parts.append(f'<div class="t hint" {anim("up", reveal + .5)}>{fmt(s["note"])}</div>')
    return f'<div class="stack center">{"".join(parts)}</div>', reveal + 2.2


def scene_compare(s):
    def card(c, d):
        lab = f'<div class="t small muted">{fmt(c["label"])}</div>' if c.get("label") else ""
        return f'''<div class="card" {anim("pop", d, .5)}>
            <div class="t cmp kana">{html.escape(c["char"])}</div>
            <div class="t reading">{html.escape(c.get("romaji", ""))}</div>{lab}</div>'''
    title = f'<div class="t title" {anim("up", 0)}>{fmt(s["title"])}</div>' if s.get("title") else ""
    tip_at = s.get("tip_at", 1.6)
    tip = f'<div class="t tip" {anim("up", tip_at)}>{fmt(s["tip"])}</div>' if s.get("tip") else ""
    return f'''<div class="stack center">{title}
        <div class="row">{card(s["left"], .25)}{card(s["right"], .55)}</div>{tip}</div>''', tip_at + 3.2


def scene_quiz(s):
    opts = s["options"]
    ans = int(s["answer"])
    count = int(s.get("countdown", 3))
    t_rev = 0.9 + count
    items = []
    for i, o in enumerate(opts):
        d = 0.4 + i * 0.15
        if i == ans:
            fx = f'animation:up .4s ease {d}s both, right .35s ease {t_rev}s both'
            mark = f'<span class="mark" {anim("stamp", t_rev, .4)}>〇</span>'
        else:
            fx = f'animation:up .4s ease {d}s both, fade .35s ease {t_rev}s both'
            mark = ""
        items.append(f'<div class="t opt" style="{fx}"><span class="optl">{"ABCD"[i]}</span>{fmt(o)}{mark}</div>')
    nums = "".join(
        f'<div class="num" style="animation:tick 1s linear {0.9 + k}s both">{count - k}</div>' for k in range(count))
    prompt = (f'<div class="t big kana q" style="font-size:{big_size(s["prompt"], 300)}px">'
              f'{html.escape(s["prompt"])}</div>') if s.get("prompt") else ""
    return f'''<div class="stack center">
        <div class="t title">{fmt(s.get("question", "¿Qué significa?"))}</div>
        {prompt}
        <div class="opts">{"".join(items)}</div>
        <div class="count">{nums}</div></div>''', t_rev + 2.0


def scene_list(s):
    step = s.get("step", 1.3)
    rows = []
    for i, it in enumerate(s["items"]):
        d = 0.5 + i * step
        # El primer element ja és a la pantalla al fotograma 0: el títol sol no fa que la gent s'aturi.
        fx = "" if i == 0 else anim("up", d - step)
        rom = f'<span class="lr">{html.escape(it.get("romaji", ""))}</span>' if it.get("romaji") else ""
        rows.append(f'''<div class="t li" {fx}>
            <span class="lj kana">{jp(it["jp"], it.get("kana"))}</span>
            <span class="lm">{fmt(it.get("meaning", ""))}{rom}</span></div>''')
    return f'''<div class="stack">
        <div class="t title left">{fmt(s["title"])}</div>
        <div class="list">{"".join(rows)}</div></div>''', 0.5 + (len(s["items"]) - 1) * step + 1.8


def scene_text(s):
    sub = f'<div class="t sub" {anim("up", .5)}>{fmt(s["sub"])}</div>' if s.get("sub") else ""
    big = (f'<div class="t big kana" {anim("pop", .15, .5, f"font-size:{big_size(s['big'])}px")}>'
           f'{html.escape(s["big"])}</div>') if s.get("big") else ""
    return f'''<div class="stack center">
        <div class="t hook" {anim("up", 0)}>{fmt(s["text"])}</div>{big}{sub}</div>''', 2.8


def scene_cta(s):
    url = f'<div class="t url" {anim("up", .9)}>{html.escape(s["url"])}</div>' if s.get("url") else ""
    return f'''<div class="stack center">
        <img class="t logo" src="logo.png" {anim("pop", .05, .55)}>
        <div class="t hook" {anim("up", .35)}>{fmt(s.get("text", "Aprende japonés gratis con **Senri**"))}</div>
        <div class="t sub" {anim("up", .65)}>{fmt(s.get("sub", "Sin cuenta ni anuncios · enlace en el perfil"))}</div>
        {url}</div>''', 3.0


# ---------- escenes de «respon abans que surti» ----------
# Totes tres segueixen el mateix ritme que el quiz: la pregunta i la imatge ja hi són al
# fotograma 0, compte enrere des de 0,9 s i la resposta just quan s'acaba.

def countdown(count):
    nums = "".join(f'<div class="num" style="animation:tick 1s linear {0.9 + k}s both">{count - k}</div>'
                   for k in range(count))
    return f'<div class="count">{nums}</div>', 0.9 + count


# Dibuixos senzills de línia (viewBox 0 0 200 200), fets per a Senri: res de tercers.
ICONS = {
    "gato": '<path d="M52 92 L48 38 L86 66 Q100 62 114 66 L152 38 L148 92"/><ellipse cx="100" cy="112" rx="58" ry="50"/>'
            '<circle cx="78" cy="106" r="6" class="fill"/><circle cx="122" cy="106" r="6" class="fill"/>'
            '<path d="M94 124 L100 130 L106 124"/><path d="M40 118 L72 122 M40 134 L72 128 M160 118 L128 122 M160 134 L128 128"/>',
    "perro": '<path d="M58 70 Q30 64 32 112 Q36 130 54 120 L58 92"/><path d="M142 70 Q170 64 168 112 Q164 130 146 120 L142 92"/>'
             '<path d="M58 70 Q100 40 142 70 L146 124 Q140 168 100 168 Q60 168 54 124 Z"/>'
             '<circle cx="82" cy="104" r="6" class="fill"/><circle cx="118" cy="104" r="6" class="fill"/>'
             '<ellipse cx="100" cy="132" rx="12" ry="8" class="fill"/><path d="M100 140 L100 150 M88 152 Q100 160 112 152"/>',
    "libro": '<path d="M100 56 Q72 42 34 48 L34 150 Q72 144 100 158 Q128 144 166 150 L166 48 Q128 42 100 56 Z"/>'
             '<path d="M100 56 L100 158"/><path d="M50 74 Q70 72 86 78 M50 96 Q70 94 86 100 M114 78 Q130 72 150 74 M114 100 Q130 94 150 96"/>',
    "cafe": '<path d="M46 84 L154 84 L146 150 Q144 162 132 162 L68 162 Q56 162 54 150 Z"/>'
            '<path d="M152 98 Q178 98 176 118 Q174 138 148 136"/>'
            '<path d="M80 40 Q72 52 80 64 M100 34 Q92 48 100 64 M120 40 Q112 52 120 64"/>',
    "arbol": '<path d="M100 172 L100 112 M100 132 L80 116 M100 124 L118 108"/>'
             '<path d="M100 26 Q140 26 146 62 Q172 74 160 104 Q150 124 124 118 Q100 128 76 118 Q50 124 40 104 Q28 74 54 62 Q60 26 100 26 Z"/>',
    "sol": '<circle cx="100" cy="100" r="34"/><path d="M100 30 L100 50 M100 150 L100 170 M30 100 L50 100 M150 100 L170 100'
           ' M50 50 L64 64 M136 136 L150 150 M150 50 L136 64 M64 136 L50 150"/>',
    "casa": '<path d="M30 98 L100 38 L170 98"/><path d="M50 82 L50 166 L150 166 L150 82"/>'
            '<path d="M86 166 L86 120 L114 120 L114 166"/><rect x="122" y="104" width="18" height="18"/>',
    "pez": '<path d="M36 100 Q80 50 140 100 Q80 150 36 100 Z"/><path d="M140 100 L172 72 L166 100 L172 128 Z"/>'
           '<circle cx="66" cy="94" r="5" class="fill"/><path d="M92 82 Q100 100 92 118"/>',
}


def icon_svg(name):
    if name not in ICONS:
        sys.exit(f"Icona desconeguda «{name}». Icones: {', '.join(ICONS)}")
    return f'<svg class="t icon" viewBox="0 0 200 200">{ICONS[name]}</svg>'


def scene_guess(s):
    """Imatge o paraula → l'espectador diu què és abans que surti la resposta."""
    cd, t_rev = countdown(int(s.get("countdown", 3)))
    if s.get("icon"):
        shown = f'<div class="pic">{icon_svg(s["icon"])}</div>'
        answer = f'<div class="t word kana" {anim("pop", t_rev, .5)}>{jp(s["jp"], s.get("kana"))}</div>'
        extra = [x for x in [s.get("romaji"), s.get("meaning")] if x]
        answer += f'<div class="t reading" {anim("up", t_rev + .35)}>{fmt(" · ".join(extra))}</div>' if extra else ""
    else:
        shown = f'<div class="t big kana q" style="font-size:{big_size(s["jp"], 300)}px">{html.escape(s["jp"])}</div>'
        answer = f'<div class="t meaning" {anim("pop", t_rev, .5)}>{fmt(s.get("meaning", ""))}</div>'
        if s.get("romaji"):
            answer += f'<div class="t reading" {anim("up", t_rev + .35)}>{html.escape(s["romaji"])}</div>'
    if s.get("note"):
        answer += f'<div class="t hint" {anim("up", t_rev + .8)}>{fmt(s["note"])}</div>'
    return f'''<div class="stack center"><div class="t title">{fmt(s.get("question", "¿Cómo se dice en japonés?"))}</div>
        {shown}<div class="reveal">{cd}<div class="ans">{answer}</div></div></div>''', t_rev + 2.6


SIGN_STYLES = {
    # Rètol d'estació (groc, lletra negra), pissarra de cafeteria i placa de porta.
    "estacion": dict(bg="#F4C430", fg="#141414", border="#141414", radius=18),
    "pizarra": dict(bg="#24382B", fg="#F3F1E7", border="#8A6A44", radius=14),
    "placa": dict(bg="#FAFAF7", fg="#1D2A22", border="#9AA39C", radius=40),
}


def scene_sign(s):
    """Un rètol de la vida real dibuixat: l'espectador el llegeix i, després del compte, surt la traducció."""
    st = SIGN_STYLES[s.get("style", "estacion")]
    cd, t_rev = countdown(int(s.get("countdown", 3)))
    rows = []
    for r in s["rows"]:
        side = html.escape(r.get("arrow", "") or r.get("price", ""))
        rows.append(f'''<div class="srow"><span class="sjp kana">{html.escape(r["jp"])}</span><span class="sside">{side}</span></div>
          <div class="smean" {anim("up", t_rev)}>{fmt(r.get("meaning", ""))}<span>{html.escape(r.get("romaji", ""))}</span></div>''')
    sign = (f'<div class="t sign" style="background:{st["bg"]};color:{st["fg"]};border-color:{st["border"]};'
            f'border-radius:{st["radius"]}px">{"".join(rows)}</div>')
    note = f'<div class="t hint" {anim("up", t_rev + .8)}>{fmt(s["note"])}</div>' if s.get("note") else ""
    return f'''<div class="stack center"><div class="t title">{fmt(s.get("question", "¿Puedes leer este cartel?"))}</div>
        {sign}{cd}{note}</div>''', t_rev + 3.0


def scene_combo(s):
    """Kanji com a suma de dibuixos: A + B = ? i, després del compte, el resultat."""
    cd, t_rev = countdown(int(s.get("countdown", 3)))
    parts = []
    for i, p in enumerate(s["parts"]):
        if i:
            parts.append('<div class="plus">+</div>')
        parts.append(f'<div class="card small"><div class="t cmp kana">{html.escape(p["k"])}</div>'
                     f'<div class="t small muted">{fmt(p.get("meaning", ""))}</div></div>')
    r = s["result"]
    reading = " · ".join(x for x in [r.get("reading"), r.get("romaji")] if x)
    res = (f'<div class="t big kana" {anim("pop", t_rev, .5, "font-size:300px")}>{html.escape(r["k"])}</div>'
           f'<div class="t meaning" {anim("up", t_rev + .3)}>{fmt(r.get("meaning", ""))}</div>')
    if reading:
        res += f'<div class="t reading kana" {anim("up", t_rev + .55)}>{html.escape(reading)}</div>'
    if s.get("hint"):
        res += f'<div class="t hint" {anim("up", t_rev + .9)}>{fmt(s["hint"])}</div>'
    return f'''<div class="stack center"><div class="t title">{fmt(s.get("question", "¿Qué kanji sale?"))}</div>
        <div class="row combo">{"".join(parts)}</div><div class="reveal">{cd}<div class="ans">{res}</div></div></div>''', t_rev + 3.0


SCENES = dict(hook=scene_hook, kanji=scene_kanji, word=scene_word, compare=scene_compare,
              quiz=scene_quiz, list=scene_list, text=scene_text, cta=scene_cta,
              guess=scene_guess, sign=scene_sign, combo=scene_combo)


def css(theme):
    c = THEMES[theme]
    f = (ASSETS / "fonts").as_uri()
    x0, y0, x1, y1 = SAFE
    return f"""
@font-face{{font-family:'Klee One';font-weight:400;src:url('{f}/klee-one-400.v1.woff2')}}
@font-face{{font-family:'Klee One';font-weight:600;src:url('{f}/klee-one-600.v1.woff2')}}
@font-face{{font-family:'Zen Kaku Gothic New';font-weight:400;src:url('{f}/zen-kaku-400.v1.woff2')}}
@font-face{{font-family:'Zen Kaku Gothic New';font-weight:500;src:url('{f}/zen-kaku-500.v1.woff2')}}
@font-face{{font-family:'Zen Kaku Gothic New';font-weight:700;src:url('{f}/zen-kaku-700.v1.woff2')}}
*{{box-sizing:border-box}} html,body{{margin:0}}
ruby{{ruby-align:center}} rt{{letter-spacing:0;text-align:center}}
body{{width:{W}px;height:{H}px;overflow:hidden;background:{c['bg']};color:{c['ink']};
  font-family:'Zen Kaku Gothic New','Noto Sans CJK JP',sans-serif;font-weight:500;position:relative}}
.kana{{font-family:'Klee One','Noto Serif CJK JP',serif;font-weight:600}}
em{{font-style:normal;color:{c['shu']}}}
.waves{{position:absolute;left:0;right:0;bottom:0;height:520px;opacity:.9}}
.brand{{position:absolute;left:{x0}px;top:{y0}px;display:flex;align-items:center;gap:16px;font-weight:700;font-size:34px;color:{c['accent']}}}
.brand img{{width:58px;height:58px;border-radius:14px}}
.safe{{position:absolute;left:{x0}px;top:{y0 + 90}px;width:{x1 - x0}px;height:{y1 - y0 - 90}px;display:flex;align-items:center;justify-content:center}}
.stack{{display:flex;flex-direction:column;gap:34px;width:100%}}
.center{{align-items:center;text-align:center}}
.hook{{font-weight:700;font-size:84px;line-height:1.12;letter-spacing:-1px;text-wrap:balance}}
.title{{font-weight:700;font-size:64px;line-height:1.15;text-wrap:balance}}
.title.left{{text-align:left}}
.sub{{font-size:46px;color:{c['muted']};line-height:1.3}}
.big{{font-size:430px;line-height:1;color:{c['accent']};white-space:nowrap}}
.big.q{{font-size:300px}}
.word{{font-size:190px;line-height:1.1;color:{c['accent']}}}
.word rt{{font-size:58px;color:{c['muted']};font-weight:400}}
.meaning{{font-weight:700;font-size:96px;line-height:1.1}}
.reading{{font-size:56px;color:{c['muted']}}}
.hint{{font-size:44px;color:{c['muted']};line-height:1.35;max-width:820px}}
.small{{font-size:38px}} .muted{{color:{c['muted']}}}
.chip{{align-self:center;background:{c['accent_soft']};color:{c['accent']};border-radius:999px;padding:10px 30px;font-size:38px;font-weight:700}}
.strokes{{width:600px;height:600px;background:{c['surface']};border:3px solid {c['line']};border-radius:36px}}
.strokes .guide line{{stroke:{c['grid']};stroke-width:.6;stroke-dasharray:2 2}}
.strokes .ghost path{{fill:none;stroke:{c['grid']};stroke-width:4.2;stroke-linecap:round;stroke-linejoin:round}}
.strokes .ink path{{fill:none;stroke:{c['ink']};stroke-width:4.2;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:1 2;stroke-dashoffset:1}}
.row{{display:flex;gap:40px;justify-content:center}}
.card{{background:{c['surface']};border:3px solid {c['line']};border-radius:40px;padding:40px 30px 34px;width:390px;display:flex;flex-direction:column;align-items:center;gap:14px}}
.cmp{{font-size:270px;line-height:1;color:{c['accent']}}}
.tip{{background:{c['shu_soft']};border-radius:28px;padding:28px 36px;font-size:48px;line-height:1.3;max-width:860px}}
.opts{{display:flex;flex-direction:column;gap:22px;width:100%}}
.opt{{position:relative;display:flex;align-items:center;gap:26px;background:{c['surface']};border:3px solid {c['line']};border-radius:28px;padding:26px 34px;font-size:52px;font-weight:700;text-align:left}}
.optl{{width:64px;height:64px;border-radius:50%;background:{c['accent_soft']};color:{c['accent']};display:flex;align-items:center;justify-content:center;font-size:36px;flex:none}}
.mark{{position:absolute;right:30px;top:50%;margin-top:-50px;font-size:100px;line-height:1;color:{c['shu']}}}
.count{{position:relative;height:120px;width:120px}}
.num{{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:96px;font-weight:700;color:{c['gold']}}}
.list{{display:flex;flex-direction:column;gap:26px}}
.li{{display:flex;align-items:center;gap:36px;background:{c['surface']};border:3px solid {c['line']};border-radius:28px;padding:22px 34px}}
.lj{{font-size:84px;color:{c['accent']};min-width:300px;line-height:1.15}}
.lj rt{{font-size:30px;color:{c['muted']};font-weight:400}}
.lm{{display:flex;flex-direction:column;font-size:50px;font-weight:700;line-height:1.15}}
.lr{{font-size:36px;font-weight:500;color:{c['muted']}}}
.logo{{width:260px;height:260px;border-radius:60px}}
.url{{font-size:42px;color:{c['accent']};font-weight:700}}
.pic{{width:520px;height:520px;background:{c['surface']};border:3px solid {c['line']};border-radius:48px;display:flex;align-items:center;justify-content:center}}
.icon{{width:400px;height:400px;fill:none;stroke:{c['ink']};stroke-width:7;stroke-linecap:round;stroke-linejoin:round}}
.icon .fill{{fill:{c['ink']};stroke:none}}
.reveal{{position:relative;width:100%;display:flex;flex-direction:column;align-items:center}}
.reveal .count{{position:absolute;top:0;left:50%;margin-left:-60px}}
.ans{{display:flex;flex-direction:column;align-items:center;gap:22px;min-height:120px}}
.sign{{width:100%;border:8px solid;padding:34px 50px;display:flex;flex-direction:column;gap:8px;box-shadow:0 18px 0 rgba(0,0,0,.12)}}
.srow{{display:flex;align-items:center;justify-content:space-between;gap:30px}}
.sjp{{font-size:120px;line-height:1.15}}
.sside{{font-size:84px;font-weight:700}}
.smean{{display:flex;gap:22px;align-items:baseline;justify-content:flex-start;background:{c['shu_soft']};color:{c['ink']};border-radius:18px;padding:8px 24px;font-size:48px;font-weight:700;margin-bottom:14px}}
.smean span{{font-size:36px;font-weight:500;color:{c['muted']}}}
.combo{{align-items:center;gap:22px}}
.card.small{{width:300px;padding:30px 20px 24px}}
.card.small .cmp{{font-size:200px}}
.plus{{font-size:110px;font-weight:700;color:{c['muted']}}}
@keyframes up{{from{{opacity:0;transform:translateY(46px)}}to{{opacity:1;transform:none}}}}
@keyframes pop{{0%{{opacity:0;transform:scale(.6)}}70%{{opacity:1;transform:scale(1.06)}}100%{{transform:scale(1)}}}}
@keyframes zoom{{from{{transform:scale(1)}}to{{transform:scale(1.07)}}}}
@keyframes draw{{0%{{stroke-dashoffset:1;opacity:0}}1%{{opacity:1}}100%{{stroke-dashoffset:0;opacity:1}}}}
@keyframes fade{{to{{opacity:.35}}}}
@keyframes right{{to{{background:{c['good_soft']};border-color:{c['good']}}}}}
@keyframes stamp{{0%{{opacity:0;transform:scale(1.8) rotate(-12deg)}}100%{{opacity:1;transform:scale(1) rotate(-8deg)}}}}
@keyframes tick{{0%{{opacity:0;transform:scale(1.4)}}15%{{opacity:1;transform:scale(1)}}85%{{opacity:1}}100%{{opacity:0}}}}
"""


def waves_svg(theme):
    c = THEMES[theme]["wave"]
    circles = "".join(f'<circle cx="{cx}" cy="{cy}" r="{r}"/>' for cx, cy in [(60, 60), (0, 30), (120, 30)] for r in (56, 42, 28, 14))
    return f'''<svg class="waves" width="{W}" height="520"><defs>
      <pattern id="s" width="120" height="60" patternUnits="userSpaceOnUse"><g fill="none" stroke="{c}" stroke-width="3">{circles}</g></pattern>
      <linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff"/></linearGradient>
      <mask id="m"><rect width="{W}" height="520" fill="url(#g)"/></mask></defs>
      <rect width="{W}" height="520" fill="url(#s)" mask="url(#m)"/></svg>'''


def page(scene, theme, brand=True):
    body, auto = SCENES[scene["type"]](scene)
    head = '<div class="brand"><img src="logo.png">Senri</div>' if brand and scene["type"] != "cta" else ""
    doc = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>{css(theme)}</style></head>
<body>{waves_svg(theme)}{head}<div class="safe">{body}</div></body></html>'''
    return doc, auto


FREEZE_JS = """async () => {
  await document.fonts.ready;
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  const anims = document.getAnimations();
  anims.forEach(a => a.pause());
  window.__seek = ms => anims.forEach(a => { a.currentTime = ms; });
  let end = 0;
  anims.forEach(a => { const t = a.effect.getComputedTiming(); end = Math.max(end, t.endTime); });
  return end;
}"""

CHECK_JS = """([x0, y0, x1, y1]) => {
  const out = [];
  document.querySelectorAll('.t').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width === 0) return;
    if (r.left < x0 - 1 || r.right > x1 + 1 || r.top < y0 - 1 || r.bottom > y1 + 1)
      out.push(`${el.className.split(' ').slice(0,2).join('.')} «${el.textContent.trim().slice(0, 30)}» surt de la zona segura`);
    if (el.scrollWidth > el.clientWidth + 2) out.push(`${el.className} «${el.textContent.trim().slice(0, 30)}» no hi cap`);
  });
  return out;
}"""


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"ffmpeg ha fallat:\n{p.stderr[-2000:]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("out")
    ap.add_argument("--stills", action="store_true", help="només un fotograma per escena (revisió ràpida)")
    ap.add_argument("--audio", help="àudio opcional (s'escurça al vídeo i s'hi fa un fos de sortida)")
    ap.add_argument("--crf", default="20")
    a = ap.parse_args()

    spec = json.loads(Path(a.spec).read_text())
    theme = spec.get("theme", "light")
    brand = spec.get("brand", True)
    scenes = spec["scenes"]
    for i, s in enumerate(scenes):
        if s.get("type") not in SCENES:
            sys.exit(f"Escena {i}: tipus desconegut «{s.get('type')}». Tipus: {', '.join(SCENES)}")

    from playwright.sync_api import sync_playwright

    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="short-"))
    shutil.copy(ASSETS / "logo.png", work / "logo.png")
    warnings, files, total = [], [], 0.0

    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page(viewport={"width": W, "height": H})
        for i, s in enumerate(scenes):
            doc, auto = page(s, theme, brand)
            f = work / f"scene{i}.html"
            f.write_text(doc)
            pg.goto(f.as_uri())
            end_ms = pg.evaluate(FREEZE_JS)
            dur = float(s.get("duration") or max(auto, end_ms / 1000 + 0.8))
            total += dur
            pg.evaluate(f"window.__seek({end_ms + 1})")
            for w in pg.evaluate(CHECK_JS, list(SAFE)):
                warnings.append(f"escena {i} ({s['type']}): {w}")

            if a.stills:
                still = out.with_name(f"{out.stem}-escena{i}.jpg")
                pg.screenshot(path=str(still), type="jpeg", quality=90)
                files.append(still)
                if i == 0:
                    pg.evaluate("window.__seek(0)")
                    pg.screenshot(path=str(out.with_name(f"{out.stem}-primer-fotograma.jpg")), type="jpeg", quality=90)
                continue

            tmp = work / f"s{i}.tmp.mp4"
            enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
                                    "-c:v", "mjpeg", "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", a.crf,
                                    "-pix_fmt", "yuv420p", "-r", str(FPS), str(tmp)], stdin=subprocess.PIPE)
            last = None
            for fr in range(round(dur * FPS)):
                ms = fr * 1000 / FPS
                if last is None or ms <= end_ms + 1000 / FPS:
                    pg.evaluate(f"window.__seek({ms})")
                    last = pg.screenshot(type="jpeg", quality=92)
                    if i == 0 and fr == 0:
                        (out.with_name(f"{out.stem}-portada.jpg")).write_bytes(last)
                enc.stdin.write(last)
            enc.stdin.close()
            if enc.wait() != 0:
                sys.exit(f"ffmpeg ha fallat a l'escena {i}")
            tmp.rename(work / f"s{i}.mp4")
            files.append(work / f"s{i}.mp4")
        browser.close()

    if a.stills:
        print(json.dumps({"stills": [str(x) for x in files], "durada_total_s": round(total, 1), "avisos": warnings},
                         ensure_ascii=False, indent=2))
        return

    lst = work / "list.txt"
    lst.write_text("".join(f"file '{x}'\n" for x in files))
    video = work / "video.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(video)])
    if spec.get("progress", True):
        # Barra fina just a sobre del logo que avança durant tot el vídeo: dona moviment des del
        # primer fotograma i diu «és curt, queda poc».
        bar_color = THEMES[theme]["accent"].lstrip("#")
        barred = work / "barred.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-f", "lavfi",
             "-i", f"color=c=0x{bar_color}:s={W}x10:r={FPS}",
             "-filter_complex", f"[0:v][1:v]overlay=x='-w+w*t/{total:.3f}':y=196:shortest=1:eval=frame,format=yuv420p",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", a.crf, "-r", str(FPS), str(barred)])
        video = barred
    tmp_out = out.with_name(out.stem + ".tmp.mp4")
    if a.audio:
        fade = max(total - 1.5, 0)
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", a.audio, "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-af", f"afade=t=out:st={fade}:d=1.5", "-shortest",
             "-movflags", "+faststart", str(tmp_out)])
    else:
        # Pista d'àudio silenciosa: algunes plataformes no deixen afegir-hi música si el vídeo no en té cap.
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
             "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(tmp_out)])
    tmp_out.rename(out)
    shutil.rmtree(work, ignore_errors=True)
    print(json.dumps({"video": str(out), "portada": str(out.with_name(f"{out.stem}-portada.jpg")),
                      "durada_s": round(total, 1), "avisos": warnings}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
