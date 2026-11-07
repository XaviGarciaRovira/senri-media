#!/usr/bin/env node
// Busca paraules i kanji al contingut de Senri perquè els vídeos facin servir
// exactament les mateixes lectures, traduccions i traços que l'app.
//
// Ús:
//   node lookup.mjs --repo /home/claude/senri --lang es 水 先生 ありがとう
//   node lookup.mjs --repo /home/claude/senri --lang es --kanji-unit k-5
//   node lookup.mjs --repo /home/claude/senri --lang es --random-words 5
//
// Per a cada terme torna un objecte JSON:
//   kanji: { type:"kanji", k, meaning, hint, on, kun, paths, examples, word }
//          (paths = traços KanjiVG, viewBox 0 0 109 109; word = la paraula d'un sol kanji, si n'hi ha, p. ex. 山 → やま)
//   paraula: { type:"word", jp, kana, romaji, meaning, alt }
// Si un terme no és al contingut de Senri, surt amb type:"missing": no te l'inventis.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const args = process.argv.slice(2);
const opt = (name, def) => {
  const i = args.indexOf(name);
  if (i === -1) return def;
  const v = args[i + 1];
  args.splice(i, 2);
  return v;
};
const repo = opt('--repo', '/home/claude/senri');
const lang = opt('--lang', 'es');
const unit = opt('--kanji-unit', null);
const randomWords = Number(opt('--random-words', 0));

const { kanaToRomaji } = await import(pathToFileURL(join(repo, 'js/romaji.js')).href);
const vocab = JSON.parse(readFileSync(join(repo, 'data/vocab.json'), 'utf8'));
const kanji = JSON.parse(readFileSync(join(repo, 'data/kanji.json'), 'utf8'));

const words = Object.values(vocab.words);
const pick = (o) => (o && typeof o === 'object' ? o[lang] ?? o.en : o);

function asWord(w) {
  return {
    type: 'word',
    jp: w.jp,
    kana: w.r,
    romaji: kanaToRomaji(w.r),
    meaning: w[lang] ?? w.en,
    alt: Array.isArray(w.alt) ? w.alt : [],
  };
}

function asKanji(k) {
  return {
    type: 'kanji',
    k: k.k,
    meaning: k[lang] ?? k.en,
    hint: pick(k.hint) ?? '',
    on: [...new Set(k.on ?? [])],
    kun: [...new Set(k.kun ?? [])],
    paths: k.paths ?? [],
    examples: words.filter((w) => w.jp.includes(k.k)).slice(0, 4).map(asWord),
  };
}

const out = [];
if (unit) {
  const u = kanji.units.find((x) => x.id === unit);
  if (!u) { console.error(`No existeix la unitat ${unit}`); process.exit(1); }
  for (const id of u.items) out.push(asKanji(kanji.kanji[id]));
}
if (randomWords > 0) {
  const pool = [...words];
  for (let i = 0; i < randomWords && pool.length; i++) out.push(asWord(pool.splice(Math.floor(Math.random() * pool.length), 1)[0]));
}
for (const term of args) {
  const k = kanji.kanji[`j:${term}`];
  const w = words.find((x) => x.jp === term) ?? words.find((x) => x.r === term);
  // Un kanji sol pot ser també una paraula (山 = やま): torna el kanji amb la paraula a dins.
  if ([...term].length === 1 && k) { out.push({ ...asKanji(k), word: w ? asWord(w) : null }); continue; }
  if (w) { out.push(asWord(w)); continue; }
  out.push({ type: 'missing', term });
}
console.log(JSON.stringify(out, null, 2));
