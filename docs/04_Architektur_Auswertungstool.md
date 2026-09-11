# Architekturvorschlag – Auswertungstool Kicker-Managerspiel 2026/27

> Entwurf zur Freigabe, Stand 07.09.2026. Grundlage: REGELN_1.md v1.1, 02_Aufgabe_Auswertungstool.md, der Beispielreport zum 34. Spieltag 2025/26 und deine Antworten von heute (nur du nutzt das Tool; die Spielerbasis kommt als Datei; Format offen gelassen).

## 1. Formatentscheidung: Python-Paket mit Kommandozeile, Excel-Erfassung und Textreport

Da du das Format offen gelassen hast, setze ich meine Empfehlung um. Die Regel-Engine wird ein reines Python-Modul ohne jede Datei- oder Oberflächenabhängigkeit: Aufstellungen und Spieltagsdaten gehen als Datenobjekte hinein, ein vollständig nachvollziehbares Ergebnis kommt heraus. Darum herum liegen austauschbare Ein- und Ausgabebausteine. Die Erfassung der kicker-Daten läuft in Stufe 1 über eine vorbefüllte Excel-Vorlage je Spieltag, weil rund 90 Zeilen in Excel schneller und fehlerärmer zu tippen sind als in einer Web-Maske. Der Report entsteht als Textdatei im bisherigen Format der Runde, ergänzt um Markierungen für Nachrücker und Strafnoten, plus eine Excel-Auswertung. Für Stufe 2 bleibt die Engine unverändert: Der kicker-Abruf über den Browser auf deinem Rechner läuft ohnehin in einer Claude-Sitzung, in der Python zur Verfügung steht, und ein Copy-Paste-Parser oder eine Streamlit-Oberfläche docken an dieselben Datenobjekte an.

## 2. Aufbau

| Modul | Aufgabe | Kennt Dateien? |
|---|---|---|
| `model.py` | Datenklassen: Spieler, Aufstellung, Spieltagsdaten, Ergebnisse | nein |
| `engine.py` | Das Regelwerk: gewertete Elf mit Nachrückern und Strafnote, fünf Kategorien, Rangpunkte mit Gleichstandsteilung, Spieltagssumme, Saisontabelle, Protokoll | nein |
| `spielerbasis.py` | Spielerbasis aus Excel/CSV einlesen und prüfen (Positionen, Dubletten, ein Manager je Spieler) | ja |
| `mail_parser.py` | Eingefügten Mailtext in Aufstellungen umsetzen, Namen gegen die Spielerbasis abgleichen, Warnungen ausgeben | nein (Text hinein, Aufstellung heraus) |
| `erfassung.py` | Excel-Erfassungsvorlage je Spieltag erzeugen und wieder einlesen | ja |
| `report.py` | Textreport im bisherigen Format und Excel-Auswertung | ja |
| `cli.py` | Befehle: `aufstellungen`, `vorlage`, `auswerten`, `saison` | ja |
| `tests/` | Die sieben Testfälle aus dem Briefing, Regressionstest 34. Spieltag 2025/26, Randfälle | – |

Die Engine importiert nichts aus den anderen Modulen. Alles, was Dateien liest oder schreibt, liegt außerhalb.

## 3. Ablauf pro Spieltag (Stufe 1)

1. Du fügst die sechs Aufstellungs-Mails in eine Textdatei ein und rufst `kicker aufstellungen 2` auf. Der Parser gleicht jeden Namen mit der Spielerbasis ab, prüft Zugehörigkeit zum Manager, Formation 3-5-2 nach kicker-Position und die Bank (vier Spieler, der letzte ein Torwart) und schreibt `aufstellungen_st02.json` plus einen Kontrollausdruck mit allen Warnungen.
2. `kicker vorlage 2` erzeugt `kicker_st02.xlsx`: Blatt „Spieler“ mit den 90 aufgestellten Spielern (Manager, Rolle Stamm/Bank 1–4, Position, Spieler, Verein, Note, Tore, Vorlagen, Elf des Tages) und Blatt „Vereine“ mit den 18 Vereinen (Gegentore, Spiel ausgefallen).
3. Du füllst die Vorlage von kicker.de aus. Leere Note bedeutet „keine Note“. Gegentore werden einmal je Verein eingetragen, nicht je Spieler.
4. `kicker auswerten 2` lässt die Engine laufen und schreibt `report_st02.txt`, `auswertung_st02.xlsx` und `ergebnis_st02.json`. Die Saisontabelle wird bei jedem Lauf aus allen vorhandenen Ergebnisdateien neu aufgebaut, sodass jeder Spieltag jederzeit korrigiert und neu gerechnet werden kann (Tippfehler, Nachholspiele).

## 4. Datenmodell

Ein Spieler hat eine eindeutige Kennung, den Namen in kicker-Schreibweise, Verein, die kicker-Position (TOR, ABW, MIT, STU – gilt die ganze Saison), Manager, Kaufpreis und eine Gültigkeit „ab/bis Spieltag“ für Winterwechsel. Eine Aufstellung besteht aus dem Manager, elf Stammspielern in genannter Reihenfolge und vier Ersatzspielern in Bankreihenfolge. Spieltagsdaten enthalten je Spieler Note oder „keine Note“, Tore, Vorlagen und Elf des Tages, je Verein die Gegentore und ob gespielt wurde. Das Ergebnis liefert je Manager die gewertete Elf mit Herkunft jedes Platzes (Stammspieler, Nachrücker für wen, Strafnote), Rohwerte und gewichtete Werte je Kategorie, Rangpunkte, Summe und Platz sowie Protokollzeilen im Klartext.

## 5. Regel-Engine

Gewertete Elf (Regeln v1.4): Stammspieler mit Note zählen selbst. Die Ausfälle werden in umgekehrter Aufstellungsreihenfolge bedient (der zuletzt genannte zuerst, der zuerst genannte bleibt am längsten drin). Für jeden Ausfall rückt der zuerst gelistete, noch nicht verbrauchte Ersatzspieler derselben kicker-Position mit Note nach. Gibt es keinen und hatte der Stammspieler 0 Minuten, rückt der zuerst gelistete Ersatzspieler derselben Position nach, der eingesetzt wurde, aber keine Note bekam (Note 5,5, Statistiken zählen, kein Strafgegentor). Sonst bleibt der Stammspieler mit Strafnote 5,5 in der Wertung; seine Tore, Vorlagen und Gegentore aus dem Spiel zählen. Der Ersatztorwart rückt nur für den Stammtorwart nach. Die gewertete Elf behält die Aufstellungsreihenfolge; ein Nachrücker steht auf dem Platz des Ersetzten.

Kategorien: Notenschnitt der elf Noten inklusive Strafnoten; Gegentore des Vereins für jeden gewerteten TOR (doppelt) und ABW (einfach); Tore mit STU doppelt; Vorlagen mit MIT doppelt; Anzahl gewerteter Spieler in der Elf des Tages. Nur die elf gewerteten Spieler zählen.

Rangpunkte: Je Kategorie werden die sechs Manager sortiert (niedrigster Schnitt, wenigste Gegentore, meiste Tore, Vorlagen, Elf-des-Tages-Nennungen). Manager mit gleichem Wert bilden eine Gruppe und teilen die Punkte der von ihnen belegten Ränge (6-5-4-3-2-1) gleichmäßig: zwei Erste je 5,5, drei Erste je 5,0, vier Dritte je 2,5. Spieltagssumme, Platz und Spieltagssieg (bei Gleichstand geteilt) folgen daraus. Die Saisontabelle summiert alle gewerteten Spieltage und führt Verlauf, Spieltagssiege, Kategorie-Profil (wo holt wer seine Punkte) und Spieler-Beiträge (gewertete Einsätze, Notenschnitt, Tore, Vorlagen, Gegentore, Elf des Tages, Strafnoten je Spieler).

Rechengenauigkeit: Schnitte und Gleichstände werden exakt verglichen (Bruchrechnung, keine Rundungsartefakte), die Anzeige rundet auf zwei Nachkommastellen. Im Beispiel liegen Andreas und Martin mit je 36,0 Notensumme exakt gleichauf und teilen 5 und 4 zu 4,5 – genau das muss die Engine reproduzieren.

## 6. Ausgaben

Der Textreport behält die Struktur des bisherigen Reports bei (Gesamtstand mit Punkten und Spieltagssiegen, Ergebnis des Spieltags, fünf Kategorie-Rankings mit Punkten und Rohwert in Klammern, je Manager die Tabelle der elf gewerteten Spieler). Neu sind eine Kopfzeile je Manager mit den gewichteten Werten, in der Spielertabelle die Rohwerte statt der bereits gewichteten Zahlen, ein Stern an Strafnoten (`5,5*`), ein Pfeil an Nachrückern mit dem Namen des ersetzten Spielers und ein kurzer Protokollblock je Manager. Die Excel-Auswertung enthält den Spieltag (Rohwerte, gewichtete Werte, Rangpunkte) und die Saison (Tabelle, Verlauf kumuliert je Spieltag, Kategorie-Profil, Spieler-Beiträge).

## 7. Tests

Die sieben Fälle aus Abschnitt 4 des Briefings werden eins zu eins als Tests umgesetzt. Dazu kommt der Regressionstest 34. Spieltag 2025/26: Aus deinem Beispiel rekonstruiere ich die Eingaben der 66 gewerteten Spieler (Gewichtung herausgerechnet) und prüfe, dass alle Rohwerte, Rangpunkte, Gleichstandsteilungen, Spieltagssummen und Plätze exakt herauskommen. Randfälle: drei- und vierfache Gleichstände, exakt gleiche Notenschnitte, Torwart auf einem freien Bankplatz, zweiter Ersatz derselben Position, Kurzeinsatz eines Verteidigers mit Gegentoren, ungültige Formation, Saisonsummierung über mehrere Spieltage.

## 8. Festlegungen, die ich treffe (bitte Einspruch, wenn eine falsch ist)

1. Positionskürzel TOR, ABW, MIT, STU wie im bisherigen Report und in der kicker-Kaderliste.
2. Managernamen im Report: Sebastian, Martin, Wolfgang, Andreas, Daniel, Thomas.
3. Gegentore sind alle Gegentore des Vereins im Spiel, unabhängig von der Einsatzzeit des Spielers („alle Gegentore seines realen Vereins“).
4. Eigentore zählen weder als Tor noch als Abzug; Elfmetertore zählen normal; Vorlagen nach kicker-Zählung.
5. Ein Ersatzspieler rückt höchstens einmal nach und nur für einen Stammspieler derselben kicker-Position; die Bankreihenfolge ist die Reihenfolge in der Mail.
6. Eine Aufstellung gilt nur mit Formation 3-5-2 nach kicker-Position und einer Bank aus vier Spielern mit Torwart am Ende. Abweichungen werden gemeldet, nicht stillschweigend korrigiert.
7. Spielabsage: Betroffene Spieler haben „keine Note“, die normale Nachrückregel greift. Sobald das Nachholspiel gespielt ist, wird der betroffene Spieltag mit den dann vorliegenden Noten neu gerechnet; das Tool kann jeden Spieltag jederzeit neu berechnen.
8. Spieltagssiege werden wie bisher als Statistik geführt, bei Gleichstand geteilt (½, ⅓ …), und sind kein Tiebreaker, solange REGELN_1.md nichts anderes sagt. Ich trage sie als Abschnitt in REGELN_1.md nach.
9. Winterwechsel: Die Spielerbasis erhält „gültig ab/bis Spieltag“; verkaufte Spieler bleiben mit ihrer Historie erhalten.
10. Ablage: Das Tool lebt in einem Ordner auf deinem Rechner (bitte im Claude-Desktop verbinden, sobald die erste Etappe steht); zusätzlich lege ich die Quelldateien im Projektwissen ab, damit jede neue Sitzung ohne Upload weiterarbeiten kann.

## 9. Offene Regelfragen

A. Mehr Ausfälle als Ersatz derselben Position: Ursprünglich (v1.2/1.3) bekam der zuerst genannte Stammspieler den Nachrücker. Seit v1.4 (Rückmeldung Wolfgang, 10.09.2026) gilt die umgekehrte Reihenfolge: Der zuletzt genannte Stammspieler wird zuerst ersetzt, der zuerst genannte bleibt am längsten drin – wer vorn steht, ist der wichtigste. Damit kann der Manager über die Reihenfolge steuern, wen er im Zweifel behält.

B. Strafnote 5,5 ohne jeden Einsatz: Zählen die Gegentore des Vereins trotzdem? Im Beispiel hat Guerreiro (ABW, 5,5) ein Gegentor angerechnet bekommen – so wurde offenbar bisher gerechnet. Mein Vorschlag: ja, Vereins-Gegentore zählen für jeden gewerteten TOR/ABW, auch mit 5,5. Das ist einfach zu erfassen und schließt das Schlupfloch, dass ein sicher nicht spielender Torwart 0 Gegentore und damit den Bestwert bringt. Die Alternative (nur bei Kurzeinsatz) braucht in der Erfassung ein zusätzliches Feld „eingesetzt“.

C. Fehlende oder ungültige Aufstellung: Mein Vorschlag ist, dass die letzte gültige Aufstellung des Managers weitergilt. Die Alternative „elf Strafnoten und 0 in allen Kategorien“ hat einen Haken: 0 Gegentore wären der Bestwert, der Manager müsste dort künstlich auf den letzten Rang gesetzt werden.

## 10. Etappenplan

Etappe 1 nach Freigabe: `model.py`, `engine.py`, Testsuite mit den sieben Fällen, Regressionstest und Randfällen, dazu Diff-Zusammenfassung und Restliste. Etappe 2: Spielerbasis-Import (sobald deine Datei da ist), Excel-Erfassungsvorlage, Textreport, Excel-Auswertung, Kommandozeile. Etappe 3: Mail-Parser (sobald Beispielmails da sind) und der Echtlauf für den 2. Spieltag. Stufe 2 danach: kicker-Import per Copy-Paste oder Browser-Abruf, optional eine Streamlit-Oberfläche auf derselben Engine.
