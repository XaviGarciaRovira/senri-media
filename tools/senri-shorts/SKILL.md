---
name: senri-shorts
description: "Genera vídeos verticals acabats (TikTok, Instagram Reels, YouTube Shorts) per a Senri sense haver de gravar res: kanji amb l'ordre de traços animat, parelles de kana que es confonen, quizzes amb compte enrere i llistes de vocabulari N5, amb la identitat visual de l'app i el contingut tret del repositori. Fes-la servir sempre que l'usuari demani fer, crear, generar o preparar un short, un TikTok, un reel, un vídeo curt o un vídeo per a xarxes de Senri, o vídeos de la setmana o del calendari de contingut, encara que no digui «skill»."
---

# Shorts de Senri

Converteix una idea en un vídeo vertical llest per publicar: escrius un guió en JSON, el script el dibuixa amb les tipografies i els colors de Senri i el codifica amb ffmpeg. No cal gravar ni editar.

Per a vídeos que l'usuari ha de gravar ell (càmera, veu en off, pantalla del mòbil) fes servir la skill `senri-guions-video`: aquesta és per als que es generen sols.

## Abans de començar

1. **Contingut de Senri.** Les lectures, els significats i els traços han de ser els de l'app. Si el repositori no és a `/home/claude/senri`, afegeix-lo (`XaviGarciaRovira/senri`) i clona'l. Després:
   ```bash
   node scripts/lookup.mjs --repo /home/claude/senri --lang es 水 先生 シャツ
   node scripts/lookup.mjs --repo /home/claude/senri --lang es --kanji-unit k-5
   ```
   Si un terme surt com a `missing`, no és a Senri: tria'n un altre o, si és imprescindible, revisa'l amb els criteris de `senri-japanese-teacher`. Un error de japonès en un vídeo públic fa més mal que no publicar-lo.
2. **Idioma.** Els comptes (@senriapp) són en castellà. Fes-los en castellà llevat que l'usuari demani català o anglès (`--lang ca|en` al lookup i textos en aquell idioma).
3. **Eines.** Cal Playwright (Chromium) i ffmpeg. No instal·lis res; si falta alguna cosa, digues-ho.

## 1. Tria el format

Un vídeo, una idea. Escull el format segons l'objectiu:

| Format | Escenes | Per què funciona |
|---|---|---|
| **Kanji en 15 s** | `hook` → `kanji` → `quiz` d'un altre kanji → `cta` | El traçat animat enganxa i el quiz final genera comentaris |
| **Parella que es confon** (シ/ツ, ソ/ン, ぬ/め, わ/ね…) | `hook` → `compare` → `list` amb paraules que la porten → `cta` | Resol un problema que tothom ha tingut; es guarda molt |
| **¿Qué significa?** | `hook` → `quiz` → `word` amb la resposta i un ús → `cta` | La gent comenta abans de veure la resposta |
| **3 paraules de…** (menjar, família, viatge) | `hook` → `list` → `text` → `cta` | Útil i fàcil de guardar |
| **Error típic** | `hook` («No digas X») → `compare` o `word` → `text` | La versió «error primer» és de les que més retenen en vídeos d'idiomes |
| **Sèrie** («Kanji del día #3») | igual que el format base, amb el número al `label` | Fa tornar la gent i ordena el perfil |

Les dades dels kanji de cada unitat (`k-1` … ) donen sèries fetes: una unitat = una setmana de vídeos.

## 2. Escriu el guió

Llegeix `references/spec.md` per als camps de cada escena. Criteris que fan que un vídeo es vegi fins al final:

- **El primer fotograma ho decideix tot.** La gent decideix en un segon i mig si s'atura, i molts el veuen sense so. El `hook` ja és visible a t=0: ha de dir per què val la pena quedar-se en 10 paraules o menys. Escriu-ne tres variants mentalment (pregunta, repte, error, curiositat) i queda't amb la més concreta.
- **Res inventat.** Cap estadística («el 90 % s'equivoca»), cap promesa («japonès en 7 dies»). Senri és experimental i gratuïta: aquest és l'argument, i és cert.
- **Durada: 15–30 s.** Un canvi visual cada 2–4 s; el script ja anima l'entrada de cada element. Per sota de 10 s sembla incomplet; per sobre de 35 s cau la retenció.
- **Temps per pensar.** En un quiz o en una paraula, deixa 2–3 s abans de la resposta (`countdown`, `reveal_at`): és aquí on l'espectador participa.
- **Tancament curt.** La `cta` no passa de 3 s. Si el vídeo acaba amb una pregunta oberta («¿Y este?»), el bucle fa que molts el tornin a veure.
- **Nivell clar.** Diu «N5» o «principiantes» en algun lloc perquè cadascú sàpiga si és per a ell.

Desa el guió com a `<carpeta>/<slug>.json`.

## 3. Revisa abans de renderitzar

```bash
python3 scripts/render_short.py guio.json out/slug.mp4 --stills
```

Triga un parell de segons. Mira les imatges (`*-escenaN.jpg` i `*-primer-fotograma.jpg`) amb Read i corregeix tots els `avisos`: un text fora de la zona segura quedarà tapat pels botons de l'app. Comprova també que el primer fotograma s'entengui sense so.

## 4. Renderitza un cop

```bash
python3 scripts/render_short.py guio.json out/slug.mp4
```

Uns 20–30 s per a un vídeo de 20 s. Després extreu 2–3 fotogrames de moments amb animació (`ffmpeg -ss <t> -i out/slug.mp4 -frames:v 1 f.jpg`) i mira'ls: és la manera de veure errors que les imatges finals no mostren (un traç que apareix abans d'hora, un compte enrere mal sincronitzat).

## 5. Lliura

Envia el vídeo i la portada amb SendUserFile i, a la resposta, deixa a punt per enganxar:

- **TikTok / Reels:** text d'1–2 línies que repeteixi el ganxo i convidi a comentar («¿Lo sabías? Escribe tu respuesta 👇»), 3–5 hashtags específics (`#japones #aprenderjapones #kanji #jlpt #japonesparaprincipiantes`), sense omplir de hashtags genèrics.
- **YouTube Shorts:** títol de menys de 60 caràcters amb la paraula clau («Cómo se escribe 水 (agua) en japonés») i el mateix text.
- Si el vídeo fa servir traços de kanji, afegeix a la descripció «Trazos: KanjiVG (CC BY-SA 3.0)»: la llicència ho demana.
- **Música:** per defecte, posa-hi música original composta amb `scripts/make_music.py` (koto i lo-fi suau, sense drets de tercers) i passa-la a `render_short.py --audio`, o afegeix-la a un vídeo ja fet amb `ffmpeg -i video.mp4 -i musica.m4a -map 0:v -map 1:a -c:v copy -c:a aac -shortest`. Canvia la `--seed` a cada vídeo perquè no sonin tots igual, i fes que la pista duri el mateix que el vídeo (`--seconds`). El perquè de cada decisió de so i com ajustar-la és a `references/musica.md`. A Instagram, si es programa amb Metricool i el compte està vinculat a una pàgina de Facebook, pots fer servir en canvi una cançó de la biblioteca (`audioConfiguration`), que ajuda més a la distribució. No hi posis mai música descarregada sense una llicència clara.

## 6. Programar a Metricool (si l'usuari ho demana)

Metricool necessita el vídeo en una adreça pública; un fitxer d'aquest espai de treball no ho és. Per tant:
- Si l'usuari té Google Drive vinculat a Metricool, puja-hi el vídeo i passa'n l'enllaç a `media`.
- Si no, deixa-li el vídeo i el text, i que el pugi ell des de l'app de Metricool, o crea la publicació amb `autoPublish: false` perquè li arribi l'avís al mòbil.
- Obté el `blogId` amb `getBrandSettings` (no el donis per sabut) i fes servir el fus horari de la marca. Instagram: `type: "REEL"`; YouTube: `type: "short"`, `madeForKids: false`, títol obligatori.
- Abans de programar, confirma amb l'usuari dia, hora i text: és contingut públic.

## Quan en demana diversos

Per a una setmana de contingut: fes una taula curta amb els vídeos (dia, format, ganxo), espera que l'usuari la validi o ajusti, i després genera'ls tots. Varia formats i temes clar/fosc perquè el perfil no sigui repetitiu, i no repeteixis cap kanji o paraula d'una setmana anterior si en tens constància.
