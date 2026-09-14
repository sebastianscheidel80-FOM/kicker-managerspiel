# -*- coding: utf-8 -*-
"""Wappen der sechs Teams als kleine SVG-Zeichnungen, an die Teamnamen angelehnt.

Alle Wappen haben dieselbe Schildform (viewBox 0 0 100 110) und ein Motiv:
  Fischköppe    – ein Fischkopf auf Blau
  Great Licors  – Flasche und Glas auf Dunkelgrün mit Gold
  Hallodries    – schiefer Zylinder mit Zwinkerauge auf Rot
  Hansa Fürze   – Comic-Furz (Puff-Wolke mit Duftlinien) auf Blau, Hansewelle unten
  Käsefüße      – Käseecke auf einem Fuß auf Gelb
  Vickings      – Helm mit Hörnern auf Nachtblau

Unbekannte Teamnamen bekommen ein neutrales Wappen mit dem Anfangsbuchstaben.
"""
from __future__ import annotations

import html

SCHILD = "M50 4 L92 16 V58 C92 82 72 100 50 106 C28 100 8 82 8 58 V16 Z"


def _rahmen(fuellung: str, rand: str, inhalt: str, titel: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 110" role="img" aria-label="{html.escape(titel)}">'
            f'<title>{html.escape(titel)}</title>'
            f'<path d="{SCHILD}" fill="{fuellung}" stroke="{rand}" stroke-width="4" stroke-linejoin="round"/>'
            f'{inhalt}</svg>')


def _fischkoeppe() -> str:
    inhalt = (
        # Fischkopf von der Seite, Maul links offen
        '<path d="M22 58 L44 40 C60 30 78 36 84 56 C78 76 60 82 44 74 Z" fill="#e9f2fb" stroke="#0b3d66" stroke-width="3" stroke-linejoin="round"/>'
        '<path d="M22 58 L38 52 L38 64 Z" fill="#0b3d66"/>'
        '<circle cx="62" cy="52" r="5" fill="#0b3d66"/><circle cx="63.5" cy="50.5" r="1.6" fill="#fff"/>'
        '<path d="M70 62 C74 66 78 66 82 62" fill="none" stroke="#0b3d66" stroke-width="2.5" stroke-linecap="round"/>'
        '<path d="M84 56 L94 48 L92 66 Z" fill="#7fb3e0" stroke="#0b3d66" stroke-width="2.5" stroke-linejoin="round"/>'
        '<circle cx="40" cy="22" r="2.5" fill="#cfe3f5"/><circle cx="48" cy="16" r="2" fill="#cfe3f5"/>'
    )
    return _rahmen("#2d6db3", "#0b3d66", inhalt, "Fischköppe")


def _great_licors() -> str:
    inhalt = (
        # Flasche
        '<rect x="30" y="44" width="18" height="44" rx="4" fill="#0f2a1e" stroke="#d9b25c" stroke-width="2.5"/>'
        '<rect x="35" y="26" width="8" height="20" fill="#0f2a1e" stroke="#d9b25c" stroke-width="2.5"/>'
        '<rect x="33" y="22" width="12" height="6" rx="1.5" fill="#d9b25c"/>'
        '<rect x="33" y="56" width="12" height="14" fill="#d9b25c" opacity=".9"/>'
        # Glas
        '<path d="M56 60 H80 L76 88 H60 Z" fill="#f7e9c6" stroke="#d9b25c" stroke-width="2.5" stroke-linejoin="round"/>'
        '<path d="M58 72 H78" stroke="#b8860b" stroke-width="3"/>'
        '<circle cx="66" cy="66" r="2" fill="#fff"/><circle cx="72" cy="64" r="1.5" fill="#fff"/>'
        # Sterne
        '<path d="M50 18 l2.2 5 5.3.4-4 3.5 1.3 5.2L50 29.4 45.2 32.1l1.3-5.2-4-3.5 5.3-.4z" fill="#d9b25c"/>'
    )
    return _rahmen("#1e3a2f", "#d9b25c", inhalt, "Great Licors")


def _hallodries() -> str:
    inhalt = (
        # schiefer Zylinder
        '<g transform="rotate(-14 50 40)">'
        '<rect x="34" y="14" width="32" height="30" rx="2" fill="#2b2418" stroke="#f3e7b7" stroke-width="2.5"/>'
        '<rect x="24" y="42" width="52" height="7" rx="3" fill="#2b2418" stroke="#f3e7b7" stroke-width="2.5"/>'
        '<rect x="34" y="34" width="32" height="6" fill="#b8860b"/>'
        '</g>'
        # Gesicht: ein Auge offen, eins zwinkernd, Schnurrbart
        '<circle cx="40" cy="64" r="4" fill="#fff"/><circle cx="41" cy="64" r="1.8" fill="#2b2418"/>'
        '<path d="M56 64 C59 61 63 61 66 64" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"/>'
        '<path d="M36 80 C42 74 48 78 50 80 C52 78 58 74 64 80 C58 84 52 82 50 81 C48 82 42 84 36 80 Z" fill="#fff"/>'
    )
    return _rahmen("#b23a3a", "#f3e7b7", inhalt, "Hallodries")


def _hansa_fuerze() -> str:
    inhalt = (
        # Bewegungslinien von links (da kam er her)
        '<path d="M14 44 H30 M12 56 H26 M16 68 H30" stroke="#dbe9f7" stroke-width="3" stroke-linecap="round" opacity=".9"/>'
        # Comic-Furz: Puff-Wolke aus Kreisen, gelbgrün
        '<g fill="#b7d94b" stroke="#4d6b12" stroke-width="2.6" stroke-linejoin="round">'
        '<circle cx="44" cy="58" r="12"/><circle cx="58" cy="50" r="13"/><circle cx="72" cy="58" r="11"/>'
        '<circle cx="52" cy="70" r="11"/><circle cx="66" cy="70" r="10"/>'
        '</g>'
        '<path d="M34 60 C40 44 76 42 82 60 C80 74 72 80 60 80 C48 80 38 74 34 60 Z" fill="#b7d94b"/>'
        # Wabernde Duftlinien nach oben
        '<path d="M46 40 C42 34 50 30 46 24 M58 36 C54 30 62 26 58 20 M70 40 C66 34 74 30 70 24" fill="none" stroke="#dbe9f7" stroke-width="3" stroke-linecap="round"/>'
        # Hansewelle unten
        '<path d="M18 90 C26 84 34 84 42 90 C50 96 58 96 66 90 C74 84 82 84 88 90" fill="none" stroke="#dbe9f7" stroke-width="3" stroke-linecap="round"/>'
    )
    return _rahmen("#1f5fa8", "#0b3d66", inhalt, "Hansa Fürze")


def _kaesefuesse() -> str:
    inhalt = (
        # Käseecke (Dreieck von vorn, Seitenfläche rechts)
        '<path d="M22 66 L54 30 L78 66 Z" fill="#f9d976" stroke="#7a5c00" stroke-width="3" stroke-linejoin="round"/>'
        '<path d="M22 66 L78 66 L78 74 L22 74 Z" fill="#f6c545" stroke="#7a5c00" stroke-width="3" stroke-linejoin="round"/>'
        '<circle cx="44" cy="56" r="4" fill="#e9a825"/><circle cx="58" cy="50" r="3" fill="#e9a825"/><circle cx="54" cy="62" r="2.5" fill="#e9a825"/><circle cx="36" cy="63" r="2" fill="#e9a825"/>'
        # Fuß darunter
        '<path d="M30 84 C28 92 36 98 48 97 C58 96 66 94 72 92 C76 90 74 84 68 84 H36 C33 84 31 83 30 84 Z" fill="#f2d2b6" stroke="#7a5c00" stroke-width="2.5" stroke-linejoin="round"/>'
        '<circle cx="70" cy="84" r="3.2" fill="#f2d2b6" stroke="#7a5c00" stroke-width="2"/><circle cx="62" cy="83" r="2.4" fill="#f2d2b6" stroke="#7a5c00" stroke-width="2"/><circle cx="56" cy="83" r="2" fill="#f2d2b6" stroke="#7a5c00" stroke-width="2"/>'
        # Duftlinien
        '<path d="M46 24 C48 20 46 16 48 12 M56 22 C58 18 56 14 58 10" fill="none" stroke="#7a5c00" stroke-width="2.5" stroke-linecap="round" opacity=".7"/>'
    )
    return _rahmen("#fff1a8", "#7a5c00", inhalt, "Käsefüße")


def _vickings() -> str:
    inhalt = (
        # Helm
        '<path d="M28 62 C28 40 40 30 50 30 C60 30 72 40 72 62 Z" fill="#9aa5b1" stroke="#0d1b2a" stroke-width="3" stroke-linejoin="round"/>'
        '<rect x="26" y="60" width="48" height="8" rx="3" fill="#6b7580" stroke="#0d1b2a" stroke-width="2.5"/>'
        '<rect x="46" y="34" width="8" height="34" fill="#6b7580" stroke="#0d1b2a" stroke-width="2"/>'
        # Hörner
        '<path d="M30 52 C16 50 12 34 20 24 C18 40 26 44 32 46 Z" fill="#f2e8d0" stroke="#0d1b2a" stroke-width="2.5" stroke-linejoin="round"/>'
        '<path d="M70 52 C84 50 88 34 80 24 C82 40 74 44 68 46 Z" fill="#f2e8d0" stroke="#0d1b2a" stroke-width="2.5" stroke-linejoin="round"/>'
        # Bart
        '<path d="M32 70 C32 84 40 94 50 98 C60 94 68 84 68 70 C62 74 56 72 50 76 C44 72 38 74 32 70 Z" fill="#c9843b" stroke="#0d1b2a" stroke-width="2.5" stroke-linejoin="round"/>'
    )
    return _rahmen("#0d1b2a", "#9aa5b1", inhalt, "Vickings")


def _neutral(team: str) -> str:
    buchstabe = html.escape((team or "?")[:1].upper())
    inhalt = f'<text x="50" y="70" font-size="48" text-anchor="middle" font-family="Georgia,serif" fill="#fff">{buchstabe}</text>'
    return _rahmen("#6b7580", "#2b2418", inhalt, team or "Team")


WAPPEN = {
    "Fischköppe": _fischkoeppe,
    "Great Licors": _great_licors,
    "Hallodries": _hallodries,
    "Hansa Fürze": _hansa_fuerze,
    "Käsefüße": _kaesefuesse,
    "Vickings": _vickings,
}


def wappen_svg(team: str) -> str:
    fn = WAPPEN.get(team)
    return fn() if fn else _neutral(team)
