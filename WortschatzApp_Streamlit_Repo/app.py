# app.py
"""
Wortschatz-Spiele (Klassen 7–9)

Nur "Nur diese Seite": seiten-spezifische CSVs unter data/pages/klasseK/klasseK_pageS.csv
Spalten: classe, page, de, en

Spiele/Features:
- Hangman: Timer, Congrats+Time, Show solution, Show German hint (optional),
  Next word & New word.
- Wörtermemory (DE↔EN): Click/Tap-to-Match (alle Plattformen), optional Desktop-Drag,
  Timer, Show solution (DE—EN), Anzahl der Paare wählbar (ganze Seite ODER k-Paare), Seed-stabil.
- Eingabe (DE→EN): Enter zum Prüfen, History-Tabelle live, Show solution, Next word (Skip),
  stabiler Items-Index (kein Vertauschen).
- Unregelmäßige Verbenmemory (aus Code): Tap-to-Match von 4 Feldern
  (Infinitive–Past Simple–Past Participle–Deutsch), tolerant bei Slash-Formen.
"""

import re
import json
import time
import unicodedata
from pathlib import Path
from datetime import datetime
import random
import hashlib

import pandas as pd
import streamlit as st

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
    ("Past Simple", "pastSimple"),
    ("Past Participle", "pastParticiple"),
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

def is_simple_word(word: str, *, ignore_articles: bool = True, ignore_abbrev: bool = True, min_length: int = 2) -> bool:
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
        df[c_page]   = pd.to_numeric(df[c_page],   errors="coerce").astype("Int64")
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

# ============================ CSV-Erkennung & Laden ============================

@st.cache_data(show_spinner=False)
def get_vocab_file_info(data_dir: Path) -> pd.DataFrame:
    file_info = []
    base = Path(data_dir)
    page_pattern = re.compile(r"/data/pages/klasse(\d+)/klasse\1_page(\d+)\.csv$", re.IGNORECASE)
    for path in base.glob("**/*.csv"):
        sp = str(path).replace("\\", "/")
        m = page_pattern.search(sp.lower())
        if m:
            classe, page = int(m.group(1)), int(m.group(2))
            if classe in (7, 8, 9):
                file_info.append({"classe": str(classe), "page": int(page), "path": path, "is_page_specific": True})
    if not file_info:
        return pd.DataFrame(columns=["classe", "page", "path", "is_page_specific"])
    df = pd.DataFrame(file_info).sort_values(["classe", "page"]).reset_index(drop=True)
    return df

@st.cache_data(show_spinner=False)
def load_and_preprocess_df(path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, sep=None, engine="python")
    except Exception as e:
        st.warning(f"CSV-Fehler {path.name}: {e}")
        return pd.DataFrame()
    col_map = {}
    for c in df.columns:
        lc = str(c).strip().lower()
        if lc in {"klasse", "class", "classe"}: col_map[c] = "classe"
        elif lc in {"seite", "page", "pg"}:      col_map[c] = "page"
        elif lc in {"de","german","deutsch","wort","vokabel","vokabel_de"}: col_map[c] = "de"
        elif lc in {"en","englisch","english","translation","vokabel_en"}:  col_map[c] = "en"
    df = df.rename(columns=col_map)
    for req in ["classe", "page", "de", "en"]:
        if req not in df.columns:
            df[req] = None
    df = df[["classe", "page", "de", "en"]].copy()
    df["de"] = df["de"].astype(str).str.strip()
    df["en"] = df["en"].astype(str).str.strip()
    df = df.dropna(how="all", subset=["de", "en"])
    return df

# ============================ Timer-UI ============================

def _timer_block(label_prefix, timer, rerun_key, extra_reset=None):
    now_ms = int(time.time() * 1000)
    current_ms = timer["elapsed_ms"] + (now_ms - timer["started_ms"] if timer["running"] else 0)
    colT1, colT2, colT3, colT4 = st.columns([1.2, 1, 1, 1])
    with colT1:
        st.metric(f"{label_prefix} Time", fmt_ms(current_ms))
    with colT2:
        if st.button("Start", key=f"{rerun_key}_start"):
            if not timer["running"]:
                timer["running"] = True
                timer["started_ms"] = int(time.time() * 1000) - timer["elapsed_ms"]
                st.rerun()
    with colT3:
        if st.button("Pause", key=f"{rerun_key}_pause"):
            if timer["running"]:
                now_ms = int(time.time() * 1000)
                timer["elapsed_ms"] = now_ms - timer["started_ms"]
                timer["running"] = False
                st.rerun()
    with colT4:
        if st.button("Reset", key=f"{rerun_key}_reset"):
            timer["running"] = False
            timer["started_ms"] = 0
            timer["elapsed_ms"] = 0
            if extra_reset:
                extra_reset()
            st.rerun()

# ============================ Hash/Subset Utils ============================

def _hash_dict_list(items, keys) -> str:
    m = hashlib.sha256()
    for it in items:
        vals = [str(it.get(k,"")) for k in keys]
        m.update(("||".join(vals)).encode("utf-8"))
    return m.hexdigest()

def _sample_subset(items, mode, k, seed_val, state_key, hash_keys):
    base_hash = _hash_dict_list(items, hash_keys)
    st_state = st.session_state.get(state_key)
    need_new = (
        st_state is None or
        st_state.get("base_hash") != base_hash or
        st_state.get("mode") != mode or
        (mode == "k" and st_state.get("k") != int(k))
    )
    if not need_new:
        return st_state["subset"]
    if mode == "all" or int(k) >= len(items):
        subset = list(items)
    else:
        order = list(range(len(items)))
        rnd = random.Random(seed_val) if seed_val else random.Random()
        rnd.shuffle(order)
        subset = [items[i] for i in order[:max(1, int(k))]]
    st.session_state[state_key] = {"base_hash": base_hash, "mode": mode, "k": int(k), "subset": subset}
    return subset

# ============================ Spiele ============================

# ---------- Hangman ----------
def game_hangman(df_view: pd.DataFrame, classe: str, page: int, seed_val: str):
    key = f"hangman_{classe}_{page}"
    state = st.session_state.get(key)
    rows = df_view.to_dict("records")
    if not rows:
        st.info("No vocabulary available.")
        return
    if state is None:
        order = list(range(len(rows)))
        rnd = random.Random(seed_val) if seed_val else random.Random()
        rnd.shuffle(order)
        row = rows[order[0]]
        state = {"order": order, "idx": 0, "solution": row["en"], "hint": row["de"],
                 "guessed": set(), "fails": 0, "solved": False,
                 "timer": {"running": False, "started_ms": 0, "elapsed_ms": 0},
                 "show_hint": False}
        st.session_state[key] = state

    def _set_word(idx):
        i = state["order"][idx]
        state["solution"] = rows[i]["en"]
        state["hint"] = rows[i]["de"]
        state["guessed"] = set()
        state["fails"] = 0
        state["solved"] = False

    def next_word():
        t = state["timer"]; t["running"] = False; t["started_ms"] = 0; t["elapsed_ms"] = 0
        state["idx"] += 1
        if state["idx"] >= len(rows):
            order = list(range(len(rows)))
            rnd = random.Random(seed_val) if seed_val else random.Random()
            rnd.shuffle(order)
            state["order"] = order
            state["idx"] = 0
        _set_word(state["idx"]); st.session_state[key] = state

    def new_word():
        t = state["timer"]; t["running"] = False; t["started_ms"] = 0; t["elapsed_ms"] = 0
        rnd = random.Random(time.time())
        i = rnd.randrange(len(rows)); state["order"][state["idx"]] = i
        _set_word(state["idx"]); st.session_state[key] = state

    solution, hint = state["solution"], state["hint"]
    t = state["timer"]
    _timer_block("Hangman", t, rerun_key=f"{key}_timer")

    opt1, opt2, opt3 = st.columns(3)
    with opt1:
        state["show_hint"] = st.checkbox("Show German hint", value=state.get("show_hint", False), key=f"{key}_showhint")
        st.session_state[key] = state
    with opt2:
        if st.button("Show solution", key=f"{key}_showsol"):
            st.info(f"Solution: {solution}")
    with opt3:
        if st.button("New word (skip)", key=f"{key}_newword"):
            new_word(); st.rerun()

    if state["show_hint"]:
        st.write(f"**German (hint):** {hint}")

    cA, cB = st.columns([1, 2])
    with cA:
        st.text(HANGMAN_PICS[min(state["fails"], len(HANGMAN_PICS)-1)])
    with cB:
        display_word = " ".join([c if (not c.isalpha() or c.lower() in state["guessed"]) else "_" for c in solution])
        st.write("**Word (EN):** " + display_word)
        with st.form(key=f"hang_form_{key}"):
            full_guess = st.text_input("Type the full word (English):", key=f"{key}_full")
            submitted = st.form_submit_button("Check (Enter)")
            if submitted and not state["solved"]:
                if normalize_text(full_guess) == normalize_text(solution):
                    if t["running"]:
                        now_ms2 = int(time.time() * 1000)
                        t["elapsed_ms"] = now_ms2 - t["started_ms"]; t["running"] = False
                    state["solved"] = True; st.session_state[key] = state
                    st.success(f"Congratulations! You solved it. Time: {fmt_ms(t['elapsed_ms'])}")
                else:
                    st.warning("Not correct.")
                st.rerun()

    if not state["solved"]:
        alphabet = list("abcdefghijklmnopqrstuvwxyz")
        for chunk in [alphabet[i:i+7] for i in range(0, len(alphabet), 7)]:
            cols = st.columns(len(chunk))
            for letter, col in zip(chunk, cols):
                with col:
                    if st.button(letter, key=f"{key}_btn_{letter}", disabled=(letter in state["guessed"])):
                        if letter in normalize_text(solution):
                            state["guessed"].add(letter)
                        else:
                            state["fails"] += 1
                        st.session_state[key] = state
                        if all((not c.isalpha()) or (c.lower() in state["guessed"]) for c in solution):
                            if t["running"]:
                                now_ms2 = int(time.time() * 1000)
                                t["elapsed_ms"] = now_ms2 - t["started_ms"]; t["running"] = False
                            state["solved"] = True; st.session_state[key] = state
                            st.success(f"Congratulations! You solved it. Time: {fmt_ms(t['elapsed_ms'])}")
                        st.rerun()
    else:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Next word", key=f"{key}_nextword"):
                next_word(); st.rerun()
        with c2:
            if st.button("New word", key=f"{key}_newword2"):
                new_word(); st.rerun()

# ---------- Wörtermemory (DE↔EN; Click/Tap; optional Drag) ----------
def game_word_memory(df_view: pd.DataFrame, classe: str, page: int,
                     show_solution_table: bool, subset_mode: str, subset_k: int,
                     seed_val: str, force_new_subset: bool = False):
    # Basis-Items
    base_items = [
        {"de": r["de"], "en": r["en"]}
        for r in df_view.to_dict("records")
        if isinstance(r["de"], str) and isinstance(r["en"], str)
    ]
    if not base_items:
        st.info("No vocabulary.")
        return

    # Session-Key für die stabile Auswahl dieses Seiten-Sets
    subset_state_key = f"memory_subset_{classe}_{page}"

    # NEU: auf Knopfdruck die bisherige Auswahl verwerfen → neue Stichprobe
    if force_new_subset:
        st.session_state.pop(subset_state_key, None)

    # Teil-Set ziehen (entweder ganze Seite oder k-Paare)
    items = _sample_subset(base_items, subset_mode, subset_k, seed_val,
                           subset_state_key, ["de", "en"])

    st.write(f"Pairs in this round: **{len(items)}**")
    st.caption("Klicke zwei Karten, die zusammengehören (DE ↔ EN). Optional: Drag-Modus auf Desktop.")

    if show_solution_table:
        st.subheader("Solution (DE — EN)")
        st.dataframe(pd.DataFrame(items)[["de", "en"]].rename(columns={"de": "DE", "en": "EN"}),
                     use_container_width=True)

    # --- Frontend (unverändert) ---
    pairs_json = json.dumps(
        [{"id": i, "de": it["de"], "en": it["en"]} for i, it in enumerate(items)],
        ensure_ascii=False
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
:root {{ --primary:#2196F3; --success:#2e7d32; --muted:#666; --danger:#d32f2f; }}
* {{ -webkit-tap-highlight-color: transparent; }}
body {{
  font-family: Arial, sans-serif; margin:0; padding:10px; background:#f6f7fb;
  -webkit-user-select: none; user-select: none; -webkit-touch-callout: none;
}}
#toolbar {{ display:flex; align-items:center; gap:8px; margin-bottom:10px; flex-wrap:wrap; }}
#timer {{
  font-weight:bold; padding:4px 8px; border:1px solid #ccc; border-radius:6px;
  background:white; min-width:90px; text-align:center;
}}
.btn {{
  padding:6px 10px; border:1px solid var(--primary); background:white; color:var(--primary);
  border-radius:8px; cursor:pointer; font-weight:bold; touch-action: manipulation;
}}
.toggle {{ border-color:#555; color:#555; }}
.btn:disabled {{ opacity:0.5; cursor:not-allowed; }}
.grid {{ display:flex; flex-wrap:wrap; gap:8px; }}
.card {{
  background:white; border:2px solid var(--primary); border-radius:10px;
  padding:10px; margin:5px; min-width:120px; text-align:center;
  touch-action: manipulation; cursor:pointer; transition: transform .06s ease;
  -webkit-user-drag: element;
}}
.card:active {{ transform: scale(0.98); }}
.correct {{ background:#e8f5e9; border-color:var(--success); cursor:default; }}
.selected {{ box-shadow:0 0 0 3px rgba(33,150,243,0.35) inset; }}
.wrong {{ animation: shake .25s linear; border-color: var(--danger)!important; }}
@keyframes shake {{
  0%,100% {{ transform: translateX(0); }}
  25% {{ transform: translateX(-4px); }}
  75% {{ transform: translateX(4px); }}
}}
#result {{ margin-top:10px; font-weight:bold; color:var(--success); }}
</style>
</head>
<body>
<div id="toolbar">
  <span>Time:</span><span id="timer">00:00.0</span>
  <button class="btn" id="startBtn">Start</button>
  <button class="btn" id="pauseBtn">Pause</button>
  <button class="btn" id="resetBtn">Reset</button>
  <button class="btn" id="shuffleBtn">Shuffle</button>
  <button class="btn toggle" id="modeBtn">Mode: </button>
</div>

<div id="box" class="grid" aria-live="polite"></div>
<div id="result"></div>

<script>
const pairs = {pairs_json};
const nativeDnD = ('ondragstart' in document.createElement('div'));
let TAP_MODE = true;

let running = false, timerId = null, startTime = null, elapsed = 0;
let correctPairs = 0, solved = false;
let draggedCard = null;
let selectedCard = null;

function fmt(ms) {{
  const tenths = Math.floor((ms % 1000) / 100);
  ms = Math.floor(ms / 1000);
  const s = ms % 60;
  const m = Math.floor(ms / 60);
  return String(m).padStart(2,'0') + ":" + String(s).padStart(2,'0') + "." + tenths;
}}
function updateTimer() {{
  if (!running) return;
  const now = Date.now();
  document.getElementById('timer').textContent = fmt(now - startTime);
}}
function startTimer() {{
  if (solved) return;
  if (!running) {{
    startTime = Date.now() - elapsed;
    timerId = setInterval(updateTimer, 100);
    running = true;
  }}
}}
function pauseTimer() {{
  if (running) {{
    clearInterval(timerId);
    elapsed = Date.now() - startTime;
    running = false;
  }}
}}
function resetTimer() {{
  clearInterval(timerId);
  running = false; startTime = null; elapsed = 0;
  document.getElementById('timer').textContent = "00:00.0";
}}

function clearBoard() {{
  const box = document.getElementById('box');
  box.innerHTML = "";
  draggedCard = null; selectedCard = null;
  correctPairs = 0; solved = false;
  document.getElementById('result').textContent = "";
}}

function markCorrect(el) {{
  el.classList.add('correct'); el.setAttribute('aria-disabled','true');
  el.style.cursor = 'default';
}}

function createCard(text, pid) {{
  const c = document.createElement('div');
  c.className = 'card';
  c.textContent = text;
  c.setAttribute('data-pid', String(pid));
  c.setAttribute('role', 'button');
  c.setAttribute('tabindex', '0');

  if (TAP_MODE || !nativeDnD) {{
    c.addEventListener('click', () => handleTap(c));
    c.addEventListener('keydown', (e) => {{
      if (e.key === 'Enter' || e.key === ' ') handleTap(c);
    }});
  }} else {{
    c.draggable = true;
    c.addEventListener('dragstart', (e) => {{
      draggedCard = c;
      c.style.opacity = '0.5';
      try {{
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', c.getAttribute('data-pid'));
      }} catch(_e) {{}}
    }});
    c.addEventListener('dragend', () => {{
      c.style.opacity = '1';
    }});
    c.addEventListener('dragover', (e) => {{
      e.preventDefault();
      try {{ e.dataTransfer.dropEffect = 'move'; }} catch(_e) {{}}
    }});
    c.addEventListener('drop', (e) => {{
      e.preventDefault();
      let srcPid = null;
      try {{ srcPid = e.dataTransfer.getData('text/plain'); }} catch(_e) {{}}
      if (!srcPid && draggedCard) srcPid = draggedCard.getAttribute('data-pid');
      const tgtPid = c.getAttribute('data-pid');
      if (!srcPid) return;
      if (srcPid === tgtPid) {{
        if (draggedCard) markCorrect(draggedCard);
        markCorrect(c);
        draggedCard = null;
        correctPairs += 1;
        checkWin();
      }} else {{
        if (draggedCard) shake(draggedCard);
        shake(c);
        if (draggedCard) draggedCard.style.opacity = '1';
        draggedCard = null;
      }}
    }});
  }}
  return c;
}}

function handleTap(card) {{
  if (solved || card.classList.contains('correct')) return;
  if (!selectedCard) {{
    selectedCard = card;
    card.classList.add('selected');
    return;
  }}
  if (selectedCard === card) {{
    card.classList.remove('selected');
    selectedCard = null;
    return;
  }}
  const a = selectedCard.getAttribute('data-pid');
  const b = card.getAttribute('data-pid');
  if (a === b) {{
    markCorrect(selectedCard); markCorrect(card);
    selectedCard.classList.remove('selected');
    selectedCard = null;
    correctPairs += 1; checkWin();
  }} else {{
    shake(selectedCard); shake(card);
    selectedCard.classList.remove('selected');
    selectedCard = null;
  }}
}}

function shake(el) {{
  el.classList.remove('wrong');
  void el.offsetWidth;
  el.classList.add('wrong');
  setTimeout(() => el.classList.remove('wrong'), 250);
}}

function shuffleArray(arr) {{
  for (let i = arr.length - 1; i > 0; i--) {{
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }}
  return arr;
}}

function layoutShuffled() {{
  clearBoard();
  const box = document.getElementById('box');
  let cards = [];
  for (const p of pairs) {{
    cards.push({{ text: p.de, pid: p.id }});
    cards.push({{ text: p.en, pid: p.id }});
  }}
  shuffleArray(cards);
  for (const c of cards) {{
    box.appendChild(createCard(c.text, c.pid));
  }}
}}

function checkWin() {{
  if (correctPairs === pairs.length && !solved) {{
    solved = true;
    pauseTimer();
    const timeText = document.getElementById('timer').textContent;
    const msg = "Congratulations! Time: " + timeText;
    document.getElementById('result').textContent = msg;
    alert(msg);
  }}
}}

function setModeLabel() {{
  const b = document.getElementById('modeBtn');
  b.textContent = "Mode: " + (TAP_MODE || !nativeDnD ? "Tap" : "Drag");
}}

document.getElementById('startBtn').addEventListener('click', () => startTimer());
document.getElementById('pauseBtn').addEventListener('click', () => pauseTimer());
document.getElementById('resetBtn').addEventListener('click', () => {{ resetTimer(); layoutShuffled(); }});
document.getElementById('shuffleBtn').addEventListener('click', () => {{ resetTimer(); layoutShuffled(); }});
document.getElementById('modeBtn').addEventListener('click', () => {{
  if (!nativeDnD) return;
  TAP_MODE = !TAP_MODE;
  setModeLabel();
  layoutShuffled();
}});

// Initial
setModeLabel();
layoutShuffled();
</script>
</body>
</html>"""

    st.components.v1.html(html, height=600, scrolling=True)


# ---------- Eingabe (DE → EN) ----------
def game_input(df_view: pd.DataFrame, classe: str, page: int):
    items = [{"de": r["de"], "en": r["en"]} for r in df_view.to_dict("records") if isinstance(r["de"], str) and isinstance(r["en"], str)]
    if not items:
        st.info("No vocabulary.")
        return
    state_key = f"input_state_{classe}_{page}"
    st_state = st.session_state.get(state_key)
    items_hash = _hash_dict_list(items, ["de","en"])
    if (st_state is None) or (st_state.get("items_hash") != items_hash):
        order = list(range(len(items))); random.Random().shuffle(order)
        st_state = {"items_hash": items_hash, "items": items, "order": order, "index": 0,
                    "score": 0, "total": 0, "history": [], "timer": {"running": False, "started_ms": 0, "elapsed_ms": 0}}
        st.session_state[state_key] = st_state
    _timer_block("Input", st_state["timer"], rerun_key=f"{state_key}_timer")
    i = st_state["index"]
    if i >= len(st_state["order"]):
        t = st_state["timer"]
        final_ms = t["elapsed_ms"] + (int(time.time() * 1000) - t["started_ms"] if t["running"] else 0)
        t["running"] = False
        st.success(f"Congratulations! You finished. Score: {st_state['score']} / {st_state['total']} — Time: {fmt_ms(final_ms)}")
        if st_state["history"]:
            df_hist = pd.DataFrame(st_state["history"])
            st.subheader("History")
            st.dataframe(df_hist.rename(columns={"de": "DE", "user": "Your answer", "en": "EN (correct)", "result": "Result"}), use_container_width=True)
        return
    idx = st_state["order"][i]; item = st_state["items"][idx]
    st.write(f"**German (DE):** {item['de']}")
    cskip, csol = st.columns(2)
    with cskip:
        if st.button("Next word (skip)", key=f"{state_key}_skip_{i}"):
            st_state["history"].append({"de": item["de"], "user": "", "en": item["en"], "result": "Skipped"})
            st_state["index"] += 1; st.session_state[state_key] = st_state; st.rerun()
    with csol:
        if st.button("Show solution", key=f"{state_key}_showsol_{i}"):
            st.info(f"Solution: {item['de']} — {item['en']}")
    with st.form(key=f"input_form_{state_key}_{i}", clear_on_submit=True):
        user = st.text_input("English (EN):", key=f"user_{state_key}_{i}")
        submitted = st.form_submit_button("Check (Enter)")
    if submitted:
        st_state["total"] += 1
        ok = normalize_text(user) == normalize_text(item["en"])
        res = "Correct" if ok else "Wrong"
        if ok:
            st_state["score"] += 1; st.success("Correct!")
        else:
            st.warning("Wrong.")
        st_state["history"].append({"de": item["de"], "user": user, "en": item["en"], "result": res})
        st_state["index"] += 1; st.session_state[state_key] = st_state; st.rerun()
    if st_state["history"]:
        df_hist = pd.DataFrame(st_state["history"])
        st.subheader("History (so far)")
        st.dataframe(df_hist.rename(columns={"de": "DE", "user": "Your answer", "en": "EN (correct)", "result": "Result"}).tail(10), use_container_width=True)

# ---------- Unregelmäßige Verbenmemory (aus Code) ----------
def game_irregulars_assign():
    def _norm(s: str) -> str:
        return s.strip().lower()
    def allowed_forms(target_key: str, verb: dict) -> set[str]:
        raw = verb[target_key]
        forms = [raw] + ([p.strip() for p in raw.split("/")] if "/" in raw else [])
        return {_norm(x) for x in forms}

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
            "matches": {t[1]: None for t in VERB_TARGETS},
            "start_ts": int(time.time()),
            "completed": False,
        }
        st.session_state.verbs_selected_idx = None
        if "verbs_word_radio" in st.session_state:
            del st.session_state["verbs_word_radio"]

    if "verbs_round" not in st.session_state:
        new_round()
    if "verbs_selected_idx" not in st.session_state:
        st.session_state.verbs_selected_idx = None

    st.subheader("Unregelmäßige Verbenmemory (Tippen statt Ziehen)")
    st.caption("Links ein **Wort** wählen, rechts das **Ziel** tippen. Slash-Formen (z. B. was/were) werden akzeptiert.")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🔁 Runde neu starten"):
            new_round(); st.rerun()
    with c2:
        if st.button("🧹 Punkte zurücksetzen"):
            st.session_state.verbs_points_total = 0; new_round(); st.rerun()
    with c3:
        if st.button("❌ Auswahl aufheben"):
            st.session_state.verbs_selected_idx = None
            if "verbs_word_radio" in st.session_state:
                del st.session_state["verbs_word_radio"]
            st.rerun()

    elapsed = int(time.time() - st.session_state.verbs_round["start_ts"])
    st.markdown(f"**Zeit:** {elapsed} Sek.  **Punkte gesamt:** {st.session_state.verbs_points_total}")

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown("#### Wörter")
        options = [(idx, it["text"]) for idx, it in enumerate(st.session_state.verbs_round["items"]) if not it["hidden"]]
        if options:
            labels = ["— bitte wählen —"] + [txt for _, txt in options]
            indices = [None] + [idx for idx, _ in options]
            if st.session_state.verbs_selected_idx is not None:
                if st.session_state.verbs_round["items"][st.session_state.verbs_selected_idx]["hidden"]:
                    st.session_state.verbs_selected_idx = None
                    if "verbs_word_radio" in st.session_state:
                        del st.session_state["verbs_word_radio"]
            if "verbs_word_radio" in st.session_state and st.session_state["verbs_word_radio"] in labels:
                chosen_label = st.radio("Wähle ein Wort", labels, key="verbs_word_radio")
            else:
                chosen_label = st.radio("Wähle ein Wort", labels, index=0, key="verbs_word_radio")
            st.session_state.verbs_selected_idx = indices[labels.index(chosen_label)]
            if st.session_state.verbs_selected_idx is not None:
                st.info(f"Ausgewählt: **{chosen_label}**")
        else:
            st.write("Alle Wörter sind zugeordnet ✅")

    with right:
        st.markdown("#### Ziele")
        for label, target_key in VERB_TARGETS:
            current_match = st.session_state.verbs_round["matches"][target_key]
            if current_match is None:
                clicked = st.button(label, key=f"verbs_target_{target_key}")
            else:
                matched_text = st.session_state.verbs_round["items"][current_match]["text"]
                clicked = st.button(f"{label}: ✅ {matched_text}", key=f"verbs_target_{target_key}", disabled=True)
            if clicked:
                sel_idx = st.session_state.verbs_selected_idx
                if sel_idx is None:
                    st.warning("Bitte erst links ein Wort auswählen.")
                else:
                    item = st.session_state.verbs_round["items"][sel_idx]
                    allowed = allowed_forms(target_key, st.session_state.verbs_round["verb"])
                    if normalize_text(item["text"]) in allowed:
                        st.session_state.verbs_round["matches"][target_key] = sel_idx
                        st.session_state.verbs_round["items"][sel_idx]["hidden"] = True
                        st.session_state.verbs_selected_idx = None
                        if "verbs_word_radio" in st.session_state:
                            del st.session_state["verbs_word_radio"]
                        st.success("Richtig! ✅"); st.rerun()
                    else:
                        st.error("Falsch – wähle ein anderes Ziel (Auswahl bleibt).")

    all_done = all(v is not None for v in st.session_state.verbs_round["matches"].values())
    if all_done and not st.session_state.verbs_round["completed"]:
        st.session_state.verbs_round["completed"] = True
        total_time = int(time.time() - st.session_state.verbs_round["start_ts"])
        st.success(f"Geschafft! Zeit: {total_time} Sek.")
        if st.button("Nächste Runde starten"):
            new_round(); st.rerun()

# ============================ Main ============================

def main():
    st.set_page_config(page_title="Wortschatz-Spiele (Klassen 7–9)", page_icon="📚", layout="wide")
    st.title("Wortschatz-Spiele (Klassen 7–9) – Grundkurs")

    c_left, c_mid, c_debug = st.columns([2, 1, 1])
    with c_left:
        st.caption("Quelle: CSVs unter `/data/pages/klasseK/klasseK_pageS.csv`. Unregelmäßige Verben sind im Code enthalten.")
    with c_mid:
        if st.button("Cache leeren"):
            st.cache_data.clear(); st.rerun()
    with c_debug:
        debug_on = st.toggle("Debug an/aus", value=False)

    DATA_DIR = Path(__file__).parent / "data"

    # --- Seiten-Vokabeln (DE↔EN) ---
    file_info_df = get_vocab_file_info(DATA_DIR)
    file_info_df = file_info_df[file_info_df["classe"].isin({"7", "8", "9"})]
    file_info_df = file_info_df[file_info_df["is_page_specific"] == True]

    classe = None; pages = []
    if not file_info_df.empty:
        classe = st.selectbox("Klasse", sorted(file_info_df["classe"].unique(), key=int), index=2)
        pages = sorted(file_info_df[file_info_df["classe"] == classe]["page"].unique(), key=int)
        if pages:
            page = st.selectbox("Seite", pages, index=0)
        else:
            page = None
    else:
        page = None

    df_view = pd.DataFrame()
    if file_info_df.empty or page is None:
        st.info("Seiten-Vokabeln nicht verfügbar oder keine Seite gewählt. DE↔EN-Spiele sind begrenzt.")
    else:
        page_specific_paths = file_info_df[(file_info_df['classe'] == classe) & (file_info_df['page'] == page)]['path']
        if not page_specific_paths.empty:
            df_view = load_and_preprocess_df(page_specific_paths.iloc[0])
            df_view = _filter_by_page_rows(df_view, int(classe), int(page))
        st.write(f"**Vokabeln verfügbar (Seite):** {len(df_view)}")

    if debug_on:
        with st.expander("Debug-Info"):
            st.write("Datei-Info (erste 50):", file_info_df.head(50))
            st.write("Beispiel-Daten (erste 20):", df_view.head(20) if not df_view.empty else "—")
            if not df_view.empty:
                st.write("Seitenverteilung:", df_view["page"].value_counts().head(10))

    # Filter für DE↔EN
    if not df_view.empty:
        st.subheader("Filter: Nur Einzelwörter")
        col1, col2, col3 = st.columns([1.5, 1, 1])
        with col1:
            filter_simple = st.checkbox("Nur Einzelwörter aktivieren", value=False)
        with col2:
            ignore_articles = st.checkbox("Artikel (to/the/a/an) ignorieren", value=True)
        with col3:
            ignore_abbrev = st.checkbox("Abkürzungen (z. B. sth/sb) ignorieren", value=True)
        min_length = st.slider("Minimale Wortlänge", 1, 6, 2, 1)
        if filter_simple:
            mask = df_view["en"].apply(lambda x: is_simple_word(x, ignore_articles=ignore_articles, ignore_abbrev=ignore_abbrev, min_length=min_length))
            df_view = df_view[mask].reset_index(drop=True)
            st.write(f"**Vokabeln nach Filter:** {len(df_view)}")
            if df_view.empty:
                st.info("Der Filter entfernt alle Vokabeln. Passe die Einstellungen an.")

    seed_val = st.text_input("Seed (optional – gleiche Reihenfolge/Subsets)", value="")
    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # WICHTIG: Hier steht das neue Spiel GENAU so im Menü, wie du es wolltest
    game = st.selectbox("Wähle ein Spiel", (
        "Hangman",
        "Wörtermemory",
        "Eingabe (DE → EN)",
        "Unregelmäßige Verbenmemory",
    ))
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    if game == "Hangman":
        if df_view.empty:
            st.info("Für Hangman sind Seiten-Vokabeln nötig.")
        else:
            game_hangman(df_view, classe, page, seed_val)

    elif game == "Wörtermemory":
        if df_view.empty:
            st.info("Für Wörtermemory sind Seiten-Vokabeln nötig.")
        else:
            max_pairs = len(df_view)

            cA, cB, cC = st.columns([1, 1, 1.5])
            with cA:
                subset_all = st.checkbox("Ganze Seite abfragen", value=True)
            with cB:
                if subset_all:
                    subset_k = max_pairs
                    st.number_input("Anzahl Paare", min_value=2, max_value=max_pairs,
                                    value=max_pairs, step=1, disabled=True)
                else:
                    default_k = min(10, max_pairs) if max_pairs >= 2 else max_pairs
                    subset_k = st.number_input("Anzahl Paare", min_value=2, max_value=max_pairs,
                                                value=default_k, step=1)
            with cC:
                show_solution_table = st.checkbox("Show solution (as list: DE — EN)", value=False)

            # NEU: Button, der eine neue Stichprobe aus der Seite erzwingt
            col_new, _ = st.columns([1, 3])
            with col_new:
                refresh_subset = st.button(
                    "Neue Wortauswahl (neue Paare)",
                    disabled=subset_all or max_pairs < 2,
                    help="Zieht ein neues zufälliges Teil-Set von dieser Seite."
                )

            subset_mode = "all" if subset_all else "k"

            game_word_memory(
                df_view, classe, page,
                show_solution_table, subset_mode, int(subset_k),
                seed_val,
                force_new_subset=refresh_subset
            )


    elif game == "Eingabe (DE → EN)":
        if df_view.empty:
            st.info("Für das Eingabe-Spiel sind Seiten-Vokabeln nötig.")
        else:
            game_input(df_view, classe, page)

    else:  # Unregelmäßige Verbenmemory
        game_irregulars_assign()

    st.caption(f"Sitzung: {datetime.now().strftime('%d.%m.%Y %H:%M')} — Geladene Vokabeln (Seite): {len(df_view)}")

if __name__ == "__main__":
    main()
