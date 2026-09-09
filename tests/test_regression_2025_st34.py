"""Regressionstest: 34. Spieltag 2025/26, nachgerechnet aus dem Report der Vorsaison.

Der Report zeigte je Manager die elf gewerteten Spieler mit Note und bereits
gewichteten Werten (TW-Gegentore ×2, STU-Tore ×2, MIT-Vorlagen ×2). Hier
werden die Rohwerte eingegeben und geprüft, dass die Engine exakt die Punkte
des Reports reproduziert – inklusive aller Gleichstandsteilungen.

Regelstand 2025/26: noch kein Strafgegentor. Spieler mit 5,5 im Report werden
als „keine Note, kein Ersatz“ modelliert (Strafnote); Guerreiro (ABW, 5,5) bekam
im Report 1 Gegentor angerechnet – Vereinsgegentore zählen also auch bei Strafnote.
Vereine sind nicht bekannt; jeder TW/ABW erhält einen eigenen Pseudo-Verein
mit seinen Gegentoren, MIT/STU teilen sich einen Dummy-Verein.
"""
from fractions import Fraction

from kickerspiel.engine import REGELN_2025_26, Kategorie, saisontabelle, schnitt_text, werte_spieltag
from kickerspiel.model import Aufstellung, Position, Spieler, Spielerdaten, Spieltagsdaten, Vereinsdaten

# (Name, Position, Note oder None, Gegentore Verein (roh), Tore (roh), Vorlagen (roh), EdT)
REPORT = {
    "Andreas": [
        ("Urbig", "TOR", 3.0, 1, 0, 0, False),
        ("Tapsoba", "ABW", 2.5, 1, 0, 0, False),
        ("Laimer", "ABW", 3.5, 1, 0, 0, False),
        ("Guerreiro", "ABW", None, 1, 0, 0, False),
        ("Aleix Garcia", "MIT", 3.0, 0, 0, 1, False),
        ("M. Tillman", "MIT", 3.5, 0, 0, 0, False),
        ("Schmid", "MIT", 4.0, 0, 0, 0, False),
        ("Nusa", "MIT", 4.0, 0, 0, 0, False),
        ("Kimmich", "MIT", 2.0, 0, 0, 1, False),
        ("Kane", "STU", 1.0, 0, 3, 0, True),
        ("Undav", "STU", 4.0, 0, 0, 1, False),
    ],
    "Daniel": [
        ("Gulacsi", "TOR", 4.0, 4, 0, 0, False),
        ("Upamecano", "ABW", 3.0, 1, 0, 0, False),
        ("Ryerson", "ABW", 3.0, 0, 0, 1, False),
        ("Lukeba", "ABW", 4.0, 4, 0, 0, False),
        ("Musiala", "MIT", 4.0, 0, 0, 0, False),
        ("Nebel", "MIT", 3.5, 0, 0, 0, False),
        ("Kramaric", "MIT", 5.0, 0, 0, 0, False),
        ("Seiwald", "MIT", 4.0, 0, 0, 0, False),
        ("Lokonga", "MIT", 4.0, 0, 0, 0, False),
        ("Luis Diaz", "STU", 2.0, 0, 0, 1, False),
        ("Bülter", "STU", None, 0, 0, 0, False),
    ],
    "Martin": [
        ("Kobel", "TOR", 2.5, 0, 0, 0, False),
        ("Tah", "ABW", 3.0, 1, 0, 0, False),
        ("Anton", "ABW", 2.5, 0, 0, 0, False),
        ("Orban", "ABW", 5.0, 4, 0, 0, False),
        ("Olise", "MIT", 3.5, 0, 0, 0, False),
        ("Maza", "MIT", 4.0, 0, 0, 0, False),
        ("Burger", "MIT", 4.0, 0, 0, 0, False),
        ("Goretzka", "MIT", 2.0, 0, 0, 1, False),
        ("Beste", "MIT", 2.5, 0, 1, 0, False),
        ("Lemperle", "STU", 4.5, 0, 0, 0, False),
        ("Pejcinovic", "STU", 2.5, 0, 1, 0, False),
    ],
    "Sebastian": [
        ("Grabara", "TOR", 3.0, 1, 0, 0, False),
        ("Stanisic", "ABW", 3.0, 1, 0, 0, False),
        ("Mittelstädt", "ABW", 4.0, 2, 0, 0, False),
        ("R. Koch", "ABW", 4.0, 2, 0, 0, False),
        ("Baumgartner", "MIT", 4.0, 0, 0, 0, False),
        ("Grifo", "MIT", 3.0, 0, 0, 0, False),
        ("Amiri", "MIT", 2.0, 0, 1, 0, False),
        ("El Khannouss", "MIT", None, 0, 0, 0, False),
        ("Suzuki", "MIT", None, 0, 0, 0, False),
        ("Tabakovic", "STU", 2.5, 0, 1, 0, False),
        ("Guirassy", "STU", 2.5, 0, 1, 0, False),
    ],
    "Thomas": [
        ("Flekken", "TOR", 3.0, 1, 0, 0, False),
        ("Doekhi", "ABW", 3.0, 0, 0, 0, False),
        ("Trimmel", "ABW", 2.5, 0, 0, 0, False),
        ("R. Baku", "ABW", 3.5, 4, 0, 0, False),
        ("Kaminski", "MIT", 5.0, 0, 0, 0, False),
        ("Stage", "MIT", 4.0, 0, 0, 0, False),
        ("Chaibi", "MIT", 4.5, 0, 0, 0, False),
        ("Poku", "MIT", None, 0, 0, 0, False),
        ("Claude-Maurice", "MIT", None, 0, 0, 0, False),
        ("Schick", "STU", 5.0, 0, 0, 0, False),
        ("Ansah", "STU", 3.5, 0, 0, 0, False),
    ],
    "Wolfgang": [
        ("Neuer", "TOR", 3.0, 1, 0, 0, False),
        ("Ginter", "ABW", 1.5, 1, 1, 1, True),
        ("Svensson", "ABW", 3.5, 0, 0, 0, False),
        ("Chabot", "ABW", 2.5, 2, 0, 0, False),
        ("S. El Mala", "MIT", 3.0, 0, 1, 0, False),
        ("Eriksen", "MIT", 1.5, 0, 0, 3, True),
        ("Führich", "MIT", 3.5, 0, 0, 1, False),
        ("Stiller", "MIT", 4.0, 0, 0, 0, False),
        ("Manzambi", "MIT", 2.0, 0, 0, 1, True),
        ("Beier", "STU", 4.5, 0, 0, 0, False),
        ("Fabio Silva", "STU", None, 0, 0, 0, False),
    ],
}

# Erwartung laut Report: (Rohwert, Rangpunkte) je Kategorie
ERWARTET = {
    "Andreas":   {"Note": ("3,27", 4.5), "Gegentore": (5, 5.0), "Tore": (6, 6.0), "Vorlagen": (5, 5.0), "EdT": (1, 5.0), "Summe": 25.5, "Platz": 2},
    "Daniel":    {"Note": ("3,82", 2.0), "Gegentore": (13, 1.0), "Tore": (0, 1.5), "Vorlagen": (2, 3.5), "EdT": (0, 2.5), "Summe": 10.5, "Platz": 5},
    "Martin":    {"Note": ("3,27", 4.5), "Gegentore": (5, 5.0), "Tore": (3, 4.0), "Vorlagen": (2, 3.5), "EdT": (0, 2.5), "Summe": 19.5, "Platz": 3},
    "Sebastian": {"Note": ("3,55", 3.0), "Gegentore": (7, 2.0), "Tore": (5, 5.0), "Vorlagen": (0, 1.5), "EdT": (0, 2.5), "Summe": 14.0, "Platz": 4},
    "Thomas":    {"Note": ("4,09", 1.0), "Gegentore": (6, 3.0), "Tore": (0, 1.5), "Vorlagen": (0, 1.5), "EdT": (0, 2.5), "Summe": 9.5, "Platz": 6},
    "Wolfgang":  {"Note": ("3,14", 6.0), "Gegentore": (5, 5.0), "Tore": (2, 3.0), "Vorlagen": (11, 6.0), "EdT": (3, 6.0), "Summe": 26.0, "Platz": 1},
}


def baue_spieltag():
    index, aufstellungen = {}, []
    daten = Spieltagsdaten(34)
    daten.vereine["Dummy"] = Vereinsdaten(0)
    for manager, zeilen in REPORT.items():
        start = []
        for name, pos, note, gt, tore, vorl, edt in zeilen:
            sid = f"{manager}:{name}"
            position = Position(pos)
            verein = f"V:{sid}" if position in (Position.TOR, Position.ABW) else "Dummy"
            index[sid] = Spieler(sid, name, verein, position, manager)
            if verein != "Dummy":
                daten.vereine[verein] = Vereinsdaten(gt)
            daten.spieler[sid] = Spielerdaten(note, tore, vorl, edt, eingesetzt=False if note is None else True)
            start.append(sid)
        aufstellungen.append(Aufstellung(manager, start, bank=[]))
    return index, aufstellungen, daten


def test_34_spieltag_2025_26_exakt_reproduziert():
    index, aufstellungen, daten = baue_spieltag()
    erg = werte_spieltag(aufstellungen, daten, index, REGELN_2025_26)

    for manager, soll in ERWARTET.items():
        m = erg.manager[manager]
        assert schnitt_text(m.werte[Kategorie.NOTE]) == soll["Note"][0], manager
        assert m.rangpunkte[Kategorie.NOTE] == Fraction(str(soll["Note"][1])), manager
        for kat, key in ((Kategorie.GEGENTORE, "Gegentore"), (Kategorie.TORE, "Tore"), (Kategorie.VORLAGEN, "Vorlagen"), (Kategorie.EDT, "EdT")):
            assert m.werte[kat] == soll[key][0], (manager, key)
            assert m.rangpunkte[kat] == Fraction(str(soll[key][1])), (manager, key)
        assert m.summe == Fraction(str(soll["Summe"])), manager
        assert m.platz == soll["Platz"], manager

    assert erg.reihenfolge == ["Wolfgang", "Andreas", "Martin", "Sebastian", "Daniel", "Thomas"]
    assert erg.spieltagssieg["Wolfgang"] == 1
    assert sum(m.summe for m in erg.manager.values()) == 105          # 5 Kategorien × 21 Punkte


def test_34_spieltag_strafnoten_und_guerreiro():
    index, aufstellungen, daten = baue_spieltag()
    erg = werte_spieltag(aufstellungen, daten, index, REGELN_2025_26)
    strafnoten = {m: sum(1 for p in e.elf if p.strafnote) for m, e in erg.manager.items()}
    assert strafnoten == {"Andreas": 1, "Daniel": 1, "Martin": 0, "Sebastian": 2, "Thomas": 2, "Wolfgang": 1}
    guerreiro = next(p for p in erg.manager["Andreas"].elf if p.name == "Guerreiro")
    assert guerreiro.strafnote and guerreiro.gegentore_gew == 1 and guerreiro.strafgegentore == 0


def test_34_spieltag_saisontabelle_ein_spieltag():
    index, aufstellungen, daten = baue_spieltag()
    erg = werte_spieltag(aufstellungen, daten, index, REGELN_2025_26)
    s = saisontabelle([erg])
    assert [z.manager for z in s.zeilen] == ["Wolfgang", "Andreas", "Martin", "Sebastian", "Daniel", "Thomas"]
    assert s.zeile("Wolfgang").spieltagssiege == 1
    assert s.zeile("Wolfgang").kategorie_profil[Kategorie.VORLAGEN] == 6
