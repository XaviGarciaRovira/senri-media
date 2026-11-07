# Format del guió JSON de `render_short.py`

```json
{
  "title": "El kanji del agua",
  "lang": "es",
  "theme": "light",
  "brand": true,
  "scenes": [ { "type": "hook", ... }, ... ]
}
```

- `theme`: `light` (paper washi, per defecte) o `dark` (bosc de nit). Alterna'ls entre vídeos perquè el perfil no sigui monòton.
- `brand`: logo i «Senri» a dalt a l'esquerra (per defecte `true`). L'escena `cta` no el porta perquè ja mostra el logo gran.
- Cada escena accepta `duration` (segons). Si no la poses, el script calcula el temps que necessiten les animacions més un marge de lectura. Posa-la quan vulguis un ritme concret.
- Text: `**paraula**` surt en vermell 朱 (èmfasi) i `\n` és un salt de línia. Fes servir l'èmfasi en una o dues paraules per escena, no més.
- Tot el japonès es dibuixa amb Klee One (forma de llibre de text, com a l'app).

## Tipus d'escena

### `hook` — primer fotograma
| camp | |
|---|---|
| `text` | la frase ganxo. Ja és visible al fotograma 0 (sense fos d'entrada). |
| `big` | opcional: caràcters grans a sota (es fan petits sols si n'hi ha més d'un). |
| `sub` | opcional: línia petita que apareix als 0,5 s. |

Fes-la servir sempre com a primera escena. Durada típica 2–3 s.

### `kanji` — traçat animat
| camp | |
|---|---|
| `k` | el kanji |
| `paths` | traços KanjiVG de `lookup.mjs` (si falten, es mostra el kanji sense animació) |
| `meaning`, `reading`, `romaji`, `hint` | apareixen quan s'acaba de dibuixar |
| `label` | xip de dalt, per defecte «Kanji N5» (p. ex. «Kanji N5 · 4 trazos») |
| `stroke_time` | segons per traç (0,55 per defecte) |

### `word` — paraula amb furigana
`jp`, `kana` (furigana si `jp` porta kanji), `romaji`, `meaning`, `note`, `label`, `reveal_at` (segon en què apareix el significat; 1,2 per defecte; dona temps a l'espectador per endevinar).

### `compare` — dos caràcters que es confonen
`title`, `left` i `right` (`char`, `romaji`, `label`), `tip`, `tip_at`.

### `quiz` — pregunta amb compte enrere
`question`, `prompt` (caràcter o paraula gran), `options` (2–4), `answer` (índex des de 0), `countdown` (3 per defecte). Després del compte, l'opció correcta es posa verda amb el segell 〇 i les altres s'esvaeixen. És el format que més comentaris genera: la gent escriu la seva resposta.

### `list` — 3–5 elements que apareixen d'un en un
`title`, `items` (`jp`, `kana`, `romaji`, `meaning`), `step` (segons entre elements, 1,3 per defecte). Més de 5 elements no caben ni es llegeixen.

### `text` — frase de transició o conclusió
`text`, `big` (opcional), `sub`.

### `cta` — tancament
`text` (per defecte «Aprende japonés gratis con **Senri**»), `sub` (per defecte «Sin cuenta ni anuncios · enlace en el perfil»), `url` (opcional). Màxim 3 s.

## Sortida
- `sortida.mp4`: H.264 1080×1920, 30 fps, amb una pista d'àudio silenciosa (perquè les plataformes deixin afegir-hi música). Amb `--audio fitxer.mp3` en fa servir un de propi, retallat i amb fos de sortida.
- `sortida-portada.jpg`: el primer fotograma, per a portada.
- Amb `--stills`: `sortida-escenaN.jpg` (cada escena acabada) i `sortida-primer-fotograma.jpg`, en un o dos segons.
- `avisos`: textos que surten de la zona segura (x 80–940, y 220–1580) o que no hi caben. Arregla'ls abans del render complet: allà la interfície de TikTok, Reels o Shorts els taparia.
