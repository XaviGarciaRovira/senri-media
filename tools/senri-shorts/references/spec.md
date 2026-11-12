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
- `progress`: barra fina a dalt que avança durant tot el vídeo (per defecte `true`).
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
| `stroke_time` | segons per traç (0,45 per defecte) |
| `teaser` | frase que surt just amb la resposta i anuncia el que ve (p. ex. «Quédate: al final, un **reto** 👀»). Al primer vídeo, la gent marxava just quan sortia el significat |
| `question` | pregunta a dalt, visible des del fotograma 0; el traç comença tot seguit i l'escena fa de ganxo. Amb `question`, el `label` surt al final com a xip |

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

### `guess` — «dilo antes que yo»
Amb `icon` (il·lustració de `assets/emoji/`: arbol, arroz, avion, bento, bicicleta, cafe, casa, coche, flor, gafas, gato, huevo, leche, libro, llave, lluvia, luna, montana, nieve, pajaro, pan, paraguas, perro, pez, reloj, te, telefono, tren, zapatos, agua): imatge → l'espectador diu la paraula japonesa; després del compte surten `jp` (amb furigana si porta `kana`), `romaji` i `meaning`. Pregunta per defecte: «¿Cómo se dice en japonés?». És recordar activament (produir la paraula), el principi de Senri.
Sense `icon`: `jp` gran (p. ex. `カメラ`) → l'espectador endevina el significat; surten `meaning` i `romaji`. Ideal per a «Si sabes katakana, ya sabes estas palabras».
Camps comuns: `question`, `countdown` (3), `note`. Les il·lustracions són Fluent Emoji (Flat) de Microsoft, llicència MIT: posa «Ilustraciones: Fluent Emoji (Microsoft, MIT)» a la descripció. Per afegir-ne una, copia el `*_flat.svg` de github.com/microsoft/fluentui-emoji (clon amb `--sparse`) a `assets/emoji/<nom>.svg`. Comprova abans que la paraula sigui a Senri (`lookup.mjs`).

### `sign` — «¿Puedes leer este cartel?»
Un rètol dibuixat de la vida real: `style` `estacion` (groc, com els de sortida de les estacions), `pizarra` (carta de cafeteria) o `placa` (placa de porta). `rows`: `jp`, `arrow` o `price` a la dreta, `meaning`, `romaji` (surten com a traducció dins el rètol després del compte). `question` amb el context («Estás en una estación…»), `countdown`, `note` (p. ex. el significat de cada kanji). Màxim 3 files.

### `combo` — kanji = dibuix + dibuix
`parts` (2–3: `k`, `meaning`), `result` (`k`, `meaning`, `reading`, `romaji`), `hint`, `question` («¿Qué kanji sale?»), `countdown`. Fes servir la pista (`hint`) de Senri (`lookup.mjs`) i només kanji que hi siguin.

## Sortida
- `sortida.mp4`: H.264 1080×1920, 30 fps, amb una pista d'àudio silenciosa (perquè les plataformes deixin afegir-hi música). Amb `--audio fitxer.mp3` en fa servir un de propi, retallat i amb fos de sortida.
- `sortida-portada.jpg`: el primer fotograma, per a portada.
- Amb `--stills`: `sortida-escenaN.jpg` (cada escena acabada) i `sortida-primer-fotograma.jpg`, en un o dos segons.
- `avisos`: textos que surten de la zona segura (x 80–940, y 220–1580) o que no hi caben. Arregla'ls abans del render complet: allà la interfície de TikTok, Reels o Shorts els taparia.

## So (automàtic)
`render_short.py` hi afegeix sol, mesclat amb `--audio`:
- **Tic-tac** a cada número del compte enrere (l'últim, més agut), **campaneta** quan surt la resposta i una **transició** suau entre escenes. Sintetitzats a `scripts/sound.py`, sense res de tercers.
- **Veu japonesa** de Senri (VOICEVOX:春日部つむぎ, els MP3 de `audio/` del repositori de Senri, `--senri`): pronuncia la resposta (quiz, guess, combo, kanji), cada fila del cartell, cada paraula de `list` i `word` i els dos caràcters de `compare`. La música baixa mentre parla. Busca el text a `audio/index.json` pel `kana`; si la paraula porta kanji, posa `say` amb la lectura en kana (p. ex. `"say": "でぐち"`). Els textos que no troba surten als `avisos`.
- **Crèdit obligatori** quan hi ha veu: «Voz: VOICEVOX:春日部つむぎ» a la descripció.
- `--no-voice` o `--no-sfx` per treure'ls.
