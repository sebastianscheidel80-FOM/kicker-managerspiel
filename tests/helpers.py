"""Bausteine für die Tests: Standardkader, Standardaufstellung, Standarddaten.

Jeder Manager bekommt einen Kader aus 11 Stammspielern (1 TOR, 3 ABW, 5 MIT,
2 STU) und 4 Ersatzspielern. Die IDs sind sprechend: "A_abw1" ist der erste
Abwehrspieler von Manager A, "A_e1" der erste Ersatzspieler, "A_tw2" der
Ersatztorwart. Alle Spieler eines Managers spielen beim Verein "V_<Manager>",
der standardmäßig 1 Gegentor kassiert; alle bekommen die Note 3,0.
Tests überschreiben gezielt einzelne Werte.
"""
from __future__ import annotations

from fractions import Fraction

from kickerspiel.model import Aufstellung, Position, Spieler, Spielerdaten, Spieltagsdaten, Vereinsdaten

STAMM = [("tor1", Position.TOR), ("abw1", Position.ABW), ("abw2", Position.ABW), ("abw3", Position.ABW),
         ("mit1", Position.MIT), ("mit2", Position.MIT), ("mit3", Position.MIT), ("mit4", Position.MIT), ("mit5", Position.MIT),
         ("stu1", Position.STU), ("stu2", Position.STU)]


def kader(manager: str, bank: list[Position] = (Position.ABW, Position.MIT, Position.STU), verein: str | None = None) -> dict[str, Spieler]:
    """Kader eines Managers; bank = Positionen der drei freien Ersatzplätze, der 4. ist immer TOR."""
    verein = verein or f"V_{manager}"
    spieler = {}
    for kurz, pos in STAMM:
        sid = f"{manager}_{kurz}"
        spieler[sid] = Spieler(sid, f"{manager} {kurz}", verein, pos, manager)
    for i, pos in enumerate(bank, 1):
        sid = f"{manager}_e{i}"
        spieler[sid] = Spieler(sid, f"{manager} e{i}", verein, pos, manager)
    spieler[f"{manager}_tw2"] = Spieler(f"{manager}_tw2", f"{manager} tw2", verein, Position.TOR, manager)
    return spieler


def aufstellung(manager: str, n_bank: int = 3) -> Aufstellung:
    start = [f"{manager}_{kurz}" for kurz, _ in STAMM]
    bank = [f"{manager}_e{i}" for i in range(1, n_bank + 1)] + [f"{manager}_tw2"]
    return Aufstellung(manager, start, bank)


def daten(index: dict[str, Spieler], spieltag: int = 2, note: float | None = 3.0, gegentore: dict[str, int] | None = None) -> Spieltagsdaten:
    """Standarddaten: jeder Spieler Note 3,0, keine Scorer, jeder Verein 1 Gegentor."""
    d = Spieltagsdaten(spieltag)
    for sid in index:
        d.spieler[sid] = Spielerdaten(note)
    for v in {s.verein for s in index.values()}:
        d.vereine[v] = Vereinsdaten((gegentore or {}).get(v, 1))
    return d


def setze(d: Spieltagsdaten, sid: str, note=None, tore=0, vorlagen=0, edt=False, eingesetzt=None) -> None:
    d.spieler[sid] = Spielerdaten(note, tore, vorlagen, edt, eingesetzt)


def F(x) -> Fraction:
    return Fraction(str(x))
