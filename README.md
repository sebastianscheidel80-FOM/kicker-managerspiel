# kicker-managerspiel – Auswertungstool

Auswertung unserer privaten Managerspiel-Runde (Bundesliga 2026/27, sechs Manager,
eigene Regeln). Das Tool bestimmt pro Spieltag die gewertete Elf jedes Managers
(inklusive Nachrückern und Strafnoten), rechnet die fünf Kategorien, die
Rangpunkte 6–1 mit Gleichstandsteilung, die Spieltagssumme und die Saisontabelle –
und zwar so, dass jeder Schritt in einer Datei nachlesbar ist.

Die verbindlichen Regeln stehen in `REGELN_1.md` (v1.2). Bei Abweichungen
zwischen Programm und Regeldatei gilt die Regeldatei; das Programm wird angepasst.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `kickerspiel/model.py` | Datenklassen: Spieler, Aufstellung, Spieltagsdaten |
| `kickerspiel/engine.py` | Regel-Engine – reine Logik, kennt keine Dateien |
| `kickerspiel/report.py` | Textreport im Format der Runde |
| `tests/` | Sieben Regel-Testfälle aus dem Briefing, Randfälle, Regressionstest 34. Spieltag 2025/26 |
| `beispiele/` | Beispielreports zum Lesen (Regressionstest, Sonderfälle) |
| `daten/spielerbasis/` | Spielerbasis der Saison (Auktionsergebnis mit kicker-Namen, Verein, Position) |
| `daten/spieltag_XX/` | Je Spieltag: Aufstellungs-Mails (.eml), kicker-Daten, Auswertung, Report |
| `docs/` | Architektur und Entscheidungen |
| `.github/workflows/tests.yml` | Tests laufen automatisch bei jedem Push |

Noch nicht enthalten (Etappe 2): Mail-Parser (`.eml` → Aufstellung), kicker-Abruf
(Schema-Seiten → Spieltagsdaten), Excel-Ausgabe, Kommandozeile.

## Einrichtung

```
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e .[test]
pytest
```

`pytest` muss alle Tests grün melden, bevor an der Engine etwas geändert wird.

## Wie die Engine rechnet (Kurzfassung)

1. **Gewertete Elf.** Jeder Stammspieler mit kicker-Note zählt selbst. Hat er keine
   Note, rückt der zuerst gelistete Ersatzspieler derselben kicker-Position nach,
   sofern der eine Note hat; Ersatzspieler ohne Note werden übersprungen. Gibt es
   keinen, bleibt der Stammspieler mit Strafnote 5,5 in der Wertung. Bei mehr
   Ausfällen als Ersatz gilt die Reihenfolge der Abgabe. Der Ersatztorwart rückt
   nur für den Stammtorwart nach.
2. **Strafgegentor.** Wer mit Strafnote gewertet wird und 0 Minuten gespielt hat,
   bekommt als Torwart oder Abwehrspieler die Gegentore seines Vereins plus ein
   Strafgegentor (Torwart alles ×2). Wer kurz gespielt hat, bekommt nur die
   Vereinsgegentore; seine Tore und Vorlagen zählen.
3. **Nicht zuordenbarer Name.** Gilt wie ein Stammspieler ohne Einsatz. Rückt
   niemand nach: 5,5, und als TOR/ABW die höchsten Gegentore des Spieltags plus
   ein Strafgegentor.
4. **Kategorien.** Notenschnitt der elf Noten; Gegentore (TOR ×2, ABW ×1); Tore
   (STU ×2); Vorlagen (MIT ×2); Anzahl gewerteter Spieler in der Elf des Tages.
5. **Rangpunkte.** Je Kategorie 6-5-4-3-2-1. Gleichstände teilen die Punkte der
   belegten Ränge (zwei Erste je 5,5; drei Erste je 5; vier Dritte je 2,5).
6. **Saison.** Summe aller Spieltage, Spieltagssiege (bei Gleichstand geteilt),
   Verlauf, Kategorie-Profil, Spieler-Beiträge.

Alle Zwischenwerte werden als exakte Brüche gerechnet; Gleichstände entstehen nur
bei wirklich gleichen Werten, nie durch Rundung.

## Montags-Ablauf (Zielbild, ab Etappe 2)

1. Sechs Aufstellungs-Mails als `.eml` in `daten/spieltag_XX/` ablegen.
2. `kicker aufstellungen XX` – Mails einlesen, Namen gegen die Spielerbasis
   abgleichen, Kontrolldatei `aufstellungen_stXX.xlsx` prüfen.
3. `kicker kickerdaten XX` – kicker-Schema-Seiten und Elf des Tages einlesen
   (Browser), Kontrolldatei `kickerdaten_stXX.xlsx` prüfen.
4. `kicker auswerten XX` – Report und Excel-Auswertung erzeugen, Saisontabelle
   aktualisieren.
5. Alles einchecken: `git add . && git commit -m "Spieltag XX ausgewertet" && git push`.

## Lesehilfe für den Report

`↑` hinter einem Namen: Nachrücker (Spalte „Herkunft“ sagt, für wen und von
welchem Bankplatz). `5,5*`: Strafnote. `GegT 3+1`: drei Vereinsgegentore plus ein
Strafgegentor. Die Zeile „gewichtet“ zeigt die Werte, die in die Rangwertung
eingehen, die Zeile „Rangpunkte“ die Punkte je Kategorie. Das Protokoll darunter
erklärt jeden Nachrücker und jede Strafnote in Klartext.
