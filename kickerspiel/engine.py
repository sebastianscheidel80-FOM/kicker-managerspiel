"""Regel-Engine des Kicker-Managerspiels (REGELN_1.md v1.2).

Reine Logik: kennt keine Dateien, keine Oberfläche, keine kicker-Seite.
Eingabe sind Spieler (Spielerbasis), Aufstellungen und Spieltagsdaten,
Ausgabe ist ein vollständig nachvollziehbares Ergebnis mit Protokoll.

Ablauf je Spieltag (werte_spieltag):
  1. Aufstellung prüfen (Formation 3-5-2, Zugehörigkeit, Bank).
  2. Gewertete Elf bestimmen: Stammspieler mit Note zählen selbst; ohne Note
     rückt der zuerst gelistete Ersatzspieler derselben kicker-Position mit
     Note nach (Aufstellungsreihenfolge); sonst Strafnote 5,5.
  3. Fünf Kategorien je Manager berechnen (Roh- und gewichtete Werte).
  4. Rangpunkte 6-5-4-3-2-1 je Kategorie mit Gleichstandsteilung.
  5. Spieltagssumme, Platz, Spieltagssieg (bei Gleichstand geteilt).
Saison (saisontabelle): Summe aller Spieltage, Verlauf, Spieltagssiege,
Kategorie-Profil, Spieler-Beiträge.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Iterable, Optional, Sequence

from .model import (
    ERSATZBANK_GROESSE,
    FORMATION,
    Aufstellung,
    Position,
    Spieler,
    Spielerdaten,
    Spieltagsdaten,
    ist_unbekannt,
    unbekannt_aufloesen,
)


# ---------------------------------------------------------------------------
# Regelwerk (Schalter mit den Werten aus REGELN_1.md v1.2)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Regelwerk:
    strafnote: Fraction = Fraction(11, 2)     # 5,5
    strafgegentor: int = 1                    # zusätzliches Gegentor bei 0 Minuten Einsatz (TOR/ABW)
    faktor_tor_gegentore: int = 2             # Torwart: Gegentore doppelt
    faktor_abw_gegentore: int = 1
    faktor_stu_tore: int = 2                  # Stürmer: Tore doppelt
    faktor_mit_vorlagen: int = 2              # Mittelfeld: Vorlagen doppelt
    max_rangpunkte: int = 6                   # Bester = 6, dann 5 ... 1
    unbekannt_max_gegentore: bool = True      # nicht zuordenbarer TOR/ABW-Platz: höchste Gegentore des Spieltags + Strafgegentor

    def faktor_gegentore(self, pos: Position) -> int:
        if pos == Position.TOR:
            return self.faktor_tor_gegentore
        if pos == Position.ABW:
            return self.faktor_abw_gegentore
        return 0

    def faktor_tore(self, pos: Position) -> int:
        return self.faktor_stu_tore if pos == Position.STU else 1

    def faktor_vorlagen(self, pos: Position) -> int:
        return self.faktor_mit_vorlagen if pos == Position.MIT else 1


REGELN_2026_27 = Regelwerk()
# Regelstand der Vorsaison (kein Strafgegentor) – für den Regressionstest 2025/26
REGELN_2025_26 = Regelwerk(strafgegentor=0)


class EngineFehler(Exception):
    """Fachlicher Fehler in Eingabedaten (z. B. ungültige Aufstellung)."""


# ---------------------------------------------------------------------------
# Kategorien
# ---------------------------------------------------------------------------

class Kategorie(str, Enum):
    NOTE = "Note"
    GEGENTORE = "Gegentore"
    TORE = "Tore"
    VORLAGEN = "Vorlagen"
    EDT = "Elf des Tages"


KATEGORIEN = [Kategorie.NOTE, Kategorie.GEGENTORE, Kategorie.TORE, Kategorie.VORLAGEN, Kategorie.EDT]
NIEDRIGER_IST_BESSER = {
    Kategorie.NOTE: True,
    Kategorie.GEGENTORE: True,
    Kategorie.TORE: False,
    Kategorie.VORLAGEN: False,
    Kategorie.EDT: False,
}


# ---------------------------------------------------------------------------
# Ergebnis-Datenklassen
# ---------------------------------------------------------------------------

class Herkunft(str, Enum):
    STAMM = "Stamm"                 # Stammspieler mit Note
    NACHRUECKER = "Nachrücker"      # Ersatzspieler, der für einen Stammspieler ohne Note nachgerückt ist
    STRAFNOTE = "Strafnote"         # Stammspieler ohne Note, niemand konnte nachrücken
    UNBEKANNT = "Unbekannt"         # nicht zuordenbarer Name, niemand konnte nachrücken


@dataclass
class GewerteterPlatz:
    """Ein Platz der gewerteten Elf mit allem, was in die Wertung eingeht."""

    position: Position
    spieler: Optional[Spieler]          # None bei unbekanntem Platz
    name: str                           # Anzeigename (kicker-Kurzname oder Name laut Mail)
    herkunft: Herkunft
    ersetzt: Optional[Spieler] = None   # bei Nachrücker: der ersetzte Stammspieler
    bankplatz: Optional[int] = None     # bei Nachrücker: Bankposition (1-basiert)
    note: Fraction = Fraction(0)
    strafnote: bool = False
    eingesetzt: Optional[bool] = True
    tore: int = 0
    tore_gew: int = 0
    vorlagen: int = 0
    vorlagen_gew: int = 0
    gegentore_verein: int = 0           # Gegentore des Vereins (roh)
    strafgegentore: int = 0             # zusätzliche Strafgegentore (roh)
    gegentore_gew: int = 0              # (Verein + Straf) × Faktor
    edt: bool = False
    daten_fehlen: bool = False

    @property
    def gegentore(self) -> int:
        return self.gegentore_verein + self.strafgegentore


@dataclass
class ManagerErgebnis:
    manager: str
    aufstellung: Aufstellung
    elf: list[GewerteterPlatz]
    werte: dict[Kategorie, Fraction] = field(default_factory=dict)
    notensumme: Fraction = Fraction(0)
    rangpunkte: dict[Kategorie, Fraction] = field(default_factory=dict)
    raenge: dict[Kategorie, int] = field(default_factory=dict)
    summe: Fraction = Fraction(0)
    platz: int = 0
    protokoll: list[str] = field(default_factory=list)
    warnungen: list[str] = field(default_factory=list)

    def gewichtet(self, kat: Kategorie) -> Fraction:
        return self.werte[kat]


@dataclass
class SpieltagErgebnis:
    spieltag: int
    manager: dict[str, ManagerErgebnis]
    reihenfolge: list[str]                     # Manager nach Summe absteigend (Gleichstand: Name)
    spieltagssieg: dict[str, Fraction]         # Anteil am Spieltagssieg je Manager (1, 1/2, 1/3 ... oder 0)
    regeln: Regelwerk = REGELN_2026_27

    def rangliste(self, kat: Kategorie) -> list[ManagerErgebnis]:
        """Manager nach Rang in der Kategorie (Gleichstand: Name)."""
        return sorted(self.manager.values(), key=lambda m: (m.raenge[kat], m.manager))


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _pos_von(spieler_id: str, index: dict[str, Spieler]) -> Position:
    if ist_unbekannt(spieler_id):
        return unbekannt_aufloesen(spieler_id)[0]
    return index[spieler_id].position


def _name_von(spieler_id: str, index: dict[str, Spieler]) -> str:
    if ist_unbekannt(spieler_id):
        return unbekannt_aufloesen(spieler_id)[1]
    return index[spieler_id].name


def note_text(wert: Fraction) -> str:
    """Einzelnote: 3,0 / 5,5 (eine Nachkommastelle, deutsche Schreibweise)."""
    return f"{float(wert):.1f}".replace(".", ",")


def schnitt_text(wert: Fraction) -> str:
    """Notenschnitt: 3,27 (zwei Nachkommastellen)."""
    return f"{float(wert):.2f}".replace(".", ",")


def punkte_text(wert: Fraction) -> str:
    """26,0 / 5,5 / 2,33"""
    f = float(wert)
    if abs(f * 2 - round(f * 2)) < 1e-9:
        return f"{f:.1f}".replace(".", ",")
    return f"{f:.2f}".replace(".", ",")


# ---------------------------------------------------------------------------
# 1. Aufstellung prüfen
# ---------------------------------------------------------------------------

def pruefe_aufstellung(a: Aufstellung, index: dict[str, Spieler], spieltag: Optional[int] = None) -> tuple[list[str], list[str]]:
    """Liefert (fehler, warnungen). Fehler machen die Aufstellung ungültig."""
    fehler: list[str] = []
    warnungen: list[str] = []

    for sid in a.alle_ids():
        if ist_unbekannt(sid):
            continue
        if sid not in index:
            fehler.append(f"Unbekannte Spieler-ID {sid!r}")
        elif not index[sid].gehoert_zu(a.manager, spieltag):
            fehler.append(f"{index[sid].name} gehört nicht zu {a.manager}" + (f" (Spieltag {spieltag})" if spieltag else ""))
    if fehler:
        return fehler, warnungen

    ids = a.alle_ids()
    doppelt = sorted({s for s in ids if ids.count(s) > 1})
    for s in doppelt:
        fehler.append(f"{_name_von(s, index)} ist mehrfach aufgestellt")

    if len(a.start) != 11:
        fehler.append(f"{len(a.start)} Stammspieler statt 11")
    zaehl = {p: 0 for p in FORMATION}
    for sid in a.start:
        zaehl[_pos_von(sid, index)] += 1
    if zaehl != FORMATION:
        ist = ", ".join(f"{zaehl[p]} {p.value}" for p in FORMATION)
        soll = ", ".join(f"{FORMATION[p]} {p.value}" for p in FORMATION)
        fehler.append(f"Formation {ist} statt {soll}")

    if len(a.bank) > ERSATZBANK_GROESSE:
        fehler.append(f"{len(a.bank)} Ersatzspieler, erlaubt sind {ERSATZBANK_GROESSE}")
    elif len(a.bank) < ERSATZBANK_GROESSE:
        warnungen.append(f"Nur {len(a.bank)} Ersatzspieler statt {ERSATZBANK_GROESSE}")
    if a.bank and _pos_von(a.bank[-1], index) != Position.TOR:
        warnungen.append("Der letzte Ersatzspieler ist kein Torwart")
    if a.bank and not any(_pos_von(s, index) == Position.TOR for s in a.bank):
        warnungen.append("Kein Ersatztorwart auf der Bank")
    return fehler, warnungen


# ---------------------------------------------------------------------------
# 2. Gewertete Elf bestimmen
# ---------------------------------------------------------------------------

def bestimme_elf(a: Aufstellung, daten: Spieltagsdaten, index: dict[str, Spieler], regeln: Regelwerk = REGELN_2026_27) -> tuple[list[GewerteterPlatz], list[str], list[str]]:
    """Wendet die Nachrückregel an. Liefert (elf, protokoll, warnungen)."""
    protokoll: list[str] = []
    warnungen: list[str] = []
    verbraucht: set[str] = set()
    elf: list[GewerteterPlatz] = []

    def daten_von(sid: str) -> tuple[Spielerdaten, bool]:
        d = daten.spieler.get(sid)
        if d is None:
            return Spielerdaten(None, eingesetzt=None), True
        return d, False

    for sid in a.start:
        pos = _pos_von(sid, index)
        name = _name_von(sid, index)

        if ist_unbekannt(sid):
            sp, d, fehlen = None, Spielerdaten(None, eingesetzt=False), False
            protokoll.append(f"{pos.value} „{name}“: Name nicht zuordenbar – gilt als Stammspieler ohne Einsatz.")
        else:
            sp = index[sid]
            d, fehlen = daten_von(sid)
            if fehlen:
                warnungen.append(f"Keine kicker-Daten für {sp.name} ({sp.verein}) erfasst – als „keine Note“ und „nicht eingesetzt“ behandelt.")

        if d.hat_note:
            elf.append(GewerteterPlatz(pos, sp, name, Herkunft.STAMM, note=d.note, eingesetzt=True,
                                       tore=d.tore, vorlagen=d.vorlagen, edt=d.edt, daten_fehlen=fehlen))
            continue

        # Nachrücker suchen: zuerst gelisteter Ersatz derselben Position mit Note, noch nicht verbraucht
        nachruecker: Optional[tuple[int, Spieler, Spielerdaten]] = None
        uebersprungen: list[str] = []
        for j, bid in enumerate(a.bank):
            if ist_unbekannt(bid) or bid in verbraucht:
                continue
            bsp = index[bid]
            if bsp.position != pos:
                continue
            bd, bfehlen = daten_von(bid)
            if bfehlen:
                warnungen.append(f"Keine kicker-Daten für Ersatzspieler {bsp.name} ({bsp.verein}) erfasst – als „keine Note“ behandelt.")
            if bd.hat_note:
                nachruecker = (j + 1, bsp, bd)
                break
            uebersprungen.append(f"  Ersatz {j + 1} {bsp.name} ({pos.value}) hat keine Note – übersprungen.")

        if nachruecker is not None:
            j, bsp, bd = nachruecker
            verbraucht.add(bsp.id)
            elf.append(GewerteterPlatz(pos, bsp, bsp.name, Herkunft.NACHRUECKER, ersetzt=sp, bankplatz=j,
                                       note=bd.note, eingesetzt=True, tore=bd.tore, vorlagen=bd.vorlagen, edt=bd.edt))
            protokoll.append(f"{pos.value} {name}: keine Note → {bsp.name} rückt nach (Bank {j}).")
            protokoll.extend(uebersprungen)
            continue

        # Strafnote
        herkunft = Herkunft.UNBEKANNT if sp is None else Herkunft.STRAFNOTE
        eingesetzt = d.eingesetzt
        if sp is not None and eingesetzt is None:
            warnungen.append(f"Für {sp.name} ist nicht erfasst, ob er eingesetzt wurde – als 0 Minuten (Strafgegentor) behandelt.")
            eingesetzt = False
        platz = GewerteterPlatz(pos, sp, name, herkunft, note=regeln.strafnote, strafnote=True, eingesetzt=eingesetzt,
                                tore=d.tore, vorlagen=d.vorlagen, edt=False, daten_fehlen=fehlen)
        elf.append(platz)
        if d.edt:
            warnungen.append(f"{name} steht ohne Note in der Elf des Tages – wird ignoriert.")
        grund = "kein Ersatz-" + pos.value + " mit Note"
        if sp is None:
            protokoll.append(f"{pos.value} „{name}“: {grund} → Strafnote {note_text(regeln.strafnote)}.")
        elif eingesetzt:
            zusatz = ""
            if d.tore or d.vorlagen:
                zusatz = f"; Kurzeinsatz: {d.tore} Tor(e), {d.vorlagen} Vorlage(n) zählen"
            protokoll.append(f"{pos.value} {name}: keine Note, {grund} → Strafnote {note_text(regeln.strafnote)}{zusatz}.")
        else:
            protokoll.append(f"{pos.value} {name}: nicht eingesetzt, {grund} → Strafnote {note_text(regeln.strafnote)}" + (", Strafgegentor" if regeln.strafgegentor and regeln.faktor_gegentore(pos) else "") + ".")
        protokoll.extend(uebersprungen)

    return elf, protokoll, warnungen


# ---------------------------------------------------------------------------
# 3. Kategorien je Manager
# ---------------------------------------------------------------------------

def berechne_werte(elf: list[GewerteterPlatz], daten: Spieltagsdaten, regeln: Regelwerk, protokoll: list[str]) -> tuple[dict[Kategorie, Fraction], Fraction]:
    notensumme = Fraction(0)
    gt = tore = vorl = edt = 0
    max_gt = daten.max_gegentore()
    for p in elf:
        notensumme += p.note
        p.tore_gew = p.tore * regeln.faktor_tore(p.position)
        p.vorlagen_gew = p.vorlagen * regeln.faktor_vorlagen(p.position)
        f = regeln.faktor_gegentore(p.position)
        if f:
            if p.spieler is None:
                p.gegentore_verein = max_gt if regeln.unbekannt_max_gegentore else 0
                p.strafgegentore = regeln.strafgegentor
                protokoll.append(f"  {p.position.value} „{p.name}“: höchste Gegentore des Spieltags {max_gt} + {regeln.strafgegentor} Strafgegentor = {p.gegentore}" + (f", ×{f} = {p.gegentore * f}" if f > 1 else "") + ".")
            else:
                v = daten.vereine.get(p.spieler.verein)
                if v is None:
                    raise EngineFehler(f"Gegentore für Verein {p.spieler.verein!r} ({p.spieler.name}) fehlen in den Spieltagsdaten")
                p.gegentore_verein = v.gegentore
                p.strafgegentore = regeln.strafgegentor if (p.strafnote and p.eingesetzt is False) else 0
                if p.strafgegentore:
                    protokoll.append(f"  {p.position.value} {p.name}: Gegentore {p.spieler.verein} {v.gegentore} + {p.strafgegentore} Strafgegentor = {p.gegentore}" + (f", ×{f} = {p.gegentore * f}" if f > 1 else "") + ".")
            p.gegentore_gew = p.gegentore * f
        else:
            p.gegentore_verein = p.strafgegentore = p.gegentore_gew = 0
        gt += p.gegentore_gew
        tore += p.tore_gew
        vorl += p.vorlagen_gew
        edt += 1 if p.edt else 0
    werte = {
        Kategorie.NOTE: notensumme / len(elf) if elf else Fraction(0),
        Kategorie.GEGENTORE: Fraction(gt),
        Kategorie.TORE: Fraction(tore),
        Kategorie.VORLAGEN: Fraction(vorl),
        Kategorie.EDT: Fraction(edt),
    }
    return werte, notensumme


# ---------------------------------------------------------------------------
# 4. Rangpunkte mit Gleichstandsteilung
# ---------------------------------------------------------------------------

def rangpunkte(werte: dict[str, Fraction], niedriger_besser: bool, max_punkte: int = 6) -> tuple[dict[str, Fraction], dict[str, int]]:
    """6-5-4-3-2-1; Gruppen gleicher Werte teilen die Punkte ihrer Ränge.

    Liefert (punkte, rang) je Manager; rang ist der erste belegte Rang der Gruppe
    (zwei Erste: beide Rang 1, der nächste Rang 3).
    """
    sortiert = sorted(werte.items(), key=lambda kv: (kv[1] if niedriger_besser else -kv[1], kv[0]))
    punkte: dict[str, Fraction] = {}
    rang: dict[str, int] = {}
    i = 0
    while i < len(sortiert):
        gruppe = [sortiert[i][0]]
        while i + len(gruppe) < len(sortiert) and sortiert[i + len(gruppe)][1] == sortiert[i][1]:
            gruppe.append(sortiert[i + len(gruppe)][0])
        raenge = range(i + 1, i + len(gruppe) + 1)
        p = Fraction(sum(max_punkte - r + 1 for r in raenge), len(gruppe))
        for m in gruppe:
            punkte[m] = p
            rang[m] = i + 1
        i += len(gruppe)
    return punkte, rang


# ---------------------------------------------------------------------------
# 5. Spieltag
# ---------------------------------------------------------------------------

def werte_spieltag(aufstellungen: Sequence[Aufstellung], daten: Spieltagsdaten, index: dict[str, Spieler], regeln: Regelwerk = REGELN_2026_27) -> SpieltagErgebnis:
    ergebnisse: dict[str, ManagerErgebnis] = {}
    for a in aufstellungen:
        fehler, warnungen = pruefe_aufstellung(a, index, daten.spieltag)
        if fehler:
            raise EngineFehler(f"Aufstellung von {a.manager} ungültig: " + "; ".join(fehler))
        elf, protokoll, w2 = bestimme_elf(a, daten, index, regeln)
        werte, notensumme = berechne_werte(elf, daten, regeln, protokoll)
        me = ManagerErgebnis(a.manager, a, elf, werte, notensumme, protokoll=protokoll, warnungen=warnungen + w2)
        if a.quelle == "uebernommen":
            me.protokoll.insert(0, f"Aufstellung übernommen: {a.hinweis or 'keine gültige Abgabe, letzte gültige Aufstellung gilt'}.")
        ergebnisse[a.manager] = me

    for kat in KATEGORIEN:
        p, r = rangpunkte({m: e.werte[kat] for m, e in ergebnisse.items()}, NIEDRIGER_IST_BESSER[kat], regeln.max_rangpunkte)
        for m, e in ergebnisse.items():
            e.rangpunkte[kat] = p[m]
            e.raenge[kat] = r[m]
    for e in ergebnisse.values():
        e.summe = sum(e.rangpunkte.values(), Fraction(0))

    _, plaetze = rangpunkte({m: e.summe for m, e in ergebnisse.items()}, niedriger_besser=False, max_punkte=regeln.max_rangpunkte)
    for m, e in ergebnisse.items():
        e.platz = plaetze[m]
    reihenfolge = sorted(ergebnisse, key=lambda m: (ergebnisse[m].platz, m))
    sieger = [m for m in ergebnisse if ergebnisse[m].platz == 1]
    spieltagssieg = {m: (Fraction(1, len(sieger)) if m in sieger else Fraction(0)) for m in ergebnisse}
    return SpieltagErgebnis(daten.spieltag, ergebnisse, reihenfolge, spieltagssieg, regeln)


# ---------------------------------------------------------------------------
# 6. Saison
# ---------------------------------------------------------------------------

@dataclass
class SaisonZeile:
    manager: str
    punkte: Fraction = Fraction(0)
    spieltagssiege: Fraction = Fraction(0)
    verlauf: dict[int, Fraction] = field(default_factory=dict)      # Spieltag -> Punkte
    kumuliert: dict[int, Fraction] = field(default_factory=dict)    # Spieltag -> Summe bis dahin
    kategorie_profil: dict[Kategorie, Fraction] = field(default_factory=dict)
    platz: int = 0


@dataclass
class SpielerBeitrag:
    spieler: Spieler
    einsaetze: int = 0              # gewertete Einsätze
    nachgerueckt: int = 0
    strafnoten: int = 0
    notensumme: Fraction = Fraction(0)
    tore: int = 0
    tore_gew: int = 0
    vorlagen: int = 0
    vorlagen_gew: int = 0
    gegentore_gew: int = 0
    edt: int = 0

    @property
    def notenschnitt(self) -> Optional[Fraction]:
        return self.notensumme / self.einsaetze if self.einsaetze else None


@dataclass
class Saison:
    zeilen: list[SaisonZeile]
    spieltage: list[int]
    beitraege: dict[str, SpielerBeitrag]

    def zeile(self, manager: str) -> SaisonZeile:
        return next(z for z in self.zeilen if z.manager == manager)


def saisontabelle(ergebnisse: Iterable[SpieltagErgebnis], manager: Optional[Sequence[str]] = None) -> Saison:
    ergebnisse = sorted(ergebnisse, key=lambda e: e.spieltag)
    if manager is None:
        manager = sorted({m for e in ergebnisse for m in e.manager})
    zeilen = {m: SaisonZeile(m, kategorie_profil={k: Fraction(0) for k in KATEGORIEN}) for m in manager}
    beitraege: dict[str, SpielerBeitrag] = {}
    for e in ergebnisse:
        for m in manager:
            z = zeilen[m]
            me = e.manager.get(m)
            pts = me.summe if me else Fraction(0)
            z.verlauf[e.spieltag] = pts
            z.punkte += pts
            z.kumuliert[e.spieltag] = z.punkte
            z.spieltagssiege += e.spieltagssieg.get(m, Fraction(0))
            if me:
                for k in KATEGORIEN:
                    z.kategorie_profil[k] += me.rangpunkte[k]
                for p in me.elf:
                    if p.spieler is None:
                        continue
                    b = beitraege.setdefault(p.spieler.id, SpielerBeitrag(p.spieler))
                    b.einsaetze += 1
                    b.nachgerueckt += 1 if p.herkunft == Herkunft.NACHRUECKER else 0
                    b.strafnoten += 1 if p.strafnote else 0
                    b.notensumme += p.note
                    b.tore += p.tore
                    b.tore_gew += p.tore_gew
                    b.vorlagen += p.vorlagen
                    b.vorlagen_gew += p.vorlagen_gew
                    b.gegentore_gew += p.gegentore_gew
                    b.edt += 1 if p.edt else 0
    _, plaetze = rangpunkte({m: z.punkte for m, z in zeilen.items()}, niedriger_besser=False)
    for m, z in zeilen.items():
        z.platz = plaetze[m]
    sortiert = sorted(zeilen.values(), key=lambda z: (z.platz, z.manager))
    return Saison(sortiert, [e.spieltag for e in ergebnisse], beitraege)
