"""
Wortschatz-Spiele (Klassen 7–9)

Vereinfachte, robuste Version:
- Nur "Nur diese Seite": Es werden ausschließlich seiten-spezifische CSVs genutzt
  (data/pages/klasseK/klasseK_pageS.csv). Kein "bis einschließlich"-Modus.
- Nach dem Laden wird zusätzlich zeilenweise auf (classe==K, page==S) gefiltert.
- CSVs werden rekursiv aus data/ geladen, Trennzeichen automatisch (Komma/Semikolon).
- Spalten werden normalisiert auf: classe, page, de, en.
- Spiele: Galgenmännchen (Hangman), Wörter ziehen (Drag & Drop), Eingabe (DE→EN).
- Optionaler Filter: "Nur Einzelwörter".

Neu:
- "Wörter ziehen": Timer (Start/Pause/Reset), englische Meldungen, "Show solution", Gratulation + Zeit
- "Eingabe (DE→EN)": Timer (Start/Pause/Reset), englische Meldungen, History-Tabelle (Correct/Wrong),
  "Show solution" zeigt DE — EN
- "Hangman": Timer (Start/Pause/Reset), "Show solution", "Show German hint" (optional), Gratulation + Zeit
"""

import re
import json
import time
import unicodedata
from pathlib import Path
from datetime import datetime
import random

import pandas as pd
import streamlit as st


# ============================ Utilities ============================

def normalize_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def is_simple_word(
    word: str,
    *,
    ignore_articles: bool = True,
    ignore_abbrev: bool = True,
    min_length: int = 2,
) -> bool:
    """Heuristik: nur simple Einzelwörter zulassen (für Lernspiele nützlich)."""
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
    """
    Erzwinge zeilenweises Filtern: nur genau die gewählte Seite und Klasse.
    (Schützt vor CSVs, die versehentlich mehrere Seiten enthalten.)
    """
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
    """mm:ss.t (Zehntelsekunde)"""
    if ms < 0: ms = 0
    tenths = (ms % 1000) // 100
    s = (ms // 1000) % 60
    m = (ms // 1000) // 60
    return f"{m:02d}:{s:02d}.{tenths}"


# ============================ Hangman Art ============================

HANGMAN_PICS = [
    " +---+\n     |\n     |\n     |\n    ===",
    " +---+\n O   |\n     |\n     |\n    ===",
    " +---+\n O   |\n |   |\n     |\n    ===",
    " +---+\n O   |\n/|   |\n     |\n    ===",
    " +---+\n O   |\n/|\\  |\n     |\n    ===",
    " +---+\n O   |\n/|\\  |\n/    |\n    ===",
    " +---+\n O   |\n/|\\  |\n/ \\  |\n    ===",
]


# ============================ CSV-Erkennung & Laden ============================

@st.cache_data(show_spinner=False)
def get_vocab_file_info(data_dir: Path) -> pd.DataFrame:
    """
    Scannt das data-Verzeichnis und liefert Metadaten zu seiten-spezifischen CSVs:
    - 'is_page_specific' == True, wenn der Pfad dem Muster data/pages/klasseK/klasseK_pageS.csv entspricht.
    - Wir behalten nur Klassen 7–9.
    """
    file_info = []
    base = Path(data_dir)
    # exakt: .../data/pages/klasse9/klasse9_page157.csv
    page_pattern = re.compile(r"/data/pages/klasse(\d+)/klasse\1_page(\d+)\.csv$", re.IGNORECASE)

    for path in base.glob("**/*.csv"):
        sp = str(path).replace("\\", "/")
        m = page_pattern.search(sp.lower())
        if m:
            classe, page = int(m.group(1)), int(m.group(2))
            if classe in (7, 8, 9):
                file_info.append({
                    "classe": str(classe),
                    "page": int(page),
                    "path": path,
                    "is_page_specific": True,
                })

    if not file_info:
        return pd.DataFrame(columns=["classe", "page", "path", "is_page_specific"])

    df = pd.DataFrame(file_info).sort_values(["classe", "page"]).reset_index(drop=True)
    return df


@st.cache_data(show_spinner=False)
def load_and_preprocess_df(path: Path) -> pd.DataFrame:
    """
    Lädt eine CSV und normalisiert die Spalten auf: classe, page, de, en.
    """
    try:
        df = pd.read_csv(path, sep=None, engine="python")
    except Exception as e:
        st.warning(f"CSV-Fehler {path.name}: {e}")
        return pd.DataFrame()

    # Spalten auf Standardnamen abbilden
    col_map = {}
    for c in df.columns:
        lc = str(c).strip().lower()
        if lc in {"klasse", "class", "classe"}:
            col_map[c] = "classe"
        elif lc in {"seite", "page", "pg"}:
            col_map[c] = "page"
        elif lc in {"de", "german", "deutsch", "wort", "vokabel", "vokabel_de"}:
            col_map[c] = "de"
        elif lc in {"en", "englisch", "english", "translation", "vokabel_en"}:
            col_map[c] = "en"

    df = df.rename(columns=col_map)
    for req in ["classe", "page", "de", "en"]:
        if req not in df.columns:
            df[req] = None

    df = df[["classe", "page", "de", "en"]].copy()
    df["de"] = df["de"].astype(str).str.strip()
    df["en"] = df["en"].astype(str).str.strip()
    df = df.dropna(how="all", subset=["de", "en"])
    return df


# ============================ Spiele-UI ============================

def game_hangman(df_view: pd.DataFrame, classe: str, page: int, seed_val: str):
    """
    Hangman mit:
    - Timer (Start/Pause/Reset)
    - optionalem deutschen Hinweis ("Show German hint")
    - "Show solution"
    - Gratulation + Zeit bei Erfolg
    """
    key = f"hangman_{classe}_{page}_{seed_val}"
    state = st.session_state.get(key)
    rnd = random.Random(seed_val if seed_val else None)

    if state is None:
        if not df_view.empty:
            row = rnd.choice(df_view.to_dict("records"))
            state = {
                "solution": row["en"],
                "hint": row["de"],
                "guessed": set(),
                "fails": 0,
                "solved": False,
                "timer": {"running": False, "started_ms": 0, "elapsed_ms": 0},
                "show_hint": False,
            }
            st.session_state[key] = state
        else:
            st.info("No vocabulary available.")
            return

    solution, hint = state["solution"], state["hint"]
    guessed, fails, solved = state["guessed"], state["fails"], state["solved"]
    t = state["timer"]

    # ----- TIMER -----
    now_ms = int(time.time() * 1000)
    current_ms = t["elapsed_ms"] + (now_ms - t["started_ms"] if t["running"] else 0)

    colT1, colT2, colT3, colT4, colT5 = st.columns([1.2, 1, 1, 1, 1.6])
    with colT1:
        st.metric("Time", fmt_ms(current_ms))
    with colT2:
        if st.button("Start", disabled=solved):
            if not t["running"]:
                t["running"] = True
                t["started_ms"] = int(time.time() * 1000) - t["elapsed_ms"]
                st.session_state[key] = state
                st.rerun()
    with colT3:
        if st.button("Pause", disabled=solved):
            if t["running"]:
                now_ms = int(time.time() * 1000)
                t["elapsed_ms"] = now_ms - t["started_ms"]
                t["running"] = False
                st.session_state[key] = state
                st.rerun()
    with colT4:
        if st.button("Reset timer"):
            t["running"] = False
            t["started_ms"] = 0
            t["elapsed_ms"] = 0
            st.session_state[key] = state
            st.rerun()
    with colT5:
        state["show_hint"] = st.checkbox("Show German hint", value=state.get("show_hint", False), disabled=solved)
        st.session_state[key] = state

    cA, cB = st.columns([1, 1])
    with cA:
        st.text(HANGMAN_PICS[min(fails, len(HANGMAN_PICS)-1)])
    with cB:
        if state["show_hint"]:
            st.write(f"**German (hint):** {hint}")
        if st.button("Show solution"):
            st.info(f"Solution: {solution}")

    def _display_word():
        return " ".join([c if (not c.isalpha() or c.lower() in guessed) else "_" for c in solution])

    st.write("**Word (EN):** " + _display_word())

    def _finish_success():
        # Stop timer and congratulate
        if t["running"]:
            now_ms2 = int(time.time() * 1000)
            t["elapsed_ms"] = now_ms2 - t["started_ms"]
            t["running"] = False
        state["solved"] = True
        st.session_state[key] = state
        st.success(f"Congratulations! You solved it. Time: {fmt_ms(t['elapsed_ms'])}")
        if st.button("Play again"):
            # New random word; reset state
            row2 = rnd.choice(df_view.to_dict("records"))
            st.session_state[key] = {
                "solution": row2["en"],
                "hint": row2["de"],
                "guessed": set(),
                "fails": 0,
                "solved": False,
                "timer": {"running": False, "started_ms": 0, "elapsed_ms": 0},
                "show_hint": False,
            }
            st.rerun()

    # Full-word guess
    with st.form(key=f"full_form_{key}"):
        full_guess = st.text_input("Type the full word (English):", key=f"full_guess_{key}", disabled=solved)
        submitted = st.form_submit_button("Check", disabled=solved)
        if submitted:
            if normalize_text(full_guess) == normalize_text(solution):
                _finish_success()
                return
            else:
                st.warning("Not correct.")

    # Alphabet buttons
    alphabet = list("abcdefghijklmnopqrstuvwxyz")
    rows = [alphabet[i:i+7] for i in range(0, len(alphabet), 7)]
    for rletters in rows:
        cols = st.columns(len(rletters))
        for letter, col in zip(rletters, cols):
            with col:
                if st.button(letter, key=f"{key}_btn_{letter}", disabled=(letter in guessed) or solved):
                    if letter in normalize_text(solution):
                        guessed.add(letter)
                    else:
                        fails += 1
                    state["guessed"], state["fails"] = guessed, fails
                    st.session_state[key] = state
                    # Check success by letters
                    if all((not c.isalpha()) or (c.lower() in guessed) for c in solution):
                        _finish_success()
                        return
                    st.rerun()


def game_drag_pairs(df_view: pd.DataFrame, show_solution: bool):
    """
    Drag&Drop-Paare-Spiel (DE ↔ EN) per HTML/JS mit:
    - Timer (Start / Pause / Reset)
    - „Show solution“ (reveal all pairs)
    - Congratulations + time at the end (English messages)
    """
    pairs = [
        {"id": i, "de": r["de"], "en": r["en"]}
        for i, r in enumerate(df_view.to_dict("records"))
        if isinstance(r["de"], str) and isinstance(r["en"], str)
    ]
    if not pairs:
        st.info("No vocabulary.")
        return

    st.write("Drag the matching cards together (DE ↔ EN).")
    st.caption("Tip: Use 'Shuffle' to restart.")

    pairs_json = json.dumps(pairs, ensure_ascii=False)
    show_solution_js = "true" if show_solution else "false"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
:root {{ --primary:#2196F3; --success:#4CAF50; --muted:#666; }}
body {{ font-family:Arial, sans-serif; margin:0; padding:10px; background:#f6f7fb; }}
#toolbar {{ display:flex; align-items:center; gap:8px; margin-bottom:10px; flex-wrap:wrap; }}
#timer {{ font-weight:bold; padding:4px 8px; border:1px solid #ccc; border-radius:6px; background:white; min-width:90px; text-align:center; }}
.btn {{
  padding:6px 10px; border:1px solid var(--primary); background:white; color:var(--primary);
  border-radius:8px; cursor:pointer; font-weight:bold;
}}
.btn:disabled {{ opacity:0.5; cursor:not-allowed; }}
.grid {{ display:flex; flex-wrap:wrap; gap:8px; }}
.card {{
  background:white; border:2px solid var(--primary); border-radius:10px;
  padding:10px; margin:5px; cursor:grab; user-select:none; min-width:120px;
}}
.correct {{ background:#e8f5e9; border-color:var(--success); cursor:default; }}
.pairrow {{ display:flex; gap:8px; align-items:center; margin-bottom:6px; }}
#result {{ margin-top:10px; font-weight:bold; color:#2e7d32; }}
</style>
</head>
<body>
<div id="toolbar">
  <span>Time:</span><span id="timer">00:00.0</span>
  <button class="btn" id="startBtn">Start</button>
  <button class="btn" id="pauseBtn">Pause</button>
  <button class="btn" id="resetBtn">Reset</button>
  <button class="btn" id="shuffleBtn">Shuffle</button>
  <button class="btn" id="solutionBtn">Show solution</button>
</div>

<div id="box" class="grid"></div>
<div id="result"></div>

<script>
const pairs = {pairs_json};
let SHOW_SOLUTION = {show_solution_js};

let draggedCard = null;
let running = false;
let timerId = null;
let startTime = null;
let elapsed = 0;   // ms
let correctPairs = 0;
let solved = false;

function fmt(ms) {{
  const tenths = Math.floor((ms % 1000) / 100);
  ms = Math.floor(ms / 1000);
  const s = ms % 60;
  const m = Math.floor(ms / 60);
  const mm = String(m).padStart(2,'0');
  const ss = String(s).padStart(2,'0');
  return `${{mm}}:${{ss}}.${{tenths}}`;
}}

function updateTimer() {{
  if (!running) return;
  const now = Date.now();
  const t = now - startTime;
  document.getElementById('timer').textContent = fmt(t);
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
  running = false;
  startTime = null;
  elapsed = 0;
  document.getElementById('timer').textContent = "00:00.0";
}}

function clearBoard() {{
  const box = document.getElementById('box');
  box.innerHTML = "";
  draggedCard = null;
  correctPairs = 0;
  solved = false;
  document.getElementById('result').textContent = "";
}}

function createCard(text, pid) {{
  const c = document.createElement('div');
  c.className = 'card';
  c.textContent = text;
  c.draggable = true;
  c.dataset.pid = String(pid);
  c.addEventListener('dragstart', e => {{ draggedCard = c; c.style.opacity='0.5'; }});
  c.addEventListener('dragend', e => {{ c.style.opacity='1'; }});
  c.addEventListener('dragover', e => e.preventDefault());
  c.addEventListener('drop', e => {{
    e.preventDefault();
    if(!draggedCard || draggedCard===c || solved) return;
    const a = draggedCard.dataset.pid, b = c.dataset.pid;
    if (a === b) {{
      markCorrect(draggedCard);
      markCorrect(c);
      draggedCard = null;
      correctPairs += 1;
      checkWin();
    }} else {{
      alert('Not a valid pair!');
      draggedCard.style.opacity='1';
      draggedCard = null;
    }}
  }});
  return c;
}}

function markCorrect(el) {{
  el.classList.add('correct');
  el.draggable = false;
  el.style.cursor = 'default';
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

function layoutSolution() {{
  clearBoard();
  const box = document.getElementById('box');
  for (const p of pairs) {{
    const row = document.createElement('div');
    row.className = 'pairrow';
    const a = createCard(p.de, p.id);
    const b = createCard(p.en, p.id);
    a.draggable = false; b.draggable = false;
    markCorrect(a); markCorrect(b);
    row.appendChild(a);
    row.appendChild(b);
    box.appendChild(row);
  }}
  document.getElementById('result').textContent = "Solution revealed.";
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

document.getElementById('startBtn').addEventListener('click', () => startTimer());
document.getElementById('pauseBtn').addEventListener('click', () => pauseTimer());
document.getElementById('resetBtn').addEventListener('click', () => {{ resetTimer(); if(!SHOW_SOLUTION) layoutShuffled(); }});
document.getElementById('shuffleBtn').addEventListener('click', () => {{ resetTimer(); layoutShuffled(); }});
document.getElementById('solutionBtn').addEventListener('click', () => {{ SHOW_SOLUTION = true; resetTimer(); layoutSolution(); }});

// Initial
if ({show_solution_js}) {{
  layoutSolution();
}} else {{
  layoutShuffled();
}}
</script>
</body>
</html>"""

    st.components.v1.html(html, height=580, scrolling=True)


def game_input(df_view: pd.DataFrame, classe: str, page: int):
    """
    Eingabespiel: Deutsch anzeigen, Englisch tippen.
    - Timer (Start/Pause/Reset) – English messages at the end
    - History table of attempts (DE, Your answer, EN (correct), Result)
    - "Show solution" displays DE — EN
    """
    rows = df_view.to_dict("records")
    random.shuffle(rows)

    state_key = f"input_state_{classe}_{page}"
    st_state = st.session_state.get(state_key)
    if not st_state:
        st_state = {
            "index": 0,
            "order": list(range(len(rows))),
            "score": 0,
            "total": 0,
            "history": [],  # list of dicts: {de, en, user, correct}
            "timer": {"running": False, "started_ms": 0, "elapsed_ms": 0},
        }
        st.session_state[state_key] = st_state

    # ----- TIMER -----
    t = st_state["timer"]
    now_ms = int(time.time() * 1000)
    current_ms = t["elapsed_ms"] + (now_ms - t["started_ms"] if t["running"] else 0)

    colT1, colT2, colT3, colT4 = st.columns([1, 1, 1, 2])
    with colT1:
        st.metric("Time", fmt_ms(current_ms))
    with colT2:
        if st.button("Start"):
            if not t["running"]:
                t["running"] = True
                t["started_ms"] = int(time.time() * 1000) - t["elapsed_ms"]
                st.session_state[state_key] = st_state
                st.rerun()
    with colT3:
        if st.button("Pause"):
            if t["running"]:
                now_ms = int(time.time() * 1000)
                t["elapsed_ms"] = now_ms - t["started_ms"]
                t["running"] = False
                st.session_state[state_key] = st_state
                st.rerun()
    with colT4:
        if st.button("Reset"):
            t["running"] = False
            t["started_ms"] = 0
            t["elapsed_ms"] = 0
            st.session_state[state_key] = st_state
            st.rerun()

    # ----- GAME LOOP -----
    i = st_state["index"]
    if i >= len(rows):
        # Finished
        final_ms = t["elapsed_ms"] + (int(time.time()*1000) - t["started_ms"] if t["running"] else 0)
        t["running"] = False
        st.success(f"Congratulations! You finished. Score: {st_state['score']} / {st_state['total']} — Time: {fmt_ms(final_ms)}")

        if st_state["history"]:
            df_hist = pd.DataFrame(st_state["history"])
            df_hist["Result"] = df_hist["correct"].map({True: "Correct", False: "Wrong"})
            df_hist = df_hist[["de", "user", "en", "Result"]].rename(columns={"de": "DE", "user": "Your answer", "en": "EN (correct)"})
            st.subheader("History")
            st.dataframe(df_hist, use_container_width=True)
        return

    # Current item
    row = rows[st_state["order"][i]]
    st.write(f"**German (DE):** {row['de']}")
    user = st.text_input("English (EN):", key=f"user_{state_key}_{i}")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Check"):
            st_state["total"] += 1
            ok = normalize_text(user) == normalize_text(row["en"])
            if ok:
                st_state["score"] += 1
                st.success("Correct!")
            else:
                st.warning("Wrong.")
            st_state["history"].append({"de": row["de"], "user": user, "en": row["en"], "correct": ok})
            st_state["index"] += 1
            st.session_state[state_key] = st_state
            st.rerun()
    with c2:
        if st.button("Show solution"):
            st.info(f"Solution: {row['de']} — {row['en']}")
    with c3:
        if st.button("Finish now"):
            # Jump to end (will show final result and time)
            st_state["index"] = len(rows)
            st.session_state[state_key] = st_state
            st.rerun()

    # Live history preview while playing
    if st_state["history"]:
        df_hist = pd.DataFrame(st_state["history"])
        df_hist["Result"] = df_hist["correct"].map({True: "Correct", False: "Wrong"})
        df_hist = df_hist[["de", "user", "en", "Result"]].rename(columns={"de": "DE", "user": "Your answer", "en": "EN (correct)"})
        st.subheader("History (so far)")
        st.dataframe(df_hist.tail(10), use_container_width=True)


# ============================ Main ============================

def main():
    st.set_page_config(page_title="Wortschatz-Spiele (Klassen 7–9)", page_icon="📚", layout="wide")
    st.title("Wortschatz-Spiele (Klassen 7–9) – Nur 'Diese Seite'")

    # Kopfzeile
    c_left, c_mid, c_debug = st.columns([2, 1, 1])
    with c_left:
        st.caption("Quelle: CSVs unter `/data/pages/klasseK/klasseK_pageS.csv`.")
    with c_mid:
        if st.button("Cache leeren"):
            st.cache_data.clear(); st.rerun()
    with c_debug:
        debug_on = st.toggle("Debug an/aus", value=False)

    DATA_DIR = Path(__file__).parent / "data"

    # CSV-Metadaten lesen (nur seiten-spezifisch)
    file_info_df = get_vocab_file_info(DATA_DIR)
    file_info_df = file_info_df[file_info_df["classe"].isin({"7", "8", "9"})]
    file_info_df = file_info_df[file_info_df["is_page_specific"] == True]

    if file_info_df.empty:
        st.warning("Keine seiten-spezifischen CSVs für Klassen 7–9 gefunden.")
        return

    # Auswahl Klasse/Seite
    classe = st.selectbox("Klasse", sorted(file_info_df["classe"].unique(), key=int), index=2)
    pages = sorted(file_info_df[file_info_df["classe"] == classe]["page"].unique(), key=int)
    if not pages:
        st.warning(f"Keine Seiten für Klasse {classe} gefunden.")
        return

    page = st.selectbox("Seite", pages, index=0)

    # Seite laden (nur seiten-spezifische Datei; KEIN Fallback)
    page_specific_paths = file_info_df[
        (file_info_df['classe'] == classe) &
        (file_info_df['page'] == page)
    ]['path']

    if page_specific_paths.empty:
        st.info("Für diese Seite existiert keine seiten-spezifische CSV unter data/pages/klasseX/klasseX_pageY.csv.")
        return

    df_view = load_and_preprocess_df(page_specific_paths.iloc[0])
    df_view = _filter_by_page_rows(df_view, int(classe), int(page))

    if df_view.empty:
        st.info("Keine Vokabeln für diese Seite.")
        return

    st.write(f"**Vokabeln verfügbar:** {len(df_view)}")

    # Debug
    if debug_on:
        with st.expander("Debug-Info"):
            st.write("Datei-Info (erste 50):", file_info_df.head(50))
            st.write("Beispiel-Daten (erste 20):", df_view.head(20))
            st.write("Seitenverteilung:", df_view["page"].value_counts().head(10))

    # Filter: Nur Einzelwörter
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
        mask = df_view["en"].apply(lambda x: is_simple_word(
            x, ignore_articles=ignore_articles, ignore_abbrev=ignore_abbrev, min_length=min_length
        ))
        df_view = df_view[mask].reset_index(drop=True)
        st.write(f"**Vokabeln nach Filter:** {len(df_view)}")
        if df_view.empty:
            st.info("Der Filter entfernt alle Vokabeln. Passe die Einstellungen an.")
            return

    seed_val = st.text_input("Seed (optional – gleiche Reihenfolge für alle)", value="")
    game = st.selectbox("Wähle ein Spiel", ("Galgenmännchen", "Wörter ziehen", "Eingabe (DE → EN)"))

    if game == "Galgenmännchen":
        game_hangman(df_view, classe, page, seed_val)
    elif game == "Wörter ziehen":
        show_solution = st.checkbox("Show solution (reveal all pairs)", value=False)
        game_drag_pairs(df_view, show_solution=show_solution)
    else:
        game_input(df_view, classe, page)

    st.caption(f"Sitzung: {datetime.now().strftime('%d.%m.%Y %H:%M')} — Insgesamt geladene Vokabeln: {len(df_view)}")


if __name__ == "__main__":
    main()
