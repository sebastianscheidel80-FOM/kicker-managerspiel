"""Auswertungstool für das private Kicker-Managerspiel 2026/27.

Paketaufbau:
  model.py   – Datenklassen (Spieler, Aufstellung, Spieltagsdaten)
  engine.py  – Regel-Engine (REGELN_1.md v1.2), reine Logik ohne Dateien
  report.py  – Textreport im Format der Runde
"""
from .engine import (  # noqa: F401
    REGELN_2025_26,
    REGELN_2026_27,
    EngineFehler,
    Herkunft,
    Kategorie,
    Regelwerk,
    Saison,
    SpieltagErgebnis,
    pruefe_aufstellung,
    rangpunkte,
    saisontabelle,
    werte_spieltag,
)
from .model import (  # noqa: F401
    Aufstellung,
    Position,
    Spieler,
    Spielerdaten,
    Spieltagsdaten,
    Vereinsdaten,
    unbekannt_id,
)

__version__ = "0.1.0"
