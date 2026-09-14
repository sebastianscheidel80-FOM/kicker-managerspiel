# -*- coding: utf-8 -*-
"""Webseite der Runde: eine Seite je Spieltag plus Startseite (docs/site/).

Die Seiten rechnen nichts selbst. Sie zeigen die Ergebnisse der Engine
(SpieltagErgebnis, Saison) – dieselben Zahlen wie der Textreport.

Aufbau einer Spieltagsseite:
  Kopf · Spieltagssieger (Wappen/Foto) · Spieltagstabelle · Gesamttabelle mit
  Verlaufspfeilen · fünf Kategorie-Kästchen · je Manager die gewertete Elf mit
  Protokoll · Link zum Textreport.

Wappen: einfache SVG-Zeichnungen, an die Teamnamen angelehnt (kickerspiel/wappen.py).
Fotos: docs/site/fotos/<Manager>.jpg, wenn vorhanden – sonst nur das Wappen.
"""
from __future__ import annotations

import html
from fractions import Fraction
from pathlib import Path
from typing import Optional

from .engine import (KATEGORIEN, Herkunft, Kategorie, ManagerErgebnis, Saison, SpieltagErgebnis,
                     note_text, punkte_text, schnitt_text)
from .spielerbasis import Spielerbasis
from .wappen import WAPPEN, wappen_svg

SAISON_TITEL = "Kickerspiel 2026/27"

KAT_KURZ = {
    Kategorie.NOTE: ("Note", "Ø-Note, niedriger ist besser"),
    Kategorie.GEGENTORE: ("Gegentore", "TW ×2, ABW ×1, wenige sind besser"),
    Kategorie.TORE: ("Tore", "Stürmer ×2"),
    Kategorie.VORLAGEN: ("Vorlagen", "Mittelfeld ×2"),
    Kategorie.EDT: ("Elf des Tages", "gewertete Spieler in der kicker-Elf"),
}

CSS = """
:root{--tinte:#1f2a33;--grau:#6b7580;--linie:#dfe3e8;--hell:#f6f7f9;--akzent:#1e3a2f;--gold:#b8860b;--rot:#b23a3a;--gruen:#2f7d4f;--gelb:#f3e7b7}
*{box-sizing:border-box}
body{margin:0;background:var(--hell);color:var(--tinte);font:15px/1.5 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--akzent)}
.wrap{max-width:1040px;margin:0 auto;padding:0 16px 40px}
header.kopf{background:var(--akzent);color:#fff;padding:18px 0}
header.kopf .wrap{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:6px 18px;padding-bottom:0}
header.kopf h1{margin:0;font-size:22px;font-weight:600;letter-spacing:.3px}
header.kopf nav a{color:#dfe8e2;text-decoration:none;margin-left:14px;font-size:14px}
header.kopf nav a:hover{color:#fff;text-decoration:underline}
h2{font-size:18px;margin:34px 0 10px;color:var(--akzent)}
h3{font-size:15px;margin:0}
.sieger{display:flex;gap:22px;align-items:center;background:#fff;border:1px solid var(--linie);border-left:6px solid var(--gold);border-radius:10px;padding:18px 22px;margin-top:22px;flex-wrap:wrap}
.sieger .bild{width:120px;height:120px;flex:0 0 120px}
.sieger .bild img,.sieger .bild svg{width:120px;height:120px;border-radius:12px;object-fit:cover;display:block}
.sieger .text small{color:var(--grau);display:block;text-transform:uppercase;letter-spacing:1px;font-size:11px}
.sieger .text .team{font-size:26px;font-weight:700;line-height:1.15}
.sieger .text .mgr{color:var(--grau);font-size:15px}
.sieger .text .punkte{font-size:20px;margin-top:6px}
.sieger .text .punkte b{color:var(--gold)}
.spalten{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media (max-width:720px){.spalten{grid-template-columns:1fr}}
table{border-collapse:collapse;width:100%;background:#fff;border:1px solid var(--linie);border-radius:8px;overflow:hidden}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--linie);vertical-align:top}
th{background:#eef1f4;font-weight:600;font-size:13px;color:var(--grau);text-transform:uppercase;letter-spacing:.4px}
tr:last-child td{border-bottom:0}
td.z,th.z{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.m{white-space:nowrap}
.tabelle{overflow-x:auto}
.mini{display:inline-block;vertical-align:middle;width:22px;height:22px;margin-right:8px}
.mini svg{width:22px;height:22px;display:block}
.pf{display:inline-block;width:1.4em;text-align:center;font-weight:700}
.pf.up{color:var(--gruen)}.pf.down{color:var(--rot)}.pf.same{color:var(--grau)}
.kats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.teams{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
@media (max-width:600px){.teams{grid-template-columns:repeat(2,1fr)}}
@media (max-width:900px){.kats{grid-template-columns:repeat(2,1fr)}}
@media (max-width:480px){.kats{grid-template-columns:1fr}}
.kat{background:#fff;border:1px solid var(--linie);border-radius:8px;padding:10px 12px}
.kat h3{font-size:14px;color:var(--akzent)}
.kat small{color:var(--grau);display:block;margin-bottom:6px;font-size:12px}
.kat ol{margin:0;padding-left:0;list-style:none;font-size:13px}
.kat li{display:flex;justify-content:space-between;gap:6px;padding:2px 0;border-top:1px dashed var(--linie)}
.kat li span.w{color:var(--grau)}
.kat li.erster{font-weight:700}
.manager{background:#fff;border:1px solid var(--linie);border-radius:10px;margin-top:16px;overflow:hidden}
.manager .kopfzeile{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px 14px;background:#eef1f4;flex-wrap:wrap}
.manager .kopfzeile .platz{font-weight:700;font-size:18px;color:var(--akzent)}
.manager .kopfzeile .summe{font-size:15px}
.manager .kopfzeile .summe b{font-size:18px}
.manager table{border:0;border-radius:0}
.manager .rang td{background:#fbfbe9;font-weight:600}
.manager .roh td{color:var(--grau);font-size:13px}
.protokoll{padding:8px 14px 12px;font-size:13px;color:var(--grau);border-top:1px solid var(--linie)}
.protokoll div{padding:1px 0}
.protokoll .warn{color:var(--rot)}
.tag{display:inline-block;font-size:11px;padding:0 6px;border-radius:9px;margin-left:6px;vertical-align:middle}
.tag.nach{background:#dff1e6;color:var(--gruen)}
.tag.straf{background:#f9dede;color:var(--rot)}
.tag.edt{background:var(--gelb);color:#7a5c00}
.tag.uebern{background:#e5e8ff;color:#3a4bb2}
td.pos{color:var(--grau);width:44px}
.fuss{margin-top:40px;color:var(--grau);font-size:13px;border-top:1px solid var(--linie);padding-top:10px}
.spieltage a{display:inline-block;margin:4px 8px 4px 0;padding:4px 10px;border:1px solid var(--linie);border-radius:6px;background:#fff;text-decoration:none}
"""


def _e(s) -> str:
    return html.escape(str(s))


def _team(basis: Spielerbasis, manager: str) -> str:
    return basis.teams.get(manager) or manager


def _mini(basis: Spielerbasis, manager: str) -> str:
    return f'<span class="mini">{wappen_svg(_team(basis, manager))}</span>'


def _pfeil(vorher: Optional[int], jetzt: int) -> str:
    if vorher is None:
        return '<span class="pf same">·</span>'
    if jetzt < vorher:
        return f'<span class="pf up" title="vorher Platz {vorher}">▲</span>'
    if jetzt > vorher:
        return f'<span class="pf down" title="vorher Platz {vorher}">▼</span>'
    return '<span class="pf same" title="unverändert">▬</span>'


def _kopf(titel: str, spieltage: list[int], aktuell: Optional[int]) -> str:
    links = ['<a href="index.html">Saison</a>']
    for n in spieltage:
        stil = ' style="text-decoration:underline"' if n == aktuell else ""
        links.append(f'<a href="spieltag-{n:02d}.html"{stil}>{n}. Spieltag</a>')
    return (f'<header class="kopf"><div class="wrap"><h1>{_e(SAISON_TITEL)} · {_e(titel)}</h1>'
            f'<nav>{"".join(links)}</nav></div></header>')


def _seite(titel: str, body: str, spieltage: list[int], aktuell: Optional[int]) -> str:
    return (f'<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{_e(SAISON_TITEL)} – {_e(titel)}</title><style>{CSS}</style></head><body>'
            f'{_kopf(titel, spieltage, aktuell)}<div class="wrap">{body}'
            f'<div class="fuss">Gewertet wird, was der kicker schreibt. Regeln: Das Goldene Buch bzw. REGELN_1.md · '
            f'Auswertung erzeugt vom Auswertungstool (kickerspiel).</div></div></body></html>')


# ---------------------------------------------------------------------------
# Bausteine
# ---------------------------------------------------------------------------

def _sieger_block(erg: SpieltagErgebnis, basis: Spielerbasis, fotos: dict[str, str]) -> str:
    sieger = [m for m, anteil in erg.spieltagssieg.items() if anteil > 0]
    sieger.sort(key=lambda m: (erg.manager[m].platz, m))
    bloecke = []
    for m in sieger:
        me = erg.manager[m]
        team = _team(basis, m)
        bild = f'<img src="{_e(fotos[m])}" alt="{_e(m)}">' if m in fotos else wappen_svg(team)
        geteilt = f" (geteilt, {punkte_text(erg.spieltagssieg[m])} Spieltagssieg)" if len(sieger) > 1 else ""
        bloecke.append(
            f'<div class="sieger"><div class="bild">{bild}</div><div class="text">'
            f'<small>Spieltagssieger {erg.spieltag}. Spieltag{_e(geteilt)}</small>'
            f'<div class="team">{_e(team)}</div><div class="mgr">{_e(m)}</div>'
            f'<div class="punkte"><b>{punkte_text(me.summe)} Punkte</b> · Ø-Note {schnitt_text(me.werte[Kategorie.NOTE])} · '
            f'{int(me.werte[Kategorie.GEGENTORE])} Gegentore · {int(me.werte[Kategorie.TORE])} Tore · '
            f'{int(me.werte[Kategorie.VORLAGEN])} Vorlagen · {int(me.werte[Kategorie.EDT])} Elf des Tages</div>'
            f'</div></div>')
    return "".join(bloecke)


def _spieltagstabelle(erg: SpieltagErgebnis, basis: Spielerbasis) -> str:
    z = ['<div class="tabelle"><table><tr><th>Platz</th><th>Team</th>'] + [f'<th class="z" title="{_e(KAT_KURZ[k][1])}">{_e(KAT_KURZ[k][0])}</th>' for k in KATEGORIEN] + ['<th class="z">Punkte</th></tr>']
    for m in erg.reihenfolge:
        me = erg.manager[m]
        z.append(f'<tr><td class="z">{me.platz}.</td><td class="m">{_mini(basis, m)}{_e(_team(basis, m))} <span style="color:var(--grau)">· {_e(m)}</span></td>'
                 + "".join(f'<td class="z">{punkte_text(me.rangpunkte[k])}</td>' for k in KATEGORIEN)
                 + f'<td class="z"><b>{punkte_text(me.summe)}</b></td></tr>')
    z.append('</table></div>')
    return "".join(z)


def _gesamttabelle(saison: Saison, vorher: Optional[Saison], basis: Spielerbasis, spieltag: Optional[int]) -> str:
    z = ['<div class="tabelle"><table><tr><th></th><th>Platz</th><th>Team</th>']
    if spieltag is not None:
        z.append(f'<th class="z">{spieltag}. Spieltag</th>')
    z.append('<th class="z">Punkte</th><th class="z">Spieltagssiege</th></tr>')
    for r in saison.zeilen:
        alt = vorher.zeile(r.manager).platz if vorher else None
        z.append(f'<tr><td>{_pfeil(alt, r.platz)}</td><td class="z">{r.platz}.</td>'
                 f'<td class="m">{_mini(basis, r.manager)}{_e(_team(basis, r.manager))} <span style="color:var(--grau)">· {_e(r.manager)}</span></td>')
        if spieltag is not None:
            z.append(f'<td class="z">{punkte_text(r.verlauf.get(spieltag, Fraction(0)))}</td>')
        z.append(f'<td class="z"><b>{punkte_text(r.punkte)}</b></td><td class="z">{punkte_text(r.spieltagssiege)}</td></tr>')
    z.append('</table></div>')
    return "".join(z)


def _kategorien(erg: SpieltagErgebnis, basis: Spielerbasis) -> str:
    out = ['<div class="kats">']
    for k in KATEGORIEN:
        titel, erkl = KAT_KURZ[k]
        out.append(f'<div class="kat"><h3>{_e(titel)}</h3><small>{_e(erkl)}</small><ol>')
        for me in erg.rangliste(k):
            wert = schnitt_text(me.werte[k]) if k == Kategorie.NOTE else str(int(me.werte[k]))
            out.append(f'<li class="{"erster" if me.raenge[k] == 1 else ""}"><span>{me.raenge[k]}. {_e(_team(basis, me.manager))}</span>'
                       f'<span class="w">{wert} · <b>{punkte_text(me.rangpunkte[k])}</b></span></li>')
        out.append('</ol></div>')
    out.append('</div>')
    return "".join(out)


UEBERN = '<span class="tag uebern">Aufstellung übernommen</span>'


def _manager_block(me: ManagerErgebnis, basis: Spielerbasis) -> str:
    team = _team(basis, me.manager)
    uebernommen = me.aufstellung.quelle == "uebernommen"
    z = [f'<div class="manager"><div class="kopfzeile"><div><span class="platz">{me.platz}.</span> '
         f'<span class="mini">{wappen_svg(team)}</span><b>{_e(team)}</b> <span style="color:var(--grau)">· {_e(me.manager)}</span>'
         f'{UEBERN if uebernommen else ""}</div>'
         f'<div class="summe"><b>{punkte_text(me.summe)}</b> Punkte</div></div>']
    z.append('<table><tr><th>Pos</th><th>Spieler</th><th class="z">Note</th><th class="z">GegT</th><th class="z">Vorl</th><th class="z">Tore</th><th>Herkunft</th></tr>')
    for p in me.elf:
        tags = ""
        if p.herkunft == Herkunft.NACHRUECKER:
            tags += '<span class="tag nach">↑ Nachrücker</span>'
        if p.strafnote:
            tags += '<span class="tag straf">5,5</span>'
        if p.edt:
            tags += '<span class="tag edt">Elf des Tages</span>'
        gt = ""
        if p.position.value in ("TOR", "ABW"):
            gt = str(p.gegentore_verein) + (f"+{p.strafgegentore}" if p.strafgegentore else "")
        herk = ""
        if p.herkunft == Herkunft.NACHRUECKER:
            herk = f"für {_e(p.ersetzt.name if p.ersetzt else 'unbekannten Namen')} (Bank {p.bankplatz})" + (", Kurzeinsatz" if p.strafnote else "")
        elif p.herkunft == Herkunft.STRAFNOTE:
            herk = "Kurzeinsatz ohne Note" if p.eingesetzt else "nicht eingesetzt"
        elif p.herkunft == Herkunft.UNBEKANNT:
            herk = "Name nicht zuordenbar"
        verein = p.spieler.verein if p.spieler else ""
        z.append(f'<tr><td class="pos">{p.position.value}</td><td>{_e(p.name)} <span style="color:var(--grau);font-size:12px">{_e(verein)}</span>{tags}</td>'
                 f'<td class="z">{note_text(p.note)}{"*" if p.strafnote else ""}</td><td class="z">{gt}</td>'
                 f'<td class="z">{p.vorlagen or ""}</td><td class="z">{p.tore or ""}</td><td>{herk}</td></tr>')
    z.append(f'<tr class="roh"><td></td><td>gewichtet (TW-GegT ×2 · MIT-Vorl ×2 · STU-Tore ×2)</td><td class="z">{schnitt_text(me.werte[Kategorie.NOTE])}</td>'
             f'<td class="z">{int(me.werte[Kategorie.GEGENTORE])}</td><td class="z">{int(me.werte[Kategorie.VORLAGEN])}</td><td class="z">{int(me.werte[Kategorie.TORE])}</td>'
             f'<td>Elf des Tages: {int(me.werte[Kategorie.EDT])}</td></tr>')
    z.append(f'<tr class="rang"><td></td><td>Rangpunkte</td><td class="z">{punkte_text(me.rangpunkte[Kategorie.NOTE])}</td>'
             f'<td class="z">{punkte_text(me.rangpunkte[Kategorie.GEGENTORE])}</td><td class="z">{punkte_text(me.rangpunkte[Kategorie.VORLAGEN])}</td>'
             f'<td class="z">{punkte_text(me.rangpunkte[Kategorie.TORE])}</td><td>Elf des Tages {punkte_text(me.rangpunkte[Kategorie.EDT])} → Summe <b>{punkte_text(me.summe)}</b></td></tr>')
    z.append('</table>')
    if me.protokoll or me.warnungen:
        z.append('<div class="protokoll">')
        z.extend(f'<div>{_e(t)}</div>' for t in me.protokoll)
        z.extend(f'<div class="warn">⚠ {_e(w)}</div>' for w in me.warnungen)
        z.append('</div>')
    z.append('</div>')
    return "".join(z)


# ---------------------------------------------------------------------------
# Seiten
# ---------------------------------------------------------------------------

def spieltag_seite(erg: SpieltagErgebnis, saison: Saison, vorher: Optional[Saison], basis: Spielerbasis,
                   spieltage: list[int], fotos: dict[str, str], textreport: Optional[str] = None) -> str:
    n = erg.spieltag
    body = [_sieger_block(erg, basis, fotos)]
    body.append(f'<h2>Ergebnis {n}. Spieltag</h2>' + _spieltagstabelle(erg, basis))
    body.append(f'<h2>Gesamtstand nach dem {n}. Spieltag</h2>' + _gesamttabelle(saison, vorher, basis, n))
    body.append('<h2>Die fünf Kategorien</h2>' + _kategorien(erg, basis))
    body.append('<h2>Die gewerteten Elfen</h2>')
    for m in erg.reihenfolge:
        body.append(_manager_block(erg.manager[m], basis))
    if textreport:
        body.append(f'<p style="margin-top:18px"><a href="{_e(textreport)}">Textreport (Rohfassung zum Zitieren)</a></p>')
    return _seite(f"{n}. Spieltag", "".join(body), spieltage, n)


def index_seite(saison: Saison, ergebnisse: list[SpieltagErgebnis], basis: Spielerbasis, fotos: dict[str, str], vorher: Optional[Saison] = None) -> str:
    spieltage = [e.spieltag for e in ergebnisse]
    body = ['<h2>Gesamttabelle</h2>', _gesamttabelle(saison, vorher, basis, None)]
    # Verlauf: Punkte je Spieltag
    z = ['<h2>Verlauf</h2><table><tr><th>Team</th>'] + [f'<th class="z">{n}.</th>' for n in spieltage] + ['<th class="z">Gesamt</th></tr>']
    for r in saison.zeilen:
        z.append(f'<tr><td class="m">{_mini(basis, r.manager)}{_e(_team(basis, r.manager))}</td>'
                 + "".join(f'<td class="z">{punkte_text(r.verlauf.get(n, Fraction(0)))}</td>' for n in spieltage)
                 + f'<td class="z"><b>{punkte_text(r.punkte)}</b></td></tr>')
    z.append('</table>')
    body.extend(z)
    body.append('<h2>Spieltage</h2><div class="spieltage">')
    for e in reversed(ergebnisse):
        sieger = ", ".join(_team(basis, m) for m, a in e.spieltagssieg.items() if a > 0)
        body.append(f'<a href="spieltag-{e.spieltag:02d}.html">{e.spieltag}. Spieltag – Sieger: {_e(sieger)}</a>')
    body.append('</div>')
    body.append('<h2>Die Teams</h2><div class="teams">')
    for m in sorted(basis.teams):
        team = basis.teams[m]
        body.append(f'<div class="kat" style="text-align:center"><div style="width:90px;height:90px;margin:0 auto 6px">{wappen_svg(team)}</div><h3>{_e(team)}</h3><small>{_e(m)}</small></div>')
    body.append('</div>')
    return _seite("Saison", "".join(body), spieltage, None)


def site_schreiben(ziel: Path, ergebnisse: list[SpieltagErgebnis], basis: Spielerbasis, saisontabelle_fn, fotos_ordner: Optional[Path] = None,
                   textreports: Optional[dict[int, Path]] = None) -> list[Path]:
    """Schreibt index.html und spieltag-NN.html nach `ziel`. Liefert die geschriebenen Pfade."""
    ziel.mkdir(parents=True, exist_ok=True)
    ergebnisse = sorted(ergebnisse, key=lambda e: e.spieltag)
    spieltage = [e.spieltag for e in ergebnisse]
    fotos: dict[str, str] = {}
    if fotos_ordner and fotos_ordner.exists():
        (ziel / "fotos").mkdir(exist_ok=True)
        for m in basis.manager():
            for endung in ("jpg", "jpeg", "png"):
                q = fotos_ordner / f"{m}.{endung}"
                if q.exists():
                    (ziel / "fotos" / q.name).write_bytes(q.read_bytes())
                    fotos[m] = f"fotos/{q.name}"
                    break
    geschrieben = []
    manager = basis.manager()
    for i, e in enumerate(ergebnisse):
        saison = saisontabelle_fn(ergebnisse[:i + 1], manager)
        vorher = saisontabelle_fn(ergebnisse[:i], manager) if i > 0 else None
        text = None
        if textreports and e.spieltag in textreports and textreports[e.spieltag].exists():
            name = f"report_st{e.spieltag:02d}.txt"
            (ziel / name).write_text(textreports[e.spieltag].read_text(encoding="utf-8"), encoding="utf-8")
            text = name
        pfad = ziel / f"spieltag-{e.spieltag:02d}.html"
        pfad.write_text(spieltag_seite(e, saison, vorher, basis, spieltage, fotos, text), encoding="utf-8")
        geschrieben.append(pfad)
    saison = saisontabelle_fn(ergebnisse, manager)
    vorher = saisontabelle_fn(ergebnisse[:-1], manager) if len(ergebnisse) > 1 else None
    pfad = ziel / "index.html"
    pfad.write_text(index_seite(saison, ergebnisse, basis, fotos, vorher), encoding="utf-8")
    geschrieben.append(pfad)
    return geschrieben
