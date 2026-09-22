# -*- coding: utf-8 -*-
"""Kasse: Einsatz und Auszahlung nach REGELN_1.md Abschnitt 4.4 (v1.5).

Reine Rechnung auf Basis der Saisontabelle – keine Wertungslogik.

  Einsatz            1 € je Manager und gewertetem Spieltag
  Spieltagssieger    50 % des Topfs → 3 € je Spieltag, bei geteiltem Sieg anteilig
  Meisterschaftstopf 50 % des Topfs → 50 % Meister, 30 % Zweiter, 20 % Dritter
  Auszahlung         am Saisonende; Saldo = Siegprämien + Platzierungsprämie − Einsatz

Der laufende Stand rechnet mit den bisher gewerteten Spieltagen (Einsatz und
Siegprämien) und zeigt die Platzierungsprämie nach aktuellem Tabellenstand als
Vorschau – sie ist erst am Saisonende verbindlich.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from .engine import Saison

EINSATZ_JE_SPIELTAG = Fraction(1)
ANTEIL_SPIELTAGSSIEGER = Fraction(1, 2)
ANTEIL_MEISTERSCHAFT = Fraction(1, 2)
PLATZIERUNG = {1: Fraction(50, 100), 2: Fraction(30, 100), 3: Fraction(20, 100)}
SPIELTAGE_GESAMT = 33          # 2026/27: 2.–34. Spieltag
KASSENWART = "Martin"


@dataclass
class KassenZeile:
    manager: str
    platz: int
    spieltagssiege: Fraction
    siegpraemie: Fraction          # bisher verdient
    platzpraemie: Fraction         # Vorschau nach aktuellem Tabellenstand
    einsatz: Fraction              # bisher fällig
    saldo: Fraction                # siegpraemie + platzpraemie − einsatz (Vorschau)
    saldo_ende: Fraction           # dasselbe mit dem vollen Saison-Einsatz


@dataclass
class Kasse:
    zeilen: list[KassenZeile]
    spieltage_gewertet: int
    spieltage_gesamt: int
    manager_anzahl: int
    praemie_je_sieg: Fraction
    topf_gesamt: Fraction
    meisterschaftstopf: Fraction
    platzpraemien: dict[int, Fraction] = field(default_factory=dict)
    kassenwart: str = KASSENWART

    @property
    def einsatz_je_manager_gesamt(self) -> Fraction:
        return EINSATZ_JE_SPIELTAG * self.spieltage_gesamt


def praemie_je_spieltagssieg(manager_anzahl: int) -> Fraction:
    """Anteil der Spieltagssieger am Tageseinsatz: bei 6 Managern 6 € × 50 % = 3 €."""
    return EINSATZ_JE_SPIELTAG * manager_anzahl * ANTEIL_SPIELTAGSSIEGER


def kasse_berechnen(saison: Saison, spieltage_gesamt: int = SPIELTAGE_GESAMT) -> Kasse:
    manager = [z.manager for z in saison.zeilen]
    n = len(manager)
    gewertet = len(saison.spieltage)
    je_sieg = praemie_je_spieltagssieg(n)
    topf = EINSATZ_JE_SPIELTAG * n * spieltage_gesamt
    meisterschaft = topf * ANTEIL_MEISTERSCHAFT
    platzpraemien = {p: meisterschaft * a for p, a in PLATZIERUNG.items()}

    # Platzierungsprämie: geteilte Plätze teilen sich die Summe der belegten Ränge
    nach_platz: dict[int, list[str]] = {}
    for z in saison.zeilen:
        nach_platz.setdefault(z.platz, []).append(z.manager)
    praemie_von: dict[str, Fraction] = {}
    for platz, leute in nach_platz.items():
        summe = sum((platzpraemien.get(platz + i, Fraction(0)) for i in range(len(leute))), Fraction(0))
        for m in leute:
            praemie_von[m] = summe / len(leute)

    zeilen = []
    for z in saison.zeilen:
        sieg = z.spieltagssiege * je_sieg
        einsatz = EINSATZ_JE_SPIELTAG * gewertet
        pp = praemie_von.get(z.manager, Fraction(0))
        zeilen.append(KassenZeile(z.manager, z.platz, z.spieltagssiege, sieg, pp, einsatz,
                                  sieg + pp - einsatz, sieg + pp - EINSATZ_JE_SPIELTAG * spieltage_gesamt))
    return Kasse(zeilen, gewertet, spieltage_gesamt, n, je_sieg, topf, meisterschaft, platzpraemien)


def euro(wert: Fraction) -> str:
    """49,50 € / −3,00 € / 1,50 €"""
    f = float(wert)
    s = f"{abs(f):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("−" if f < 0 else "") + s + " €"
