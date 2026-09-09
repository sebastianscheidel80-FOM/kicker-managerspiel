"""Textreport im Format der Runde (wie der Report der Vorsaison), ergänzt um
Roh- und gewichtete Werte, Markierungen für Nachrücker (↑) und Strafnoten (*)
sowie ein Protokoll je Manager.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Optional

from .engine import KATEGORIEN, Herkunft, Kategorie, ManagerErgebnis, Saison, SpieltagErgebnis, note_text, punkte_text, schnitt_text

TRENNER = "*" * 65
KAT_TITEL = {
    Kategorie.EDT: "ELF DES TAGES",
    Kategorie.GEGENTORE: "GEGENTORE",
    Kategorie.NOTE: "NOTE",
    Kategorie.VORLAGEN: "VORLAGEN",
    Kategorie.TORE: "TORE",
}
KAT_REIHENFOLGE = [Kategorie.EDT, Kategorie.GEGENTORE, Kategorie.NOTE, Kategorie.VORLAGEN, Kategorie.TORE]


def _rohwert(m: ManagerErgebnis, kat: Kategorie) -> str:
    w = m.werte[kat]
    return schnitt_text(w) if kat == Kategorie.NOTE else str(int(w))


def _rangliste(titel: str, eintraege: list[tuple[int, str, str]]) -> list[str]:
    """eintraege: (rang, name, text). Gleiche Ränge: nur der erste bekommt die Nummer."""
    zeilen = [titel, ""]
    letzter = None
    for rang, name, text in eintraege:
        praefix = f"{rang}." if rang != letzter else "  "
        zeilen.append(f"{praefix:<3}{name}, {text}")
        letzter = rang
    zeilen.append("")
    return zeilen


def textreport(erg: SpieltagErgebnis, saison: Optional[Saison] = None, saison_name: str = "2026-2027",
               teams: Optional[dict[str, str]] = None) -> str:
    teams = teams or {}
    z: list[str] = []
    z.append(f"KICKERSPIEL SAISON {saison_name}")
    z.append("")
    z.append(TRENNER)
    z.append("")

    if saison is not None:
        z.append(f"GESAMTSTAND NACH DEM {erg.spieltag}. SPIELTAG")
        z.append("")
        z += _rangliste("PUNKTE", [(s.platz, s.manager, f"{punkte_text(s.punkte)} Punkte") for s in saison.zeilen])
        siege = sorted(saison.zeilen, key=lambda s: (-s.spieltagssiege, s.manager))
        eintraege, rang, letzter = [], 0, None
        for i, s in enumerate(siege, 1):
            if s.spieltagssiege != letzter:
                rang, letzter = i, s.spieltagssiege
            eintraege.append((rang, s.manager, punkte_text(s.spieltagssiege)))
        z += _rangliste("SPIELTAGSSIEGE", eintraege)
        z.append(TRENNER)
        z.append("")

    z += _rangliste(f"ERGEBNIS {erg.spieltag}. SPIELTAG", [(erg.manager[m].platz, m, f"{punkte_text(erg.manager[m].summe)} Punkte") for m in erg.reihenfolge])

    for kat in KAT_REIHENFOLGE:
        eintraege = [(m.raenge[kat], m.manager, f"{punkte_text(m.rangpunkte[kat])} Punkte ({_rohwert(m, kat)})") for m in erg.rangliste(kat)]
        z += _rangliste(KAT_TITEL[kat], eintraege)

    z.append("")
    for name in erg.reihenfolge:
        z += _managerblock(erg.manager[name], teams.get(name))
    return "\n".join(z).rstrip() + "\n"


def _managerblock(m: ManagerErgebnis, team: Optional[str]) -> list[str]:
    kopf = f"MANAGER: {m.manager.upper()}" + (f" ({team})" if team else "")
    z = [kopf]
    z.append(f"Ø-Note {schnitt_text(m.werte[Kategorie.NOTE])} · Gegentore {int(m.werte[Kategorie.GEGENTORE])} · Tore {int(m.werte[Kategorie.TORE])} · "
             f"Vorlagen {int(m.werte[Kategorie.VORLAGEN])} · Elf des Tages {int(m.werte[Kategorie.EDT])}  →  {punkte_text(m.summe)} Punkte (Platz {m.platz})")
    z.append("-" * 62)
    z.append(f"{'Pos':<4}{'Spieler':<20}{'Elf':<4}{'Note':<6}{'GegT':<6}{'Vorl':<6}{'Tore':<6}Herkunft")
    z.append(f"{'---':<4}{'-' * 19:<20}{'---':<4}{'----':<6}{'----':<6}{'----':<6}{'----':<6}--------")
    for p in m.elf:
        name = p.name + (" ↑" if p.herkunft == Herkunft.NACHRUECKER else "")
        note = note_text(p.note) + ("*" if p.strafnote else "")
        gt = ""
        if p.position.value in ("TOR", "ABW"):
            gt = str(p.gegentore_verein) + (f"+{p.strafgegentore}" if p.strafgegentore else "")
        vorl = str(p.vorlagen) if p.vorlagen else ""
        tore = str(p.tore) if p.tore else ""
        herkunft = ""
        if p.herkunft == Herkunft.NACHRUECKER:
            herkunft = f"für {p.ersetzt.name if p.ersetzt else 'unbekannten Namen'} (Bank {p.bankplatz})"
        elif p.herkunft == Herkunft.STRAFNOTE:
            herkunft = "Strafnote" + (", Kurzeinsatz" if p.eingesetzt else ", nicht eingesetzt")
        elif p.herkunft == Herkunft.UNBEKANNT:
            herkunft = "Name nicht zuordenbar"
        z.append(f"{p.position.value:<4}{name:<20}{'ja' if p.edt else '':<4}{note:<6}{gt:<6}{vorl:<6}{tore:<6}{herkunft}")
    z.append(f"{'':<4}{'gewichtet':<20}{int(m.werte[Kategorie.EDT]):<4}{schnitt_text(m.werte[Kategorie.NOTE]):<6}"
             f"{int(m.werte[Kategorie.GEGENTORE]):<6}{int(m.werte[Kategorie.VORLAGEN]):<6}{int(m.werte[Kategorie.TORE]):<6}TW-GegT ×2 · MIT-Vorl ×2 · STU-Tore ×2")
    z.append(f"{'':<4}{'Rangpunkte':<20}{punkte_text(m.rangpunkte[Kategorie.EDT]):<4}{punkte_text(m.rangpunkte[Kategorie.NOTE]):<6}"
             f"{punkte_text(m.rangpunkte[Kategorie.GEGENTORE]):<6}{punkte_text(m.rangpunkte[Kategorie.VORLAGEN]):<6}{punkte_text(m.rangpunkte[Kategorie.TORE]):<6}Summe {punkte_text(m.summe)}")
    if m.protokoll or m.warnungen:
        z.append("Protokoll:")
        for zeile in m.protokoll:
            z.append(f"  {zeile}")
        for w in m.warnungen:
            z.append(f"  Warnung: {w}")
    z.append("")
    z.append("")
    return z
