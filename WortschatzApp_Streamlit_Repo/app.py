"""
Wortschatz-Spiele (Klassen 7–9)

Robust:
- CSVs werden rekursiv aus data/ geladen, Trennzeichen automatisch (Komma/Semikolon).
- Spalten normalisiert: classe, page, de, en.
- Für Dateien unter data/pages/klasseK/klasseK_pageS.csv werden classe/page
  strikt aus dem Dateinamen abgeleitet (verhindert falsche Seitenzuordnung).
- Spiele: Galgenmännchen, Wörter ziehen (Drag & Drop), Eingabe (DE→EN).
- Filter: "Nur Einzelwörter".
"""

import os
import re
import json
import unicodedata
import random
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit import components

# ============================ Galgenmännchen ============================
HANGMAN_PICS = [
    "",
    "\n\n\n\n\n\n----",
    "\n\n\n\n\n |\n----",
    "\n\n\n\n  |\n  |\n----",
    "\n  O\n\n\n  |\n----",
    "\n  O\n  |\n\n  |\n----",
    "\n  O\n /|\n\n  |\n----",
    "\n  O\n /|\n / \n  |\n----",
    "\n  O\n /|\n / \n  |\n / \\\n----",
]

# ============================ Hilfsfunktionen ============================
def normalize_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = " ".join(s.split())
    return s

def answers_equal(user_answer: str, correct: str) -> bool:
    a_norm = normalize_text(user_answer)
    for variant in str(correct).split("/"):
        if a_norm == normalize_text(variant):
            return True
    return False

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

def _render_word_drag(pairs):
    pairs_json = json.dumps(pairs, ensure_ascii=False)
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
:root {{ --primary:#2196F3; --success:#4CAF50; }}
body {{ font-family:Arial, sans-serif; margin:0; padding:10px; background:#f6f7fb; }}
.card {{
  background:white; border:2px solid var(--primary); border-radius:10px;
  padding:10px; margin:5px; cursor:grab; user-select:none; min-width:120px;
  text-align:center; box-shadow:0 2px 6px rgba(0,0,0,.06);
}}
.card.correct {{ background:var(--success); border-color:var(--success); color:white; cursor:default; }}
#gameContainer {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(130px,1fr)); gap:10px; margin-top:10px; }}
#timer {{ font-size:1em; color:var(--primary); margin-bottom:10px; }}
button {{
  padding:6px 12px; margin-top:10px; border:2px solid var(--primary); border-radius:6px;
  background:var(--primary); color:white; cursor:pointer;
}}
</style></head>
<body>
  <div id="timer">⏱️ Zeit: <span id="timeValue">0</span> Sekunden</div>
  <div id="gameContainer"></div>
  <button onclick="restartGame()">🔄 Neustart</button>
<script>
const pairs = {pairs_json};
let time=0, timerId=null, draggedCard=null;
let words = pairs.map(p => ({{en:p.en, de:p.de}}));
function shuffle(a){{for(let i=a.length-1;i>0;i--){{const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]];}}}}
function isPair(a,b){{return words.some(w => (w.en===a && w.de===b) || (w.en===b && w.de===a));}}
function checkWin(){{if(document.querySelectorAll('.card:not(.correct)').length===0){{clearInterval(timerId);alert(`🏆 Gewonnen! Zeit: ${{time}} Sekunden`);}}}}
function startGame(){{
  const box=document.getElementById('gameContainer'); box.innerHTML='';
  clearInterval(timerId); time=0; document.getElementById('timeValue').textContent=time;
  timerId=setInterval(()=>{{time++;document.getElementById('timeValue').textContent=time;}},1000);
  const all=words.flatMap(w=>[w.en,w.de]); shuffle(all);
  for(const w of all){{
    const c=document.createElement('div'); c.className='card'; c.textContent=w; c.draggable=true;
    c.addEventListener('dragstart',e=>{{draggedCard=e.target; e.target.style.opacity='0.5';}});
    c.addEventListener('dragover',e=>e.preventDefault());
    c.addEventListener('drop',e=>{{
      e.preventDefault(); if(!draggedCard||draggedCard===e.target) return;
      const a=draggedCard.textContent.trim(), b=e.target.textContent.trim();
      if(isPair(a,b)){{ c.classList.add('correct'); e.target.classList.add('correct'); draggedCard.draggable=false; e.target.draggable=false; draggedCard=null; checkWin(); }}
      else{{ alert('❌ Kein gültiges Paar!'); draggedCard.style.opacity='1'; draggedCard=null; }}
    }});
    c.addEventListener('dragend',e=>e.target.style.opacity='1');
    box.appendChild(c);
  }}
}}
function restartGame(){{clearInterval(timerId);startGame();}}
document.addEventListener('DOMContentLoaded',startGame);
</script></body></html>"""
    return html

# ============================ Robuster Loader ============================
@st.cache_data(show_spinner=False)
def get_all_vocab_file_paths(data_dir: os.PathLike | str) -> list[Path]:
    """
    Sucht rekursiv nach allen CSV-Dateipfaden in data_dir und gibt sie zurück.
    Liest noch keine Daten ein.
    """
    base = Path(data_dir)
    paths: list[Path] = []
    for root, _, files in os.walk(base):
        for fn in files:
            if fn.lower().endswith(".csv"):
                paths.append(Path(root) / fn)
    if not paths:
        raise FileNotFoundError(f"Keine CSV-Dateien in {base.resolve()} gefunden.")
    return paths

def load_and_preprocess_df(path: Path) -> pd.DataFrame:
    """
    Liest eine einzelne CSV-Datei und normalisiert ihre Spalten.
    """
    try:
        df = pd.read_csv(path, sep=None, engine="python")
    except Exception as e:
        st.warning(f"CSV-Fehler {path.name}: {e}")
        return pd.DataFrame()

    # Spaltennamen vereinheitlichen
    col_map = {}
    for c in df.columns:
        lc = str(c).strip().lower()
        if lc in {"klasse", "class", "classe"}:
            col_map[c] = "classe"
        elif lc in {"page", "seite"}:
            col_map[c] = "page"
        elif lc in {"de", "deutsch", "german"}:
            col_map[c] = "de"
        elif lc in {"en", "englisch", "english"}:
            col_map[c] = "en"
    df = df.rename(columns=col_map)
    
    # Pfadinformation hinzufügen
    sp = str(path).replace("\\", "/")
    df["source_path"] = sp
    df["source_is_page"] = "/data/pages/" in sp.lower()

    # Fehlende Pflichtspalten ergänzen
    if "classe" not in df.columns: df["classe"] = ""
    if "page" not in df.columns: df["page"] = None
    if "de" not in df.columns: df["de"] = ""
    if "en" not in df.columns: df["en"] = ""

    # Typen & säubern
    df["classe"] = df["classe"].astype(str)
    df["page"] = pd.to_numeric(df["page"], errors="coerce").astype("Int64")
    df["de"] = df["de"].astype(str)
    df["en"] = df["en"].astype(str)
    df = df[(df["de"].str.strip() != "") & (df["en"].str.strip() != "")]
    
    # Härte Robustheit: Klasse/Seite aus Dateipfad erzwingen (nur pages/)
    page_pattern = re.compile(r"/data/pages/klasse(\d+)/klasse\1_page(\d+)\.csv$", re.IGNORECASE)
    m = page_pattern.search(sp.lower())
    if m:
        k, pg = m.group(1), m.group(2)
        df["classe"] = str(int(k))
        df["page"] = int(pg)

    return df.drop_duplicates(subset=["classe", "page", "de", "en"]).reset_index(drop=True)

# ============================ App ============================
def main() -> None:
    st.set_page_config(page_title="Wortschatz-Spiele (7–9)", page_icon="🎯", layout="centered")
    st.title("🎯 Wortschatz-Spiele (Klassen 7–9)")
    st.caption("Wähle Klasse & Seite. Spiele: Galgenmännchen, Wörter ziehen, Eingabe (DE→EN).")

    c_reset, c_debug, _ = st.columns([1,1,6])
    with c_reset:
        if st.button("🔄 Cache leeren"):
            st.cache_data.clear(); st.rerun()
    with c_debug:
        debug_on = st.toggle("Debug an/aus", value=False)

    DATA_DIR = Path(__file__).parent / "data"
    try:
        all_file_paths = get_all_vocab_file_paths(DATA_DIR)
        
        # Lade zunächst nur alle Vokabeln, um die Auswahlfelder zu füllen
        df_all_class_page = pd.concat([load_and_preprocess_df(p) for p in all_file_paths], ignore_index=True)
        df_all_class_page = df_all_class_page[df_all_class_page["classe"].isin({"7", "8", "9"})]
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        return

    classes = sorted(df_all_class_page["classe"].unique(), key=lambda x: int(x))
    if not classes:
        st.warning("Keine Klassen gefunden."); return

    classe = st.selectbox("Klasse", classes, format_func=lambda x: f"Klasse {x}")
    df_class = df_all_class_page[df_all_class_page["classe"] == classe]
    pages = sorted(df_class["page"].dropna().unique())
    if not pages:
        st.warning("Keine Seiten für diese Klasse gefunden."); return

    page = st.selectbox("Seite", pages, index=0)
    mode = st.radio("Umfang", ["Nur diese Seite", "Bis einschließlich dieser Seite"], horizontal=True)

    # Lade die Vokabeln dynamisch basierend auf der Auswahl
    if mode == "Nur diese Seite":
        # Priorität für spezifische pages-Dateien
        df_view = df_all_class_page[(df_all_class_page["classe"] == classe) & (df_all_class_page["page"] == page) & (df_all_class_page["source_is_page"] == True)]
        
        # Wenn keine spezifischen Dateien gefunden, nehme alle für die Seite
        if df_view.empty:
            df_view = df_all_class_page[(df_all_class_page["classe"] == classe) & (df_all_class_page["page"] == page)]
            st.caption("Keine spezifische Quelldatei gefunden, verwende alle passenden Einträge.")
        else:
            st.caption("Quelle: **data/pages/** (classe/page aus Dateinamen erzwungen).")
    else:
        df_view = df_all_class_page[(df_all_class_page["classe"] == classe) & (df_all_class_page["page"] <= page)]

    st.write(f"**Vokabeln verfügbar**: {len(df_view)}")
    if df_view.empty:
        st.info("Keine Vokabeln für diese Auswahl."); return

    if debug_on:
        with st.expander("🔍 Debug: Quellenübersicht"):
            st.write(f"Auswahl: Klasse {classe}, Seite {int(page)}, Modus: {mode}")
            if "source_path" in df_view.columns:
                top = df_view["source_path"].value_counts().head(12)
                st.table(top)
            st.dataframe(df_view.head(30))

    # --- Filter: Nur Einzelwörter ---
    st.subheader("Filter: Nur Einzelwörter")
    col1, col2, col3, col4 = st.columns(4)
    with col1: filter_simple = st.checkbox("Nur Einzelwörter aktivieren", value=False)
    with col2: ignore_articles = st.checkbox("Artikel/‘to ’ ignorieren", value=True)
    with col3: ignore_abbrev = st.checkbox("Abkürzungen ausschließen", value=True)
    with col4: min_length = st.number_input("Min. Wortlänge", 1, 10, 2, 1, format="%d")

    if filter_simple:
        mask = df_view["en"].apply(lambda x: is_simple_word(
            x, ignore_articles=ignore_articles, ignore_abbrev=ignore_abbrev, min_length=min_length
        ))
        df_view = df_view[mask].reset_index(drop=True)
        st.write(f"**Vokabeln nach Filter**: {len(df_view)}")
        if df_view.empty:
            st.info("Der Filter entfernt alle Vokabeln. Passe die Einstellungen an."); return

    seed_val = st.text_input("Seed (optional – gleiche Reihenfolge für alle)", value="")
    rnd = random.Random(seed_val if seed_val else None)

    game = st.selectbox("Wähle ein Spiel", ("Galgenmännchen", "Wörter ziehen", "Eingabe (DE → EN)"))

    # --- Galgenmännchen ---
    if game == "Galgenmännchen":
        key = f"hangman_{classe}_{page}_{mode}_{filter_simple}_{seed_val}"
        state = st.session_state.get(key)
        if state is None:
            row = rnd.choice(df_view.to_dict("records"))
            state = {"solution": row["en"], "hint": row["de"], "guessed": set(), "fails": 0}
            st.session_state[key] = state

        solution, hint = state["solution"], state["hint"]
        guessed, fails = state["guessed"], state["fails"]

        st.write(f"**Hinweis (DE)**: {hint}")
        st.text(HANGMAN_PICS[min(fails, len(HANGMAN_PICS)-1)])
        display_word = " ".join([c if (not c.isalpha() or c.lower() in guessed) else "_" for c in solution])
        st.write("**Wort (EN):** " + display_word)

        with st.form(key=f"full_form_{key}"):
            full_guess = st.text_input("Gesamtes Wort (engl.) eingeben", key=f"full_guess_{key}")
            if st.form_submit_button("Wort prüfen (komplett)"):
                g = normalize_text(full_guess)
                if g and answers_equal(g, solution):
                    guessed.update(c for c in normalize_text(solution) if c.isalpha()); st.success("✔ Korrekt!")
                else:
                    fails += 1
                state["guessed"], state["fails"] = guessed, fails
                st.session_state[key] = state; st.rerun()

        alphabet = list("abcdefghijklmnopqrstuvwxyz")
        rows = [alphabet[i:i+7] for i in range(0, len(alphabet), 7)]
        for r in rows:
            cols = st.columns(len(r))
            for letter, col in zip(r, cols):
                with col:
                    if st.button(letter, key=f"{key}_btn_{letter}", disabled=(letter in guessed)):
                        if letter in normalize_text(solution): guessed.add(letter)
                        else: fails += 1
                        state["guessed"], state["fails"] = guessed, fails
                        st.session_state[key] = state; st.rerun()

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Neue Karte"): st.session_state.pop(key, None); st.rerun()
        with c2:
            if st.button("Lösung anzeigen"):
                guessed.update(c for c in normalize_text(solution) if c.isalpha())
                state["guessed"], state["fails"] = guessed, min(fails, 8)
                st.session_state[key] = state; st.rerun()
        with c3: st.write(f"Fehler: {fails} / 8")

        if all((not c.isalpha()) or (c.lower() in guessed) for c in solution):
            st.success(f"🎉 Richtig! Das Wort war: {solution}")
        elif fails >= 8:
            st.error(f"🚫 Leider verloren. Das Wort war: {solution}")

    # --- Wörter ziehen ---
    elif game == "Wörter ziehen":
        if df_view.empty: st.info("Nicht genügend Daten."); return
        sample = df_view.sample(n=min(len(df_view), 8), random_state=rnd.randint(0, 10**9))
        pairs = [{"en": row["en"], "de": row["de"]} for _, row in sample.iterrows()]
        components.v1.html(_render_word_drag(pairs), height=620, scrolling=True)

    # --- Eingabe (DE → EN) ---
    else:
        key = f"input_{classe}_{page}_{mode}_{filter_simple}_{seed_val}"
        st_state = st.session_state.get(key)
        max_q = 10
        if not st_state:
            order = list(df_view.index); rnd.shuffle(order); order = order[: min(max_q, len(order))]
            st_state = {"order": order, "index": 0, "score": 0, "total": 0, "results": []}
            st.session_state[key] = st_state

        if st_state["index"] >= len(st_state["order"]):
            st.success(f"Serie beendet! {st_state['score']} von {st_state['total']} richtig.")
            if st.session_state[key]["results"]:
                t = pd.DataFrame(st_state["results"]); t.index += 1
                st.table(t.rename(columns={"de":"Deutsch","answer":"Deine Antwort","en":"Richtig","correct":"Korrekt"}))
            if st.button("Neue Serie"): st.session_state.pop(key, None); st.rerun()
        else:
            idx = st_state["order"][st_state["index"]]
            row = df_view.loc[idx]
            if st_state["results"]:
                t = pd.DataFrame(st_state["results"]).assign(Bewertung=lambda d: d["correct"].apply(lambda c: "✅" if c else "❌"))
                t.index += 1; st.table(t.rename(columns={"de":"Deutsch","answer":"Deine Antwort","en":"Richtig"})[["Deutsch","Deine Antwort","Richtig","Bewertung"]])
            st.write(f"**Deutsch:** {row['de']}")
            sol_key = f"show_solution_{key}"
            if sol_key in st.session_state:
                st.info(f"✔ Lösung: {st.session_state[sol_key]}")
                if st.button("Weiter"):
                    st_state["results"].append({"de": row["de"], "en": row["en"], "answer": "(angezeigt)", "correct": False})
                    st_state["total"] += 1; st_state["index"] += 1
                    del st.session_state[sol_key]; st.session_state[key] = st_state; st.rerun()
            else:
                with st.form(key=f"input_form_{key}"):
                    ans = st.text_input("Englisches Wort eingeben", key=f"ans_{key}")
                    if st.form_submit_button("Prüfen"):
                        ok = answers_equal(ans, row["en"])
                        if ok: st.success("✔ Richtig!"); st_state["score"] += 1
                        else: st.error(f"✘ Falsch — Richtig ist: {row['en']}")
                        st_state["results"].append({"de": row["de"], "en": row["en"], "answer": ans, "correct": ok})
                        st_state["total"] += 1; st_state["index"] += 1
                        st.session_state[key] = st_state; st.rerun()
                c2, c3 = st.columns(2)
                with c2:
                    if st.button("Lösung anzeigen"):
                        st.session_state[sol_key] = row["en"]; st.rerun()
                with c3:
                    if st.button("Serie beenden"):
                        st_state["index"] = len(st_state["order"]); st.session_state[key] = st_state; st.rerun()
                st.write(f"Frage {st_state['index'] + 1} / {len(st_state['order'])} – Punkte: {st_state['score']} / {st_state['total']}")

    st.caption(f"Sitzung: {datetime.now().strftime('%d.%m.%Y %H:%M')} — Insgesamt geladene Vokabeln: {len(df_view)}")

if __name__ == "__main__":
    main()
