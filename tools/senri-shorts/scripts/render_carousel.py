#!/usr/bin/env python3
"""Genera un carrusel d'Instagram (diapositives 1080x1350, 4:5) amb l'estil de Senri a partir d'un guió JSON.

Ús:
  python3 render_carousel.py guio.json carpeta_sortida/

Escriu carpeta/01.jpg, 02.jpg… i avisa si algun text no hi cap o surt dels marges.
Format del guió: vegeu references/carrusels.md.
"""
import argparse
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_short import THEMES, ASSETS, fmt, jp  # noqa: E402

W, H = 1080, 1350
# La graella del perfil retalla els costats (3:4): deixa el contingut entre x 90 i 990.
SAFE = (90, 60, 990, 1290)


def esc(s):
    return html.escape(str(s or ""))


def s_cover(s):
    big = f'<div class="t big kana" style="font-size:{min(380, int(860 / max(1, len(s["big"]))))}px">{esc(s["big"])}</div>' if s.get("big") else ""
    sub = f'<div class="t sub">{fmt(s["sub"])}</div>' if s.get("sub") else ""
    chip = f'<div class="t chip">{fmt(s["label"])}</div>' if s.get("label") else ""
    return f'''<div class="stack center">{chip}<div class="t hook">{fmt(s["title"])}</div>{big}{sub}
      <div class="t swipe">{fmt(s.get("swipe", "Desliza →"))}</div></div>'''


def s_table(s):
    rows = []
    for r in s["rows"]:
        cells = "".join(
            f'<div class="cell"><span class="ck kana">{esc(c[0])}</span><span class="cr">{esc(c[1])}</span></div>'
            if c else '<div class="cell empty"></div>' for c in r)
        rows.append(f'<div class="trow">{cells}</div>')
    note = f'<div class="t tip">{fmt(s["note"])}</div>' if s.get("note") else ""
    return f'''<div class="stack"><div class="t title">{fmt(s["title"])}</div>
      <div class="t table">{"".join(rows)}</div>{note}</div>'''


def s_pairs(s):
    rows = []
    for p in s["items"]:
        rows.append(f'''<div class="t pair">
          <div class="pc"><span class="pk kana">{esc(p["a"])}</span><span class="cr">{esc(p.get("ar", ""))}</span></div>
          <div class="pc"><span class="pk kana">{esc(p["b"])}</span><span class="cr">{esc(p.get("br", ""))}</span></div>
          <div class="ptip">{fmt(p.get("tip", ""))}</div></div>''')
    return f'<div class="stack"><div class="t title">{fmt(s["title"])}</div>{"".join(rows)}</div>'


def s_list(s):
    rows = []
    for it in s["items"]:
        rom = f'<span class="lr">{esc(it.get("romaji"))}</span>' if it.get("romaji") else ""
        rows.append(f'''<div class="t li"><span class="lj kana">{jp(it["jp"], it.get("kana"))}</span>
          <span class="lm">{fmt(it.get("meaning", ""))}{rom}</span></div>''')
    note = f'<div class="t tip">{fmt(s["note"])}</div>' if s.get("note") else ""
    return f'<div class="stack"><div class="t title">{fmt(s["title"])}</div><div class="list">{"".join(rows)}</div>{note}</div>'


def s_kanji(s):
    ex = "".join(f'<div class="t li small"><span class="lj kana">{jp(e["jp"], e.get("kana"))}</span>'
                 f'<span class="lm">{fmt(e.get("meaning", ""))}<span class="lr">{esc(e.get("romaji"))}</span></span></div>'
                 for e in s.get("examples", []))
    reading = " · ".join(x for x in [s.get("reading"), s.get("romaji")] if x)
    hint = f'<div class="t hintc">{fmt(s["hint"])}</div>' if s.get("hint") else ""
    return f'''<div class="stack center"><div class="t chip">{fmt(s.get("label", "Kanji N5"))}</div>
      <div class="t kbig kana">{esc(s["k"])}</div>
      <div class="t meaning">{fmt(s.get("meaning", ""))}</div>
      <div class="t reading kana">{esc(reading)}</div>{hint}<div class="list wide">{ex}</div></div>'''


def grammar_jp(src):
    """Frase amb la sintaxi de tools/grammar-*.txt: 学生{がくせい} → furigana, [は] o [へ|に] → partícula en vermell."""
    import re
    out = []
    for tok in src.split():
        m = re.fullmatch(r"\[(.+?)\]", tok)
        if m:
            out.append(f"<em>{esc(m.group(1).split('|')[0])}</em>")
            continue
        out.append(re.sub(r"([^{}\s]+?)\{(.+?)\}", lambda g: f"<ruby>{esc(g.group(1))}<rt>{esc(g.group(2))}</rt></ruby>", esc(tok)))
    return "".join(out)


def s_sentences(s):
    rows = "".join(f'<div class="t sent"><div class="sj kana">{grammar_jp(it["jp"])}</div>'
                   f'<div class="se">{fmt(it.get("es", ""))}</div></div>' for it in s["items"])
    note = f'<div class="t tip">{fmt(s["note"])}</div>' if s.get("note") else ""
    return f'<div class="stack"><div class="t title">{fmt(s["title"])}</div>{rows}{note}</div>'


def s_quiz(s):
    opts = "".join(f'<div class="t opt{" right" if s.get("show_answer") and i == s.get("answer") else ""}">'
                   f'<span class="optl">{"ABCD"[i]}</span>{fmt(o)}'
                   f'{"<span class=mark>〇</span>" if s.get("show_answer") and i == s.get("answer") else ""}</div>'
                   for i, o in enumerate(s["options"]))
    prompt = f'<div class="t big kana q" style="font-size:{min(260, int(800 / max(1, len(s["prompt"]))))}px">{esc(s["prompt"])}</div>' if s.get("prompt") else ""
    foot = f'<div class="t sub">{fmt(s["foot"])}</div>' if s.get("foot") else ""
    return f'''<div class="stack center"><div class="t title">{fmt(s.get("question", "¿Qué significa?"))}</div>
      {prompt}<div class="opts">{opts}</div>{foot}</div>'''


def s_text(s):
    title = f'<div class="t title">{fmt(s["title"])}</div>' if s.get("title") else ""
    big = f'<div class="t big kana" style="font-size:{min(300, int(860 / max(1, len(s["big"]))))}px">{esc(s["big"])}</div>' if s.get("big") else ""
    return f'<div class="stack center">{title}{big}<div class="t body">{fmt(s.get("text", ""))}</div></div>'


def s_cta(s):
    return f'''<div class="stack center"><img class="t logo" src="logo.png">
      <div class="t hook">{fmt(s.get("text", "Guárdalo y practica gratis con **Senri**"))}</div>
      <div class="t sub">{fmt(s.get("sub", "Sin cuenta ni anuncios · enlace en el perfil"))}</div></div>'''


SLIDES = dict(cover=s_cover, table=s_table, pairs=s_pairs, list=s_list, kanji=s_kanji,
              quiz=s_quiz, text=s_text, cta=s_cta, sentences=s_sentences)


def css(theme):
    c = THEMES[theme]
    f = (ASSETS / "fonts").as_uri()
    x0, y0, x1, y1 = SAFE
    return f"""
@font-face{{font-family:'Klee One';font-weight:600;src:url('{f}/klee-one-600.v1.woff2')}}
@font-face{{font-family:'Zen Kaku Gothic New';font-weight:500;src:url('{f}/zen-kaku-500.v1.woff2')}}
@font-face{{font-family:'Zen Kaku Gothic New';font-weight:700;src:url('{f}/zen-kaku-700.v1.woff2')}}
*{{box-sizing:border-box}} html,body{{margin:0}}
ruby{{ruby-align:center}} rt{{letter-spacing:0;text-align:center}}
body{{width:{W}px;height:{H}px;overflow:hidden;background:{c['bg']};color:{c['ink']};position:relative;
  font-family:'Zen Kaku Gothic New','Noto Sans CJK JP',sans-serif;font-weight:500}}
.kana{{font-family:'Klee One','Noto Serif CJK JP',serif;font-weight:600}}
em{{font-style:normal;color:{c['shu']}}}
.waves{{position:absolute;left:0;right:0;bottom:0;height:360px;opacity:.8}}
.brand{{position:absolute;left:{x0}px;top:{y0}px;display:flex;align-items:center;gap:14px;font-weight:700;font-size:30px;color:{c['accent']}}}
.brand img{{width:50px;height:50px;border-radius:12px}}
.pg{{position:absolute;right:{W - x1}px;top:{y0 + 8}px;font-size:28px;font-weight:700;color:{c['muted']}}}
.safe{{position:absolute;left:{x0}px;top:{y0 + 90}px;width:{x1 - x0}px;height:{y1 - y0 - 90}px;display:flex;align-items:center;justify-content:center}}
.stack{{display:flex;flex-direction:column;gap:30px;width:100%}}
.center{{align-items:center;text-align:center}}
.hook{{font-weight:700;font-size:80px;line-height:1.12;letter-spacing:-1px;text-wrap:balance}}
.title{{font-weight:700;font-size:58px;line-height:1.15;text-wrap:balance}}
.sub{{font-size:40px;color:{c['muted']};line-height:1.3;text-wrap:balance}}
.body{{font-size:46px;line-height:1.4;text-wrap:pretty;max-width:860px}}
.swipe{{font-size:36px;font-weight:700;color:{c['accent']};background:{c['accent_soft']};border-radius:999px;padding:12px 32px}}
.big{{line-height:1;color:{c['accent']};white-space:nowrap}}
.kbig{{font-size:300px;line-height:1;color:{c['accent']}}}
.meaning{{font-weight:700;font-size:72px;line-height:1.1}}
.reading{{font-size:46px;color:{c['muted']}}}
.chip{{align-self:center;background:{c['accent_soft']};color:{c['accent']};border-radius:999px;padding:10px 28px;font-size:34px;font-weight:700}}
.table{{display:flex;flex-direction:column;gap:14px}}
.trow{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px}}
.cell{{background:{c['surface']};border:3px solid {c['line']};border-radius:24px;height:178px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px}}
.cell.empty{{background:none;border:none}}
.ck{{font-size:100px;line-height:1.05;color:{c['accent']}}}
.cr{{font-size:36px;font-weight:700;color:{c['muted']}}}
.tip{{background:{c['shu_soft']};border-radius:26px;padding:24px 32px;font-size:38px;line-height:1.3}}
.pair{{display:grid;grid-template-columns:130px 130px 1fr;gap:18px;align-items:center;background:{c['surface']};border:3px solid {c['line']};border-radius:28px;padding:10px 24px}}
.pc{{display:flex;flex-direction:column;align-items:center}}
.pk{{font-size:88px;line-height:1.05;color:{c['accent']}}}
.ptip{{font-size:34px;line-height:1.3}}
.list{{display:flex;flex-direction:column;gap:20px}} .list.wide{{width:100%}}
.li{{display:flex;align-items:center;gap:32px;background:{c['surface']};border:3px solid {c['line']};border-radius:26px;padding:18px 30px;text-align:left}}
.lj{{font-size:76px;color:{c['accent']};min-width:270px;line-height:1.15}}
.li.small .lj{{font-size:64px;min-width:220px}}
.lj rt{{font-size:28px;color:{c['muted']};font-weight:500}}
.lm{{display:flex;flex-direction:column;font-size:44px;font-weight:700;line-height:1.15}}
.lr{{font-size:32px;font-weight:500;color:{c['muted']}}}
.opts{{display:flex;flex-direction:column;gap:18px;width:100%}}
.opt{{position:relative;display:flex;align-items:center;gap:24px;background:{c['surface']};border:3px solid {c['line']};border-radius:26px;padding:22px 30px;font-size:48px;font-weight:700;text-align:left}}
.opt.right{{background:{c['good_soft']};border-color:{c['good']}}}
.optl{{width:60px;height:60px;border-radius:50%;background:{c['accent_soft']};color:{c['accent']};display:flex;align-items:center;justify-content:center;font-size:32px;flex:none}}
.mark{{position:absolute;right:28px;top:50%;margin-top:-46px;font-size:92px;line-height:1;color:{c['shu']};transform:rotate(-8deg)}}
em ruby rt{{color:{c['shu']}}}
.sent{{background:{c['surface']};border:3px solid {c['line']};border-radius:26px;padding:20px 30px;display:flex;flex-direction:column;gap:6px}}
.sj{{font-size:62px;line-height:1.5;color:{c['ink']}}} .sj rt{{font-size:24px;color:{c['muted']};font-weight:500}}
.se{{font-size:38px;color:{c['muted']};font-weight:700}}
.hintc{{font-size:38px;color:{c['muted']};text-wrap:balance}}
.logo{{width:220px;height:220px;border-radius:50px}}
"""


def waves(theme):
    col = THEMES[theme]["wave"]
    circles = "".join(f'<circle cx="{cx}" cy="{cy}" r="{r}"/>' for cx, cy in [(60, 60), (0, 30), (120, 30)] for r in (56, 42, 28, 14))
    return f'''<svg class="waves" width="{W}" height="360"><defs>
      <pattern id="s" width="120" height="60" patternUnits="userSpaceOnUse"><g fill="none" stroke="{col}" stroke-width="3">{circles}</g></pattern>
      <linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff"/></linearGradient>
      <mask id="m"><rect width="{W}" height="360" fill="url(#g)"/></mask></defs>
      <rect width="{W}" height="360" fill="url(#s)" mask="url(#m)"/></svg>'''


CHECK_JS = """([x0, y0, x1, y1]) => {
  const out = [];
  document.querySelectorAll('.t').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width === 0) return;
    if (r.left < x0 - 1 || r.right > x1 + 1 || r.top < y0 - 1 || r.bottom > y1 + 1)
      out.push(`«${el.textContent.trim().slice(0, 30)}» surt dels marges`);
    if (el.scrollWidth > el.clientWidth + 2) out.push(`«${el.textContent.trim().slice(0, 30)}» no hi cap`);
  });
  return out;
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("guio")
    ap.add_argument("out")
    a = ap.parse_args()
    g = json.loads(Path(a.guio).read_text())
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    theme = g.get("theme", "light")
    slides = g["slides"]
    (out / "logo.png").write_bytes((ASSETS / "logo.png").read_bytes())
    from playwright.sync_api import sync_playwright
    warns = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        for i, s in enumerate(slides, 1):
            th = s.get("theme", theme)
            head = '' if s["type"] == "cta" else '<div class="brand"><img src="logo.png">Senri</div>'
            num = f'<div class="pg">{i}/{len(slides)}</div>' if g.get("numbers", True) else ""
            doc = (f'<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>{css(th)}</style></head>'
                   f'<body>{waves(th)}{head}{num}<div class="safe">{SLIDES[s["type"]](s)}</div></body></html>')
            f = out / f"_s{i:02d}.html"
            f.write_text(doc)
            pg.goto(f.as_uri())
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(80)
            warns += [f"diapositiva {i}: {w}" for w in pg.evaluate(CHECK_JS, list(SAFE))]
            pg.screenshot(path=str(out / f"{i:02d}.jpg"), type="jpeg", quality=92)
            f.unlink()
        b.close()
    (out / "logo.png").unlink()
    print(f"{len(slides)} diapositives a {out}")
    for w in warns:
        print("AVÍS:", w)


if __name__ == "__main__":
    main()
