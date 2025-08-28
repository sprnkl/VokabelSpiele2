"""
Wortschatz-Spiele (Klassen 7–9)

Vereinfachte, robuste Version:
- Nur "Nur diese Seite": Es werden ausschließlich seiten-spezifische CSVs genutzt
  (data/pages/klasseK/klasseK_pageS.csv). Kein "bis einschließlich"-Modus.
- Nach dem Laden wird zusätzlich zeilenweise auf (classe==K, page==S) gefiltert.
- CSVs werden rekursiv aus data/ geladen, Trennzeichen automatisch (Komma/Semikolon).
- Spalten werden normalisiert auf: classe, page, de, en.
- Spiele: Galgenmännchen, Wörter ziehen (Drag & Drop), Eingabe (DE→EN).
- Optionaler Filter: "Nur Einzelwörter".
"""

import os
import re
import json
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
def get_vocab_file_info(data_dir: os.PathLike | str) -> pd.DataFrame:
    """
    Scannt das data-Verzeichnis und liefert Metadaten zu CSVs:
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
        else:
            # Alles, was NICHT dem Muster entspricht, ignorieren wir in dieser Version.
            pass

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
    key = f"hangman_{classe}_{page}_{seed_val}"
    state = st.session_state.get(key)
    rnd = random.Random(seed_val if seed_val else None)

    if state is None:
        if not df_view.empty:
            row = rnd.choice(df_view.to_dict("records"))
            state = {"solution": row["en"], "hint": row["de"], "guessed": set(), "fails": 0}
            st.session_state[key] = state
        else:
            st.warning("Keine Vokabeln verfügbar.")
            return

    solution, hint = state["solution"], state["hint"]
    guessed, fails = state["guessed"], state["fails"]

    st.write(f"**Hinweis (DE):** {hint}")
    st.text(HANGMAN_PICS[min(fails, len(HANGMAN_PICS)-1)])
    display_word = " ".join([c if (not c.isalpha() or c.lower() in guessed) else "_" for c in solution])
    st.write("**Wort (EN):** " + display_word)

    with st.form(key=f"full_form_{key}"):
        full_guess = st.text_input("Gesamtes Wort (engl.) eingeben", key=f"full_guess_{key}")
        submitted = st.form_submit_button("Prüfen")
        if submitted:
            if normalize_text(full_guess) == normalize_text(solution):
                st.success("Richtig!")
                st.session_state.pop(key, None)
                st.rerun()
            else:
                st.warning("Leider falsch.")

    alphabet = list("abcdefghijklmnopqrstuvwxyz")
    rows = [alphabet[i:i+7] for i in range(0, len(alphabet), 7)]
    for r in rows:
        cols = st.columns(len(r))
        for letter, col in zip(r, cols):
            with col:
                if st.button(letter, key=f"{key}_btn_{letter}", disabled=(letter in guessed)):
                    if letter in normalize_text(solution):
                        guessed.add(letter)
                    else:
                        fails += 1
                    state["guessed"], state["fails"] = guessed, fails
                    st.session_state[key] = state
                    st.rerun()


def game_drag_pairs(df_view: pd.DataFrame):
    """Einfaches Drag&Drop-Paare-Spiel (DE ↔ EN) per HTML/JS."""
    pairs = [(r["de"], r["en"]) for _, r in df_view.iterrows() if isinstance(r["de"], str) and isinstance(r["en"], str)]
    st.write("Ziehe passende Karten zusammen (DE ↔ EN).")

    pairs_json = json.dumps(pairs, ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
:root {{ --primary:#2196F3; --success:#4CAF50; }}
body {{ font-family:Arial, sans-serif; margin:0; padding:10px; background:#f6f7fb; }}
.card {{
  background:white; border:2px solid var(--primary); border-radius:10px;
  padding:10px; margin:5px; cursor:grab; user-select:none; min-width:120px;
}}
.grid {{ display:flex; flex-wrap:wrap; gap:8px; }}
.correct {{ background:#e8f5e9; border-color:var(--success); }}
</style>
</head>
<body>
<div id="box" class="grid"></div>
<script>
const pairs = {pairs_json};
let all = [];
for (const [de,en] of pairs) {{
  all.push(de); all.push(en);
}}
all = all.sort(() => Math.random() - 0.5);

const box = document.getElementById('box');
let draggedCard = null;

function isPair(a, b) {{
  for (const [de,en] of pairs) {{
    if ((a === de && b === en) || (a === en && b === de)) return true;
  }}
  return false;
}}

function startGame() {{
  box.innerHTML = '';
  for(const w of all){{
    const c=document.createElement('div'); c.className='card'; c.textContent=w; c.draggable=true;
    c.addEventListener('dragstart',e=>{{draggedCard=e.target; e.target.style.opacity='0.5';}});
    c.addEventListener('dragover',e=>e.preventDefault());
    c.addEventListener('drop',e=>{{
      e.preventDefault(); if(!draggedCard||draggedCard===e.target) return;
      const a=draggedCard.textContent.trim(), b=e.target.textContent.trim();
      if(isPair(a,b)){{ e.target.classList.add('correct'); draggedCard.classList.add('correct'); draggedCard.draggable=false; e.target.draggable=false; draggedCard=null; }}
      else{{ alert('Kein gültiges Paar!'); draggedCard.style.opacity='1'; draggedCard=null; }}
    }});
    c.addEventListener('dragend',e=>e.target.style.opacity='1');
    box.appendChild(c);
  }}
}}
document.addEventListener('DOMContentLoaded',startGame);
</script>
</body>
</html>"""
    st.components.v1.html(html, height=520, scrolling=True)


def game_input(df_view: pd.DataFrame):
    """Eingabespiel: Deutsch anzeigen, Englisch tippen."""
    rows = df_view.to_dict("records")
    random.shuffle(rows)
    st_state = st.session_state.get("input_state")
    if not st_state:
        st_state = {"index": 0, "order": list(range(len(rows))), "score": 0, "total": 0}
        st.session_state["input_state"] = st_state

    i = st_state["index"]
    if i >= len(rows):
        st.success(f"Fertig! Punkte: {st_state['score']} / {st_state['total']}")
        return

    row = rows[st_state["order"][i]]
    st.write(f"**Deutsch:** {row['de']}")
    sol_key = "input_solution"
    user = st.text_input("Englische Übersetzung:", key=f"user_{i}")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Prüfen"):
            st_state["total"] += 1
            if normalize_text(user) == normalize_text(row["en"]):
                st_state["score"] += 1
                st.success("Richtig!")
            else:
                st.warning("Leider falsch.")
            st_state["index"] += 1
            st.session_state["input_state"] = st_state
            st.rerun()
    with c2:
        if st.button("Lösung anzeigen"):
            st.session_state[sol_key] = row["en"]; st.rerun()
    with c3:
        if st.button("Serie beenden"):
            st_state["index"] = len(st_state["order"]); st.session_state["input_state"] = st_state; st.rerun()
    if sol_key in st.session_state:
        st.info(f"Lösung: {st.session_state[sol_key]}")


# ============================ Main ============================

def main():
    st.set_page_config(page_title="Wortschatz-Spiele (Klassen 7–9)", page_icon="📚", layout="wide")
    st.title("Wortschatz-Spiele (Klassen 7–9) – Hauptschule")

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
        game_drag_pairs(df_view)
    else:
        game_input(df_view)

    st.caption(f"Sitzung: {datetime.now().strftime('%d.%m.%Y %H:%M')} — Insgesamt geladene Vokabeln: {len(df_view)}")


if __name__ == "__main__":
    main()
