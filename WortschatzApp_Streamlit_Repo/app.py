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
- Hangman: Timer, Congrats+Time, Show solution, Show German hint (optional),
  Next word & New word.
- Wörter Memory (DE↔EN): Click/Tap-to-Match (alle Plattformen), optional Desktop-Drag,
  Timer, Show solution (DE—EN), Anzahl der Paare wählbar (ganze Seite ODER k-Paare), Seed-stabil,
  Button: „Neue Wortauswahl (neue Paare)“.
- Eingabe (DE→EN): Enter zum Prüfen, History-Tabelle live, Show solution, Next word (Skip).
- Unregelmäßige Verben Memory (aus Code): Tap-to-Match von 4 Feldern
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
    df["de"] = df["de"].astype(str).str.strip()
    df["en"] = df["en"].astype(str).str.strip()
    df = df.dropna(how="all", subset=["de", "en"])

    for k in ["classe", "page"]:
        try:
            df[k] = pd.to_numeric(df[k], errors="coerce")
        except Exception:
            pass

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
            order = list(range(len(rows)))    # FIX
            rnd = random.Random(seed_val) if seed_val else random.Random()
            rnd.shuffle(order)
            state["order"] = order
            state["idx"] = 0
        _set_word(state["idx"]); st.session_state[key] = state

    def new_word():
        t = state["timer"]; t["running"] = False; t["started_ms"] = 0; t["elapsed_ms"] = 0
        rnd = random.Random(time.time())
        i = rnd.randrange(len(rows))
        state["order"][state["idx"]] = i
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
                else:
                    st.warning("Not correct.")
                st.rerun()

    if state["solved"]:
        st.success(f"Congratulations! You solved it. Time: {fmt_ms(t['elapsed_ms'])}")

    if not state["solved"] and state["fails"] < len(HANGMAN_PICS)-1:
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
                            state["solved"] = True
                            st.session_state[key] = state

                        st.rerun()
    elif not state["solved"] and state["fails"] >= len(HANGMAN_PICS)-1:
        st.error("Game over. Try another word.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Next word", key=f"{key}_nextword_fail"):
                next_word(); st.rerun()
        with c2:
            if st.button("New word", key=f"{key}_newword_fail"):
                new_word(); st.rerun()
    else:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Next word", key=f"{key}_nextword"):
                next_word(); st.rerun()
        with c2:
            if st.button("New word", key=f"{key}_newword2"):
                new_word(); st.rerun()

# ---------- Wörter Memory (DE↔EN; Click/Tap; optional Drag) ----------
def game_word_memory(df_view: pd.DataFrame, classe: str, page: int,
                     show_solution_table: bool, subset_mode: str, subset_k: int,
                     seed_val: str, force_new_subset: bool = False):
    base_items = [
        {"de": r["de"], "en": r["en"]}
        for r in df_view.to_dict("records")
        if isinstance(r["de"], str) and isinstance(r["en"], str)
    ]
    if not base_items:
        st.info("No vocabulary.")
        return

    subset_state_key = f"memory_subset_{classe}_{page}"

    if force_new_subset:
        st.session_state.pop(subset_state_key, None)

    # WICHTIGER FIX: subset_mode kommt bereits als "all" oder "k" an – nicht erneut gegen UI-Label prüfen!
    items = _sample_subset(
        base_items, subset_mode, int(subset_k),
        seed_val, subset_state_key, ["de", "en"]
    )

    st.write(f"Pairs in this round: **{len(items)}**")
    st.caption("Klicke zwei Karten, die zusammengehören (DE ↔ EN). Optional: Drag-Modus auf Desktop.")

    if show_solution_table:
        st.subheader("Solution (DE — EN)")
        st.dataframe(
            pd.DataFrame(items)[["de", "en"]].rename(columns={"de": "DE", "en": "EN"}),
            use_container_width=True
        )

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
.correct {{ background:#e8f5e9; border-color:#2e7d32; cursor:default; }}
.selected {{ box-shadow:0 0 0 3px rgba(33,150,243,0.35) inset; }}
.wrong {{ animation: shake .25s linear; border-color: #d32f2f!important; }}
@keyframes shake {{
  0%,100% {{ transform: translateX(0); }}
  25% {{ transform: translateX(-4px); }}
  75% {{ transform: translateX(4px); }}
}}
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
    [arr[i], arr[j]] = [arr[j], arr[i]];    // FIX
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

setModeLabel();
layoutShuffled();
</script>
</body>
</html>"""

    st.components.v1.html(html, height=600, scrolling=True)

# ---------- Eingabe (DE → EN) ----------
def game_input(df_view: pd.DataFrame, classe: str, page: int):
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

    items_hash = _hash_dict_list(items, ["de", "en"])
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
            {"text": verb["infinitive"],  "match": "infinitive",      "hidden": False},
            {"text": verb["pastSimple"],    "match": "pastSimple",      "hidden": False},
            {"text": verb["pastParticiple"],  "match": "pastParticiple",    "hidden": False},
            {"text": verb["meaning"],       "match": "meaning",         "hidden": False},
        ]
        random.shuffle(items)
        st.session_state.verbs_round = {
            "verb": verb,
            "items": items,
            "matches": {k: None for (_, k) in VERB_TARGETS},
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

    st.subheader("Unregelmäßige Verben Memory (Tippen statt Ziehen)")
    st.caption("Links ein Wort wählen, rechts das Ziel tippen. Slash-Formen (z. B. was/were) werden akzeptiert.")

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
    st.markdown(f"**Zeit:** {elapsed} Sek.      **Punkte gesamt:** {st.session_state.verbs_points_total}")

    left, right = st.columns(2, gap="large")

    with left:
        st.markdown("#### Wörter")
        options = [(i, it["text"]) for i, it in enumerate(st.session_state.verbs_round["items"]) if not it["hidden"]]
        if options:
            labels  = ["— bitte wählen —"] + [txt for _, txt in options]
            indices = [None] + [i for i, _ in options]

            if st.session_state.verbs_selected_idx is not None:
                if st.session_state.verbs_round["items"][st.session_state.verbs_selected_idx]["hidden"]:
                    st.session_state.verbs_selected_idx = None
                    if "verbs_word_radio" in st.session_state:
                        del st.session_state["verbs_word_radio"]

            if "verbs_word_radio" in st.session_state and st.session_state["verbs_word_radio"] in labels:
                chosen_label = st.radio("Wähle ein Wort", labels, key="verbs_word_radio")
            else:
                chosen_label = st.radio("Wähle ein Wort", labels, key="verbs_word_radio")

            if chosen_label == "— bitte wählen —":
                st.session_state.verbs_selected_idx = None
            else:
                try:
                    chosen_index = labels.index(chosen_label)
                    st.session_state.verbs_selected_idx = indices[chosen_index]
                except ValueError:
                    st.session_state.verbs_selected_idx = None

            if st.session_state.verbs_selected_idx is not None:
                st.info(f"Ausgewählt: **{chosen_label}**")
        else:
            st.write("Alle Wörter sind zugeordnet ✅")

    with right:
        st.markdown("#### Ziele")
        target_idx = st.session_state.verbs_selected_idx

        for name, key in VERB_TARGETS:
            current_match_text = st.session_state.verbs_round["matches"][key]

            if current_match_text is not None:
                st.button(f"{name}: ✅ {current_match_text}", key=f"verbs_target_{key}", disabled=True)
            else:
                btn_key = f"verb_target_btn_{key}"
                text = name
                if target_idx is not None:
                    selected_word = st.session_state.verbs_round["items"][target_idx]["text"]
                    text = f"Zuordnen: {name} (Wort: '{selected_word}')"

                if st.button(text, key=btn_key, disabled=(target_idx is None)):
                    if target_idx is not None:
                        selected_item = st.session_state.verbs_round["items"][target_idx]
                        selected_text = selected_item["text"]

                        # erlaubte Formen (Slash tolerant)
                        def allowed_forms(target_key: str, verb: dict) -> set[str]:
                            raw = verb[target_key]
                            forms = [raw]
                            if target_key != "meaning" and "/" in raw:
                                forms += [p.strip() for p in raw.split("/")]
                            return {normalize_text(x) for x in forms}

                        target_forms = allowed_forms(key, st.session_state.verbs_round["verb"])
                        selected_norm = normalize_text(selected_text)
                        is_correct = selected_norm in target_forms

                        if is_correct:
                            st.session_state.verbs_round["matches"][key] = selected_text
                            selected_item["hidden"] = True
                            st.session_state.verbs_points_total += 1

                            if all(st.session_state.verbs_round["matches"].values()):
                                st.session_state.verbs_round["completed"] = True

                            st.session_state.verbs_selected_idx = None
                            if "verbs_word_radio" in st.session_state:
                                del st.session_state["verbs_word_radio"]
                            st.success("Richtig! ✅"); st.rerun()
                        else:
                            st.error(f"Falsch! '{selected_text}' ist nicht die korrekte Form für {name}.")
                            st.session_state.verbs_selected_idx = None
                            if "verbs_word_radio" in st.session_state:
                                del st.session_state["verbs_word_radio"]
                            st.rerun()

    if st.session_state.verbs_round["completed"]:
        total_time = int(time.time() - st.session_state.verbs_round["start_ts"])
        st.balloons()
        st.success(f"Sehr gut! Alle 4 Formen von **{st.session_state.verbs_round['verb']['meaning']}** korrekt zugeordnet! Zeit: {total_time} Sek.")
        if st.button("Nächste Runde starten"):
            new_round(); st.rerun()

# ============================ Haupt-UI (Controller) ============================

def main():
    BASE_DIR = Path(__file__).parent

    st.title("📚 Wortschatz-Spiele")

    # Sidebar
    with st.sidebar:
        if st.button("🧹 Cache leeren (Dateisuche neu starten)"):
            st.cache_data.clear()
            st.rerun()

        if "dev_mode" not in st.session_state:
            st.session_state.dev_mode = False
        st.session_state.dev_mode = st.checkbox("Dev/Debug-Modus", value=st.session_state.dev_mode, key="dev_mode_cbox")

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
            st.subheader("Debug Info")
            st.write("df_info ist leer.")
        return

    def sort_key(label: str):
        m = re.search(r"Klasse (\d+)", label)
        klasse_num = int(m.group(1)) if m else 99
        kurs_order = 0 if 'E-Kurs' in label else (1 if 'G-Kurs' in label else (2 if 'Französisch' in label else 3))
        return (klasse_num, kurs_order)

    unique_labels = sorted(df_info["label"].unique(), key=sort_key)
    selected_label = st.selectbox("1. Wähle Klasse/Kurs", unique_labels)

    if selected_label:
        filtered_df = df_info[df_info["label"] == selected_label].reset_index(drop=True)
        unique_pages = sorted(filtered_df["page"].unique())
        selected_page = st.selectbox("2. Wähle Seite", unique_pages)

        current_info = filtered_df[filtered_df["page"] == selected_page].iloc[0]
        selected_path = current_info["path"]
        selected_classe = current_info["classe"]

        df_vocab = load_and_preprocess_df(selected_path)

        if df_vocab.empty:
            st.warning(f"Datei **{selected_path.name}** enthält keine Vokabeln.")

        game_options = {
            "Eingabe (DE → EN)": "input",
            "Wörter Memory (DE ↔ EN)": "memory",
            "Hangman (EN)": "hangman",
            "Unregelmäßige Verben Memory (aus Code)": "irregulars",
        }
        game_choice_label = st.selectbox("Wähle ein Spiel", list(game_options.keys()))
        game_choice = game_options.get(game_choice_label)

        if game_choice in ["input", "memory", "hangman"]:
            seed_val = st.sidebar.text_input("3. Seed (optional, für Reproduzierbarkeit)", value="")

            if game_choice == "input":
                if len(df_vocab) < 1:
                    st.info("Für das Eingabe-Spiel sind Seiten-Vokabeln nötig.")
                    st.caption(f"Sitzung: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} – Geladene Vokabeln (Seite): {len(df_vocab)}")
                else:
                    game_input(df_vocab, selected_label, selected_page)

            elif game_choice == "memory":
                memory_subset_mode = st.sidebar.radio(
                    "4. Wortanzahl wählen",
                    options=["Alle Vokabeln", "Subset (k Paare)"],
                    key="memory_subset_mode"
                )
                memory_subset_k = 0
                if memory_subset_mode == "Subset (k Paare)":
                    memory_subset_k = st.sidebar.slider(
                        "Anzahl Paare (k)",
                        min_value=2,
                        max_value=len(df_vocab),
                        value=min(10, len(df_vocab))
                    )

                show_sol = st.sidebar.checkbox("Lösungstabelle anzeigen")

                colBtn, _ = st.sidebar.columns(2)
                with colBtn:
                    if st.button("Neue Wortauswahl / Shuffle", key="new_subset_btn"):
                        force_new = True
                    else:
                        force_new = False

                if len(df_vocab) < 2:
                    st.info("Für das Memory-Spiel werden mindestens 2 Vokabelpaare benötigt.")
                else:
                    game_word_memory(
                        df_vocab, selected_label, selected_page,
                        show_sol,
                        "all" if memory_subset_mode == "Alle Vokabeln" else "k",
                        memory_subset_k,
                        seed_val,
                        force_new_subset=force_new
                    )

            elif game_choice == "hangman":
                if len(df_vocab) < 1:
                    st.info("Für das Hangman-Spiel sind Seiten-Vokabeln nötig.")
                else:
                    game_hangman(df_vocab, selected_label, selected_page, seed_val)

        elif game_choice == "irregulars":
            game_irregulars_assign()

        if st.session_state.dev_mode:
            st.subheader("Debug Info: Aktuelle Auswahl")
            st.write(f"Pfad: `{selected_path}`")
            st.dataframe(df_vocab.head(3))

    else:
        st.info("Wähle links eine Klasse und einen Kurs, um mit dem Spiel zu beginnen.")
        if st.session_state.dev_mode:
            st.subheader("Debug Info: Gefundene Dateien")
            st.dataframe(df_info.head(3))

if __name__ == "__main__":
    main()
