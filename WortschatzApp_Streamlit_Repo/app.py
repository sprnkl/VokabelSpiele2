"""
Deutsche Wortschatz‑Trainer‑App für Klassen 7–9.

Diese Streamlit‑Anwendung liest alle CSV‑Dateien im Verzeichnis
``data/`` (rekursiv) und stellt den Inhalt als Vokabelliste zur
Verfügung. Anschließend können die Schülerinnen und Schüler drei
verschiedene Spiele spielen, um ihren Wortschatz zu üben: Galgenmännchen,
Memory und Eingabe. Für alle Spiele existiert eine optionale
Filterung auf „nur Einzelwörter“, bei der Abkürzungen, zusammengesetzte
Begriffe und Wörter mit Artikeln oder „to “ entfernt werden.

Die CSV‑Dateien müssen mindestens die Spalten ``klasse``, ``page``,
``de`` und ``en`` enthalten. Die Anwendung ist vollständig offline
verwendbar.
"""

import os
import re
import unicodedata
import random
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit import components
import json

# ASCII‑Darstellungen für den Galgen. Je höher der Index, desto weiter ist der
# Galgen aufgebaut. Insgesamt sind acht Fehlversuche erlaubt. Diese Bilder
# werden im Galgenmännchen‑Spiel verwendet.
HANGMAN_PICS: list[str] = [
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

# -----------------------------------------------------------------------------
# Hilfsfunktionen
# -----------------------------------------------------------------------------

def normalize_text(s: str) -> str:
    """Trimmt und entfernt diakritische Zeichen, wandelt in Kleinbuchstaben um."""
    if not isinstance(s, str):
        return ""
    s = s.strip().lower()
    # Entferne Akzente und diakritische Zeichen
    s = "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )
    # Mehrfache Leerzeichen zusammenfassen
    s = " ".join(s.split())
    return s


def answers_equal(user_answer: str, correct: str) -> bool:
    """Vergleicht die Benutzereingabe mit der richtigen Lösung.

    Unterstützt mehrere Varianten im ``correct``‑String, die mit ``/``
    separiert sind.
    """
    a_norm = normalize_text(user_answer)
    for variant in str(correct).split("/"):
        if a_norm == normalize_text(variant):
            return True
    return False


def is_simple_word(word: str, *, ignore_articles: bool = True, ignore_abbrev: bool = True, min_length: int = 2) -> bool:
    """Bestimmt, ob ein englisches Wort für das „Nur‑Einzelwörter“‑Spiel geeignet ist.

    Ein einfaches Wort darf keine Leerzeichen, Schrägstriche oder Bindestriche
    enthalten. Optional können Wörter mit führenden Artikeln (``a``, ``an``,
    ``the``) oder ``to `` ignoriert werden. Abkürzungen wie ``sth.``, ``sb.``
    und Kürzel mit Punkten können ausgeschlossen werden. Zudem wird eine
    minimale Länge geprüft.
    """
    if not isinstance(word, str):
        return False
    w = word.strip()
    # Falls "to " oder Artikel vorhanden, entfernen, wenn gewünscht
    if ignore_articles:
        w = re.sub(r'^(to\s+|the\s+|a\s+|an\s+)', '', w, flags=re.IGNORECASE)
    # Mehrfachvarianten wie "word1/word2" -> gelten nicht als Einzelwort
    if '/' in w:
        return False
    # Leerzeichen oder Bindestriche
    if ' ' in w or '-' in w:
        return False
    # Abkürzungen ausschließen, wenn gewünscht
    if ignore_abbrev and re.search(r'\b(sth|sb|etc|e\.g|i\.e)\b', w, flags=re.IGNORECASE):
        return False
    # Keine Punkte innerhalb des Wortes
    if '.' in w:
        return False
    return len(w) >= min_length


# -----------------------------------------------------------------------------
# Rendering für das Drag‑and‑Drop‑Spiel
# -----------------------------------------------------------------------------
def _render_word_drag(pairs):
    """Erzeugt den HTML‑Code für das Drag‑and‑Drop‑Spiel.

    ``pairs`` ist eine Liste von Diktaten mit den Schlüsseln ``en`` und ``de``.
    Für jedes Paar wird sowohl das englische als auch das deutsche Wort als
    Karte erzeugt. Der Benutzer muss passende Paare durch Ziehen und
    Ablegen finden. Ein Timer misst die Zeit.
    """
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
    }}
    .card {{
      background: white;
      border: 2px solid var(--primary);
      border-radius: 10px;
      padding: 10px;
      margin: 5px;
      cursor: grab;
      user-select: none;
      min-width: 100px;
      text-align: center;
    }}
    .card.correct {{
      background: var(--success);
      border-color: var(--success);
      cursor: not-allowed;
    }}
    #gameContainer {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
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
      border-radius: 5px;
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


@st.cache_data(show_spinner=False)
def load_vocab(data_dir: str = "data") -> pd.DataFrame:
    """Lädt alle CSV‑Dateien im angegebenen Verzeichnis rekursiv.

    Die CSV‑Dateien müssen mindestens die Spalten ``klasse``, ``page``,
    ``de`` und ``en`` besitzen. Zeilen mit leeren oder fehlenden Werten
    werden entfernt. Doppelte Einträge (identische Kombination aus
    Klasse, Seite, Deutsch und Englisch) werden entfernt.
    """
    paths: list[str] = []
    for root, _, files in os.walk(data_dir):
        for fn in files:
            if fn.lower().endswith(".csv"):
                paths.append(os.path.join(root, fn))
    if not paths:
        raise FileNotFoundError(f"Keine CSV‑Dateien im Verzeichnis {data_dir} gefunden.")

    frames = []
    for p in paths:
        try:
            df = pd.read_csv(p)
            frames.append(df)
        except Exception as e:
            st.warning(f"Fehler beim Laden von {p}: {e}")
    if not frames:
        raise ValueError("Es konnten keine Daten geladen werden.")
    df = pd.concat(frames, ignore_index=True)

    # Spaltennamen vereinheitlichen (case‑insensitive)
    col_map = {}
    for c in df.columns:
        lc = c.strip().lower()
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
        raise ValueError(f"Fehlende Spalten {missing} in den CSV‑Dateien.")

    # Datentypen bereinigen
    df["classe"] = df["classe"].astype(str)
    df["page"] = pd.to_numeric(df["page"], errors="coerce").astype('Int64')
    df["de"] = df["de"].astype(str)
    df["en"] = df["en"].astype(str)

    # Zeilen mit leeren Feldern verwerfen
    df = df[(df["de"].str.strip() != "") & (df["en"].str.strip() != "")]

    # Doppelte entfernen
    df = df.drop_duplicates(subset=["classe", "page", "de", "en"]).reset_index(drop=True)

    # Nur Klassen 7–9 zulassen
    df = df[df["classe"].isin({"7", "8", "9"})]

    return df


# -----------------------------------------------------------------------------
# Streamlit App
# -----------------------------------------------------------------------------

def main() -> None:
    """Hauptroutine der App."""
    st.set_page_config(
        page_title="Wortschatz‑Spiele (Klassen 7–9)",
        page_icon="🎯",
        layout="centered",
    )

    st.title("🎯 Wortschatz‑Spiele für Klassen 7–9")
    st.caption(
        "Übe deinen englischen Wortschatz mit drei Spielen: Galgenmännchen, Memory und Eingabe. "
        "Wähle zuerst deine Klasse und die Seite."
    )

    # Daten laden
    try:
        DATA_DIR = Path(__file__).parent / "data"
        df = load_vocab(DATA_DIR)
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        return

    # Klassenliste
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
    mode = st.radio(
        "Umfang",
        options=["Nur diese Seite", "Bis einschließlich dieser Seite"],
        horizontal=True,
    )

    # Filtere Daten entsprechend des gewählten Umfangs
    if mode == "Nur diese Seite":
        df_view = df_class[df_class["page"] == page]
    else:
        df_view = df_class[df_class["page"] <= page]

    st.write(f"**Vokabeln verfügbar**: {len(df_view)}")
    if df_view.empty:
        st.info("Keine Vokabeln für diese Auswahl.")
        return

    # Optionen für Nur‑Einzelwörter
    st.subheader("Filter: Nur Einzelwörter")
    col_opt1, col_opt2, col_opt3, col_opt4 = st.columns(4)
    with col_opt1:
        filter_simple = st.checkbox("Nur Einzelwörter aktivieren", value=False)
    with col_opt2:
        ignore_articles = st.checkbox("Artikel/‘to ’ ignorieren", value=True)
    with col_opt3:
        ignore_abbrev = st.checkbox("Abkürzungen ausschließen", value=True)
    with col_opt4:
        min_length = st.number_input(
            "Min. Wortlänge", min_value=1, max_value=10, value=2, step=1, format="%d"
        )

    # Filtern der Daten bei aktivierter Option
    if filter_simple:
        mask = df_view["en"].apply(
            lambda x: is_simple_word(
                x,
                ignore_articles=ignore_articles,
                ignore_abbrev=ignore_abbrev,
                min_length=min_length,
            )
        )
        df_view = df_view[mask].reset_index(drop=True)
        st.write(f"**Vokabeln nach Filter**: {len(df_view)}")
        if df_view.empty:
            st.info("Der Filter entfernt alle Vokabeln. Passe die Einstellungen an.")
            return

    # Seed für deterministische Reihenfolge
    seed_val = st.text_input(
        "Seed (optional – gleiche Reihenfolge für alle)", value=""
    )
    rnd = random.Random(seed_val if seed_val else None)

    # Auswahl des Spiels
    # Der Benutzer kann zwischen drei Spielen wählen. Das bisherige Memory‑Spiel
    # wurde durch ein Drag‑and‑Drop‑Spiel ersetzt, bei dem jeweils die
    # englischen und deutschen Begriffe einander zugeordnet werden müssen.
    game = st.selectbox(
        "Wähle ein Spiel",
        ("Galgenmännchen", "Wörter ziehen", "Eingabe (DE → EN)"),
    )

    # -------------------------------------------------------------------------
    # Galgenmännchen
    # -------------------------------------------------------------------------
    if game == "Galgenmännchen":
        # Initialisiere Sitzungszustand
        key = f"hangman_{classe}_{page}_{mode}_{filter_simple}_{seed_val}"
        state = st.session_state.get(key, None)
        if state is None:
            # Neue Runde starten
            row = rnd.choice(df_view.to_dict("records"))
            state = {
                "solution": row["en"],
                "hint": row["de"],
                "guessed": set(),
                "fails": 0,
            }
            st.session_state[key] = state

        # Zeige Hinweis, Galgen und geratene Buchstaben an
        solution = state["solution"]
        hint = state["hint"]
        guessed = state["guessed"]
        fails = state["fails"]

        st.write(f"**Hinweis (DE)**: {hint}")
        # ASCII‑Zeichnung des Galgens je nach Fehlerzahl anzeigen
        pic_index = min(fails, len(HANGMAN_PICS) - 1)
        st.text(HANGMAN_PICS[pic_index])

        # Wort mit Platzhaltern anzeigen
        display_word = " ".join(
            [c if (not c.isalpha() or c.lower() in guessed) else "_" for c in solution]
        )
        st.write("**Wort (EN):** " + display_word)

        # Eingabe für das gesamte Wort als Formular, damit Enter den Button auslöst
        full_guess = None
        full_submitted = False
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
            # Status in Session aktualisieren und neu rendern
            state["guessed"] = guessed
            state["fails"] = fails
            st.session_state[key] = state
            st.rerun()

        # On‑Screen‑Tastatur für Buchstaben A–Z
        alphabet = list("abcdefghijklmnopqrstuvwxyz")
        rows = [alphabet[i:i+7] for i in range(0, len(alphabet), 7)]
        for r in rows:
            cols = st.columns(len(r))
            for letter, col in zip(r, cols):
                disabled = letter in guessed
                with col:
                    if st.button(letter, key=f"{key}_btn_{letter}", disabled=disabled):
                        # Prüfe Buchstabe
                        if letter in normalize_text(solution):
                            guessed.add(letter)
                        else:
                            fails += 1
                        # Status aktualisieren
                        state["guessed"] = guessed
                        state["fails"] = fails
                        st.session_state[key] = state
                        st.rerun()

        # Neue Karte, Lösung anzeigen und Fehleranzeige
        col_h1, col_h2, col_h3 = st.columns(3)
        with col_h1:
            if st.button("Neue Karte"):
                st.session_state.pop(key, None)
                st.rerun()
        with col_h2:
            # Auf Wunsch das komplette Wort aufdecken
            if st.button("Lösung anzeigen"):
                # Zeige alle Buchstaben und markiere das Spiel als beendet
                guessed.update(c for c in normalize_text(solution) if c.isalpha())
                fails = min(fails, 8)
                state["guessed"] = guessed
                state["fails"] = fails
                st.session_state[key] = state
                st.rerun()
        with col_h3:
            st.write(f"Fehler: {fails} / 8")

        # Sieg oder Niederlage
        won = all((not c.isalpha()) or (c.lower() in guessed) for c in solution)
        if won:
            st.success(f"🎉 Richtig! Das Wort war: {solution}")
        elif fails >= 8:
            st.error(f"🚫 Leider verloren. Das Wort war: {solution}")

        # Status speichern
        state["guessed"] = guessed
        state["fails"] = fails
        st.session_state[key] = state

    # -------------------------------------------------------------------------
    # Wörter ziehen (Drag‑and‑Drop)
    # -------------------------------------------------------------------------
    elif game == "Wörter ziehen":
        """
        Dieses Spiel ersetzt das klassische Memory. Es zeigt bis zu acht Paare
        gleichzeitig an und erlaubt es den Schülerinnen und Schülern, die
        deutschen und englischen Begriffe durch Ziehen und Ablegen
        zusammenzuführen. Ein Timer misst die benötigte Zeit. Das HTML‑Layout
        und die Logik werden durch die Hilfsfunktion `_render_word_drag`
        erzeugt.
        """
        # Stelle sicher, dass genügend Daten vorhanden sind
        if df_view.empty:
            st.info("Nicht genügend Daten für dieses Spiel.")
            return
        # Wähle bis zu 8 zufällige Paare
        sample = df_view.sample(n=min(len(df_view), 8), random_state=rnd.randint(0, 10**9))
        pairs = [
            {"en": row["en"], "de": row["de"]}
            for _, row in sample.iterrows()
        ]
        # Erzeuge HTML für das Spiel
        html = _render_word_drag(pairs)
        # Betten das Spiel ein; erhöhe die Höhe, um genügend Platz zu schaffen
        # Verwende die v1‑Schnittstelle für Komponenten, damit Streamlit 1.37 funktioniert
        components.v1.html(html, height=600, scrolling=True)

    # -------------------------------------------------------------------------
    # Eingabe (DE → EN)
    # -------------------------------------------------------------------------
    else:  # Eingabe (DE → EN)
        key = f"input_{classe}_{page}_{mode}_{filter_simple}_{seed_val}"
        input_state = st.session_state.get(key, None)

        # Anzahl der Fragen pro Serie. Standard: 10 oder alle verfügbaren, falls weniger vorhanden.
        max_questions = 10

        # Initialisieren des Zustands, wenn nicht vorhanden
        if input_state is None or not input_state:
            order = list(df_view.index)
            rnd.shuffle(order)
            order = order[: min(max_questions, len(order))]
            input_state = {
                "order": order,
                "index": 0,
                "score": 0,
                "total": 0,
                "results": [],  # Liste, um Antworten für die Zusammenfassung zu speichern
            }
            st.session_state[key] = input_state

        # Wenn alle Fragen beantwortet sind, Zusammenfassung anzeigen
        if input_state["index"] >= len(input_state["order"]):
            st.success(
                f"Serie beendet! Du hast {input_state['score']} von {input_state['total']} Fragen richtig."
            )
            # Zusammenfassung der Ergebnisse als Tabelle
            if input_state["results"]:
                summary_df = pd.DataFrame(input_state["results"])
                summary_df.index += 1
                st.write("**Zusammenfassung der Antworten:**")
                st.table(
                    summary_df.rename(
                        columns={"de": "Deutsch", "answer": "Deine Antwort", "en": "Richtig", "correct": "Korrekt"}
                    )
                )
            # Button für neue Serie
            if st.button("Neue Serie"):
                st.session_state.pop(key, None)
                st.rerun()
        else:
            # Aktuelle Frage anzeigen
            idx_in_order = input_state["order"][input_state["index"]]
            current_row = df_view.loc[idx_in_order]
            # Zeige eine laufende Liste der bisherigen Antworten mit ✅/❌
            if input_state["results"]:
                res_df = pd.DataFrame(input_state["results"])
                # Ersetze Bool durch Haken/Kreuz zur besseren Lesbarkeit
                res_df = res_df.assign(
                    bewertet=res_df["correct"].apply(lambda c: "✅" if c else "❌")
                )
                res_df.index += 1
                st.write("**Bisherige Antworten:**")
                st.table(
                    res_df.rename(
                        columns={
                            "de": "Deutsch",
                            "answer": "Deine Antwort",
                            "en": "Richtig",
                            "bewertet": "Bewertung",
                        }
                    )[["Deutsch", "Deine Antwort", "Richtig", "Bewertung"]]
                )

            st.write(f"**Deutsch:** {current_row['de']}")

            # Schlüssel für das Anzeigen der Lösung
            sol_key = f"show_solution_{key}"

            # Prüfen, ob die Lösung bereits angezeigt wurde
            if sol_key in st.session_state:
                # Lösung anzeigen und auf Weiter warten
                correct_word = st.session_state[sol_key]
                st.info(f"✔ Lösung: {correct_word}")
                if st.button("Weiter"):
                    # Als angezeigt/übersprungen werten
                    input_state["results"].append(
                        {
                            "de": current_row["de"],
                            "en": current_row["en"],
                            "answer": "(angezeigt)",
                            "correct": False,
                        }
                    )
                    input_state["total"] += 1
                    input_state["index"] += 1
                    # Lösche das Anzeigen‑Flag
                    del st.session_state[sol_key]
                    st.session_state[key] = input_state
                    st.rerun()
            else:
                # Formular für Eingabe und Prüfung, Enter löst automatisch aus
                with st.form(key=f"input_form_{key}"):
                    answer = st.text_input("Englisches Wort eingeben", key=f"ans_{key}")
                    submit_answer = st.form_submit_button("Prüfen")
                # Buttons für Lösung anzeigen und Serie beenden
                col_i2, col_i3 = st.columns(2)
                with col_i2:
                    if st.button("Lösung anzeigen"):
                        # Speichere das Wort zur Anzeige und render neu
                        st.session_state[sol_key] = current_row["en"]
                        st.rerun()
                with col_i3:
                    if st.button("Serie beenden"):
                        # Direkt abbrechen und Zusammenfassung anzeigen
                        input_state["index"] = len(input_state["order"])
                        st.session_state[key] = input_state
                        st.rerun()
                # Auswerten der Antwort
                if submit_answer:
                    correct = answers_equal(answer, current_row["en"])
                    if correct:
                        st.success("✔ Richtig!")
                        input_state["score"] += 1
                    else:
                        st.error(f"✘ Falsch — Richtig ist: {current_row['en']}")
                    input_state["results"].append(
                        {
                            "de": current_row["de"],
                            "en": current_row["en"],
                            "answer": answer,
                            "correct": correct,
                        }
                    )
                    input_state["total"] += 1
                    input_state["index"] += 1
                    st.session_state[key] = input_state
                    st.rerun()
                # Fortschrittsanzeige
                st.write(
                    f"Frage {input_state['index'] + 1} / {len(input_state['order'])} – Punkte: {input_state['score']} / {input_state['total']}"
                )

    # Footer
    st.caption(
        f"Sitzung: {datetime.now().strftime('%d.%m.%Y %H:%M')} "
        f"— Insgesamt geladene Vokabeln: {len(df)}"
    )


if __name__ == "__main__":
    main()
