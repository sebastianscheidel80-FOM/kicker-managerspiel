"""Kommandozeile: python -m kickerspiel <befehl> [spieltag]

  aufstellungen N   .eml in daten/spieltag_N/eml/ → aufstellungen_stN.xlsx
  kickerdaten N     Schema-Texte in daten/spieltag_N/kicker/ → kickerdaten_stN.xlsx
  auswerten N       beide Excel-Dateien → Engine → report_stN.txt, auswertung_stN.xlsx, ergebnis_stN.json, saison.xlsx
  saison            saison.xlsx aus allen vorhandenen Spieltagen neu bauen

Alle Pfade relativ zum Repository-Ordner (Option --root, Standard: aktuelles Verzeichnis).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import dateien
from .engine import EngineFehler, pruefe_aufstellung, saisontabelle, werte_spieltag
from .html_report import site_schreiben
from .kicker_parser import KickerImport, elf_des_tages_parsen, schema_dateien_lesen, zuordnen
from .mail_parser import MailAufstellung, Zuordnung, lade_adressen, ordner_verarbeiten
from .model import Aufstellung
from .report import textreport
from .spielerbasis import lade_spielerbasis

SAISON_NAME = "2026-2027"


class Pfade:
    def __init__(self, root: Path):
        self.root = root
        self.spielerbasis = root / "daten" / "spielerbasis" / "Spielerbasis_2026-27.xlsx"
        self.adressen = root / "daten" / "privat" / "manager_adressen.csv"
        self.saison = root / "daten" / "saison.xlsx"
        self.site = root / "docs" / "site"
        self.fotos = root / "daten" / "fotos"

    def spieltag(self, n: int) -> Path:
        return self.root / "daten" / f"spieltag_{n:02d}"

    def aufstellungen(self, n: int) -> Path:
        return self.spieltag(n) / f"aufstellungen_st{n:02d}.xlsx"

    def kickerdaten(self, n: int) -> Path:
        return self.spieltag(n) / f"kickerdaten_st{n:02d}.xlsx"

    def vorhandene_spieltage(self) -> list[int]:
        out = []
        for d in sorted((self.root / "daten").glob("spieltag_*")):
            try:
                n = int(d.name.split("_")[1])
            except ValueError:
                continue
            if self.aufstellungen(n).exists() and self.kickerdaten(n).exists():
                out.append(n)
        return out


def cmd_aufstellungen(p: Pfade, n: int) -> int:
    basis = lade_spielerbasis(p.spielerbasis)
    adressen = lade_adressen(p.adressen)
    ordner = p.spieltag(n) / "eml"
    mails = ordner_verarbeiten(ordner, basis, n, adressen)
    if not mails:
        print(f"Keine .eml-Dateien in {ordner}")
        return 1
    fehler = 0
    for ma in mails:
        status = "FEHLER" if ma.fehler else ("Hinweise" if ma.warnungen else "ok")
        print(f"{ma.manager or '?':10} {status:9} {ma.datei}")
        for z in ma.zuordnungen:
            if z.art != "exakt":
                print(f"           {z.rolle:5} {z.name_mail!r} → {z.spieler.name if z.spieler else '???'} ({z.art}) {z.hinweis}")
        for f in ma.fehler:
            print(f"           FEHLER: {f}")
            fehler += 1
        for w in ma.warnungen:
            print(f"           Hinweis: {w}")
    # Regel „Fehlende oder ungültige Aufstellung“: letzte gültige Aufstellung des Managers gilt weiter
    gueltig = {ma.manager for ma in mails if ma.manager and ma.aufstellung and not ma.fehler}
    for m in sorted(set(basis.manager()) - gueltig):
        grund = "keine Mail gefunden" if m not in {ma.manager for ma in mails} else "Abgabe ungültig"
        ersatz = _letzte_gueltige_aufstellung(p, basis, m, n)
        if ersatz is None:
            print(f"{m:10} FEHLT     {grund} – auch keine frühere gültige Aufstellung vorhanden")
            fehler += 1
            continue
        aufst, von = ersatz
        mails = [ma for ma in mails if ma.manager != m] + [_uebernommene_mail(aufst, von, grund, basis)]
        print(f"{m:10} ÜBERNOMMEN {grund} → letzte gültige Aufstellung vom {von}. Spieltag gilt")
    dateien.aufstellungen_schreiben(p.aufstellungen(n), mails, basis, n)
    print(f"\nGeschrieben: {p.aufstellungen(n)}")
    return 1 if fehler else 0


def _letzte_gueltige_aufstellung(p: Pfade, basis, manager: str, n: int):
    """Sucht rückwärts die letzte Aufstellung des Managers, die für Spieltag n gültig ist."""
    for k in range(n - 1, 0, -1):
        pfad = p.aufstellungen(k)
        if not pfad.exists():
            continue
        for a in dateien.aufstellungen_lesen(pfad, basis):
            if a.manager != manager:
                continue
            fehler, _ = pruefe_aufstellung(a, basis.spieler, n)
            if not fehler:
                return a, k
    return None


def _uebernommene_mail(a, von: int, grund: str, basis):
    hinweis = f"{grund}, letzte gültige Aufstellung vom {von}. Spieltag übernommen"
    zuordnungen = []
    for rolle, ids in (("Stamm", a.start), ("Bank", a.bank)):
        for sid in ids:
            sp = basis.spieler.get(sid)
            zuordnungen.append(Zuordnung(sp.name if sp else sid, sp, "übernommen", rolle, hinweis))
    aufst = Aufstellung(a.manager, list(a.start), list(a.bank), quelle="uebernommen", hinweis=hinweis)
    return MailAufstellung(datei=f"(übernommen aus Spieltag {von})", absender="", absender_name="", datum=None,
                           betreff="", manager=a.manager, aufstellung=aufst, zuordnungen=zuordnungen, warnungen=[hinweis])


def cmd_kickerdaten(p: Pfade, n: int) -> int:
    basis = lade_spielerbasis(p.spielerbasis)
    ordner = p.spieltag(n) / "kicker"
    spiele = schema_dateien_lesen(ordner)
    if not spiele:
        print(f"Keine schema_*.txt in {ordner}")
        return 1
    edt_datei = ordner / "elf_des_tages.txt"
    edt, edt_warn = ([], [f"{edt_datei.name} fehlt – Elf des Tages leer"]) if not edt_datei.exists() else elf_des_tages_parsen(edt_datei.read_text(encoding="utf-8"), spiele)
    imp = KickerImport(n, spiele, edt, warnungen=edt_warn)
    zuordnen(imp, basis)
    dateien.kickerdaten_schreiben(p.kickerdaten(n), imp, basis)
    for sp in spiele:
        print(f"{sp.heim} – {sp.gast} {sp.tore_heim}:{sp.tore_gast}  Spieler: {len(sp.spieler)}  Tore: {len(sp.tore)}" + (f"  WARNUNGEN: {len(sp.warnungen)}" if sp.warnungen else ""))
        for w in sp.warnungen:
            print(f"    {w}")
    for w in imp.warnungen:
        print(f"    {w}")
    zugeordnet = len(imp.zuordnung)
    print(f"Elf des Tages: {len(edt)} Spieler. Spieler der Basis zugeordnet: {zugeordnet} von {len(basis.spieler)}")
    print(f"Geschrieben: {p.kickerdaten(n)}")
    return 0


def cmd_auswerten(p: Pfade, n: int) -> int:
    basis = lade_spielerbasis(p.spielerbasis)
    try:
        aufst = dateien.aufstellungen_lesen(p.aufstellungen(n), basis)
        daten = dateien.kickerdaten_lesen(p.kickerdaten(n), n, basis)
        erg = werte_spieltag(aufst, daten, basis.spieler)
    except (EngineFehler, FileNotFoundError, ValueError) as exc:
        print(f"Abbruch: {exc}")
        return 1
    ergebnisse = _alle_ergebnisse(p, basis, ausser=n) + [erg]
    saison = saisontabelle(ergebnisse, basis.manager())
    txt = textreport(erg, saison, SAISON_NAME, basis.teams)
    ordner = p.spieltag(n)
    (ordner / f"report_st{n:02d}.txt").write_text(txt, encoding="utf-8")
    dateien.auswertung_schreiben(ordner / f"auswertung_st{n:02d}.xlsx", erg, basis)
    dateien.json_schreiben(ordner / f"ergebnis_st{n:02d}.json", dateien.ergebnis_json(erg))
    dateien.saison_schreiben(p.saison, saison, basis)
    print(txt)
    print(f"Geschrieben: report_st{n:02d}.txt, auswertung_st{n:02d}.xlsx, ergebnis_st{n:02d}.json, {p.saison.name}")
    return 0


def cmd_site(p: Pfade) -> int:
    """Webseite (docs/site/) aus allen ausgewerteten Spieltagen erzeugen."""
    basis = lade_spielerbasis(p.spielerbasis)
    ergebnisse = _alle_ergebnisse(p, basis)
    if not ergebnisse:
        print("Noch kein ausgewerteter Spieltag vorhanden")
        return 1
    reports = {e.spieltag: p.spieltag(e.spieltag) / f"report_st{e.spieltag:02d}.txt" for e in ergebnisse}
    dateien_ = site_schreiben(p.site, ergebnisse, basis, saisontabelle, p.fotos, reports)
    for d in dateien_:
        print(f"Geschrieben: {d}")
    return 0


def cmd_saison(p: Pfade) -> int:
    basis = lade_spielerbasis(p.spielerbasis)
    ergebnisse = _alle_ergebnisse(p, basis)
    if not ergebnisse:
        print("Noch kein ausgewerteter Spieltag vorhanden")
        return 1
    saison = saisontabelle(ergebnisse, basis.manager())
    dateien.saison_schreiben(p.saison, saison, basis)
    for z in saison.zeilen:
        print(f"{z.platz}. {z.manager:10} {float(z.punkte):6.1f} Punkte  Spieltagssiege {float(z.spieltagssiege):.2f}")
    print(f"Geschrieben: {p.saison}")
    return 0


def _alle_ergebnisse(p: Pfade, basis, ausser: int | None = None):
    out = []
    for n in p.vorhandene_spieltage():
        if n == ausser:
            continue
        aufst = dateien.aufstellungen_lesen(p.aufstellungen(n), basis)
        daten = dateien.kickerdaten_lesen(p.kickerdaten(n), n, basis)
        out.append(werte_spieltag(aufst, daten, basis.spieler))
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m kickerspiel", description="Auswertungstool Kicker-Managerspiel")
    parser.add_argument("--root", default=".", help="Repository-Ordner (Standard: aktuelles Verzeichnis)")
    sub = parser.add_subparsers(dest="befehl", required=True)
    for name in ("aufstellungen", "kickerdaten", "auswerten"):
        s = sub.add_parser(name)
        s.add_argument("spieltag", type=int)
    sub.add_parser("saison")
    sub.add_parser("site")
    args = parser.parse_args(argv)
    p = Pfade(Path(args.root).resolve())
    if args.befehl == "aufstellungen":
        return cmd_aufstellungen(p, args.spieltag)
    if args.befehl == "kickerdaten":
        return cmd_kickerdaten(p, args.spieltag)
    if args.befehl == "auswerten":
        return cmd_auswerten(p, args.spieltag)
    if args.befehl == "site":
        return cmd_site(p)
    return cmd_saison(p)


if __name__ == "__main__":
    sys.exit(main())
