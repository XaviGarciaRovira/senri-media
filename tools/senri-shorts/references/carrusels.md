# Carrusels d'Instagram (`render_carousel.py`)

```bash
python3 scripts/render_carousel.py guio.json carpeta/   # escriu carpeta/01.jpg, 02.jpg…
```
Diapositives de 1080×1350 (4:5) amb l'estil de Senri. El contingut es manté entre x 90 i x 990, perquè la graella del perfil (3:4) en retalla els costats. Corregeix tots els `AVÍS` i mira les imatges (un full de contactes amb `ffmpeg -i carpeta/%02d.jpg -vf "scale=360:-1,tile=4x2" -frames:v 1 m.jpg`) abans de pujar-les.

## Per què carrusels
Els reels porten gent nova. Els carrusels són el contingut que la gent desa i envia: taules, guies i resums per repassar. Instagram té en compte els enviaments per missatge sobretot per arribar a no-seguidors, i els guardats indiquen valor. Un carrusel bo és una «xuleta» que algú vol tenir al mòbil.

## Guió
```json
{"theme": "light", "numbers": true, "slides": [ {"type": "cover", ...}, ... ]}
```
`**paraula**` en vermell, `\n` salt de línia. Cada diapositiva pot portar el seu `theme`.

| tipus | camps |
|---|---|
| `cover` | `label` (xip), `title`, `big` (caràcters grans), `sub`, `swipe` («Desliza →» per defecte) |
| `table` | `title`, `rows` (llistes de 5 `[kana, romaji]` o `null` per a un forat), `note`. Màxim 5 files sense `note`, o 4 amb `note` |
| `pairs` | `title`, `items` (`a`, `ar`, `b`, `br`, `tip`). Màxim 5 |
| `list` | `title`, `items` (`jp`, `kana`, `romaji`, `meaning`), `note`. Màxim 6 |
| `kanji` | `k`, `label`, `meaning`, `reading`, `romaji`, `examples` (com `list`, màxim 3) |
| `quiz` | `question`, `prompt`, `options`, `answer`, `show_answer` (true a la diapositiva de la resposta), `foot` |
| `text` | `title`, `big`, `text` |
| `cta` | `text`, `sub` |

## Criteris
- **Portada**: promet una cosa concreta i completa («Todo el hiragana en un carrusel», «8 palabras para pedir en un restaurante»). La portada és el ganxo; la diapositiva 2 ha de complir-lo de seguida.
- 5–10 diapositives. L'última sempre és `cta` («Guárdalo y practica gratis con **Senri**»).
- Contingut tret de Senri (`lookup.mjs` o `js/data.js`). Res que no hi sigui sense revisar-lo amb els criteris de `senri-japanese-teacher`.
- No facis servir ゛ ni ゜ sols en text normal (es veuen malament): escriu «dakuten».
- **Text de la publicació**: què hi ha + «Guárdalo» + una crida a **enviar-lo** («Envíaselo a quien…») + pregunta per comentar + 3–5 hashtags.
- **Text alternatiu** (`mediaAltText`, un per imatge): descriu què hi ha a cada diapositiva. Ajuda l'accessibilitat i la cerca.

## Metricool
Puja les imatges a `senri-media/carrusels/AAAA-MM-DD-tema/` i passa les adreces `raw.githubusercontent.com` a `media` (en ordre), amb `providers: [{"network":"instagram"}]` i `instagramData: {"type":"POST"}`. Com a esborrany fins que l'usuari digui «endavant».
