Wortschatz‑Spiele (Klassen 7–9)
================================

Dieses Paket enthält eine komplett deutsche Version der Streamlit‑App, mit der
Schüler der Klassen 7–9 ihren englischen Wortschatz üben können. Die Anwendung
lädt alle CSV‑Dateien im Verzeichnis `data/` (rekursiv) und erlaubt, die
angezeigten Vokabeln nach Klasse und Seite zu filtern. Anschließend können
drei unterschiedliche Spiele gespielt werden:

* **Galgenmännchen** – Rate das englische Wort Buchstabe für Buchstabe. Das
  Programm zeigt eine ASCII‑Grafik des Galgens, die sich bei jedem falschen
  Versuch weiter aufbaut. Außerdem steht eine Bildschirmtastatur zur
  Verfügung, um einzelne Buchstaben anzuklicken; du kannst aber auch das
  gesamte Wort eintippen.
* **Wörter ziehen** – Finde die Paare per Drag‑and‑Drop: Es werden die
  englischen und deutschen Begriffe als Karten angezeigt. Ziehe die Karten
  zusammen, um passende Paare zu bilden. Ein Timer misst die benötigte Zeit.
* **Eingabe (DE → EN)** – Schreibe das passende englische Wort.

Zudem gibt es eine Option **„Nur Einzelwörter“**, welche längere Begriffe,
Abkürzungen und Wörter mit mehreren Bestandteilen ausfiltert. Diese Option
steht für alle Spiele zur Verfügung.

### Vorbereitung

1. Sorge dafür, dass **Python 3.11+** installiert ist (idealerweise via Anaconda).
2. Installiere die benötigten Bibliotheken (einmalig):

   ```bat
   install_requirements.bat
   ```

3. Starte die Anwendung:

   ```bat
   start_wortschatz_spiele.bat
   ```

Die Anwendung öffnet sich in deinem Standardbrowser. Falls der Port 8501
belegt ist, wählt die Anwendung automatisch einen freien Port.

### Daten aktualisieren

Um neue Vokabeln hinzuzufügen, lege weitere CSV‑Dateien ins Unterverzeichnis
`data/`. Das Programm erkennt sie beim nächsten Start automatisch. Jede CSV
muss mindestens die Spalten **`klasse`**, **`page`**, **`de`**, **`en`** besitzen.

### Debugging

Sollte die App nicht starten, hilft die Datei `start_debug.bat`. Sie führt die
App im Debug‑Modus aus, hält die Konsole offen und schreibt ein Logfile
`start_debug.log`.
