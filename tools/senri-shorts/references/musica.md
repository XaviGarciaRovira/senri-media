# Música per als shorts: per què sona així

`make_music.py` compon música original (sense drets de tercers). Aquestes són les decisions i d'on surten, per si cal ajustar-les.

## Què ha de fer la música en un vídeo d'aprendre japonès
- **Acompanyar, no competir.** El protagonista és el text i el japonès que surt en pantalla. Res de veu ni lletra: la música vocal i familiar distreu més quan es llegeix o s'aprèn.
- **Calmada però no somnolenta.** En un estudi, la música molt lenta (66 bpm) va alentir el processament, i la ràpida (138 bpm) no el va millorar. Per això el generador es queda entre 72 i 84 bpm: el rang del lo-fi (60–80 bpm), una mica viu perquè els vídeos són curts.
- **Constant.** Sense canvis bruscos de volum ni d'estil en 15–30 s: el vídeo ja té prou moviment.

## Llenguatge musical
- **Escala yo** (1 2 4 5 6, la pentatònica de les cançons populars japoneses) al koto: sona japonesa i alegre, sense el to trist de l'escala in.
- **Acords de 7a** (maj7, m7, 7sus4) en piano elèctric, en progressions de 4 compassos. Una d'elles és IV–V–iii–vi, la progressió més típica del pop japonès.
- **Motiu de 2 compassos** que es repeteix amb petites variacions i silencis, i que acaba a la tònica perquè la frase «tanqui».

## Producció lo-fi
- Bateria escassa: bombo a l'1 (i de vegades al 3), aro al 2 i al 4, xarleston a les corxeres amb una mica de swing. El bombo, lleugerament fora de quadrícula, perquè soni tocat.
- Bateria filtrada a uns 2 kHz; la resta «s'aparta» quan entra el bombo (sidechain), com en el lo-fi de veritat.
- Calidesa: saturació suau (tanh), vaivé de cinta molt lleu al piano, cruixit de vinil discret, reverberació de sala (convolució).

## Mescla per al mòbil
- Gairebé tothom ho escolta pels altaveus del mòbil, que no reprodueixen greus: tall per sota de 90 Hz, baix tocat al registre mig i un punt de presència a 1,5–3,5 kHz.
- **-16 LUFS i -1 dBTP**: el nivell recomanat per a vídeos de text amb música de fons. Prou fort per sonar a l'altura d'altres vídeos sense que la plataforma el baixi.
- Si algun dia el vídeo porta veu, baixa la música a -20 LUFS (`--lufs -20`) perquè la veu s'entengui.

## Ajustos ràpids
| Si sona… | Prova |
|---|---|
| massa rítmica | `--no-drums` |
| massa lenta o ràpida | `--bpm 72` … `--bpm 88` |
| igual que l'anterior | una altra `--seed` |
| massa fluixa sota el text | `--lufs -14` |
