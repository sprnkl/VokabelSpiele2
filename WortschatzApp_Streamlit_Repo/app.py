# app.py
# -*- coding: utf-8 -*-

"""
Wortschatz-Spiele (Klassen 5–10, E/G & Französisch 6–9)

Seiten-spezifische CSVs:
NEU: prepared_data/pages/klasseX_<e|g|französisch>/klasseX_<e|g|französisch>_pageY.csv
ALT: data/pages/klasseK/klasseK_pageY.csv

CSV-Spalten (Seitenlisten):
- classe (Zahl), page (Zahl), de, en
 (Hinweis: Für Französisch werden Spaltenköpfe wie 'fr', 'französisch', 'français', 'french'
  intern auf 'en' gemappt. Spiele bleiben unverändert.)

Spiele/Features:
- Eingabe (DE→EN/FR oder umgekehrt): tolerante Prüfung (Klammern, "to", Artikel, Varianten,
  Tippfehler = "fast richtig"), sofortige Rückmeldung mit Lösung, Fortschritt, Serie,
  Auswertung am Ende, "Nur Fehlerwörter üben".
- Multiple Choice: 4 Antworten, beide Richtungen, gleiche Auswertung wie Eingabe.
- Wörter Memory (DE↔EN/FR): Antippen oder Ziehen, Timer, Vorlesen bei Treffer,
  auf dem Handy in Runden zu 8 Paaren, Anzahl der Paare wählbar, Seed-stabil.
- Hangman: Akzente werden mit aufgedeckt, Klammer-Zusätze ausgeblendet, laufender Timer.
- Unregelmäßige Verben (nur Englisch): Wort antippen, dann passende Form antippen.
- Mehrere Seiten kombinierbar, Direktlink/QR-Code (?klasse=7e&seite=133&spiel=mc).
"""

import re
import json
import time
import unicodedata
from pathlib import Path
from datetime import datetime
import random
import hashlib
import functools
import inspect

import pandas as pd
import streamlit as st

# Seite konfigurieren (früh)
st.set_page_config(page_title="Wortschatz-Spiele (Klassen 5–10, E/G/Französisch)", page_icon="📚", layout="wide")

# ============================ UNREGELMÄSSIGE VERBEN – DIREKT IM CODE ============================
VERBS = [
    {"infinitive": "be", "pastSimple": "was/were", "pastParticiple": "been", "meaning": "sein"},
    {"infinitive": "begin", "pastSimple": "began", "pastParticiple": "begun", "meaning": "beginnen, anfangen"},
    {"infinitive": "break", "pastSimple": "broke", "pastParticiple": "broken", "meaning": "brechen, zerbrechen"},
    {"infinitive": "bring", "pastSimple": "brought", "pastParticiple": "brought", "meaning": "bringen, mitbringen"},
    {"infinitive": "buy", "pastSimple": "bought", "pastParticiple": "bought", "meaning": "kaufen"},
    {"infinitive": "catch", "pastSimple": "caught", "pastParticiple": "caught", "meaning": "fangen, erwischen"},
    {"infinitive": "come", "pastSimple": "came", "pastParticiple": "come", "meaning": "kommen"},
    {"infinitive": "cost", "pastSimple": "cost", "pastParticiple": "cost", "meaning": "kosten"},
    {"infinitive": "cut", "pastSimple": "cut", "pastParticiple": "cut", "meaning": "schneiden, mähen"},
    {"infinitive": "do", "pastSimple": "did", "pastParticiple": "done", "meaning": "tun, machen"},
    {"infinitive": "drink", "pastSimple": "drank", "pastParticiple": "drunk", "meaning": "trinken"},
    {"infinitive": "drive", "pastSimple": "drove", "pastParticiple": "driven", "meaning": "(Auto) fahren, antreiben"},
    {"infinitive": "eat", "pastSimple": "ate", "pastParticiple": "eaten", "meaning": "essen"},
    {"infinitive": "fall", "pastSimple": "fell", "pastParticiple": "fallen", "meaning": "fallen, hinfallen"},
    {"infinitive": "feel", "pastSimple": "felt", "pastParticiple": "felt", "meaning": "fühlen"},
    {"infinitive": "find", "pastSimple": "found", "pastParticiple": "found", "meaning": "finden"},
    {"infinitive": "fly", "pastSimple": "flew", "pastParticiple": "flown", "meaning": "fliegen"},
    {"infinitive": "forget", "pastSimple": "forgot", "pastParticiple": "forgotten", "meaning": "vergessen"},
    {"infinitive": "get", "pastSimple": "got", "pastParticiple": "got/gotten", "meaning": "bekommen, holen"},
    {"infinitive": "give", "pastSimple": "gave", "pastParticiple": "given", "meaning": "geben"},
    {"infinitive": "go", "pastSimple": "went", "pastParticiple": "gone", "meaning": "gehen"},
    {"infinitive": "have", "pastSimple": "had", "pastParticiple": "had", "meaning": "haben"},
    {"infinitive": "hear", "pastSimple": "heard", "pastParticiple": "heard", "meaning": "hören"},
    {"infinitive": "hurt", "pastSimple": "hurt", "pastParticiple": "hurt", "meaning": "verletzen, wehtun"},
    {"infinitive": "keep", "pastSimple": "kept", "pastParticiple": "kept", "meaning": "behalten"},
    {"infinitive": "know", "pastSimple": "knew", "pastParticiple": "known", "meaning": "wissen, kennen"},
    {"infinitive": "leave", "pastSimple": "left", "pastParticiple": "left", "meaning": "abfahren, weggehen"},
    {"infinitive": "lose", "pastSimple": "lost", "pastParticiple": "lost", "meaning": "verlieren"},
    {"infinitive": "make", "pastSimple": "made", "pastParticiple": "made", "meaning": "machen"},
    {"infinitive": "mean", "pastSimple": "meant", "pastParticiple": "meant", "meaning": "bedeuten, meinen"},
    {"infinitive": "meet", "pastSimple": "met", "pastParticiple": "met", "meaning": "treffen, kennenlernen"},
    {"infinitive": "pay", "pastSimple": "paid", "pastParticiple": "paid", "meaning": "bezahlen"},
    {"infinitive": "put", "pastSimple": "put", "pastParticiple": "put", "meaning": "setzen, legen"},
    {"infinitive": "read", "pastSimple": "read", "pastParticiple": "read", "meaning": "lesen"},
    {"infinitive": "ride", "pastSimple": "rode", "pastParticiple": "ridden", "meaning": "reiten, fahren"},
    {"infinitive": "ring", "pastSimple": "rang", "pastParticiple": "rung", "meaning": "läuten, anrufen"},
    {"infinitive": "run", "pastSimple": "ran", "pastParticiple": "run", "meaning": "rennen, laufen"},
    {"infinitive": "say", "pastSimple": "said", "pastParticiple": "said", "meaning": "sagen"},
    {"infinitive": "see", "pastSimple": "saw", "pastParticiple": "seen", "meaning": "sehen"},
    {"infinitive": "sell", "pastSimple": "sold", "pastParticiple": "sold", "meaning": "verkaufen"},
    {"infinitive": "send", "pastSimple": "sent", "pastParticiple": "sent", "meaning": "schicken"},
    {"infinitive": "sing", "pastSimple": "sang", "pastParticiple": "sung", "meaning": "singen"},
    {"infinitive": "sit", "pastSimple": "sat", "pastParticiple": "sat", "meaning": "sitzen"},
    {"infinitive": "sleep", "pastSimple": "slept", "pastParticiple": "slept", "meaning": "schlafen"},
    {"infinitive": "speak", "pastSimple": "spoke", "pastParticiple": "spoken", "meaning": "sprechen"},
    {"infinitive": "spend", "pastSimple": "spent", "pastParticiple": "spent", "meaning": "ausgeben, verbringen"},
    {"infinitive": "stand", "pastSimple": "stood", "pastParticiple": "stood", "meaning": "stehen"},
    {"infinitive": "take", "pastSimple": "took", "pastParticiple": "taken", "meaning": "nehmen"},
    {"infinitive": "teach", "pastSimple": "taught", "pastParticiple": "taught", "meaning": "unterrichten"},
    {"infinitive": "tell", "pastSimple": "told", "pastParticiple": "told", "meaning": "erzählen"},
    {"infinitive": "think", "pastSimple": "thought", "pastParticiple": "thought", "meaning": "denken"},
    {"infinitive": "throw", "pastSimple": "threw", "pastParticiple": "thrown", "meaning": "werfen"},
    {"infinitive": "understand", "pastSimple": "understood", "pastParticiple": "understood", "meaning": "verstehen"},
    {"infinitive": "wear", "pastSimple": "wore", "pastParticiple": "worn", "meaning": "tragen, anhaben"},
    {"infinitive": "win", "pastSimple": "won", "pastParticiple": "won", "meaning": "gewinnen"},
    {"infinitive": "write", "pastSimple": "wrote", "pastParticiple": "written", "meaning": "schreiben"},
]
VERB_TARGETS = [
    ("Infinitive", "infinitive"),
    ("Simple Past (2. Form des Verbs)", "pastSimple"),
    ("Past Participle (3. Form des Verbs)", "pastParticiple"),
    ("Meaning (Deutsch)", "meaning"),
]

# ============================ Utilities ============================

def normalize_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[^\w\s/-]", "", s)  # /- für "was/were"
    s = re.sub(r"\s+", " ", s)
    return s

def is_simple_word(
    word: str,
    *,
    ignore_articles: bool = True,
    ignore_abbrev: bool = True,
    min_length: int = 2,
) -> bool:
    if not isinstance(word, str):
        return False
    w = word.strip()
    if ignore_articles:
        w = re.sub(r"^(to\s+|the\s+|a\s+|an\s+)", "", w, flags=re.IGNORECASE)
    if "/" in w or " " in w or "-" in w:
        return False
    if ignore_abbrev and re.search(r"\b(sth|sb|etc|e\.g|i\.e)\b", w, flags=re.IGNORECASE):
        return False
    if "." in w:
        return False
    return len(w) >= min_length

def _filter_by_page_rows(df: pd.DataFrame, classe: int, page: int) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    cols = {c.lower(): c for c in df.columns}
    c_classe = cols.get("classe")
    c_page = cols.get("page")
    if c_classe is None or c_page is None:
        return df
    try:
        df = df.copy()
        df[c_classe] = pd.to_numeric(df[c_classe], errors="coerce").astype("Int64")
        df[c_page]  = pd.to_numeric(df[c_page],  errors="coerce").astype("Int64")
        mask = (df[c_classe] == int(classe)) & (df[c_page] == int(page))
        return df[mask].reset_index(drop=True)
    except Exception:
        return df

def fmt_ms(ms: int) -> str:
    if ms < 0:
        ms = 0
    tenths = (ms % 1000) // 100
    s = (ms // 1000) % 60
    m = (ms // 1000) // 60
    return f"{m:02d}:{s:02d}.{tenths}"

# ============================ Antwort-Prüfung (tolerant) ============================

LANG_NAMES = {"EN": "Englisch", "FR": "Französisch", "DE": "Deutsch"}
TTS_LANG = {"EN": "en-GB", "FR": "fr-FR", "DE": "de-DE"}

# Grammatik-Kürzel, die beim Prüfen ignoriert werden
_MARKERS = {
    "sb", "sth", "sbs", "sths", "etw", "jdn", "jdm", "jds", "jd",
    "adj", "adv", "pl", "sg", "inv", "loc", "fam", "v", "n", "m", "f", "mf", "fm",
}
_LEADING_WORDS = {
    "to", "the", "a", "an",
    "le", "la", "les", "un", "une", "des",
    "der", "die", "das", "ein", "eine",
}


def norm_answer(s: str, plain_umlauts: bool = False) -> str:
    """Vergleichs-Normalisierung: klein, ohne Akzente/Satzzeichen, Umlaute = ae/oe/ue
    (plain_umlauts=True: ä/ö/ü -> a/o/u, für Schüler, die die Punkte weglassen)."""
    if not isinstance(s, str):
        return ""
    s = s.strip().lower()
    s = s.replace("’", "'").replace("\xad", "")  # weiches Trennzeichen entfernen
    s = re.sub(r"\b(l|d|j|qu|n|s|c|m|t)'\s*", r"\1 ", s)  # l'école -> l école
    if plain_umlauts:
        s = s.replace("ä", "a").replace("ö", "o").replace("ü", "u")
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("œ", "oe"), ("æ", "ae")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _strip_markers(words: list[str]) -> list[str]:
    return [w for w in words if w not in _MARKERS]


def _strip_leading(words: list[str]) -> list[str]:
    while len(words) > 1 and (words[0] in _LEADING_WORDS or words[0] == "l"):
        words = words[1:]
    return words


_ENDINGS = {"e", "r", "s", "n", "m", "in", "en", "er", "es", "em", "innen"}
_ENDING_TOKEN = re.compile(r"^([^\W\d_][\w-]*)((?:/[a-zäöüß]{1,5})+)([.,;:!?]*)$")


def _expand_endings(text: str, limit: int = 64) -> set:
    """Deutsche Kurzschreibweisen auflösen: "ein/e" -> "ein", "eine"; "andere/r/s" -> andere/anderer/anderes."""
    if "/" not in text:
        return set()
    results = [""]
    changed = False
    for tok in text.split():
        m = _ENDING_TOKEN.match(tok)
        endings = m.group(2).split("/")[1:] if m else []
        if m and endings and all(e in _ENDINGS for e in endings):
            opts = [m.group(1) + m.group(3)] + [m.group(1) + e + m.group(3) for e in endings]
            changed = True
        else:
            opts = [tok]
        results = [(r + " " + o).strip() for r in results for o in opts][:limit]
    return set(results) if changed else set()


@functools.lru_cache(maxsize=20000)
def answer_variants(solution: str) -> frozenset:
    """Alle Schreibweisen, die als richtig gelten.

    Beispiele: "(to) send" -> {"to send", "send"};
    "lie (lay, lain)" -> {"lie lay lain", "lie"};
    "grandson / granddaughter" -> {"grandson", "granddaughter", ...}
    """
    if not isinstance(solution, str):
        return frozenset()
    raw = solution.strip()
    bases = {
        raw,
        re.sub(r"\([^)]*\)", " ", raw),            # Klammerinhalt weg
        raw.replace("(", "").replace(")", ""),      # Klammern auflösen
    }
    for b in list(bases):                           # "ein/e andere/r/s" -> "eine anderer", ...
        bases.update(_expand_endings(b))
    parts = set()
    for b in bases:
        parts.add(b)
        for p in re.split(r"[/;,]", b):
            parts.add(p)
        for p in re.split(r"[/;]", b):              # "der Schüler, die Schülerin; ..." -> erster Teil komplett
            parts.add(p)
    out = set()
    for p in parts:
        for plain in (False, True):
            n = norm_answer(p, plain_umlauts=plain)
            if not n:
                continue
            words = n.split()
            for w in (words, _strip_markers(words), _strip_leading(words), _strip_leading(_strip_markers(words))):
                v = " ".join(w).strip()
                if v:
                    out.add(v)
    # Einzelbuchstaben (z. B. aus "f/m") nicht als Antwort akzeptieren
    full = norm_answer(raw)
    return frozenset(v for v in out if len(v) >= 2 or v == full)


def _levenshtein(a: str, b: str) -> int:
    """Editierabstand; zwei vertauschte Nachbarbuchstaben zählen als 1 Fehler."""
    if a == b:
        return 0
    la, lb = len(a), len(b)
    d = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        d[i][0] = i
    for j in range(lb + 1):
        d[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[la][lb]


def _core(v: str) -> str:
    """Wort ohne Artikel/"to"/Grammatik-Kürzel – Grundlage für die Tippfehler-Toleranz."""
    return " ".join(_strip_leading(_strip_markers(v.split())))


def _user_forms(user: str) -> set:
    forms = set()
    for plain in (False, True):
        u = norm_answer(user, plain_umlauts=plain)
        if u:
            forms.add(u)
            forms.add(_core(u))
    return {f for f in forms if f}


def _allowed_typos(n: int, lenient: bool) -> int:
    if lenient:  # Deutsch: großzügig, aber kurze Wörter exakt (Hand ≠ Hund)
        return 0 if n < 5 else (1 if n < 9 else (2 if n < 13 else 3))
    return 0 if n < 4 else (1 if n < 9 else 2)


def _best_distance(forms, variants):
    best = None
    for f in forms:
        cf = _core(f)
        for v in variants:
            d = _levenshtein(cf, _core(v))
            if best is None or d < best:
                best = d
    return best


def check_answer(user: str, solution: str, lenient: bool = False, others=()) -> str:
    """'correct' | 'almost' (kleiner Tippfehler) | 'wrong'

    lenient=True (für deutsche Antworten): Rechtschreibfehler zählen als richtig,
    solange das Wort noch erkennbar ist – es geht ja um die Fremdsprache.
    others: Lösungen der anderen Wörter derselben Seite. Ein Tippfehler zählt nicht,
    wenn das Getippte eigentlich ein anderes Wort der Seite ist (Traum ≠ Baum).
    """
    forms = _user_forms(user)
    if not forms:
        return "wrong"
    variants = answer_variants(solution)
    if forms & variants:
        return "correct"
    # Mehrere Bedeutungen auf einmal, z. B. "schwer, schwierig"
    parts = [p for p in re.split(r"[,;/]", user) if p.strip()]
    if len(parts) > 1 and all(_user_forms(p) & variants for p in parts):
        return "correct"

    # Tippfehler-Toleranz
    match_dist = None
    for f in forms:
        cf = _core(f)
        for v in variants:
            cv = _core(v)
            if len(cv) < 4:
                continue
            d = _levenshtein(cf, cv)
            if d <= _allowed_typos(len(cv), lenient) and (match_dist is None or d < match_dist):
                match_dist = d
    if match_dist is None:
        return "wrong"

    # Ist das Getippte eigentlich ein anderes Wort derselben Seite?
    own = norm_answer(solution)
    for o in others:
        if not isinstance(o, str) or norm_answer(o) == own:
            continue
        ov = answer_variants(o)
        if forms & ov:
            return "wrong"
        d_o = _best_distance(forms, ov)
        if d_o is not None and d_o < match_dist:
            return "wrong"
    return "correct" if lenient else "almost"


def main_form(solution: str) -> str:
    """Kernform eines Eintrags (für Hangman und Vorlesen), Akzente bleiben erhalten.
    "(to) send" -> "send"; "le développement (m)" -> "le développement";
    "scarf, pl scarves" -> "scarf"; "grandson / granddaughter" -> "grandson"
    """
    if not isinstance(solution, str):
        return ""
    s = re.sub(r"\([^)]*\)", " ", solution)
    s = re.sub(r",\s*pl\.?\s+[^,;/]*", " ", s)  # ", pl scarves" / ", pl crime series" weg
    s = re.split(r"\s/\s|;", s)[0]
    if "/" in s and " " not in s.strip():
        s = s.split("/")[0]
    s = re.sub(r"\b(adj|adv|sb|sth|etw|jdn|jdm)\.?(?=\s|$)", " ", s)
    s = re.sub(r"(?<!\S)(f/m|m/f|f|m|pl|v|n)\.?$", " ", s.strip())
    s = re.sub(r"\s+", " ", s).strip(" ,;")
    return s or solution.strip()


# ============================ Kleine HTML-Bausteine ============================

# Volle Breite: neuere Streamlit-Versionen nutzen width="stretch",
# ältere use_container_width=True (wird künftig entfernt) – so läuft die App mit beiden.
try:
    _NEW_WIDTH_API = "width" in inspect.signature(st.button).parameters
except (TypeError, ValueError):
    _NEW_WIDTH_API = False
WIDE = {"width": "stretch"} if _NEW_WIDTH_API else {"use_container_width": True}


def js_json(obj) -> str:
    """JSON sicher in <script> einbetten (auch wenn ein Wort "</script>" enthält)."""
    return (json.dumps(obj, ensure_ascii=False)
            .replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def embed_html(html: str, height: int):
    """HTML mit JavaScript einbetten.
    Neuere Streamlit-Versionen: st.iframe; ältere: st.components.v1.html
    (wird in Zukunft entfernt – so läuft die App mit beiden)."""
    if hasattr(st, "iframe"):
        st.iframe(html, height=max(int(height), 1))
    else:
        st.components.v1.html(html, height=height, scrolling=True)


AUTOSIZE_JS = """
<script>
// Höhe des eingebetteten Elements an den Inhalt anpassen (kein doppeltes Scrollen)
function __fit() {
  try {
    const h = Math.ceil(document.documentElement.getBoundingClientRect().height);
    if (window.frameElement && h > 0) window.frameElement.style.height = h + 'px';
  } catch (e) {}
}
window.addEventListener('load', __fit); window.addEventListener('resize', __fit);
setTimeout(__fit, 50); setTimeout(__fit, 400);
</script>"""


VOICE_JS = """
<script>
// Vorlesen: immer dieselbe, möglichst natürliche Frauenstimme nehmen.
// (Ohne feste Wahl nimmt der Browser beim ersten Klick seine Standardstimme und danach
// oft die erste Stimme der Liste – unter Windows z. B. eine männliche Roboterstimme.)
const __MALE = /\\bmale\\b|david|mark\\b|george|guy\\b|ryan|thomas|daniel|paul\\b|henri|claude|alex\\b|fred\\b|rishi|oliver|arthur|james|william|christopher|eric\\b|roger|andrew|brian|liam|remy|rémy|jerome|jérôme|gerard|antoine|nicolas|mathieu|alain/i;
const __FEMALE = /female|zira|hazel|susan|libby|sonia|maisie|aria\\b|jenny|michelle|emma|ava\\b|samantha|karen|moira|tessa|serena|kate\\b|fiona|martha|victoria|allison|julie|hortense|denise|eloise|vivienne|brigitte|amelie|amélie|audrey|aurelie|aurélie|marie|celine|céline|virginie|sylvie|charlotte|ariane|google fran/i;
const __voiceCache = {};
function __pickVoice(lang) {
  if (__voiceCache[lang]) return __voiceCache[lang];
  let vs = [];
  try { vs = speechSynthesis.getVoices() || []; } catch (e) {}
  const want = lang.toLowerCase(), pre = want.slice(0, 2);
  let best = null, bestScore = -1e9;
  vs.forEach((v, i) => {
    const vl = (v.lang || '').toLowerCase().replace('_', '-');
    if (!vl.startsWith(pre)) return;
    const n = v.name || '';
    let sc = 0;
    if (vl === want) sc += 5;
    if (__FEMALE.test(n)) sc += 20;
    if (__MALE.test(n)) sc -= 50;
    if (/natural|online|neural|premium|enhanced/i.test(n)) sc += 10;
    if (/google/i.test(n)) sc += 3;
    sc -= i * 0.001;  // bei Gleichstand: Reihenfolge des Browsers
    if (sc > bestScore) { bestScore = sc; best = v; }
  });
  if (best) __voiceCache[lang] = best;
  return best;
}
function __sayNow(txt, lang) {
  const u = new SpeechSynthesisUtterance(txt); u.lang = lang; u.rate = 0.9;
  const v = __pickVoice(lang); if (v) u.voice = v;
  speechSynthesis.cancel(); speechSynthesis.speak(u);
}
function __say(txt, lang) {
  if (!txt || !('speechSynthesis' in window)) return false;
  // Sofort sprechen (Tablets erlauben Ton nur direkt beim Antippen). Ist die Stimmenliste
  // noch nicht geladen, nimmt der Browser seine Standardstimme für die Sprache.
  __sayNow(txt, lang);
  return true;
}
try { speechSynthesis.getVoices(); } catch (e) {}
</script>"""


def status_bar(timer: dict, nonce: str = "", progress=None, chips=()):
    """Kompakte Statusleiste: Fortschritt, Info-Chips und laufende Stoppuhr in einer Zeile.

    progress: None oder (text, Anteil 0..1); chips: Liste von (Text, Stil) mit Stil in
    {"orange", "violet", "green", "red"}.
    """
    now_ms = int(time.time() * 1000)
    cur = timer["elapsed_ms"] + (now_ms - timer["started_ms"] if timer["running"] else 0)
    running = "true" if timer["running"] else "false"
    prog_html = ""
    if progress is not None:
        text, frac = progress
        pct = max(0.0, min(1.0, float(frac))) * 100
        prog_html = (f'<div class="prog"><div class="ptxt">{text}</div>'
                     f'<div class="pbar"><div class="pfill" style="width:{pct:.1f}%"></div></div></div>')
    chip_html = "".join(f'<span class="chip {style}">{html_escape(t)}</span>' for t, style in chips)
    embed_html(f"""
<style>
body {{ margin:0; font-family:'Source Sans Pro','Segoe UI',Arial,sans-serif; background:transparent; }}
.bar {{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; padding:2px 1px 4px 1px; }}
.prog {{ flex: 1 1 220px; min-width: 180px; }}
.ptxt {{ font-size:14px; color:#1f2340; margin-bottom:5px; }}
.ptxt b {{ color:#5e35b1; }}
.pbar {{ height:10px; background:#e3e8f4; border-radius:999px; overflow:hidden; }}
.pfill {{ height:100%; background:linear-gradient(90deg,#1e88e5,#5e35b1); border-radius:999px; transition:width .3s; }}
.chip {{ font-weight:700; font-size:15px; border-radius:999px; padding:6px 12px; white-space:nowrap; }}
.orange {{ background:#fff3e0; color:#e65100; }}
.violet {{ background:#ede7f6; color:#4527a0; }}
.green {{ background:#e8f5e9; color:#1b5e20; }}
.red {{ background:#ffebee; color:#b71c1c; }}
.timer {{ background:#e3f2fd; color:#1565c0; }}
</style>
<div class="bar">{prog_html}{chip_html}<span class="chip timer" id="t">⏱ 00:00</span></div>
<script>
// {nonce}
const base = {cur}; const running = {running}; const t0 = Date.now();
function f(ms) {{ const s = Math.floor(ms/1000); return String(Math.floor(s/60)).padStart(2,'0') + ':' + String(s%60).padStart(2,'0'); }}
function upd() {{ document.getElementById('t').textContent = '⏱ ' + f(base + (running ? Date.now() - t0 : 0)); }}
upd(); if (running) setInterval(upd, 250);
</script>{AUTOSIZE_JS}""", height=48)


def keyed_container(key: str, border: bool = False):
    """Container mit festem Namen (für gezieltes Styling); ältere Streamlit-Versionen ohne Namen."""
    try:
        return st.container(key=key, border=border)
    except TypeError:
        return st.container(border=border)


def speak_button(text: str, lang: str, label: str = "🔊 Anhören"):
    """Button, der das Wort vom Browser vorlesen lässt."""
    if not text:
        return
    t = js_json(main_form(text))
    l = js_json(TTS_LANG.get(lang, "en-GB"))
    embed_html(f"""
<button id="b" style="font-family:'Source Sans Pro',Arial,sans-serif;font-size:15px;padding:6px 14px;
  border:2px solid #1e88e5;background:white;color:#1565c0;border-radius:10px;cursor:pointer;">{label}</button>
{VOICE_JS}
<script>
const txt = {t}; const lang = {l};
document.getElementById('b').addEventListener('click', () => {{
  try {{
    if (!__say(txt, lang)) document.getElementById('b').textContent = '🔇 nicht verfügbar';
  }} catch (e) {{ document.getElementById('b').textContent = '🔇 nicht verfügbar'; }}
}});
</script>""", height=46)


def focus_input(aria_label: str, nonce: str):
    """Setzt den Cursor ins Antwortfeld (damit man direkt weitertippen kann)."""
    embed_html(f"""<script>
// {nonce}
setTimeout(() => {{
  try {{
    const el = window.parent.document.querySelector('input[aria-label="{aria_label}"]');
    if (el) el.focus({{ preventScroll: true }});
  }} catch (e) {{}}
}}, 200);
</script>""", height=0)


def vocab_card(text: str, sub: str = ""):
    st.markdown(
        f'<div class="vocab-card"><div class="vocab-sub">{html_escape(sub)}</div>'
        f'<div class="vocab-word">{html_escape(text)}</div></div>',
        unsafe_allow_html=True,
    )


def html_escape(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


# ============================ Hangman Art ============================

HANGMAN_PICS = [
    " +---+\n     |\n     |\n     |\n   ===",
    " +---+\n O   |\n     |\n     |\n   ===",
    " +---+\n O   |\n |   |\n     |\n   ===",
    " +---+\n O   |\n/|   |\n     |\n   ===",
    " +---+\n O   |\n/|\\  |\n     |\n   ===",
    " +---+\n O   |\n/|\\  |\n/    |\n   ===",
    " +---+\n O   |\n/|\\  |\n/ \\  |\n   ===",
]

def hangman_svg(fails: int, lost: bool = False, won: bool = False) -> str:
    """Gezeichneter Galgen; Teile erscheinen mit jedem Fehler (max. 6)."""
    fig = "#c62828" if lost else ("#2e7d32" if won else "#5e35b1")
    parts = [
        '<circle cx="128" cy="62" r="16" />',                 # Kopf
        '<line x1="128" y1="78" x2="128" y2="128" />',        # Körper
        '<line x1="128" y1="90" x2="106" y2="112" />',        # linker Arm
        '<line x1="128" y1="90" x2="150" y2="112" />',        # rechter Arm
        '<line x1="128" y1="128" x2="110" y2="160" />',       # linkes Bein
        '<line x1="128" y1="128" x2="146" y2="160" />',       # rechtes Bein
    ]
    body = "".join(parts[:max(0, min(fails, 6))])
    face = ""
    if won:
        face = '<path d="M121 66 q7 6 14 0" stroke-width="2.5" />'
    elif lost:
        face = ('<line x1="121" y1="56" x2="125" y2="60" stroke-width="2.5" /><line x1="125" y1="56" x2="121" y2="60" stroke-width="2.5" />'
                '<line x1="131" y1="56" x2="135" y2="60" stroke-width="2.5" /><line x1="135" y1="56" x2="131" y2="60" stroke-width="2.5" />')
    return f"""<div class="hang-svg"><svg viewBox="0 0 200 190" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Galgen, {fails} von 6 Fehlern">
  <g stroke="#8d6e63" stroke-width="6" stroke-linecap="round" fill="none">
    <line x1="20" y1="180" x2="120" y2="180" /><line x1="50" y1="180" x2="50" y2="14" />
    <line x1="48" y1="14" x2="132" y2="14" /><line x1="50" y1="44" x2="80" y2="14" />
  </g>
  <line x1="128" y1="14" x2="128" y2="46" stroke="#a1887f" stroke-width="3" />
  <g stroke="{fig}" stroke-width="5" stroke-linecap="round" fill="none">{body}{face if fails >= 1 else ''}</g>
</svg></div>"""


# ============================ CSV-Erkennung & Laden ============================

@st.cache_data(show_spinner=False)
def get_vocab_file_info(base_dir: Path) -> pd.DataFrame:
    """
    Liefert eine Tabelle mit allen seiten-spezifischen CSVs.
    Erkennt E/G sowie 'französisch'/'franzoesisch' als Kurs.
    Filtert Französisch auf Klassen 6–9.
    """
    rows = []

    PAGE_REGEX = re.compile(r"page(\d+)", re.IGNORECASE)
    KLASSE_REGEX = re.compile(r"klasse(\d+)_?(e|g|französisch|franzoesisch)?$", re.IGNORECASE)

    # Neues Schema
    new_root = base_dir / "prepared_data" / "pages"
    if new_root.exists():
        for p in new_root.rglob("*.csv"):
            folder = p.parent.name.lower()
            klasse_match = KLASSE_REGEX.match(folder)
            page_match = PAGE_REGEX.search(p.stem)
            if klasse_match and page_match:
                try:
                    num = int(klasse_match.group(1))
                    course_raw = (klasse_match.group(2) or "").lower()

                    if course_raw in ["französisch", "franzoesisch"]:
                        course = "französisch"
                    elif course_raw in ["e", "g"]:
                        course = course_raw
                    else:
                        course = ""

                    page = int(page_match.group(1))

                    if course == "französisch" and num not in (6, 7, 8, 9):
                        continue

                    course_label_map = {"e": "E-Kurs", "g": "G-Kurs", "französisch": "Französisch", "": ""}
                    course_label = course_label_map.get(course, "")
                    label = f"Klasse {num} {course_label}".strip()

                    rows.append({"classe": num, "course": course, "page": page, "path": p, "label": label})
                except Exception:
                    continue

    # Altes Schema
    old_root = base_dir / "data" / "pages"
    if old_root.exists():
        for p in old_root.rglob("*.csv"):
            folder = p.parent.name.lower()
            m_old = re.match(r"klasse(\d+)$", folder, re.IGNORECASE)
            page_match = PAGE_REGEX.search(p.stem)
            if m_old and page_match:
                try:
                    num = int(m_old.group(1))
                    page = int(page_match.group(1))
                    label = f"Klasse {num}"
                    rows.append({"classe": num, "course": "", "page": page, "path": p, "label": label})
                except Exception:
                    continue

    if not rows:
        return pd.DataFrame(columns=["classe", "course", "page", "path", "label"])

    df = pd.DataFrame(rows)

    mask_fr = (df["course"] == "französisch")
    df = df[~mask_fr | df["classe"].isin([6, 7, 8, 9])].copy()

    df["_k"] = df["classe"].astype(int)
    order_map = {"e": 0, "g": 1, "französisch": 2, "": 3}
    df["_c"] = df["course"].map(order_map).fillna(3).astype(int)
    df["_p"] = df["page"].astype(int)

    df = df.sort_values(["_k", "_c", "_p"]).drop(columns=["_k", "_c", "_p"]).reset_index(drop=True)
    return df

@st.cache_data(show_spinner=False)
def load_and_preprocess_df(path: Path) -> pd.DataFrame:
    """CSV laden und auf Schema ['classe','page','de','en'] normalisieren.
    Versucht explizite Trennzeichen und Codierung für robuste Ladung."""
    
    # 1. Versuch: Automatische Erkennung mit UTF-8 (der beste Allrounder)
    try:
        df = pd.read_csv(path, sep=None, engine="python", encoding='utf-8')
    except Exception:
        # 2. Versuch: Semikolon (häufig in DE/FR) mit UTF-8
        try:
            df = pd.read_csv(path, sep=';', engine='python', encoding='utf-8')
        except Exception:
            # 3. Versuch: Komma (häufig in EN/US) mit UTF-8
            try:
                df = pd.read_csv(path, sep=',', engine='python', encoding='utf-8')
            except Exception as e:
                # 4. Fallback: Codierung unbekannt (ISO-8859-1 oder Windows-1252)
                try:
                    df = pd.read_csv(path, sep=None, engine='python', encoding='iso-8859-1')
                except Exception as e:
                    st.warning(f"CSV-Fehler {path.name}: Ladefehler, möglicherweise falsches Trennzeichen oder unbekannte Codierung: {e}")
                    return pd.DataFrame()

    col_map = {}
    for c in df.columns:
        lc = str(c).strip().lower()
        if lc in {"klasse", "class", "classe"}:
            col_map[c] = "classe"
        elif lc in {"seite", "page", "pg"}:
            col_map[c] = "page"
        elif lc in {"de", "german", "deutsch", "wort", "vokabel", "vokabel_de"}:
            col_map[c] = "de"
        elif lc in {
            "en", "englisch", "english", "translation", "vokabel_en",
            "fr", "französisch", "français", "francais", "french", "franzoesisch"
        }:
            col_map[c] = "en"

    df = df.rename(columns=col_map)
    for req in ["classe", "page", "de", "en"]:
        if req not in df.columns:
            df[req] = None

    df = df[["classe", "page", "de", "en"]].copy()
    # Text säubern; leere Felder (je nach pandas-Version NaN oder "nan") erkennen
    def _clean(x):
        if not isinstance(x, str):
            return ""
        x = x.strip()
        return "" if x.lower() in ("nan", "none", "null") else x
    df["de"] = df["de"].map(_clean)
    df["en"] = df["en"].map(_clean)
    # Zeilen ohne Deutsch ODER ohne Fremdsprache weglassen (z. B. Platzhalter "ChatGPT fragen")
    df = df[(df["de"] != "") & (df["en"] != "")].reset_index(drop=True)

    for k in ["classe", "page"]:
        try:
            df[k] = pd.to_numeric(df[k], errors="coerce")
        except Exception:
            pass

    return df

# ============================ Hash/Subset Utils ============================

def _hash_dict_list(items, keys) -> str:
    m = hashlib.sha256()
    for it in items:
        vals = [str(it.get(k, "")) for k in keys]
        m.update(("||".join(vals)).encode("utf-8"))
    return m.hexdigest()

def _sample_subset(items, mode, k, seed_val, state_key, hash_keys):
    """
    items: Liste von dicts
    mode: 'all' oder 'k'
    k: Anzahl bei mode 'k'
    seed_val: Seed (String) oder ''
    state_key: Key in session_state
    hash_keys: Keys für Hash-Stabilität
    """
    base_hash = _hash_dict_list(items, keys=hash_keys) if isinstance(hash_keys, list) else _hash_dict_list(items, hash_keys)
    st_state = st.session_state.get(state_key)

    need_new = (
        st_state is None or
        st_state.get("base_hash") != base_hash or
        st_state.get("mode") != mode or
        (mode == "k" and st_state.get("k") != int(k))
    )

    if not need_new:
        return st_state["subset"]

    if mode == "all" or int(k) >= len(items) or int(k) <= 1:
        # k<=1 als Robustheit => gesamte Seite
        subset = list(items)
    else:
        order = list(range(len(items)))
        rnd = random.Random(seed_val) if seed_val else random.Random()
        rnd.shuffle(order)
        subset = [items[i] for i in order[:max(2, int(k))]]  # mindestens 2 Paare

    st.session_state[state_key] = {
        "base_hash": base_hash,
        "mode": mode,
        "k": int(k),
        "subset": subset,
    }
    return subset

# ============================ Gemeinsame Übungs-Logik (Eingabe + Multiple Choice) ============================

RESULT_LABELS = {
    "correct": "✅ Richtig",
    "almost": "🟡 Fast richtig",
    "wrong": "❌ Falsch",
    "skipped": "⏭️ Übersprungen",
}


def _vocab_items(df_view: pd.DataFrame):
    return [
        {"de": r["de"], "en": r["en"]}
        for r in df_view.to_dict("records")
        if isinstance(r["de"], str) and isinstance(r["en"], str) and r["de"] and r["en"]
    ]


def _new_practice_state(items, base_hash, round_label="Alle Wörter"):
    order = list(range(len(items)))
    random.Random().shuffle(order)
    return {
        "base_hash": base_hash,
        "items": list(items),
        "order": order,
        "index": 0,
        "counts": {"correct": 0, "almost": 0, "wrong": 0, "skipped": 0},
        "streak": 0,
        "best_streak": 0,
        "history": [],  # {item, user, result}
        "last": None,
        "timer": {"running": True, "started_ms": int(time.time() * 1000), "elapsed_ms": 0},
        "round_label": round_label,
        "celebrated": False,
        # nur Multiple Choice
        "options": None,
        "answered": None,
    }


def _get_practice_state(state_key, items):
    base_hash = _hash_dict_list(items, ["de", "en"])
    s = st.session_state.get(state_key)
    if s is None or s.get("base_hash") != base_hash or "counts" not in s:
        s = _new_practice_state(items, base_hash)
        st.session_state[state_key] = s
    return s


def _register_result(s, item, user, result):
    s["counts"][result] += 1
    if result == "correct":
        s["streak"] += 1
        s["best_streak"] = max(s["best_streak"], s["streak"])
        if s["streak"] in (5, 10, 15, 20, 30, 50):
            st.toast(f"🔥 {s['streak']} richtig hintereinander!")
    elif result != "almost":
        s["streak"] = 0
    s["history"].append({"item": item, "user": user, "result": result})


def _stop_timer(t):
    if t["running"]:
        t["elapsed_ms"] = t["elapsed_ms"] + int(time.time() * 1000) - t["started_ms"]
        t["running"] = False


def _status_row(s):
    n = len(s["order"])
    done = min(s["index"], n)
    status_bar(
        s["timer"], nonce=f"{s['index']}",
        progress=(f"<b>{html_escape(s['round_label'])}</b> · Wort {min(done + 1, n)} von {n}", done / n if n else 0),
        chips=[(f"🔥 Serie: {s['streak']}", "orange"), (f"✅ {s['counts']['correct']}", "green")],
    )


def _history_df(s, q_field, a_field, q_name, a_name):
    return pd.DataFrame([
        {
            q_name: h["item"][q_field],
            "Deine Antwort": h["user"],
            f"Lösung ({a_name})": h["item"][a_field],
            "Ergebnis": RESULT_LABELS[h["result"]],
        }
        for h in s["history"]
    ])


def _round_summary(s, state_key, q_field, a_field, q_name, a_name):
    _stop_timer(s["timer"])
    c = s["counts"]
    n = len(s["order"])
    pct = round(100 * c["correct"] / n) if n else 0
    if pct >= 90:
        msg = "Hervorragend! 🌟"
    elif pct >= 70:
        msg = "Sehr gut gemacht! 💪"
    elif pct >= 50:
        msg = "Gut! Übe die Fehlerwörter noch einmal. 🙂"
    else:
        msg = "Weiter üben – mit den Fehlerwörtern wird's besser! 🚀"
    st.markdown(
        f'<div class="summary-card"><div class="summary-big">{c["correct"]} von {n} richtig ({pct} %)</div>'
        f'<div>{msg}</div>'
        f'<div class="summary-small">🟡 fast richtig: {c["almost"]} · ❌ falsch: {c["wrong"]} · ⏭️ übersprungen: {c["skipped"]}'
        f' · 🔥 beste Serie: {s["best_streak"]} · ⏱ Zeit: {fmt_ms(s["timer"]["elapsed_ms"])[:5]}</div></div>',
        unsafe_allow_html=True,
    )
    if pct >= 80 and not s["celebrated"]:
        st.balloons()
        s["celebrated"] = True

    to_repeat = [h["item"] for h in s["history"] if h["result"] != "correct"]
    # doppelte entfernen, Reihenfolge behalten
    seen, uniq = set(), []
    for it in to_repeat:
        k = (it["de"], it["en"])
        if k not in seen:
            seen.add(k)
            uniq.append(it)

    b1, b2 = st.columns(2)
    with b1:
        if uniq and st.button(f"🔁 Nur Fehlerwörter üben ({len(uniq)})", key=f"{state_key}_repeat",
                              type="primary", **WIDE):
            st.session_state[state_key] = _new_practice_state(uniq, s["base_hash"], "Fehlerwörter")
            st.rerun()
    with b2:
        if st.button("🔄 Alle Wörter nochmal", key=f"{state_key}_restart", **WIDE):
            st.session_state.pop(state_key, None)
            st.rerun()

    if s["history"]:
        st.markdown("##### 📋 Deine Antworten")
        st.dataframe(_history_df(s, q_field, a_field, q_name, a_name), **WIDE, hide_index=True)


def _feedback_banner(last, a_name, lang, foreign_field):
    if not last:
        return
    item, res, user = last["item"], last["result"], last["user"]
    sol = html_escape(item[last["a_field"]])
    q = html_escape(item[last["q_field"]])
    if res == "correct":
        note = ""
        if user and last["a_field"] == "de" and not (_user_forms(user) & answer_variants(item[last["a_field"]])) \
                and not all(_user_forms(p) & answer_variants(item[last["a_field"]])
                            for p in re.split(r"[,;/]", user) if p.strip()):
            note = '<br><span class="fb-small">Kleine Rechtschreibfehler im Deutschen sind okay – so schreibt man es richtig.</span>'
        st.markdown(f'<div class="fb fb-ok">✅ Richtig! <b>{q}</b> = <b>{sol}</b>{note}</div>', unsafe_allow_html=True)
    elif res == "almost":
        st.markdown(
            f'<div class="fb fb-almost">🟡 Fast richtig! Achte auf die Schreibweise: <b>{q}</b> = <b>{sol}</b>'
            f'<br><span class="fb-small">Du hast geschrieben: {html_escape(user)}</span></div>',
            unsafe_allow_html=True)
    elif res == "skipped":
        st.markdown(f'<div class="fb fb-wrong">⏭️ Übersprungen. <b>{q}</b> = <b>{sol}</b></div>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="fb fb-wrong">❌ Leider falsch. <b>{q}</b> = <b>{sol}</b>'
            f'<br><span class="fb-small">Du hast geschrieben: {html_escape(user) or "–"}</span></div>',
            unsafe_allow_html=True)
    if res != "correct":
        speak_button(item[foreign_field], lang, label=f"🔊 {LANG_NAMES.get(lang, '')} anhören")


def _direction_fields(direction):
    # direction: "de2x" (Deutsch -> Fremdsprache) oder "x2de"
    return ("de", "en") if direction == "de2x" else ("en", "de")


# ---------- Eingabe ----------
def game_input(df_view: pd.DataFrame, classe: str, page, lang: str = "EN", direction: str = "de2x"):
    items = _vocab_items(df_view)
    if not items:
        st.info("Keine Vokabeln vorhanden.")
        return

    q_field, a_field = _direction_fields(direction)
    foreign = LANG_NAMES.get(lang, "Englisch")
    q_name, a_name = ("Deutsch", foreign) if direction == "de2x" else (foreign, "Deutsch")

    state_key = f"input_state_{classe}_{page}_{direction}"
    s = _get_practice_state(state_key, items)

    _status_row(s)

    i = s["index"]
    if i >= len(s["order"]):
        _feedback_banner(s["last"], a_name, lang, "en")
        _round_summary(s, state_key, q_field, a_field, q_name, a_name)
        return

    _feedback_banner(s["last"], a_name, lang, "en")

    item = s["items"][s["order"][i]]
    vocab_card(item[q_field], sub=f"{q_name} → {a_name}")
    if q_field == "en":
        speak_button(item["en"], lang, label=f"🔊 {foreign} anhören")

    input_label = f"Deine Antwort auf {a_name}"
    with keyed_container("answer_box", border=True):
        with st.form(key=f"input_form_{state_key}_{i}", clear_on_submit=True, border=False):
            user = st.text_input(input_label, key=f"user_{state_key}_{i}", placeholder="Hier tippen und Enter drücken …")
            # Enter löst den ersten Button aus (= Prüfen)
            b1, b2, b3 = st.columns([1.2, 1, 1])
            with b1:
                submitted = st.form_submit_button("✔ Prüfen", type="primary", key=f"{state_key}_check_{i}", **WIDE)
            with b2:
                skipped = st.form_submit_button("⏭️ Überspringen", key=f"{state_key}_skip_{i}", **WIDE)
            with b3:
                show_sol = st.form_submit_button("💡 Lösung zeigen", key=f"{state_key}_showsol_{i}", **WIDE)
    if s["history"]:  # erst nach der ersten Antwort automatisch ins Feld (sonst springt die Seite)
        focus_input(input_label, nonce=f"{state_key}_{i}")

    if skipped:
        _register_result(s, item, "", "skipped")
        s["last"] = {"item": item, "user": "", "result": "skipped", "q_field": q_field, "a_field": a_field}
        s["index"] += 1
        if s["index"] >= len(s["order"]):
            _stop_timer(s["timer"])
        st.rerun()
    if show_sol:
        st.info(f"Lösung: {item[q_field]} — {item[a_field]}")
        submitted = False

    if submitted:
        if not user.strip():
            st.warning("Bitte gib zuerst eine Antwort ein (oder klicke auf „Überspringen“).")
        else:
            others = [it[a_field] for it in items if it[a_field] != item[a_field]]
            res = check_answer(user, item[a_field], lenient=(a_field == "de"), others=others)
            _register_result(s, item, user, res)
            s["last"] = {"item": item, "user": user, "result": res, "q_field": q_field, "a_field": a_field}
            s["index"] += 1
            if s["index"] >= len(s["order"]):
                _stop_timer(s["timer"])
            st.rerun()

    if s["history"]:
        with st.expander(f"📋 Bisherige Antworten ({len(s['history'])})"):
            st.dataframe(_history_df(s, q_field, a_field, q_name, a_name).iloc[::-1],
                         **WIDE, hide_index=True)


# ---------- Multiple Choice ----------
def game_multiple_choice(df_view: pd.DataFrame, classe: str, page, lang: str = "EN", direction: str = "de2x"):
    items = _vocab_items(df_view)
    if len(items) < 2:
        st.info("Für Multiple Choice werden mindestens 2 Vokabeln benötigt.")
        return

    q_field, a_field = _direction_fields(direction)
    foreign = LANG_NAMES.get(lang, "Englisch")
    q_name, a_name = ("Deutsch", foreign) if direction == "de2x" else (foreign, "Deutsch")

    state_key = f"mc_state_{classe}_{page}_{direction}"
    s = _get_practice_state(state_key, items)

    _status_row(s)

    i = s["index"]
    if i >= len(s["order"]):
        _round_summary(s, state_key, q_field, a_field, q_name, a_name)
        return

    item = s["items"][s["order"][i]]
    correct_text = item[a_field]

    if s.get("options") is None:
        # Ablenker von der ganzen Seite (nicht nur aus der Fehlerwörter-Runde)
        all_items = _vocab_items(df_view)
        pool, seen = [], {norm_answer(correct_text)}
        for it in all_items:
            n = norm_answer(it[a_field])
            if n and n not in seen:
                seen.add(n)
                pool.append(it[a_field])
        rnd = random.Random()
        opts = [correct_text] + rnd.sample(pool, min(3, len(pool)))
        rnd.shuffle(opts)
        s["options"] = opts
        s["answered"] = None

    vocab_card(item[q_field], sub=f"{q_name} → {a_name}: Welche Antwort passt?")
    if q_field == "en":
        speak_button(item["en"], lang, label=f"🔊 {foreign} anhören")

    answered = s.get("answered")
    opts = s["options"]
    for row_start in range(0, len(opts), 2):
        cols = st.columns(2)
        for j, col in zip(range(row_start, min(row_start + 2, len(opts))), cols):
            opt = opts[j]
            with col:
                if answered is None:
                    if st.button(opt, key=f"{state_key}_opt_{i}_{j}", **WIDE):
                        s["answered"] = j
                        res = "correct" if opt == correct_text else "wrong"
                        _register_result(s, item, opt, res)
                        st.rerun()
                else:
                    is_correct = opt == correct_text
                    prefix = "✅ " if is_correct else ("❌ " if j == answered else "")
                    st.button(prefix + opt, key=f"{state_key}_opt_{i}_{j}", **WIDE,
                              disabled=not is_correct, type="primary" if is_correct else "secondary")

    if answered is not None:
        if opts[answered] == correct_text:
            st.markdown('<div class="fb fb-ok">✅ Richtig!</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="fb fb-wrong">❌ Leider falsch. <b>{html_escape(item[q_field])}</b> = '
                f'<b>{html_escape(correct_text)}</b></div>', unsafe_allow_html=True)
        cs, cn = st.columns([1, 1])
        with cs:
            speak_button(item["en"], lang, label=f"🔊 {foreign} anhören")
        with cn:
            if st.button("Weiter ➡️", key=f"{state_key}_next_{i}", type="primary", **WIDE):
                s["index"] += 1
                s["options"] = None
                s["answered"] = None
                if s["index"] >= len(s["order"]):
                    _stop_timer(s["timer"])
                st.rerun()


# ---------- Hangman ----------
def _base_letter(c: str) -> str:
    d = unicodedata.normalize("NFKD", c)
    return d[0].lower() if d else c.lower()


def _is_revealed(c: str, guessed: set) -> bool:
    if not c.isalpha():
        return True
    b = _base_letter(c)
    if b not in "abcdefghijklmnopqrstuvwxyz":
        return True  # z. B. œ, ß: wird direkt angezeigt
    return b in guessed


def game_hangman(df_view: pd.DataFrame, classe: str, page, seed_val: str, lang: str = "EN"):
    key = f"hangman_{classe}_{page}"
    rows = df_view.to_dict("records")
    rows = [r for r in rows if isinstance(r.get("en"), str) and r["en"] and any(ch.isalpha() for ch in main_form(r["en"]))]
    if not rows:
        st.info("Keine Vokabeln vorhanden.")
        return
    foreign = LANG_NAMES.get(lang, "Englisch")

    state = st.session_state.get(key)

    def _fresh_timer():
        return {"running": True, "started_ms": int(time.time() * 1000), "elapsed_ms": 0}

    def _set_word(idx):
        i = state["order"][idx]
        state["full"] = rows[i]["en"]
        state["solution"] = main_form(rows[i]["en"])
        state["hint"] = rows[i]["de"]
        state["guessed"] = set()
        state["fails"] = 0
        state["solved"] = False
        state["timer"] = _fresh_timer()
        state["msg"] = None

    if state is None or state.get("n_rows") != len(rows) or "full" not in state:
        order = list(range(len(rows)))
        rnd = random.Random(seed_val) if seed_val else random.Random()
        rnd.shuffle(order)
        state = {"order": order, "idx": 0, "n_rows": len(rows), "show_hint": False, "score": 0}
        _set_word(0)
        st.session_state[key] = state

    def next_word():
        state["idx"] += 1
        if state["idx"] >= len(rows):
            order = list(range(len(rows)))
            rnd = random.Random(seed_val) if seed_val else random.Random()
            rnd.shuffle(order)
            state["order"] = order
            state["idx"] = 0
        _set_word(state["idx"])

    def new_word():
        i = random.Random(time.time()).randrange(len(rows))
        state["order"][state["idx"]] = i
        _set_word(state["idx"])

    def _mark_solved():
        _stop_timer(state["timer"])
        if not state["solved"]:
            state["score"] = state.get("score", 0) + 1
        state["solved"] = True

    solution, hint, t = state["solution"], state["hint"], state["timer"]
    max_fails = len(HANGMAN_PICS) - 1

    status_bar(
        t, nonce=f"{state['idx']}_{len(state['guessed'])}_{state['fails']}",
        chips=[(f"❤️ Fehler: {state['fails']} von {max_fails}", "red" if state["fails"] else "violet"),
               (f"🏆 Gelöst: {state.get('score', 0)}", "orange")],
    )

    show_sol_now = False
    with keyed_container("hang_opts"):
        opt1, opt2, opt3 = st.columns([1.4, 1, 1])
        with opt1:
            state["show_hint"] = st.checkbox("🇩🇪 Hinweis zeigen", value=state.get("show_hint", False), key=f"{key}_showhint")
        with opt2:
            if st.button("💡 Lösung", key=f"{key}_showsol", **WIDE):
                show_sol_now = True
        with opt3:
            if st.button("⏭️ Anderes Wort", key=f"{key}_newword", **WIDE):
                new_word(); st.rerun()
    if show_sol_now:
        st.info(f"Lösung: {state['full']}")

    if state["show_hint"]:
        st.markdown(f'<div class="fb fb-hint">🇩🇪 Hinweis: <b>{html_escape(hint)}</b></div>', unsafe_allow_html=True)

    playing = not state["solved"] and state["fails"] < max_fails
    cA, cB = st.columns([1, 1.7])
    with cA:
        st.markdown(hangman_svg(state["fails"], lost=(not state["solved"] and not playing),
                                won=state["solved"]), unsafe_allow_html=True)
    with cB:
        display_word = " ".join(c if _is_revealed(c, state["guessed"]) else "_" for c in solution)
        st.markdown(f'<div class="hang-word">{html_escape(display_word)}</div>', unsafe_allow_html=True)
        st.caption(f"Gesuchtes Wort auf {foreign} · tippe Buchstaben an")

        if playing:
            sol_letters = {_base_letter(c) for c in solution if c.isalpha()}
            with keyed_container("hang_kb"):
                alphabet = list("abcdefghijklmnopqrstuvwxyz")
                for chunk in [alphabet[i:i+7] for i in range(0, len(alphabet), 7)]:
                    cols = st.columns(7)
                    for letter, col in zip(chunk, cols):
                        with col:
                            if st.button(letter.upper(), key=f"{key}_btn_{letter}",
                                         disabled=(letter in state["guessed"]), **WIDE):
                                state["guessed"].add(letter)
                                if letter not in sol_letters:
                                    state["fails"] += 1
                                state["msg"] = None
                                if all(_is_revealed(c, state["guessed"]) for c in solution):
                                    _mark_solved()
                                st.rerun()

        # Formular immer anzeigen (nach dem Lösen nur ausgegraut) – stabiler über alle Streamlit-Versionen
        with st.form(key=f"hang_form_{key}", clear_on_submit=True):
            full_guess = st.text_input(f"Oder ganzes Wort eintippen ({foreign}):", key=f"{key}_full", disabled=not playing)
            submitted = st.form_submit_button("✔ Prüfen", disabled=not playing)
            if submitted and playing and full_guess.strip():
                res = check_answer(full_guess, solution)
                if res != "correct":
                    res2 = check_answer(full_guess, state["full"])
                    res = "correct" if res2 == "correct" else res
                if res == "correct":
                    _mark_solved()
                elif res == "almost":
                    state["msg"] = "🟡 Fast! Prüfe die Schreibweise noch einmal."
                else:
                    state["msg"] = "❌ Das ist es leider nicht."
                st.rerun()
        if playing and state.get("msg"):
            st.warning(state["msg"])

    if state["solved"]:
        st.markdown(
            f'<div class="fb fb-ok">🎉 Super, gelöst! <b>{html_escape(state["full"])}</b> = {html_escape(hint)}'
            f' · ⏱ {fmt_ms(t["elapsed_ms"])[:5]}</div>', unsafe_allow_html=True)
        speak_button(state["full"], lang, label=f"🔊 {foreign} anhören")

    if not playing and not state["solved"]:
        _stop_timer(t)
        st.markdown(
            f'<div class="fb fb-wrong">😵 Leider verloren. Das Wort war: <b>{html_escape(state["full"])}</b>'
            f' = {html_escape(hint)}</div>', unsafe_allow_html=True)
        speak_button(state["full"], lang, label=f"🔊 {foreign} anhören")
        if st.button("➡️ Nächstes Wort", key=f"{key}_nextword_fail", type="primary"):
            next_word(); st.rerun()
    elif state["solved"]:
        if st.button("➡️ Nächstes Wort", key=f"{key}_nextword", type="primary"):
            next_word(); st.rerun()


# ---------- Wörter Memory (DE↔EN; Click/Tap; optional Drag) ----------
def game_word_memory(df_view: pd.DataFrame, classe: str, page,
                     show_solution_table: bool, subset_mode: str, subset_k: int,
                     seed_val: str, force_new_subset: bool = False, lang: str = "EN"):
    base_items = [
        {"de": r["de"], "en": r["en"]}
        for r in df_view.to_dict("records")
        if isinstance(r["de"], str) and isinstance(r["en"], str)
    ]
    if not base_items:
        st.info("Keine Vokabeln vorhanden.")
        return

    subset_state_key = f"memory_subset_{classe}_{page}"

    if force_new_subset:
        st.session_state.pop(subset_state_key, None)

    # subset_mode kommt bereits als "all" oder "k" an
    items = _sample_subset(
        base_items, subset_mode, int(subset_k),
        seed_val, subset_state_key, ["de", "en"]
    )

    st.caption(f"Paare in dieser Runde: **{len(items)}** · Tippe zwei Karten an, die zusammengehören. "
               "Auf dem Handy wird in kleineren Runden gespielt.")

    if show_solution_table:
        st.markdown("##### Lösung")
        st.dataframe(
            pd.DataFrame(items)[["de", "en"]].rename(columns={"de": "Deutsch", "en": LANG_NAMES.get(lang, "EN")}),
            **WIDE, hide_index=True
        )

    pairs_json = js_json(
        [{"id": i, "de": it["de"], "en": it["en"], "say": main_form(it["en"])} for i, it in enumerate(items)]
    )
    tts_lang = js_json(TTS_LANG.get(lang, "en-GB"))

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
:root {{ --primary:#1e88e5; --violet:#5e35b1; --success:#2e7d32; --danger:#d32f2f; }}
* {{ -webkit-tap-highlight-color: transparent; box-sizing: border-box; }}
body {{
  font-family: 'Source Sans Pro', Arial, sans-serif; margin:0; padding:10px; background:#f4f6fb;
  -webkit-user-select: none; user-select: none; -webkit-touch-callout: none;
}}
#toolbar {{ display:flex; align-items:center; gap:8px; margin-bottom:10px; flex-wrap:wrap; }}
#timer {{
  font-weight:bold; padding:6px 12px; border-radius:999px; background:#e3f2fd; color:#1565c0;
  min-width:90px; text-align:center; font-size:16px;
}}
#progress {{ font-weight:bold; color:var(--violet); }}
.btn {{
  padding:7px 12px; border:2px solid var(--primary); background:white; color:#1565c0;
  border-radius:10px; cursor:pointer; font-weight:bold; touch-action: manipulation; font-size:14px;
}}
.btn:hover {{ background:var(--primary); color:white; }}
.toggle {{ border-color:#7e57c2; color:#5e35b1; }}
.grid {{ display:flex; flex-wrap:wrap; gap:8px; }}
.card {{
  background:white; border:2px solid #90caf9; border-radius:12px;
  padding:12px 10px; min-width:120px; flex: 1 1 140px; text-align:center; font-size:16px;
  touch-action: manipulation; cursor:pointer; transition: transform .08s ease, box-shadow .15s ease;
  -webkit-user-drag: element; box-shadow: 0 1px 3px rgba(0,0,0,.08);
}}
.card.de {{ border-color:#64b5f6; }}
.card.fx {{ border-color:#b39ddb; background:#fbf9ff; }}
.card .tag {{
  display:inline-block; font-size:10px; font-weight:800; letter-spacing:.05em; border-radius:6px;
  padding:1px 5px; margin-bottom:4px; color:white; background:#64b5f6;
}}
.card.fx .tag {{ background:#9575cd; }}
.card .txt {{ display:block; }}
.card {{ position:relative; }}
.card .say {{
  position:absolute; top:4px; right:4px; margin:0; border:1.5px solid #b39ddb; background:white;
  color:#5e35b1; border-radius:999px; padding:1px 7px; font-size:14px; line-height:1.35; cursor:pointer;
  touch-action: manipulation;
}}
.card .say:hover {{ background:#ede7f6; }}
.card:hover {{ box-shadow: 0 3px 8px rgba(30,136,229,.25); }}
.card:active {{ transform: scale(0.97); }}
.correct {{ background:#e8f5e9 !important; border-color:#2e7d32 !important; color:#1b5e20; cursor:default; opacity:.75; }}
.selected {{ background:#e3f2fd; border-color:var(--primary); box-shadow:0 0 0 3px rgba(30,136,229,0.35); }}
.wrong {{ animation: shake .3s linear; border-color: #d32f2f!important; background:#ffebee; }}
@keyframes shake {{
  0%,100% {{ transform: translateX(0); }}
  25% {{ transform: translateX(-5px); }}
  75% {{ transform: translateX(5px); }}
}}
#overlay {{
  display:none; position:absolute; inset:0; background:rgba(30,20,60,.55); align-items:flex-start;
  justify-content:center; z-index:10; padding-top:30px;
}}
body {{ position:relative; }}
#overlay .box {{
  background:white; border-radius:18px; padding:26px 30px; text-align:center; max-width:90%;
  box-shadow:0 10px 30px rgba(0,0,0,.3); animation: pop .35s ease;
}}
#overlay h2 {{ margin:0 0 8px 0; font-size:28px; }}
#overlay p {{ font-size:18px; margin:6px 0 16px 0; }}
@keyframes pop {{ from {{ transform: scale(.7); opacity:0; }} to {{ transform: scale(1); opacity:1; }} }}
</style>
</head>
<body>
<div id="toolbar">
  <span id="timer">⏱ 00:00</span>
  <span id="progress"></span>
  <button class="btn" id="shuffleBtn">🔀 Neu mischen</button>
  <button class="btn toggle" id="modeBtn">Modus: </button>
  <button class="btn toggle" id="soundBtn">🔊 Ton an</button>
</div>

<div id="box" class="grid" aria-live="polite"></div>
<div id="overlay"><div class="box"><h2 id="ovTitle"></h2><p id="ovText"></p><button class="btn" id="ovBtn"></button></div></div>

{VOICE_JS}
<script>
const allPairs = {pairs_json};
const TTS_LANG = {tts_lang};
const LANG_TAG = {js_json(lang if lang in ("EN", "FR") else "EN")};
const nativeDnD = ('ondragstart' in document.createElement('div'));
let TAP_MODE = true;
let SOUND = true;
const CHUNK = (window.innerWidth < 700 && allPairs.length > 10) ? 8 : allPairs.length;

let running = false, timerId = null, startTime = null, elapsed = 0;
let order = [], roundIdx = 0, pairs = [];
let correctPairs = 0, solved = false;
let draggedCard = null, selectedCard = null;

function fmt(ms) {{
  const s = Math.floor(ms / 1000);
  return String(Math.floor(s / 60)).padStart(2,'0') + ":" + String(s % 60).padStart(2,'0');
}}
function updateTimer() {{
  document.getElementById('timer').textContent = "⏱ " + fmt(running ? Date.now() - startTime : elapsed);
}}
function startTimer() {{
  if (!running) {{ startTime = Date.now() - elapsed; timerId = setInterval(updateTimer, 250); running = true; }}
}}
function pauseTimer() {{
  if (running) {{ clearInterval(timerId); elapsed = Date.now() - startTime; running = false; updateTimer(); }}
}}
function resetTimer() {{
  clearInterval(timerId); running = false; startTime = null; elapsed = 0; updateTimer();
}}

function speak(txt, always) {{
  if (!SOUND && !always) return;
  try {{ __say(txt, TTS_LANG); }} catch (e) {{}}
}}

function markCorrect(el) {{
  el.classList.add('correct'); el.classList.remove('selected'); el.setAttribute('aria-disabled','true');
}}

function onMatch(a, b) {{
  markCorrect(a); markCorrect(b);
  const p = pairs.find(p => String(p.id) === a.getAttribute('data-pid'));
  if (p) speak(p.say);
  correctPairs += 1; updateProgress(); checkWin();
}}

function createCard(text, pid, isForeign) {{
  const c = document.createElement('div');
  c.className = 'card' + (isForeign ? ' fx' : ' de');
  const tag = document.createElement('span'); tag.className = 'tag'; tag.textContent = isForeign ? LANG_TAG : 'DE';
  const txt = document.createElement('span'); txt.className = 'txt'; txt.textContent = text;
  c.appendChild(tag); c.appendChild(txt);
  if (isForeign) {{
    // Lautsprecher: Wort anhören, ohne die Karte auszuwählen
    const p = allPairs.find(p => String(p.id) === String(pid));
    const sb = document.createElement('button');
    sb.type = 'button'; sb.className = 'say'; sb.textContent = '🔊';
    sb.title = 'Anhören'; sb.setAttribute('aria-label', 'Anhören: ' + text);
    sb.draggable = false;
    sb.addEventListener('click', (e) => {{ e.stopPropagation(); e.preventDefault(); speak(p ? p.say : text, true); }});
    sb.addEventListener('keydown', (e) => {{ e.stopPropagation(); }});
    sb.addEventListener('dragstart', (e) => {{ e.preventDefault(); e.stopPropagation(); }});
    c.appendChild(sb);
  }}
  c.setAttribute('data-pid', String(pid));
  c.setAttribute('role', 'button');
  c.setAttribute('tabindex', '0');

  if (TAP_MODE || !nativeDnD) {{
    c.addEventListener('click', () => handleTap(c));
    c.addEventListener('keydown', (e) => {{ if (e.key === 'Enter' || e.key === ' ') handleTap(c); }});
  }} else {{
    c.draggable = true;
    c.addEventListener('dragstart', (e) => {{
      startTimer();
      draggedCard = c; c.style.opacity = '0.5';
      try {{ e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', c.getAttribute('data-pid')); }} catch(_e) {{}}
    }});
    c.addEventListener('dragend', () => {{ c.style.opacity = '1'; }});
    c.addEventListener('dragover', (e) => {{ e.preventDefault(); try {{ e.dataTransfer.dropEffect = 'move'; }} catch(_e) {{}} }});
    c.addEventListener('drop', (e) => {{
      e.preventDefault();
      let srcPid = null;
      try {{ srcPid = e.dataTransfer.getData('text/plain'); }} catch(_e) {{}}
      if (!srcPid && draggedCard) srcPid = draggedCard.getAttribute('data-pid');
      const tgtPid = c.getAttribute('data-pid');
      if (!srcPid || !draggedCard || draggedCard === c || c.classList.contains('correct')) return;
      if (srcPid === tgtPid) {{
        draggedCard.style.opacity = '1'; onMatch(draggedCard, c);
      }} else {{
        shake(draggedCard); shake(c); draggedCard.style.opacity = '1';
      }}
      draggedCard = null;
    }});
  }}
  return c;
}}

function handleTap(card) {{
  if (solved || card.classList.contains('correct')) return;
  startTimer();
  if (!selectedCard) {{ selectedCard = card; card.classList.add('selected'); return; }}
  if (selectedCard === card) {{ card.classList.remove('selected'); selectedCard = null; return; }}
  const a = selectedCard.getAttribute('data-pid');
  const b = card.getAttribute('data-pid');
  if (a === b) {{
    onMatch(selectedCard, card);
  }} else {{
    shake(selectedCard); shake(card);
    selectedCard.classList.remove('selected');
  }}
  selectedCard = null;
}}

function shake(el) {{
  el.classList.remove('wrong'); void el.offsetWidth; el.classList.add('wrong');
  setTimeout(() => el.classList.remove('wrong'), 350);
}}

function shuffleArray(arr) {{
  for (let i = arr.length - 1; i > 0; i--) {{
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }}
  return arr;
}}

function nRounds() {{ return Math.ceil(allPairs.length / CHUNK); }}

function updateProgress() {{
  const r = nRounds() > 1 ? ("Runde " + (roundIdx + 1) + "/" + nRounds() + " · ") : "";
  document.getElementById('progress').textContent = r + correctPairs + " von " + pairs.length + " Paaren";
}}

function layoutRound() {{
  const box = document.getElementById('box');
  box.innerHTML = "";
  draggedCard = null; selectedCard = null; correctPairs = 0; solved = false;
  pairs = order.slice(roundIdx * CHUNK, (roundIdx + 1) * CHUNK);
  let cards = [];
  for (const p of pairs) {{
    cards.push({{ text: p.de, pid: p.id, fx: false }});
    cards.push({{ text: p.en, pid: p.id, fx: true }});
  }}
  shuffleArray(cards);
  for (const c of cards) box.appendChild(createCard(c.text, c.pid, c.fx));
  updateProgress();
  setTimeout(() => {{ try {{ __fit(); }} catch (e) {{}} }}, 30);
}}

function newGame() {{
  document.getElementById('overlay').style.display = 'none';
  resetTimer();
  order = shuffleArray(allPairs.slice());
  roundIdx = 0;
  layoutRound();
}}

function showOverlay(title, text, btnText, onClick) {{
  document.getElementById('ovTitle').textContent = title;
  document.getElementById('ovText').textContent = text;
  const b = document.getElementById('ovBtn');
  b.textContent = btnText; b.onclick = onClick;
  document.getElementById('overlay').style.display = 'flex';
  try {{ window.frameElement.scrollIntoView({{ behavior: 'smooth', block: 'start' }}); }} catch (e) {{}}
}}

function checkWin() {{
  if (correctPairs === pairs.length && !solved) {{
    solved = true;
    if (roundIdx + 1 < nRounds()) {{
      showOverlay("👍 Runde geschafft!", "Weiter geht's mit Runde " + (roundIdx + 2) + " von " + nRounds() + ".",
        "Weiter ➡️", () => {{ document.getElementById('overlay').style.display = 'none'; roundIdx += 1; layoutRound(); }});
    }} else {{
      pauseTimer();
      showOverlay("🎉 Geschafft!", "Alle " + allPairs.length + " Paare gefunden in " + fmt(elapsed) + ".",
        "🔄 Nochmal spielen", newGame);
    }}
  }}
}}

function setModeLabel() {{
  document.getElementById('modeBtn').textContent = "Modus: " + (TAP_MODE || !nativeDnD ? "Antippen" : "Ziehen");
}}

document.getElementById('shuffleBtn').addEventListener('click', newGame);
document.getElementById('modeBtn').addEventListener('click', () => {{
  if (!nativeDnD) return;
  TAP_MODE = !TAP_MODE; setModeLabel(); layoutRound();
}});
document.getElementById('soundBtn').addEventListener('click', () => {{
  SOUND = !SOUND;
  document.getElementById('soundBtn').textContent = SOUND ? "🔊 Ton an" : "🔇 Ton aus";
}});

setModeLabel();
newGame();
</script>
{AUTOSIZE_JS}
</body>
</html>"""

    embed_html(html, height=620)


# ---------- Unregelmäßige Verben Memory (aus Code) ----------
def game_irregulars_assign():
    def allowed_forms(target_key: str, verb: dict) -> set[str]:
        raw = verb[target_key]
        forms = [raw]
        if target_key != "meaning" and "/" in raw:
            forms += [p.strip() for p in raw.split("/")]
        return {normalize_text(x) for x in forms}

    if "verbs_points_total" not in st.session_state:
        st.session_state.verbs_points_total = 0

    def new_round():
        verb = random.choice(VERBS)
        items = [
            {"text": verb["infinitive"], "match": "infinitive", "hidden": False},
            {"text": verb["pastSimple"], "match": "pastSimple", "hidden": False},
            {"text": verb["pastParticiple"], "match": "pastParticiple", "hidden": False},
            {"text": verb["meaning"], "match": "meaning", "hidden": False},
        ]
        random.shuffle(items)
        st.session_state.verbs_round = {
            "verb": verb,
            "items": items,
            "matches": {k: None for (_, k) in VERB_TARGETS},
            "start_ts": int(time.time()),
            "completed": False,
            "timer": {"running": True, "started_ms": int(time.time() * 1000), "elapsed_ms": 0},
        }
        st.session_state.verbs_selected_idx = None
        st.session_state.verbs_msg = None

    if "verbs_round" not in st.session_state or "timer" not in st.session_state.verbs_round:
        new_round()
    if "verbs_selected_idx" not in st.session_state:
        st.session_state.verbs_selected_idx = None

    rnd_state = st.session_state.verbs_round

    st.caption("1️⃣ Tippe links auf ein Wort. 2️⃣ Tippe rechts auf die passende Form. "
               "Slash-Formen (z. B. was/were) werden akzeptiert.")

    status_bar(rnd_state["timer"], nonce=str(rnd_state["start_ts"]),
               chips=[(f"🏆 Punkte: {st.session_state.verbs_points_total}", "orange")])

    if st.session_state.get("verbs_msg"):
        kind, text = st.session_state.verbs_msg
        css = "fb-ok" if kind == "ok" else "fb-wrong"
        st.markdown(f'<div class="fb {css}">{text}</div>', unsafe_allow_html=True)

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown("#### Wörter")
        options = [(i, it["text"]) for i, it in enumerate(rnd_state["items"]) if not it["hidden"]]
        if options:
            for i, txt in options:
                is_sel = st.session_state.verbs_selected_idx == i
                if st.button(("👉 " if is_sel else "") + txt, key=f"verbs_word_{i}",
                             type="primary" if is_sel else "secondary", **WIDE):
                    st.session_state.verbs_selected_idx = None if is_sel else i
                    st.session_state.verbs_msg = None
                    st.rerun()
        else:
            st.write("Alle Wörter sind zugeordnet ✅")

    with right:
        st.markdown("#### Ziele")
        target_idx = st.session_state.verbs_selected_idx

        for name, key in VERB_TARGETS:
            current_match_text = rnd_state["matches"][key]
            if current_match_text is not None:
                st.button(f"{name}: ✅ {current_match_text}", key=f"verbs_target_{key}", disabled=True,
                          **WIDE)
            else:
                if st.button(name, key=f"verb_target_btn_{key}", disabled=(target_idx is None),
                             **WIDE):
                    selected_item = rnd_state["items"][target_idx]
                    selected_text = selected_item["text"]
                    if normalize_text(selected_text) in allowed_forms(key, rnd_state["verb"]):
                        rnd_state["matches"][key] = selected_text
                        selected_item["hidden"] = True
                        st.session_state.verbs_points_total += 1
                        if all(rnd_state["matches"].values()):
                            rnd_state["completed"] = True
                            _stop_timer(rnd_state["timer"])
                        st.session_state.verbs_msg = ("ok", f"✅ Richtig! „{selected_text}“ ist {name}.")
                    else:
                        st.session_state.verbs_msg = ("err", f"❌ Falsch! „{selected_text}“ ist nicht {name}.")
                    st.session_state.verbs_selected_idx = None
                    st.rerun()
        if target_idx is None and not rnd_state["completed"]:
            st.caption("Wähle zuerst links ein Wort aus.")

    if rnd_state["completed"]:
        v = rnd_state["verb"]
        if not rnd_state.get("celebrated"):
            st.balloons()
            rnd_state["celebrated"] = True
        st.markdown(
            f'<div class="fb fb-ok">🎉 Sehr gut! <b>{v["infinitive"]} – {v["pastSimple"]} – {v["pastParticiple"]}</b>'
            f' ({html_escape(v["meaning"])}) · ⏱ {fmt_ms(rnd_state["timer"]["elapsed_ms"])[:5]}</div>',
            unsafe_allow_html=True)
        speak_button(f'{v["infinitive"]}, {v["pastSimple"].replace("/", ", ")}, {v["pastParticiple"].replace("/", ", ")}',
                     "EN", label="🔊 Alle Formen anhören")

    b1, b2 = st.columns(2)
    with b1:
        if st.button("➡️ Nächstes Verb" if rnd_state["completed"] else "🔁 Anderes Verb",
                     key="verbs_next", type="primary" if rnd_state["completed"] else "secondary"):
            new_round(); st.rerun()
    with b2:
        if st.button("🧹 Punkte zurücksetzen", key="verbs_reset_points"):
            st.session_state.verbs_points_total = 0; new_round(); st.rerun()


# ============================ Haupt-UI (Controller) ============================

APP_CSS = """
<style>
/* Etwas kompakter oben */
.block-container { padding-top: 3.5rem; max-width: 1100px; }

/* Ausgewähltes Spiel / Hauptbuttons blau statt rot */
button[kind="primary"],
button[data-testid="baseButton-primary"],
button[data-testid="stBaseButton-primary"],
button[kind="primaryFormSubmit"],
button[data-testid="baseButton-primaryFormSubmit"],
button[data-testid="stBaseButton-primaryFormSubmit"] {
  background-color: #1e88e5 !important; border-color: #1e88e5 !important; color: white !important;
}
button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover,
button[kind="primaryFormSubmit"]:hover,
button[data-testid="baseButton-primaryFormSubmit"]:hover,
button[data-testid="stBaseButton-primaryFormSubmit"]:hover {
  background-color: #1565c0 !important; border-color: #1565c0 !important;
}
button:disabled[kind="primary"], button:disabled[data-testid="stBaseButton-primary"],
button:disabled[data-testid="baseButton-primary"] {
  background-color: #2e7d32 !important; border-color: #2e7d32 !important; opacity: 1 !important;
}

/* Kopfbereich */
.app-hero {
  background: linear-gradient(135deg, #1e88e5 0%, #5e35b1 100%);
  color: white; border-radius: 16px; padding: 18px 22px; margin-bottom: 18px;
}
.app-hero h1 { color: white; margin: 0; padding: 0; font-size: 2rem; line-height: 1.2; }
.app-hero p { margin: 6px 0 0 0; opacity: .92; font-size: 1rem; }

/* Schritt-Überschriften */
.step-title { font-size: 1.15rem; font-weight: 700; margin: 4px 0 8px 0; }
.step-badge {
  display: inline-block; background: #1e88e5; color: white; border-radius: 999px;
  width: 1.7rem; height: 1.7rem; line-height: 1.7rem; text-align: center;
  margin-right: 8px; font-size: .95rem;
}

/* Spiel-Kacheln */
.game-tile-desc { font-size: .85rem; color: #666; margin: -4px 0 6px 2px; min-height: 2.4em; }
div[data-testid="stButton"] button p { font-size: 1rem; }

/* Vokabelkarte */
.vocab-card {
  background: linear-gradient(135deg, #e3f2fd 0%, #ede7f6 100%);
  border-radius: 16px; padding: 18px 20px; margin: 8px 0 10px 0; text-align: center;
  border: 1px solid #d1c4e9;
}
.vocab-sub { font-size: .85rem; color: #5e35b1; font-weight: 600; margin-bottom: 4px; }
.vocab-word { font-size: 1.8rem; font-weight: 700; color: #1a237e; line-height: 1.25; }

/* Rückmeldungen */
.fb { border-radius: 12px; padding: 12px 16px; margin: 6px 0 10px 0; font-size: 1.05rem; }
.fb-ok { background: #e8f5e9; border-left: 6px solid #2e7d32; color: #1b5e20; }
.fb-almost { background: #fff8e1; border-left: 6px solid #f9a825; color: #6d4c00; }
.fb-wrong { background: #ffebee; border-left: 6px solid #d32f2f; color: #8e0000; }
.fb-hint { background: #ede7f6; border-left: 6px solid #5e35b1; color: #311b92; }
.fb-small { font-size: .9rem; opacity: .85; }

.streak-pill {
  background: #fff3e0; color: #e65100; font-weight: 700; border-radius: 999px;
  padding: 6px 12px; text-align: center; margin-top: 2px; white-space: nowrap;
}
.summary-card {
  background: linear-gradient(135deg, #1e88e5 0%, #5e35b1 100%); color: white;
  border-radius: 16px; padding: 20px 22px; margin: 6px 0 14px 0; text-align: center; font-size: 1.1rem;
}
.summary-big { font-size: 1.8rem; font-weight: 800; margin-bottom: 4px; }
.summary-small { font-size: .95rem; opacity: .92; margin-top: 8px; }

.hang-word {
  font-family: 'Courier New', monospace; font-size: 2rem; font-weight: 700; letter-spacing: .12em;
  color: #1a237e; background: #f3f6ff; border-radius: 12px; padding: 10px 14px; word-break: break-word;
}

/* Seitenleiste farbig passend zum Kopfbereich */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #e3f2fd 0%, #ede7f6 100%);
  border-right: 1px solid #d1c4e9;
}
section[data-testid="stSidebar"] .sb-head {
  background: linear-gradient(135deg, #1e88e5 0%, #5e35b1 100%);
  color: white; font-weight: 700; font-size: 1.15rem;
  border-radius: 12px; padding: 10px 14px; margin-bottom: 6px;
}
section[data-testid="stSidebar"] .sb-sub { font-size: .85rem; color: #5e35b1; margin: 0 2px 12px 2px; }
section[data-testid="stSidebar"] div[data-testid="stButton"] button {
  background: white; border: 2px solid #1e88e5; color: #1565c0; border-radius: 10px;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover {
  background: #1e88e5; color: white;
}
section[data-testid="stSidebar"] input { background: white; border-radius: 8px; }

/* ---------- Layout 2.0 ---------- */

/* Grundschrift etwas größer, Buttons höher (leichter zu treffen) */
html, body, [data-testid="stAppViewContainer"] { font-size: 17px; }
div[data-testid="stButton"] button, div[data-testid="stFormSubmitButton"] button { min-height: 2.9rem; border-radius: 12px; }
.vocab-word { font-size: 2.1rem; }

/* Kein Deploy-Knopf / Entwickler-Menü */
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"], #MainMenu { display: none !important; }

/* Kopfbereich schlanker */
.app-hero { padding: 14px 20px; margin-bottom: 14px; }

/* Spiel-Karten als Raster: PC 3 nebeneinander, Handy 2 */
.st-key-game_grid [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 12px !important; }
.st-key-game_grid [data-testid="stColumn"], .st-key-game_grid [data-testid="column"] {
  flex: 1 1 calc(33.333% - 12px) !important; min-width: calc(33.333% - 12px) !important; width: auto !important;
}
.st-key-game_grid button { min-height: 5.4rem !important; border-radius: 16px !important; padding: 10px 12px !important;
  white-space: normal !important; transition: transform .08s ease, box-shadow .15s ease; }
.st-key-game_grid button:hover { transform: translateY(-2px); }
.st-key-game_grid button p { font-size: 1.08rem !important; font-weight: 700 !important; line-height: 1.25; }
/* Titel und Beschreibung umbrechen statt abschneiden */
.st-key-game_grid button, .st-key-game_grid button * {
  white-space: normal !important; overflow: visible !important; text-overflow: clip !important; max-width: 100%;
}
/* Verben-Ziele (z. B. „Past Participle (3. Form des Verbs)“), Wörter und „Zurück“: umbrechen statt abschneiden */
[class*="st-key-verb_target_btn_"] button, [class*="st-key-verb_target_btn_"] button *,
[class*="st-key-verbs_target_"] button, [class*="st-key-verbs_target_"] button *,
[class*="st-key-verbs_word_"] button, [class*="st-key-verbs_word_"] button *,
.st-key-open_setup button, .st-key-open_setup button * {
  white-space: normal !important; overflow: visible !important; text-overflow: clip !important; max-width: 100%;
}
.sum-line { margin-bottom: 2px; }

/* Kompakte Leiste über dem Spiel */
.sum-line { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; min-height: 2.9rem; }
.sum-chip { background: #eef3fd; color: #1f2340; border-radius: 999px; padding: 6px 12px; font-weight: 600; font-size: .95rem; }
.sum-game { background: linear-gradient(135deg, #1e88e5 0%, #5e35b1 100%); color: white; }

/* Hangman */
.hang-svg { max-width: 230px; margin: 0 auto; }
.hang-svg svg { width: 100%; height: auto; display: block; }
.st-key-hang_kb [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 6px !important; }
.st-key-hang_kb [data-testid="stColumn"], .st-key-hang_kb [data-testid="column"] {
  min-width: 0 !important; flex: 1 1 0 !important; width: auto !important;
}
.st-key-hang_kb button { min-height: 2.6rem !important; padding: 0 !important; font-weight: 700; }
.st-key-hang_kb [data-testid="stVerticalBlock"] { gap: 6px !important; }

/* Hangman-Optionen: Buttons auch auf dem Handy nebeneinander */
@media (max-width: 640px) {
  .st-key-hang_opts [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 8px !important; }
  .st-key-hang_opts [data-testid="stColumn"]:first-child, .st-key-hang_opts [data-testid="column"]:first-child {
    flex: 1 1 100% !important; min-width: 100% !important; }
  .st-key-hang_opts [data-testid="stColumn"], .st-key-hang_opts [data-testid="column"] {
    flex: 1 1 calc(50% - 8px) !important; min-width: calc(50% - 8px) !important; }
  .st-key-summary_bar [data-testid="stHorizontalBlock"] { gap: 8px !important; }
  .st-key-summary_bar .sum-line { margin-bottom: 10px; }
  /* Eingabe: Prüfen über volle Breite, Überspringen + Lösung nebeneinander */
  .st-key-answer_box [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 8px !important; }
  .st-key-answer_box [data-testid="stColumn"], .st-key-answer_box [data-testid="column"] {
    flex: 1 1 calc(50% - 8px) !important; min-width: calc(50% - 8px) !important; }
  .st-key-answer_box [data-testid="stColumn"]:first-child, .st-key-answer_box [data-testid="column"]:first-child {
    flex: 1 1 100% !important; min-width: 100% !important; }
}

/* Antwortfeld + Buttons als eine Einheit */
.st-key-answer_box { background: #fbfcff; }

/* Seitenleiste: Schrift immer dunkel (auch wenn das Gerät im Dunkelmodus ist) */
section[data-testid="stSidebar"], section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] summary { color: #1f2340; }
section[data-testid="stSidebar"] .sb-head, section[data-testid="stSidebar"] .sb-head * { color: white; }
section[data-testid="stSidebar"] .sb-sub { color: #5e35b1; }

@media (max-width: 640px) {
  .app-hero h1 { font-size: 1.4rem; }
  .app-hero p { font-size: .92rem; }
  .block-container { padding-top: 3rem; padding-left: .8rem; padding-right: .8rem; }
  .vocab-word { font-size: 1.7rem; }
  .hang-word { font-size: 1.5rem; }
  .hang-svg { max-width: 150px; }
  .st-key-game_grid [data-testid="stColumn"], .st-key-game_grid [data-testid="column"] {
    flex: 1 1 calc(50% - 12px) !important; min-width: calc(50% - 12px) !important;
  }
  .st-key-game_grid button { min-height: 5rem !important; }
  .st-key-game_grid button p { font-size: 1rem !important; }
  .st-key-hang_kb button p { font-size: .95rem !important; }
}
</style>
"""


def _step_title(num, text: str):
    badge = f'<span class="step-badge">{num}</span>' if num else ""
    st.markdown(f'<div class="step-title">{badge}{text}</div>', unsafe_allow_html=True)


def _tiles_css(games) -> str:
    """CSS für die Spiel-Karten: eigene Farbe + Beschreibung je Spiel."""
    rules = []
    for code, icon, title, desc, color in games:
        k = f".st-key-game_tile_{code}"
        d = desc.replace('"', "'")
        rules.append(f"""
{k} button {{ border: 2px solid {color} !important; background: white !important; color: #1f2340 !important; }}
{k} button:hover {{ background: {color}14 !important; }}
{k} button p::after {{ content: "{d}"; display: block; font-size: .8rem; font-weight: 400; opacity: .8; margin-top: 4px; }}
{k} button[kind="primary"], {k} button[data-testid="stBaseButton-primary"], {k} button[data-testid="baseButton-primary"] {{
  background: {color} !important; color: white !important; box-shadow: 0 4px 12px {color}55;
}}""")
    return "<style>" + "".join(rules) + "</style>"


COURSE_CODES = {"e": "e", "g": "g", "französisch": "f", "": ""}


def _server_qr_data_uri(query: str):
    """QR-Code direkt in Python erzeugen (funktioniert auch, wenn das Schulnetz CDNs sperrt)."""
    try:
        import segno
        url = str(getattr(st.context, "url", "") or "")
    except Exception:
        return None
    if not url.startswith("http"):
        return None
    base = url.split("?", 1)[0]
    base = re.sub(r"/~/\+/?$", "/", base)
    try:
        return segno.make(f"{base}?{query}", error="m").svg_data_uri(scale=5, border=2)
    except Exception:
        return None


def _share_box(query: str):
    """Link + QR-Code zur aktuellen Übung (für Tafel/Beamer oder zum Teilen)."""
    q = js_json(query)
    qr_uri = _server_qr_data_uri(query)
    if qr_uri:
        st.markdown(f'<img src="{qr_uri}" alt="QR-Code" style="width:180px;background:white;border-radius:8px;">',
                    unsafe_allow_html=True)
    js_qr = "" if qr_uri else (
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>')
    embed_html(f"""
<div style="font-family:'Source Sans Pro',Arial,sans-serif;font-size:13px;">
  <input id="u" readonly style="width:100%;padding:6px;border:1px solid #b39ddb;border-radius:8px;font-size:12px;">
  <button id="c" style="margin-top:6px;padding:5px 10px;border:2px solid #1e88e5;background:white;color:#1565c0;
    border-radius:8px;cursor:pointer;font-weight:bold;">📋 Link kopieren</button>
  <div id="qr" style="margin-top:10px;background:white;padding:8px;display:inline-block;border-radius:8px;"></div>
</div>
{js_qr}
<script>
let loc;
try {{ loc = window.top.location; void loc.href; }} catch (e) {{ try {{ loc = window.parent.location; }} catch (e2) {{ loc = null; }} }}
let base = loc ? (loc.origin + loc.pathname.replace(/\\/~\\/\\+\\/?$/, '/')) : '';
const url = base + '?' + {q};
document.getElementById('u').value = url;
document.getElementById('c').onclick = () => {{
  const el = document.getElementById('u'); el.select();
  try {{ navigator.clipboard.writeText(url); }} catch (e) {{ document.execCommand('copy'); }}
  document.getElementById('c').textContent = '✅ Kopiert';
}};
try {{ new QRCode(document.getElementById('qr'), {{ text: url, width: 180, height: 180 }}); }}
catch (e) {{ document.getElementById('qr').style.display = 'none'; }}
</script>""", height=90 if qr_uri else 290)


def main():
    BASE_DIR = Path(__file__).parent

    st.markdown(APP_CSS, unsafe_allow_html=True)
    hero_sub = ('<p>Wähle deine Klasse und Seite – dann such dir ein Spiel aus!</p>'
                if st.session_state.get("setup_open", "klasse" not in st.query_params) else "")
    st.markdown(f'<div class="app-hero"><h1>📚 Wortschatz-Spiele</h1>{hero_sub}</div>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown(
            '<div class="sb-head">⚙️ Einstellungen</div>'
            '<div class="sb-sub">Hier musst du normalerweise nichts ändern.</div>',
            unsafe_allow_html=True,
        )
        if st.button("🔄 Vokabeln neu laden", help="Hilft, wenn etwas hängt oder neue Vokabeln noch nicht angezeigt werden."):
            st.cache_data.clear()
            st.rerun()

        if "dev_mode" not in st.session_state:
            st.session_state.dev_mode = False
        st.session_state.dev_mode = st.checkbox(
            "🛠️ Technische Infos anzeigen", value=st.session_state.dev_mode, key="dev_mode_cbox",
            help="Zeigt Details zu den geladenen Dateien – nur zur Fehlersuche nötig.")

    df_info = get_vocab_file_info(BASE_DIR)

    if df_info.empty:
        st.error("❌ **Keine Vokabeldateien gefunden.**")
        st.markdown(
            "Bitte stelle sicher, dass die CSV-Dateien nach dem Muster "
            "**`klasseX_<e|g|französisch>_pageY.csv`** im Ordner "
            "**`prepared_data/pages/klasseX_<e|g|französisch>/`** liegen "
            "oder im alten Schema **`data/pages/klasseX/`** (ohne Kurs)."
        )
        st.caption(f"Basisverzeichnis: `{BASE_DIR}`")
        if st.session_state.dev_mode:
            st.subheader("Technische Infos")
            st.write("df_info ist leer.")
        return

    def sort_key(label: str):
        m = re.search(r"Klasse (\d+)", label)
        klasse_num = int(m.group(1)) if m else 99
        kurs_order = 0 if 'E-Kurs' in label else (1 if 'G-Kurs' in label else (2 if 'Französisch' in label else 3))
        return (klasse_num, kurs_order)

    unique_labels = sorted(df_info["label"].unique(), key=sort_key)

    # Kurz-Codes für Direktlinks, z. B. "7e", "8g", "7f"
    label_to_code, code_to_label = {}, {}
    for lbl, grp in df_info.groupby("label"):
        first = grp.iloc[0]
        code = f"{int(first['classe'])}{COURSE_CODES.get(first['course'], '')}"
        label_to_code[lbl] = code
        code_to_label[code] = lbl

    # Auswahl merkt sich die App selbst (damit Schritt 1+2 zugeklappt werden können).
    # Beim ersten Laden werden Direktlink-Parameter übernommen.
    if "sel" not in st.session_state:
        qp = st.query_params
        qp_label = code_to_label.get(str(qp.get("klasse", "")).lower())
        st.session_state.sel = {
            "label": qp_label or unique_labels[0],
            "page": qp.get("seite"),
            "end": qp.get("bis"),
            "multi": bool(qp.get("bis")),
        }
        if qp.get("spiel"):
            st.session_state.game_choice = qp.get("spiel")
        # Mit Direktlink direkt ins Spiel, sonst erst auswählen
        st.session_state.setup_open = qp_label is None
    sel = st.session_state.sel
    if sel["label"] not in unique_labels:
        sel["label"] = unique_labels[0]

    def _index_of(val, options):
        try:
            return options.index(int(val))
        except (TypeError, ValueError):
            return 0

    # Spiele (Code, Symbol, Titel, Beschreibung, Farbe)
    def _games_for(is_fr: bool, lname: str):
        g = [
            ("input", "✍️", "Eingabe", "Übersetzung selbst tippen", "#1e88e5"),
            ("mc", "🎯", "Multiple Choice", "Aus 4 Antworten wählen", "#00897b"),
            ("memory", "🃏", "Wörter Memory", "Passende Paare finden", "#43a047"),
            ("hangman", "🪢", "Hangman", "Wort Buchstabe für Buchstabe raten", "#f57c00"),
        ]
        if not is_fr:
            g.append(("irregulars", "🔀", "Unregelmäßige Verben", "Verbformen zuordnen", "#8e24aa"))
        return g

    setup_open = st.session_state.get("setup_open", True)

    if setup_open:
        # ---------- Schritt 1: Klasse/Kurs + Seite ----------
        with st.container(border=True):
            _step_title(1, "Klasse und Seite wählen")
            col_k, col_p, col_p2 = st.columns([3, 1.4, 1.4])
            with col_k:
                sel["label"] = st.selectbox("Klasse/Kurs", unique_labels, index=unique_labels.index(sel["label"]))
            pages_tmp = [int(p) for p in sorted(df_info[df_info["label"] == sel["label"]]["page"].unique())]
            with col_p:
                sel["page"] = st.selectbox("Seite im Buch", pages_tmp, index=_index_of(sel["page"], pages_tmp))
            sel["multi"] = st.checkbox("📚 Mehrere Seiten zusammen üben (z. B. für einen Vokabeltest)",
                                       value=bool(sel["multi"]))
            if sel["multi"]:
                later_tmp = [p for p in pages_tmp if p >= int(sel["page"])]
                with col_p2:
                    sel["end"] = st.selectbox("bis Seite", later_tmp, index=_index_of(sel["end"], later_tmp))

    selected_label = sel["label"]
    filtered_df = df_info[df_info["label"] == selected_label].reset_index(drop=True)
    unique_pages = [int(p) for p in sorted(filtered_df["page"].unique())]
    selected_page = unique_pages[_index_of(sel["page"], unique_pages)]
    sel["page"] = selected_page
    end_page = selected_page
    if sel["multi"]:
        later_pages = [p for p in unique_pages if p >= selected_page]
        end_page = later_pages[_index_of(sel["end"], later_pages)]
        sel["end"] = end_page

    sel_rows = filtered_df[(filtered_df["page"] >= selected_page) & (filtered_df["page"] <= end_page)]
    sel_rows = sel_rows.sort_values("page")
    current_info = sel_rows.iloc[0]
    selected_path = current_info["path"]
    selected_classe = current_info["classe"]

    frames = [load_and_preprocess_df(p) for p in sel_rows["path"]]
    frames = [f for f in frames if not f.empty]
    df_vocab = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["classe", "page", "de", "en"])

    page_key = str(selected_page) if end_page == selected_page else f"{selected_page}-{end_page}"
    page_text = f"Seite {selected_page}" if end_page == selected_page else f"Seiten {selected_page}–{end_page}"

    is_french = current_info["course"] == "französisch"
    lang = "FR" if is_french else "EN"
    lang_name = LANG_NAMES[lang]

    games = _games_for(is_french, lang_name)
    game_codes = [g[0] for g in games]
    if st.session_state.get("game_choice") not in game_codes:
        st.session_state.game_choice = "input"
    game_choice = st.session_state.game_choice
    g_icon, g_title = next((g[1], g[2]) for g in games if g[0] == game_choice)
    game_title = f"{g_icon} {g_title}" + (f" ({lang_name})" if game_choice in ("input", "hangman") else "")

    # Farben + Beschreibungen der Spiel-Karten
    st.markdown(_tiles_css(games), unsafe_allow_html=True)

    if setup_open:
        # ---------- Schritt 2: Spiel wählen (Karten) ----------
        with st.container(border=True):
            _step_title(2, "Spiel auswählen")
            with keyed_container("game_grid"):
                cols = st.columns(len(games))
                for (code, icon, title, desc, color), col in zip(games, cols):
                    with col:
                        is_active = game_choice == code
                        if st.button(f"{icon} {title}", key=f"game_tile_{code}",
                                     type="primary" if is_active else "secondary", **WIDE):
                            st.session_state.game_choice = code
                            st.session_state.setup_open = False
                            st.rerun()
            st.caption("Tippe auf ein Spiel – dann geht's los.")
    else:
        # ---------- Kompakte Leiste statt Schritt 1+2 ----------
        with keyed_container("summary_bar", border=True):
            c_info, c_btn = st.columns([3.2, 1.8])
            with c_info:
                st.markdown(
                    f'<div class="sum-line"><span class="sum-chip">📚 {html_escape(selected_label)}</span>'
                    f'<span class="sum-chip">📖 {html_escape(page_text)}</span>'
                    f'<span class="sum-chip sum-game">{html_escape(game_title)}</span></div>',
                    unsafe_allow_html=True)
            with c_btn:
                if st.button("⬅️ Zurück zur Auswahl", key="open_setup", **WIDE):
                    st.session_state.setup_open = True
                    st.rerun()

    # Adresszeile aktuell halten (für Direktlinks)
    desired_qp = {"klasse": label_to_code.get(selected_label, ""), "seite": str(selected_page), "spiel": game_choice}
    if end_page != selected_page:
        desired_qp["bis"] = str(end_page)
    try:
        if {k: st.query_params.get(k) for k in st.query_params.keys()} != desired_qp:
            st.query_params.clear()
            for k, v in desired_qp.items():
                st.query_params[k] = v
    except Exception:
        pass

    with st.sidebar:
        with st.expander("🔗 Übung teilen (Link / QR-Code)"):
            st.caption("Damit landen alle direkt in dieser Klasse, Seite und diesem Spiel.")
            _share_box("&".join(f"{k}={v}" for k, v in desired_qp.items()))

    # ---------- Schritt 3: Spielen ----------
    with st.container(border=True):
        if setup_open:
            _step_title(3, game_title)
        if game_choice != "irregulars":
            st.caption(f"{selected_label} · {page_text} · {len(df_vocab)} Vokabeln")

        if df_vocab.empty and game_choice != "irregulars":
            st.warning(f"Datei **{selected_path.name}** enthält keine Vokabeln.")

        if game_choice in ["input", "mc", "memory", "hangman"]:
            with st.sidebar:
                seed_val = st.text_input(
                    "🎲 Gleiche Reihenfolge für alle (Code, optional)", value="",
                    help="Wenn alle in der Klasse denselben Code eingeben (z. B. 7), bekommen alle dieselben Wörter in derselben Reihenfolge. Leer lassen = jedes Mal neu gemischt."
                )

            if game_choice in ("input", "mc"):
                direction = st.radio(
                    "Richtung",
                    options=["de2x", "x2de"],
                    format_func=lambda d: f"Deutsch → {lang_name}" if d == "de2x" else f"{lang_name} → Deutsch",
                    horizontal=True,
                    key="direction_choice",
                    label_visibility="collapsed",
                )
                if len(df_vocab) < 1:
                    st.info("Für dieses Spiel sind Seiten-Vokabeln nötig.")
                    st.caption(f"Sitzung: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} – Geladene Vokabeln (Seite): {len(df_vocab)}")
                elif game_choice == "input":
                    game_input(df_vocab, selected_label, page_key, lang=lang, direction=direction)
                else:
                    game_multiple_choice(df_vocab, selected_label, page_key, lang=lang, direction=direction)

            elif game_choice == "memory":
                force_new = False
                with st.expander("⚙️ Memory-Einstellungen (Anzahl der Karten, Lösung)", expanded=False):
                    memory_subset_mode = st.radio(
                        "Mit wie vielen Wörtern möchtest du spielen?",
                        options=["Alle Vokabeln", "Subset (k Paare)"],
                        format_func=lambda o: "Alle Wörter der Seite" if o == "Alle Vokabeln" else "Nur einige Wörter",
                        key="memory_subset_mode",
                        horizontal=True,
                    )
                    memory_subset_k = 0
                    if memory_subset_mode == "Subset (k Paare)":
                        if len(df_vocab) > 2:
                            memory_subset_k = st.slider(
                                "Anzahl der Wortpaare",
                                min_value=2,
                                max_value=len(df_vocab),
                                value=min(10, len(df_vocab))
                            )
                        else:
                            memory_subset_k = len(df_vocab)

                    show_sol = st.checkbox("Lösungen anzeigen")

                    if st.button("🔀 Andere Wörter auswählen", key="new_subset_btn"):
                        force_new = True

                if len(df_vocab) < 2:
                    st.info("Für das Memory-Spiel werden mindestens 2 Vokabelpaare benötigt.")
                else:
                    game_word_memory(
                        df_vocab, selected_label, page_key,
                        show_sol,
                        "all" if memory_subset_mode == "Alle Vokabeln" else "k",
                        memory_subset_k,
                        seed_val,
                        force_new_subset=force_new,
                        lang=lang,
                    )

            elif game_choice == "hangman":
                if len(df_vocab) < 1:
                    st.info("Für das Hangman-Spiel sind Seiten-Vokabeln nötig.")
                else:
                    game_hangman(df_vocab, selected_label, page_key, seed_val, lang=lang)

        elif game_choice == "irregulars":
            game_irregulars_assign()

    if st.session_state.dev_mode:
        st.subheader("Technische Infos: aktuelle Auswahl")
        st.write(f"Pfad: `{selected_path}`")
        st.write(f"Klasse: {selected_classe}")
        st.dataframe(df_vocab.head(3))


if __name__ == "__main__":
    main()
