"""
Deutsche Wortschatz-Trainer-App für Klassen 7–9.

- Liest alle CSV-Dateien unter data/ (rekursiv).
- Spalten: classe, page, de, en
- Drei Spiele: Galgenmännchen, Wörter ziehen (Drag & Drop), Eingabe (DE → EN)
- Optionaler Filter „Nur Einzelwörter“.
- Bei „Nur diese Seite“ werden – falls vorhanden – bevorzugt die CSVs aus data/pages/... genutzt.
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

# ---------------------------------------------------------------------
# Konstante: ASCII-Bilder für Galgenmännchen
# ---------------------------------------------------------------------
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

# ---------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------
def normalize_text(s: str) -> str:
    """Trimmt, entfernt diakritische Zeichen, macht lowercase und fasst Spaces zusammen."""
    if not isinstance(s, str):
        return ""
    s = s.strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = " ".join(s.split())
    return s


def answers_equal(user_answer: str, correct: str) -> bool:
    """Vergleich mit evtl. mehreren Varianten im correct-String, getrennt durch '/'."""
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
    """Filterkriterium für „Nur Einzelwörter“."""
    if not isinstance(word, str):
        return False
    w = word.strip()
    if ignore_articles:
        w = re.sub(r"^(to\s+|the\s+|a\s+|an\s+)", "", w, flags=re.IGNORECASE)
    if "/" in w:
        return False
    if " " in w or "-" in w:
        return False
    if ignore_abbrev and re.search(r"\b(sth|sb|etc|e\.g|i\.e)\b", w, flags=re.IGNORECASE):
        return False
    if "." in w:
        return False
    return len(w) >= min_length


def _render_word_drag(pairs):
    """HTML für das Drag-&-Drop-Spiel erzeugen (words = [{"en":..., "de":...}, ...])."""
    pairs_json = json.dumps(pairs, ensure_ascii=False)
    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    :root {{
      --primary: #2196F3;
      --success: #4CAF50;
    }}
    body {{
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 10px;
      background: #f6f7fb;
    }}
    .card {{
      background: white;
      border: 2px solid var(--primary);
      border-radius: 10px;
      padding: 10px;
      margin: 5px;
      cursor: grab;
      user-select: none;
      min-width: 120px;
      text-align: center;
      box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }}
    .card.correct {{
      background: var(--success);
      border-color: var(--success);
      color: white;
      cursor: default;
    }}
    #gameContainer {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
      gap: 10px;
      margin-top: 10px;
    }}
    #timer {{
      font-size: 1em;
      color: var(--primary);
      margin-bottom: 10px;
    }}
    button {{
      padding: 6px 12px;
      margin-top: 10px;
      border: 2px solid var(--primary);
      border-radius: 6px;
      background: var(--primary);
      color: white;
      cursor: pointer;
    }}
  </style>
</head>
<body>
  <div id="timer">⏱️ Zeit: <span id="timeValue">0</span> Sekunden</div>
  <div id="gameContainer"></div>
  <button onclick="restartGame()">🔄 Neustart</button>

  <script>
    const pairs = {pairs_json};
    let time = 0;
    let timerId = null;
    let draggedCard = null;
    let words = pairs.map(p => ({{ en: p.en, de: p.de }}));

    function shuffleArray(array) {{
      for (let i = array.length - 1; i > 0; i--) {{
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
      }}
    }}

    function startGame() {{
      const gameContainer = document.getElementById('gameContainer');
      gameContainer.innerHTML = '';
      clearInterval(timerId);
      time = 0;
      document.getElementById('timeValue').textContent = time;
      timerId = setInterval(() => {{
        time++;
        document.getElementById('timeValue').textContent = time;
      }}, 1000);
      const allWords = words.flatMap(w => [w.en, w.de]);
      shuffleArray(allWords);
      allWords.forEach(word => {{
        const card = document.createElement('div');
        card.className = 'card';
        card.textContent = word;
        card.draggable = true;
        card.addEventListener('dragstart', (e) => {{
          draggedCard = e.target;
          e.target.style.opacity = '0.5';
        }});
        card.addEventListener('dragover', (e) => e.preventDefault());
        card.addEventListener('drop', (e) => {{
          e.preventDefault();
          if (!draggedCard || draggedCard === e.target) return;
          const w1 = draggedCard.textContent.trim();
          const w2 = e.target.textContent.trim();
          if (isPair(w1, w2)) {{
            draggedCard.classList.add('correct');
            e.target.classList.add('correct');
            draggedCard.draggable = false;
            e.target.draggable = false;
            draggedCard = null;
            checkWin();
          }} else {{
            alert('❌ Kein gültiges Paar!');
            draggedCard.style.opacity = '1';
            draggedCard = null;
          }}
        }});
        card.addEventListener('dragend', (e) => {{
          e.target.style.opacity = '1';
        }});
        gameContainer.appendChild(card);
      }});
    }}

    function isPair(a, b) {{
      return words.some(w => (w.en === a && w.de === b) || (w.en === b && w.de === a));
    }}

    function checkWin() {{
      const remaining = document.querySelectorAll('.card:not(.correct)').length;
      if (remaining === 0) {{
        clearInterval(timerId);
        alert(`🏆 Gewonnen! Zeit: ${{time}} Sekunden`);
      }}
    }}

    function restartGame() {{
      clearInterval(timerId);
      startGame();
    }}

    document.addEventListener('DOMContentLoaded', () => {{
      startGame();
    }});
  </script>
</body>
</html>
"""
    return html

# ---------------------------------------------------------------------
# Daten laden – mit Quelleninfo (pages vs. andere)
# ---------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_vocab(data_dir: os.PathLike | str) -> pd.DataFrame:
    """
    Lädt alle CSVs rekursiv aus data_dir.
    Merkt sich die Quelle je Zeile:
      - source_path (Pfad als String)
      - source_is_page (True, wenn Pfad unter /data/pages/ liegt)
    """
    base = Path(data_dir)
    paths = []
    for root, _, files in os.walk(base):
        for fn in files:
            if fn.lower().endswith(".csv"):
                paths.append(Path(root) / fn)

    if not paths:
        raise FileNotFoundError(f"Keine CSV-Dateien im Verzeichnis {base.resolve()} gefunden.")

    frames = []
    for p in paths:
        try:
            # sep=None + engine="python" erkennt Komma/Semikolon automatisch
            df = pd.read_csv(p, sep=None, engine="python")
            sp = str(p).replace("\\", "/").lower()
            df["source_path"] = sp
            df["source_is_page"] = ("/data/pages/" in sp) or ("/pages/" in sp)
            frames.append(df)
        except Exception as e:
            st.warning(f"Fehler beim Laden von {p}: {e}")

    if not frames:
        raise ValueError("Es konnten keine Daten geladen werden.")

    df = pd.concat(frames, ignore_index=True)

    # Spalten vereinheitlichen (case-insensitive)
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

    required = {"classe", "page", "de", "en"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Fehlende Spalten {missing} in den CSV-Dateien.")

    # Typen & Bereinigung
    df["classe"] = df["classe"].astype(str)
    df["page"] = pd.to_numeric(df["page"], errors="coerce").astype("Int64")
    df["de"] = df["de"].astype(str)
    df["en"] = df["en"].astype(str)

    df = df[(df["de"].str.strip() != "") & (df["en"].str.strip() != "")]
    df = df.drop_duplicates(subset=["classe", "page", "de", "en"]).reset_index(drop=True)
    df = df[df["classe"].isin({"7", "8", "9"})]

    return df

# ---------------------------------------------------------------------
# Streamlit App
# ---------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="Wortschatz-Spiele (Klassen 7–9)", page_icon="🎯", layout="centered")
    st.title("🎯 Wortschatz-Spiele für Klassen 7–9")
    st.caption("Wähle zuerst Klasse und Seite. Spiele dann: Galgenmännchen, Wörter ziehen oder Eingabe (DE → EN).")

    # Cache-Reset bei Datenwechsel
    if st.button("🔄 Cache leeren"):
        st.cache_data.clear()
        st.rerun()

    # Daten laden (relativ zu app.py)
    try:
        DATA_DIR = Path(__file__).parent / "data"
        df = load_vocab(DATA_DIR)
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        return

    # Klassen/Seiten
    classes = sorted(df["classe"].unique(), key=lambda x: int(x))
    if not classes:
        st.warning("Keine Klassen gefunden.")
        return

    classe = st.selectbox("Klasse", classes, format_func=lambda x: f"Klasse {x}")
    df_class = df[df["classe"] == classe]
    pages = sorted(df_class["page"].dropna().unique())
    if not pages:
        st.warning("Keine Seiten für diese Klasse gefunden.")
        return

    page = st.selectbox("Seite", pages, index=0)
    mode = st.radio("Umfang", options=["Nur diese Seite", "Bis einschließlich dieser Seite"], horizontal=True)

    # Umfang-Filter mit Priorisierung der Seiten-CSVs
    if mode == "Nur diese Seite":
        mask = (df["classe"] == classe) & (df["page"] == page)
        candidates = df[mask].copy()
        page_only = candidates[candidates.get("source_is_page", False) == True]
        if len(page_only) > 0:
            df_view = page_only
            st.caption("Quelle priorisiert: data/pages (exakte Seite).")
        else:
            df_view = candidates
    else:
        df_view = df_class[df_class["page"] <= page]

    st.write(f"**Vokabeln verfügbar**: {len(df_view)}")
    if df_view.empty:
        st.info("Keine Vokabeln für diese Auswahl.")
        return

    # Filter: Nur Einzelwörter
    st.subheader("Filter: Nur Einzelwörter")
    col_opt1, col_opt2, col_opt3, col_opt4 = st.columns(4)
    with col_opt1:
        filter_simple = st.checkbox("Nur Einzelwörter aktivieren", value=False)
    with col_opt2:
        ignore_articles = st.checkbox("Artikel/‘to ’ ignorieren", value=True)
    with col_opt3:
        ignore_abbrev = st.checkbox("Abkürzungen ausschließen", value=True)
    with col_opt4:
        min_length = st.number_input("Min. Wortlänge", min_value=1, max_value=10, value=2, step=1, format="%d")

    if filter_simple:
        mask = df_view["en"].apply(
            lambda x: is_simple_word(x, ignore_articles=ignore_articles, ignore_abbrev=ignore_abbrev, min_length=min_length)
        )
        df_view = df_view[mask].reset_index(drop=True)
        st.write(f"**Vokabeln nach Filter**: {len(df_view)}")
        if df_view.empty:
            st.info("Der Filter entfernt alle Vokabeln. Passe die Einstellungen an.")
            return

    # Seed (deterministische Reihenfolge)
    seed_val = st.text_input("Seed (optional – gleiche Reihenfolge für alle)", value="")
    rnd = random.Random(seed_val if seed_val else None)

    # Spielauswahl
    game = st.selectbox("Wähle ein Spiel", ("Galgenmännchen", "Wörter ziehen", "Eingabe (DE → EN)"))

    # -----------------------------------------------------------------
    # Galgenmännchen
    # -----------------------------------------------------------------
    if game == "Galgenmännchen":
        key = f"hangman_{classe}_{page}_{mode}_{filter_simple}_{seed_val}"
        state = st.session_state.get(key, None)
        if state is None:
            row = rnd.choice(df_view.to_dict("records"))
            state = {"solution": row["en"], "hint": row["de"], "guessed": set(), "fails": 0}
            st.session_state[key] = state

        solution = state["solution"]
        hint = state["hint"]
        guessed = state["guessed"]
        fails = state["fails"]

        st.write(f"**Hinweis (DE)**: {hint}")
        st.text(HANGMAN_PICS[min(fails, len(HANGMAN_PICS) - 1)])

        display_word = " ".join([c if (not c.isalpha() or c.lower() in guessed) else "_" for c in solution])
        st.write("**Wort (EN):** " + display_word)

        # Ganzes Wort prüfen (Form – Enter löst aus)
        with st.form(key=f"full_form_{key}"):
            full_guess = st.text_input("Gesamtes Wort (engl.) eingeben", key=f"full_guess_{key}")
            full_submitted = st.form_submit_button("Wort prüfen (komplett)")
        if full_submitted:
            g = normalize_text(full_guess)
            if g:
                if answers_equal(g, solution):
                    guessed.update(c for c in normalize_text(solution) if c.isalpha())
                    st.success("✔ Korrekt – du hast das Wort erraten!")
                else:
                    fails += 1
            state["guessed"] = guessed
            state["fails"] = fails
            st.session_state[key] = state
            st.rerun()

        # On-Screen-Tastatur
        alphabet = list("abcdefghijklmnopqrstuvwxyz")
        rows = [alphabet[i : i + 7] for i in range(0, len(alphabet), 7)]
        for r in rows:
            cols = st.columns(len(r))
            for letter, col in zip(r, cols):
                disabled = letter in guessed
                with col:
                    if st.button(letter, key=f"{key}_btn_{letter}", disabled=disabled):
                        if letter in normalize_text(solution):
                            guessed.add(letter)
                        else:
                            fails += 1
                        state["guessed"] = guessed
                        state["fails"] = fails
                        st.session_state[key] = state
                        st.rerun()

        col_h1, col_h2, col_h3 = st.columns(3)
        with col_h1:
            if st.button("Neue Karte"):
                st.session_state.pop(key, None)
                st.rerun()
        with col_h2:
            if st.button("Lösung anzeigen"):
                guessed.update(c for c in normalize_text(solution) if c.isalpha())
                fails = min(fails, 8)
                state["guessed"] = guessed
                state["fails"] = fails
                st.session_state[key] = state
                st.rerun()
        with col_h3:
            st.write(f"Fehler: {fails} / 8")

        won = all((not c.isalpha()) or (c.lower() in guessed) for c in solution)
        if won:
            st.success(f"🎉 Richtig! Das Wort war: {solution}")
        elif fails >= 8:
            st.error(f"🚫 Leider verloren. Das Wort war: {solution}")

        state["guessed"] = guessed
        state["fails"] = fails
        st.session_state[key] = state

    # -----------------------------------------------------------------
    # Wörter ziehen (Drag & Drop)
    # -----------------------------------------------------------------
    elif game == "Wörter ziehen":
        if df_view.empty:
            st.info("Nicht genügend Daten für dieses Spiel.")
            return
        sample = df_view.sample(n=min(len(df_view), 8), random_state=rnd.randint(0, 10**9))
        pairs = [{"en": row["en"], "de": row["de"]} for _, row in sample.iterrows()]
        html = _render_word_drag(pairs)
        components.v1.html(html, height=620, scrolling=True)

    # -----------------------------------------------------------------
    # Eingabe (DE → EN)
    # -----------------------------------------------------------------
    else:
        key = f"input_{classe}_{page}_{mode}_{filter_simple}_{seed_val}"
        input_state = st.session_state.get(key, None)
        max_questions = 10

        if input_state is None or not input_state:
            order = list(df_view.index)
            rnd.shuffle(order)
            order = order[: min(max_questions, len(order))]
            input_state = {"order": order, "index": 0, "score": 0, "total": 0, "results": []}
            st.session_state[key] = input_state

        if input_state["index"] >= len(input_state["order"]):
            st.success(f"Serie beendet! Du hast {input_state['score']} von {input_state['total']} Fragen richtig.")
            if input_state["results"]:
                summary_df = pd.DataFrame(input_state["results"])
                summary_df.index += 1
                st.write("**Zusammenfassung der Antworten:**")
                st.table(
                    summary_df.rename(
                        columns={"de": "Deutsch", "answer": "Deine Antwort", "en": "Richtig", "correct": "Korrekt"}
                    )
                )
            if st.button("Neue Serie"):
                st.session_state.pop(key, None)
                st.rerun()
        else:
            idx_in_order = input_state["order"][input_state["index"]]
            current_row = df_view.loc[idx_in_order]

            if input_state["results"]:
                res_df = pd.DataFrame(input_state["results"]).assign(
                    Bewertung=lambda d: d["correct"].apply(lambda c: "✅" if c else "❌")
                )
                res_df.index += 1
                st.write("**Bisherige Antworten:**")
                st.table(res_df.rename(columns={"de": "Deutsch", "answer": "Deine Antwort", "en": "Richtig"})[["Deutsch", "Deine Antwort", "Richtig", "Bewertung"]])

            st.write(f"**Deutsch:** {current_row['de']}")
            sol_key = f"show_solution_{key}"

            if sol_key in st.session_state:
                correct_word = st.session_state[sol_key]
                st.info(f"✔ Lösung: {correct_word}")
                if st.button("Weiter"):
                    input_state["results"].append({"de": current_row["de"], "en": current_row["en"], "answer": "(angezeigt)", "correct": False})
                    input_state["total"] += 1
                    input_state["index"] += 1
                    del st.session_state[sol_key]
                    st.session_state[key] = input_state
                    st.rerun()
            else:
                with st.form(key=f"input_form_{key}"):
                    answer = st.text_input("Englisches Wort eingeben", key=f"ans_{key}")
                    submit_answer = st.form_submit_button("Prüfen")
                col_i2, col_i3 = st.columns(2)
                with col_i2:
                    if st.button("Lösung anzeigen"):
                        st.session_state[sol_key] = current_row["en"]
                        st.rerun()
                with col_i3:
                    if st.button("Serie beenden"):
                        input_state["index"] = len(input_state["order"])
                        st.session_state[key] = input_state
                        st.rerun()

                if submit_answer:
                    correct = answers_equal(answer, current_row["en"])
                    if correct:
                        st.success("✔ Richtig!")
                        input_state["score"] += 1
                    else:
                        st.error(f"✘ Falsch — Richtig ist: {current_row['en']}")
                    input_state["results"].append({"de": current_row["de"], "en": current_row["en"], "answer": answer, "correct": correct})
                    input_state["total"] += 1
                    input_state["index"] += 1
                    st.session_state[key] = input_state
                    st.rerun()

                st.write(f"Frage {input_state['index'] + 1} / {len(input_state['order'])} – Punkte: {input_state['score']} / {input_state['total']}")

    st.caption(f"Sitzung: {datetime.now().strftime('%d.%m.%Y %H:%M')} — Insgesamt geladene Vokabeln: {len(df)}")


if __name__ == "__main__":
    main()
