"""kicker-Spielschema (Reiter „Schema“) und Elf des Tages aus gespeichertem
Seitentext in Spieltagsdaten umsetzen.

Der Seitentext wird über den Browser gelesen und als .txt gespeichert
(daten/spieltag_XX/kicker/schema_<heim>_<gast>.txt). Aufbau des Textes:

    Bundesliga 2026/27, 2. Spieltag
    Frankfurt / 13. Platz / 1 / : / 4 / 1 / : / 0 / Augsburg / 1. Platz
    TORE
      Heimtor:  Schütze / Art, Vorlagengeber / Minute / Heim / : / Gast
      Gasttor:  Heim / : / Gast / Minute / Schütze / Art, Vorlagengeber
      Eigentor: "Name (Eigentor)"
    AUFSTELLUNG   Frankfurt  Name5,0 ... (11)   Augsburg  Name2,0 ... (11)
    TRAINER
    WECHSEL       Frankfurt  Einwechsler[Note] / Minute / Ausgewechselter[Note] ...
    RESERVEBANK   Frankfurt  Name (Tor), Name, Name ...
    KARTEN
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .model import Spielerdaten, Spieltagsdaten, Vereinsdaten
from .spielerbasis import Spielerbasis, ohne_initial

# kicker-Kurzname des Vereins (Schema/Tabelle) -> Vereinsname in der Spielerbasis
VEREINE = {
    "Bayern": "Bayern", "Leverkusen": "Leverkusen", "Frankfurt": "Frankfurt", "Dortmund": "Dortmund",
    "Stuttgart": "Stuttgart", "Leipzig": "Leipzig", "Freiburg": "Freiburg", "Augsburg": "Augsburg",
    "Mainz": "Mainz", "Bremen": "Bremen", "Köln": "Köln", "Union": "Union", "Union Berlin": "Union",
    "Hoffenheim": "Hoffenheim", "M’gladbach": "Gladbach", "M'gladbach": "Gladbach", "Gladbach": "Gladbach",
    "Mönchengladbach": "Gladbach", "HSV": "HSV", "Hamburg": "HSV", "Hamburger SV": "HSV",
    "Schalke": "Schalke", "Elversberg": "Elversberg", "Paderborn": "Paderborn",
    # Langformen (kicker zeigt sie im Schema-Kopf bei breitem Fenster)
    "FC Bayern München": "Bayern", "Bayern München": "Bayern", "Bayer 04 Leverkusen": "Leverkusen", "Bayer Leverkusen": "Leverkusen",
    "Eintracht Frankfurt": "Frankfurt", "Borussia Dortmund": "Dortmund", "VfB Stuttgart": "Stuttgart", "RB Leipzig": "Leipzig",
    "SC Freiburg": "Freiburg", "FC Augsburg": "Augsburg", "1. FSV Mainz 05": "Mainz", "FSV Mainz 05": "Mainz",
    "SV Werder Bremen": "Bremen", "Werder Bremen": "Bremen", "1. FC Köln": "Köln", "1. FC Union Berlin": "Union",
    "TSG Hoffenheim": "Hoffenheim", "TSG 1899 Hoffenheim": "Hoffenheim", "Borussia Mönchengladbach": "Gladbach", "Bor. Mönchengladbach": "Gladbach",
    "FC Schalke 04": "Schalke", "SV Elversberg": "Elversberg", "SC Paderborn 07": "Paderborn", "SC Paderborn": "Paderborn",
}
ABSCHNITTE = {"TORE", "AUFSTELLUNG", "TRAINER", "WECHSEL", "RESERVEBANK", "KARTEN", "KICKER ABO", "SPIELINFO", "INFO", "BESONDERE VORKOMMNISSE"}
MINUTE = re.compile(r"^\d{1,3}'(\s*\+\d+)?$")
NOTE_AM_ENDE = re.compile(r"^(.*?)(\d,\d)\s*$")
EIGENTOR = re.compile(r"\s*\(Eigentor\)\s*", re.I)
ELFMETER = re.compile(r"\s*\((Elfmeter|Foulelfmeter|Handelfmeter)\)\s*", re.I)


@dataclass
class KickerSpieler:
    verein: str
    name: str
    note: Optional[str] = None      # "3,5" oder None
    status: str = "Startelf"        # Startelf | Eingewechselt | Reservebank
    minute: Optional[str] = None
    tore: int = 0
    vorlagen: int = 0
    edt: bool = False

    @property
    def eingesetzt(self) -> bool:
        return self.status != "Reservebank"


@dataclass
class Tor:
    minute: str
    verein: str                     # Verein, dem das Tor zählt
    schuetze: str
    eigentor: bool
    art: str
    vorlage: Optional[str]
    stand: str


@dataclass
class Spiel:
    heim: str
    gast: str
    tore_heim: int
    tore_gast: int
    spieler: list[KickerSpieler] = field(default_factory=list)
    tore: list[Tor] = field(default_factory=list)
    warnungen: list[str] = field(default_factory=list)
    quelle: str = ""


def _verein(name: str) -> str:
    n = name.strip()
    if n in VEREINE:
        return VEREINE[n]
    for k, v in VEREINE.items():
        if k.lower() == n.lower():
            return v
    raise ValueError(f"Unbekannter Vereinsname im Schema: {name!r}")


def _name_note(zeile: str) -> tuple[str, Optional[str]]:
    m = NOTE_AM_ENDE.match(zeile.strip())
    if m and m.group(1).strip():
        return m.group(1).strip(), m.group(2)
    return zeile.strip(), None


# ---------------------------------------------------------------------------
# Schema-Seite
# ---------------------------------------------------------------------------

def schema_parsen(text: str, quelle: str = "") -> Spiel:
    zeilen = [z.rstrip() for z in text.splitlines()]
    roh = [z.strip() for z in zeilen]

    # Kopf: Teams und Ergebnis
    start = next((i for i, z in enumerate(roh) if re.match(r"^Bundesliga \d{4}/\d{2}, \d+\. Spieltag$", z)), None)
    if start is None:
        raise ValueError("Kopfzeile 'Bundesliga ..., N. Spieltag' nicht gefunden")
    i = start + 1
    kopf = []
    while i < len(roh) and roh[i] not in ("INFO", "SCHEMA", "TORE", "AUFSTELLUNG"):
        if roh[i] and not roh[i].endswith("Platz"):
            kopf.append(roh[i])
        i += 1
    namen = [k for k in kopf if not re.match(r"^\d+$|^:$", k)]
    zahlen = [k for k in kopf if re.match(r"^\d+$", k)]
    if len(namen) < 2 or len(zahlen) < 2:
        raise ValueError(f"Teams/Ergebnis im Kopf nicht erkannt: {kopf}")
    heim, gast = _verein(namen[0]), _verein(namen[1])
    tore_heim, tore_gast = int(zahlen[0]), int(zahlen[1])
    spiel = Spiel(heim, gast, tore_heim, tore_gast, quelle=quelle)

    # Abschnitte einsammeln
    abschnitte: dict[str, list[str]] = {}
    aktuell = None
    for z in roh[i:]:
        if z in ABSCHNITTE:
            aktuell = z
            abschnitte[aktuell] = []      # Reiterleiste nennt „AUFSTELLUNG“ schon vorher – der spätere, echte Abschnitt zählt
            continue
        if aktuell and z:
            abschnitte[aktuell].append(z)

    _aufstellung_parsen(spiel, abschnitte.get("AUFSTELLUNG", []))
    _wechsel_parsen(spiel, abschnitte.get("WECHSEL", []))
    _reservebank_parsen(spiel, abschnitte.get("RESERVEBANK", []))
    _tore_parsen(spiel, abschnitte.get("TORE", []))
    _plausibilitaet(spiel)
    return spiel


def _team_bloecke(spiel: Spiel, zeilen: list[str], art: str = "") -> dict[str, list[str]]:
    """Zerlegt einen Abschnitt in {verein: zeilen} anhand der Team-Zwischenüberschriften.

    Im breiten Seitenlayout zeigt kicker keine Zwischenüberschriften; dann wird nach Struktur geteilt:
    AUFSTELLUNG erste elf Zeilen = Heim, RESERVEBANK erste Zeile = Heim, WECHSEL nach dem
    Verein des ausgewechselten Spielers.
    """
    bloecke: dict[str, list[str]] = {}
    aktuell = None
    for z in zeilen:
        try:
            v = _verein(z)
        except ValueError:
            v = None
        if v in (spiel.heim, spiel.gast) and z == z.strip() and not NOTE_AM_ENDE.match(z):
            aktuell = v
            bloecke.setdefault(aktuell, [])
            continue
        if aktuell:
            bloecke[aktuell].append(z)
    if bloecke or not zeilen:
        return bloecke
    if art == "AUFSTELLUNG":
        return {spiel.heim: zeilen[:11], spiel.gast: zeilen[11:]}
    if art == "RESERVEBANK":
        return {spiel.heim: zeilen[:1], spiel.gast: zeilen[1:2]}
    if art == "WECHSEL":
        team_von = {p.name: p.verein for p in spiel.spieler}
        for j in range(0, len(zeilen) - 2, 3):
            if not MINUTE.match(zeilen[j + 1]):
                spiel.warnungen.append(f"Wechsel-Zeile nicht verstanden: {zeilen[j]!r}")
                continue
            aus, _ = _name_note(zeilen[j + 2])
            v = team_von.get(aus)
            if v is None:
                spiel.warnungen.append(f"Ausgewechselter {aus!r} keinem Team zuzuordnen")
                continue
            bloecke.setdefault(v, []).extend(zeilen[j:j + 3])
        return bloecke
    return bloecke


def _aufstellung_parsen(spiel: Spiel, zeilen: list[str]) -> None:
    for verein, block in _team_bloecke(spiel, zeilen, "AUFSTELLUNG").items():
        for z in block:
            name, note = _name_note(z)
            spiel.spieler.append(KickerSpieler(verein, name, note, "Startelf"))


def _wechsel_parsen(spiel: Spiel, zeilen: list[str]) -> None:
    for verein, block in _team_bloecke(spiel, zeilen, "WECHSEL").items():
        j = 0
        while j < len(block):
            if j + 2 < len(block) and MINUTE.match(block[j + 1]):
                ein, ein_note = _name_note(block[j])
                aus, _ = _name_note(block[j + 2])
                spiel.spieler.append(KickerSpieler(verein, ein, ein_note, "Eingewechselt", block[j + 1]))
                j += 3
            else:
                spiel.warnungen.append(f"Wechsel-Zeile nicht verstanden ({verein}): {block[j]!r}")
                j += 1


def _reservebank_parsen(spiel: Spiel, zeilen: list[str]) -> None:
    for verein, block in _team_bloecke(spiel, zeilen, "RESERVEBANK").items():
        for z in block:
            for name in z.split(","):
                n = re.sub(r"\s*\((Tor|TW)\)\s*", "", name).strip()
                if n:
                    spiel.spieler.append(KickerSpieler(verein, n, None, "Reservebank"))


def _tore_parsen(spiel: Spiel, zeilen: list[str]) -> None:
    # Nachspielzeit "90'" / "+2" auf zwei Zeilen → eine Minute "90'+2"
    t: list[str] = []
    for z in zeilen:
        if re.match(r"^\+\d+$", z) and t and MINUTE.match(t[-1]):
            t[-1] = t[-1] + z
        else:
            t.append(z)
    heim_stand, gast_stand = 0, 0
    k = 0
    while k < len(t):
        # Stand-Tripel suchen
        if k + 2 < len(t) and re.match(r"^\d+$", t[k]) and t[k + 1] == ":" and re.match(r"^\d+$", t[k + 2]):
            h, g = int(t[k]), int(t[k + 2])
            stand = f"{h}:{g}"
            if h > heim_stand:
                # Heimtor: davor Schütze, Art, Minute
                schuetze, art, minute = t[k - 3], t[k - 2], t[k - 1]
                verein = spiel.heim
            else:
                # Gasttor: danach Minute, Schütze, Art
                minute, schuetze, art = t[k + 3], t[k + 4], t[k + 5]
                verein = spiel.gast
            heim_stand, gast_stand = h, g
            if not MINUTE.match(minute):
                spiel.warnungen.append(f"Torzeile ohne Minute beim Stand {stand}: {minute!r}")
            eigentor = bool(EIGENTOR.search(schuetze))
            schuetze = EIGENTOR.sub("", schuetze).strip()
            elfmeter = bool(ELFMETER.search(schuetze))
            schuetze = ELFMETER.sub("", schuetze).strip()          # "Kane (Elfmeter)" → Kane, zählt normal
            vorlage = None
            if "," in art:
                art, vorlage = [x.strip() for x in art.split(",", 1)]
            if elfmeter:
                art = f"{art} (Elfmeter)" if art else "Elfmeter"
            spiel.tore.append(Tor(minute, verein, schuetze, eigentor, art, vorlage, stand))
            k += 3 if verein == spiel.heim else 6
            continue
        k += 1

    # Tore und Vorlagen den Spielern zuschreiben
    for tor in spiel.tore:
        if not tor.eigentor:
            sp = _finde_spieler(spiel, tor.verein, tor.schuetze)
            if sp:
                sp.tore += 1
            else:
                spiel.warnungen.append(f"Torschütze {tor.schuetze!r} ({tor.verein}) nicht in der Aufstellung gefunden")
        if tor.vorlage:
            sp = _finde_spieler(spiel, tor.verein, tor.vorlage)
            if sp:
                sp.vorlagen += 1
            else:
                spiel.warnungen.append(f"Vorlagengeber {tor.vorlage!r} ({tor.verein}) nicht in der Aufstellung gefunden")


def _finde_spieler(spiel: Spiel, verein: str, name: str) -> Optional[KickerSpieler]:
    n = name.strip()
    for sp in spiel.spieler:
        if sp.verein == verein and sp.name == n:
            return sp
    # tolerant: Initial weglassen / Nachname
    n2 = ohne_initial(n)
    for sp in spiel.spieler:
        if sp.verein == verein and ohne_initial(sp.name) == n2:
            return sp
    return None


def _plausibilitaet(spiel: Spiel) -> None:
    for v in (spiel.heim, spiel.gast):
        n = sum(1 for s in spiel.spieler if s.verein == v and s.status == "Startelf")
        if n != 11:
            spiel.warnungen.append(f"{v}: {n} Startspieler statt 11")
    for v, soll in ((spiel.heim, spiel.tore_heim), (spiel.gast, spiel.tore_gast)):
        ist = sum(1 for t in spiel.tore if t.verein == v)
        if ist != soll:
            spiel.warnungen.append(f"{v}: {ist} Tore in der Torliste, Ergebnis sagt {soll}")


# ---------------------------------------------------------------------------
# Elf des Tages
# ---------------------------------------------------------------------------

def elf_des_tages_parsen(text: str, spiele: list[Spiel]) -> tuple[list[tuple[str, str]], list[str]]:
    """Sucht in der gespeicherten Seite die elf Spieler (Verein, Name).

    Erwartet Zeilen wie "Name" gefolgt von "Verein" oder "Name (Verein)"; jeder
    Spieler des Spieltags, dessen Name auftaucht, wird geprüft. Liefert
    (gefunden, warnungen).
    """
    alle = [(s.verein, s.name) for sp in spiele for s in sp.spieler]
    gefunden: list[tuple[str, str]] = []
    zeilen = [z.strip() for z in text.splitlines() if z.strip()]
    # kicker-Seite: je Spieler eine Zeile mit der Note ("1", "1,5"), darunter der Name
    paare = [zeilen[i + 1] for i in range(len(zeilen) - 1) if re.match(r"^\d(,\d)?$", zeilen[i]) and not re.match(r"^\d", zeilen[i + 1])]
    if 8 <= len(paare) <= 11:
        zeilen = paare
    for i, z in enumerate(zeilen):
        kandidaten = [(v, n) for v, n in alle if n == z or z.startswith(n + " (") or z == f"{n} ({v})"]
        if not kandidaten:
            continue
        if len(kandidaten) > 1:
            # Verein aus der Umgebung (nächste Zeile oder Klammer) bestimmen
            umgebung = " ".join(zeilen[i:i + 2])
            passend = [k for k in kandidaten if k[0].lower() in umgebung.lower() or any(kk.lower() in umgebung.lower() for kk, vv in VEREINE.items() if vv == k[0])]
            kandidaten = passend or kandidaten[:1]
        if kandidaten[0] not in gefunden:
            gefunden.append(kandidaten[0])
    warnungen = []
    if len(gefunden) != 11:
        warnungen.append(f"Elf des Tages: {len(gefunden)} Spieler erkannt statt 11 – bitte prüfen")
    return gefunden, warnungen


# ---------------------------------------------------------------------------
# Zusammenführen zu Spieltagsdaten
# ---------------------------------------------------------------------------

@dataclass
class KickerImport:
    spieltag: int
    spiele: list[Spiel]
    edt: list[tuple[str, str]]
    zuordnung: dict[tuple[str, str], str] = field(default_factory=dict)   # (verein, kicker-name) -> Spieler-ID der Basis
    warnungen: list[str] = field(default_factory=list)

    def alle_spieler(self) -> list[KickerSpieler]:
        return [s for sp in self.spiele for s in sp.spieler]


def zuordnen(imp: KickerImport, basis: Spielerbasis) -> None:
    """Ordnet jedem Spieler der Basis seinen kicker-Datensatz zu (über Verein + Name)."""
    je_verein: dict[str, list[KickerSpieler]] = {}
    for s in imp.alle_spieler():
        je_verein.setdefault(s.verein, []).append(s)
    for sid, sp in basis.spieler.items():
        kandidaten = je_verein.get(sp.verein, [])
        treffer = [k for k in kandidaten if k.name == sp.name]
        if not treffer:
            n2 = ohne_initial(sp.name).lower()
            treffer = [k for k in kandidaten if ohne_initial(k.name).lower() == n2]
        if not treffer:
            aliase = basis.aliase.get(sid, set())
            treffer = [k for k in kandidaten if k.name.lower() in aliase or ohne_initial(k.name).lower() in aliase]
        if len(treffer) == 1:
            imp.zuordnung[(treffer[0].verein, treffer[0].name)] = sid
        elif len(treffer) > 1:
            imp.warnungen.append(f"{sp.name} ({sp.verein}): mehrere kicker-Einträge passen: {[t.name for t in treffer]}")
    for (v, n) in imp.edt:
        pass


def spieltagsdaten_bauen(imp: KickerImport, basis: Spielerbasis) -> Spieltagsdaten:
    daten = Spieltagsdaten(imp.spieltag)
    for sp in imp.spiele:
        daten.vereine[sp.heim] = Vereinsdaten(sp.tore_gast)
        daten.vereine[sp.gast] = Vereinsdaten(sp.tore_heim)
    edt = set(imp.edt)
    kicker_je_key = {(s.verein, s.name): s for s in imp.alle_spieler()}
    for key, sid in imp.zuordnung.items():
        s = kicker_je_key[key]
        daten.spieler[sid] = Spielerdaten(s.note, s.tore, s.vorlagen, key in edt, eingesetzt=s.eingesetzt)
    # Spieler der Basis, deren Verein gespielt hat, aber die nirgends auftauchen: nicht im Kader → 0 Minuten
    for sid, sp in basis.spieler.items():
        if sid not in daten.spieler and sp.verein in daten.vereine:
            daten.spieler[sid] = Spielerdaten(None, 0, 0, False, eingesetzt=False)
    return daten


def schema_dateien_lesen(ordner: str | Path) -> list[Spiel]:
    spiele = []
    for p in sorted(Path(ordner).glob("schema_*.txt")):
        spiele.append(schema_parsen(p.read_text(encoding="utf-8"), quelle=p.name))
    return spiele
