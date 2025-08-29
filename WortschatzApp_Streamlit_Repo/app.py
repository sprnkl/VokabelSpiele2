"""
Wortschatz-Spiele (Klassen 7–9)

Nur "Nur diese Seite": seiten-spezifische CSVs unter data/pages/klasseK/klasseK_pageS.csv
Spalten: classe, page, de, en

Spiele/Features:
- Hangman: Timer, Congrats+Time, Show solution, Show German hint (optional),
  Next word (Sequenz) & New word (Skip).
- Wörter ziehen: Timer, Congrats+Time, Show solution als Tabelle (DE — EN),
  Drag&Drop (Desktop inkl. Safari/macOS) mit dataTransfer.setData,
  Auto-Tap-Modus (iOS), Mode-Schalter im Spiel.
- Eingabe (DE→EN): Enter zum Prüfen, History-Tabelle live, Show solution (DE — EN),
  Next word (Skip), stabiler Items-Index (kein Vertauschen).
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
    file_info = []
    base = Path(data_dir)
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
    try:
        df = pd.read_csv(path, sep=None, engine="python")
    except Exception as e:
        st.warning(f"CSV-Fehler {path.name}: {e}")
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
        idx = 0
        row = rows[order[idx]]
        state = {
            "order": order,
            "idx": idx,
            "solution": row["en"],
            "hint": row["de"],
            "guessed": set(),
            "fails": 0,
            "solved": False,
            "timer": {"running": False, "started_ms": 0, "elapsed_ms": 0},
            "show_hint": False,
        }
        st.session_state[key] = state

    def next_word():
        t = state["timer"]
        t["running"] = False
        t["started_ms"] = 0
        t["elapsed_ms"] = 0
        state["idx"] += 1
        if state["idx"] >= len(rows):
            order = list(range(len(rows)))
            rnd = random.Random(seed_val) if seed_val else random.Random()
            rnd.shuffle(order)
            state["order"] = order
            state["idx"] = 0
        i = state["order"][state["idx"]]
        state["solution"] = rows[i]["en"]
        state["hint"] = rows[i]["de"]
        state["guessed"] = set()
        state["fails"] = 0
        state["solved"] = False
        st.session_state[key] = state

    def new_word():
        t = state["timer"]
        t["running"] = False
        t["started_ms"] = 0
        t["elapsed_ms"] = 0
        rnd = random.Random(time.time())
        i = rnd.randrange(len(rows))
        state["solution"] = rows[i]["en"]
        state["hint"] = rows[i]["de"]
        state["guessed"] = set()
        state["fails"] = 0
        state["solved"] = False
        st.session_state[key] = state

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
            new_word()
            st.rerun()

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
                        t["elapsed_ms"] = now_ms2 - t["started_ms"]
                        t["running"] = False
                    state["solved"] = True
                    st.session_state[key] = state
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
                                t["elapsed_ms"] = now_ms2 - t["started_ms"]
                                t["running"] = False
                            state["solved"] = True
                            st.session_state[key] = state
                            st.success(f"Congratulations! You solved it. Time: {fmt_ms(t['elapsed_ms'])}")
                        st.rerun()
    else:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Next word", key=f"{key}_nextword"):
                next_word()
                st.rerun()
        with c2:
            if st.button("New word", key=f"{key}_newword2"):
                new_word()
                st.rerun()


# ---------- Wörter ziehen (Drag & Drop + Tap-to-Match) ----------

def game_drag_pairs(df_view: pd.DataFrame, show_solution_table: bool):
    """
    Desktop (inkl. Safari/macOS): HTML5-Drag mit dataTransfer.setData
    iOS (iPhone/iPad): Tap-to-Match (Drag nicht zuverlässig verfügbar)
    Umschaltbar im Spiel (auf iOS bleibt Tap erzwungen)
    """
    pairs = [
        {"id": i, "de": r["de"], "en": r["en"]}
        for i, r in enumerate(df_view.to_dict("records"))
        if isinstance(r["de"], str) and isinstance(r["en"], str)
    ]
    if not pairs:
        st.info("No vocabulary.")
        return

    st.write("Match the cards (DE ↔ EN).")
    st.caption("On iPhone/iPad, drag is limited by Safari – tap two cards to match instead.")

    if show_solution_table:
        st.subheader("Solution (DE — EN)")
        st.dataframe(pd.DataFrame(pairs)[["de", "en"]].rename(columns={"de": "DE", "en": "EN"}), use_container_width=True)

    pairs_json = json.dumps(pairs, ensure_ascii=False)

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

const isiOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
               (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

// Feature detection: native drag&drop vorhanden?
const nativeDnD = ('ondragstart' in document.createElement('div'));

// Startmodus: iOS -> Tap, sonst Drag
let TOUCH_MODE = isiOS ? true : false;

let running = false, timerId = null, startTime = null, elapsed = 0; // ms
let correctPairs = 0, solved = false;
let draggedCard = null;       // für native DnD (Desktop)
let selectedCard = null;      // für Tap-to-Match

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

  if (TOUCH_MODE || !nativeDnD) {{
    // Tap-to-Match
    c.addEventListener('click', () => handleTap(c));
    c.addEventListener('keydown', (e) => {{
      if (e.key === 'Enter' || e.key === ' ') handleTap(c);
    }});
  }} else {{
    // Native HTML5 Drag&Drop (Desktop + Safari/macOS)
    c.draggable = true;
    c.addEventListener('dragstart', (e) => {{
      draggedCard = c;
      c.style.opacity = '0.5';
      try {{
        // Safari/macOS benötigt setData, sonst wird kein 'drop' ausgelöst
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
      if (solved) return;
      let srcPid = null;
      try {{ srcPid = e.dataTransfer.getData('text/plain'); }} catch(_e) {{}}
      if (!srcPid && draggedCard) {{
        srcPid = draggedCard.getAttribute('data-pid');
      }}
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
  void el.offsetWidth; // reflow
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
  b.textContent = "Mode: " + (TOUCH_MODE || !nativeDnD ? "Tap" : "Drag");
  if (isiOS) {{
    b.disabled = true; b.title = "Tap mode is enforced on iOS Safari";
  }}
}}

document.getElementById('startBtn').addEventListener('click', () => startTimer());
document.getElementById('pauseBtn').addEventListener('click', () => pauseTimer());
document.getElementById('resetBtn').addEventListener('click', () => {{ resetTimer(); layoutShuffled(); }});
document.getElementById('shuffleBtn').addEventListener('click', () => {{ resetTimer(); layoutShuffled(); }});
document.getElementById('modeBtn').addEventListener('click', () => {{
  if (isiOS) return; // auf iOS bleibt Tap
  TOUCH_MODE = !TOUCH_MODE;
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

def _hash_items(items):
    m = hashlib.sha256()
    for it in items:
        m.update((str(it.get("de","")) + "||" + str(it.get("en",""))).encode("utf-8"))
    return m.hexdigest()

def game_input(df_view: pd.DataFrame, classe: str, page: int):
    """
    Eingabespiel (DE→EN):
    - Stabiler Items-Index im State (keine Vertauschungen)
    - Timer, Enter zum Prüfen
    - Show solution (DE — EN), Next word (skip)
    - Live-History mit Result (Correct/Wrong/Skipped)
    """
    items = [
        {"de": r["de"], "en": r["en"]}
        for r in df_view.to_dict("records")
        if isinstance(r["de"], str) and isinstance(r["en"], str)
    ]
    if not items:
        st.info("No vocabulary.")
        return

    state_key = f"input_state_{classe}_{page}"
    st_state = st.session_state.get(state_key)

    items_hash = _hash_items(items)
    if (st_state is None) or (st_state.get("items_hash") != items_hash):
        order = list(range(len(items)))
        random.Random().shuffle(order)
        st_state = {
            "items_hash": items_hash,
            "items": items,
            "order": order,
            "index": 0,
            "score": 0,
            "total": 0,
            "history": [],  # {de, user, en, result}
            "timer": {"running": False, "started_ms": 0, "elapsed_ms": 0},
        }
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
            st.dataframe(
                df_hist.rename(columns={
                    "de": "DE", "user": "Your answer", "en": "EN (correct)", "result": "Result"
                }),
                use_container_width=True
            )
        return

    idx = st_state["order"][i]
    item = st_state["items"][idx]
    st.write(f"**German (DE):** {item['de']}")

    cskip, csol = st.columns(2)
    with cskip:
        if st.button("Next word (skip)", key=f"{state_key}_skip_{i}"):
            st_state["history"].append({"de": item["de"], "user": "", "en": item["en"], "result": "Skipped"})
            st_state["index"] += 1
            st.session_state[state_key] = st_state
            st.rerun()
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
            st_state["score"] += 1
            st.success("Correct!")
        else:
            st.warning("Wrong.")
        st_state["history"].append({"de": item["de"], "user": user, "en": item["en"], "result": res})
        st_state["index"] += 1
        st.session_state[state_key] = st_state
        st.rerun()

    if st_state["history"]:
        df_hist = pd.DataFrame(st_state["history"])
        st.subheader("History (so far)")
        st.dataframe(
            df_hist.rename(columns={"de": "DE", "user": "Your answer", "en": "EN (correct)", "result": "Result"}).tail(10),
            use_container_width=True
        )


# ============================ Main ============================

def main():
    st.set_page_config(page_title="Wortschatz-Spiele (Klassen 7–9)", page_icon="📚", layout="wide")
    st.title("Wortschatz-Spiele (Klassen 7–9) – Nur 'Diese Seite'")

    c_left, c_mid, c_debug = st.columns([2, 1, 1])
    with c_left:
        st.caption("Quelle: CSVs unter `/data/pages/klasseK/klasseK_pageS.csv`.")
    with c_mid:
        if st.button("Cache leeren"):
            st.cache_data.clear(); st.rerun()
    with c_debug:
        debug_on = st.toggle("Debug an/aus", value=False)

    DATA_DIR = Path(__file__).parent / "data"

    file_info_df = get_vocab_file_info(DATA_DIR)
    file_info_df = file_info_df[file_info_df["classe"].isin({"7", "8", "9"})]
    file_info_df = file_info_df[file_info_df["is_page_specific"] == True]

    if file_info_df.empty:
        st.warning("Keine seiten-spezifischen CSVs für Klassen 7–9 gefunden.")
        return

    classe = st.selectbox("Klasse", sorted(file_info_df["classe"].unique(), key=int), index=2)
    pages = sorted(file_info_df[file_info_df["classe"] == classe]["page"].unique(), key=int)
    if not pages:
        st.warning(f"Keine Seiten für Klasse {classe} gefunden.")
        return

    page = st.selectbox("Seite", pages, index=0)

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

    if debug_on:
        with st.expander("Debug-Info"):
            st.write("Datei-Info (erste 50):", file_info_df.head(50))
            st.write("Beispiel-Daten (erste 20):", df_view.head(20))
            st.write("Seitenverteilung:", df_view["page"].value_counts().head(10))

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
    game = st.selectbox("Wähle ein Spiel", ("Hangman", "Wörter ziehen", "Eingabe (DE → EN)"))

    if game == "Hangman":
        game_hangman(df_view, classe, page, seed_val)
    elif game == "Wörter ziehen":
        show_solution_table = st.checkbox("Show solution (as list: DE — EN)", value=False)
        game_drag_pairs(df_view, show_solution_table=show_solution_table)
    else:
        game_input(df_view, classe, page)

    st.caption(f"Sitzung: {datetime.now().strftime('%d.%m.%Y %H:%M')} — Insgesamt geladene Vokabeln: {len(df_view)}")


if __name__ == "__main__":
    main()
