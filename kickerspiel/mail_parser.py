"""Aufstellungs-Mails (.eml) in Aufstellungen umsetzen.

Bekannte Formate der Runde (2. Spieltag 2026/27):
  * vier Zeilen TOR/ABW/MIT/STU, Namen durch Leerzeichen, Ersatz in Klammern
  * ein Name je Zeile, Leerzeile zwischen den Blöcken, Ersatz in Klammern,
    Kürzel wie "T", "V", "TTV" hinter den Namen (werden ignoriert)
  * kommagetrennt je Zeile, Ersatz in Klammern, Kommentarzeile, zitierte Vormail
  * ein Name je Zeile, Ersatz mit führendem "|" (auch "||"), Semikolon in Klammern

Vorgehen:
  1. Mailtext holen (Klartext, sonst HTML → Text), zitierte Vormails und
     Signaturen abschneiden.
  2. Zeile für Zeile: Klammern und "|" markieren Ersatzspieler; Namen werden
     gegen den Kader des Absenders abgeglichen – erst exakt, dann tolerant.
  3. Zeilen ohne jede Zuordnung außerhalb des Aufstellungsblocks sind Kommentare.
     Unzuordenbare Namen innerhalb des Blocks werden als "?POS:Name" geführt;
     die Position ergibt sich aus der Lücke in der Formation.
"""
from __future__ import annotations

import csv
import email
import html
import re
from dataclasses import dataclass, field
from email import policy
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from typing import Optional

from .engine import pruefe_aufstellung
from .model import FORMATION, Aufstellung, Position, Spieler, unbekannt_id
from .spielerbasis import Spielerbasis, normalisieren

ZITAT_MARKER = [
    re.compile(r"^Am .{4,80} schrieb\b", re.I),
    re.compile(r"^(Gesendet|Von|An|Betreff|From|Sent|To|Subject|Datum|Date)\s*:", re.I),
    re.compile(r"^-{3,}\s*Urspr", re.I),
    re.compile(r"^--\s*$"),
    re.compile(r"^[-_=]{8,}\s*$"),
    re.compile(r"^>"),
]
KUERZEL = re.compile(r"^[TVtv]+$|^\d+$|^[A-Za-z]$")
BANK_KEYWORDS = re.compile(r"^\s*(bank|ersatz|ersatzbank|reserve)\s*[:\-]?\s*", re.I)
TRENNER = re.compile(r"[,;/]+")


@dataclass
class Zuordnung:
    name_mail: str
    spieler: Optional[Spieler]
    art: str                      # exakt | tolerant | unbekannt
    rolle: str                    # Stamm | Bank
    hinweis: str = ""


@dataclass
class MailAufstellung:
    datei: str
    absender: str
    absender_name: str
    datum: Optional[str]
    betreff: str
    manager: Optional[str]
    aufstellung: Optional[Aufstellung]
    zuordnungen: list[Zuordnung] = field(default_factory=list)
    ignoriert: list[str] = field(default_factory=list)
    warnungen: list[str] = field(default_factory=list)
    fehler: list[str] = field(default_factory=list)
    text: str = ""


# ---------------------------------------------------------------------------
# 1. Mail lesen und Text bereinigen
# ---------------------------------------------------------------------------

def eml_lesen(pfad: str | Path) -> tuple[str, str, Optional[str], str, str]:
    """Liefert (absender_adresse, absender_name, datum_iso, betreff, text)."""
    msg = email.message_from_bytes(Path(pfad).read_bytes(), policy=policy.default)
    name, adresse = parseaddr(msg.get("From", ""))
    datum = None
    try:
        d = parsedate_to_datetime(msg.get("Date", ""))
        datum = d.isoformat()
    except Exception:
        pass
    body = msg.get_body(preferencelist=("plain",))
    if body is not None:
        text = body.get_content()
    else:
        body = msg.get_body(preferencelist=("html",))
        text = html_zu_text(body.get_content()) if body is not None else ""
    return adresse.lower(), name, datum, str(msg.get("Subject", "")).strip(), text


def html_zu_text(h: str) -> str:
    h = re.sub(r"(?is)<(script|style).*?</\1>", "", h)
    h = re.sub(r"(?i)<br\s*/?>", "\n", h)
    h = re.sub(r"(?i)</(p|div|tr|li|h\d)>", "\n", h)
    h = re.sub(r"(?i)<(p|div|tr|li)[^>]*>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    return html.unescape(h).replace("\xa0", " ")


def zitat_abschneiden(text: str) -> str:
    zeilen = text.splitlines()
    for i, z in enumerate(zeilen):
        s = z.strip()
        if any(m.search(s) for m in ZITAT_MARKER):
            return "\n".join(zeilen[:i])
    return text


# ---------------------------------------------------------------------------
# 2. Absender → Manager
# ---------------------------------------------------------------------------

def lade_adressen(pfad: str | Path) -> dict[str, str]:
    """CSV mit Spalten Manager;Team;E-Mail → {adresse: manager}."""
    pfad = Path(pfad)
    if not pfad.exists():
        return {}
    with open(pfad, encoding="utf-8", newline="") as f:
        return {str(z.get("E-Mail", "")).strip().lower(): str(z.get("Manager", "")).strip()
                for z in csv.DictReader(f, delimiter=";") if z.get("E-Mail")}


def manager_bestimmen(adresse: str, absender_name: str, betreff: str, adressen: dict[str, str], basis: Spielerbasis) -> Optional[str]:
    if adresse in adressen:
        return adressen[adresse]
    kandidaten = basis.manager()
    for m in kandidaten:
        if normalisieren(m) in normalisieren(absender_name) or normalisieren(m) in normalisieren(adresse):
            return m
    for m, team in basis.teams.items():
        if team and normalisieren(team) in normalisieren(betreff):
            return m
    return None


# ---------------------------------------------------------------------------
# 3. Namen erkennen
# ---------------------------------------------------------------------------

@dataclass
class _Treffer:
    name_mail: str
    spieler: Optional[Spieler]
    art: str
    bank: bool
    zeile: int
    hinweis: str = ""


def _segmente(zeile: str) -> list[tuple[str, bool]]:
    """Zerlegt eine Zeile in (segment, ist_bank)."""
    s = zeile.strip()
    if not s:
        return []
    bank_ganz = False
    if s.startswith("|"):
        bank_ganz = True
        s = s.lstrip("|").strip()
    m = BANK_KEYWORDS.match(s)
    if m:
        bank_ganz = True
        s = s[m.end():]
    ergebnis: list[tuple[str, bool]] = []
    pos = 0
    for k in re.finditer(r"\(([^)]*)\)", s):
        vorher = s[pos:k.start()].strip()
        if vorher:
            ergebnis.append((vorher, bank_ganz))
        ergebnis.append((k.group(1).strip(), True))
        pos = k.end()
    rest = s[pos:].strip()
    if rest:
        ergebnis.append((rest, bank_ganz))
    return ergebnis


def _tokens(segment: str) -> list[list[str]]:
    """Segment → Liste von Token-Gruppen (durch Komma/Semikolon/Schrägstrich getrennt)."""
    gruppen = []
    for teil in TRENNER.split(segment):
        toks = [t for t in re.split(r"\s+", teil.strip()) if t]
        toks = [t.strip(".:!?*\"'“”„") or t for t in toks]
        toks = [t for t in toks if t and t not in ("-", "–")]
        if toks:
            gruppen.append(toks)
    return gruppen


def _erkenne(text: str, kader: list[Spieler], basis: Spielerbasis) -> tuple[list[_Treffer], list[str]]:
    zeilen = text.splitlines()
    treffer: list[_Treffer] = []
    ignoriert: list[str] = []

    # Pass 1: exakte Treffer, um den Aufstellungsblock zu finden
    def scan(zeile_nr: int, zeile: str, tolerant: bool) -> tuple[list[_Treffer], list[str]]:
        gefunden, uebrig = [], []
        for segment, bank in _segmente(zeile):
            for toks in _tokens(segment):
                i = 0
                while i < len(toks):
                    if KUERZEL.match(toks[i]):
                        i += 1
                        continue
                    hit = None
                    # 1) exakte Treffer, längste Wortfolge zuerst (Kürzel dürfen nicht Teil des Namens sein)
                    for laenge in (3, 2, 1):
                        if i + laenge > len(toks) or any(KUERZEL.match(x) for x in toks[i:i + laenge]):
                            continue
                        kandidat = " ".join(toks[i:i + laenge])
                        sp, art, _ = basis.finde(kandidat, kader)
                        if sp is not None and art == "exakt":
                            hit = (_Treffer(kandidat, sp, art, bank, zeile_nr, ""), laenge)
                            break
                    # 2) tolerante Treffer (Tippfehler), nur wenn kein Einzelwort der Folge exakt passt
                    if hit is None and tolerant:
                        for laenge in (2, 1):
                            if i + laenge > len(toks) or any(KUERZEL.match(x) for x in toks[i:i + laenge]):
                                continue
                            kandidat = " ".join(toks[i:i + laenge])
                            if len(kandidat) < 4:
                                continue
                            sp, art, _ = basis.finde(kandidat, kader)
                            if sp is None:
                                continue
                            # Ein Einzelwort der Folge, das exakt auf einen ANDEREN Spieler passt, verbietet die Folge
                            if laenge > 1 and any((lambda r: r[0] is not None and r[1] == "exakt" and r[0].id != sp.id)(basis.finde(x, kader)) for x in toks[i:i + laenge]):
                                continue
                            if art in ("tolerant", "exakt"):
                                art = "tolerant"
                                hit = (_Treffer(kandidat, sp, art, bank, zeile_nr, f"Schreibweise: „{kandidat}“ → „{sp.name}“"), laenge)
                                break
                    if hit:
                        gefunden.append(hit[0])
                        i += hit[1]
                    else:
                        uebrig.append((toks[i], bank))
                        i += 1
        return gefunden, uebrig

    def ist_kommentar(zeile: str, gefunden: list[_Treffer]) -> bool:
        """Fließtext-Zeile (Kommentar, Signatur), in der zufällig ein Spielername vorkommt:
        mindestens vier inhaltliche Wörter, von denen weniger als die Hälfte exakt auf Spieler passen."""
        woerter = [t for seg, _ in _segmente(zeile) for grp in _tokens(seg) for t in grp if not KUERZEL.match(t)]
        if len(woerter) < 4:
            return False
        getroffen = sum(len(t.name_mail.split()) for t in gefunden)
        return getroffen * 2 < len(woerter)

    exakt_je_zeile = {}
    kommentare: set[int] = set()
    for nr, z in enumerate(zeilen):
        g, _ = scan(nr, z, tolerant=False)
        if ist_kommentar(z, g):
            kommentare.add(nr)
            continue
        if g:
            exakt_je_zeile[nr] = g
    if not exakt_je_zeile:
        return [], [z.strip() for z in zeilen if z.strip()]
    erste, letzte = min(exakt_je_zeile), max(exakt_je_zeile)

    # Pass 2: innerhalb des Blocks tolerant, Rest als unbekannt/ignoriert
    for nr, z in enumerate(zeilen):
        if not z.strip():
            continue
        if nr < erste or nr > letzte or nr in kommentare:
            ignoriert.append(z.strip())
            continue
        g, uebrig = scan(nr, z, tolerant=True)
        treffer.extend(g)
        for tok, bank in uebrig:
            if len(tok) >= 3 and tok[0].isupper():
                treffer.append(_Treffer(tok, None, "unbekannt", bank, nr, "kein Spieler des Kaders passt"))
            else:
                ignoriert.append(tok)
    return treffer, ignoriert


# ---------------------------------------------------------------------------
# 4. Aufstellung bauen
# ---------------------------------------------------------------------------

def _position_fuer_unbekannt(t: _Treffer, treffer: list[_Treffer], luecken: dict[Position, int]) -> tuple[Position, str]:
    offen = [p for p, n in luecken.items() if n > 0]
    if len(offen) == 1:
        return offen[0], "Position aus der Formationslücke"
    nachbarn = [x.spieler.position for x in treffer if x.zeile == t.zeile and x.spieler and not x.bank]
    if nachbarn:
        mehrheit = max(set(nachbarn), key=nachbarn.count)
        if luecken.get(mehrheit, 0) > 0:
            return mehrheit, "Position aus den Nachbarn in derselben Zeile"
    if offen:
        return offen[0], "Position unklar – erste offene Lücke angenommen, bitte prüfen"
    return Position.MIT, "Position unklar – keine Lücke in der Formation, bitte prüfen"


def aufstellung_aus_text(text: str, manager: str, basis: Spielerbasis, spieltag: int) -> tuple[Optional[Aufstellung], list[Zuordnung], list[str], list[str], list[str]]:
    """Liefert (aufstellung, zuordnungen, ignoriert, warnungen, fehler)."""
    kader = basis.kader(manager, spieltag)
    text = zitat_abschneiden(text)
    treffer, ignoriert = _erkenne(text, kader, basis)
    warnungen: list[str] = []

    # Doppelte Nennungen entfernen (z. B. Name im Kommentar wiederholt)
    gesehen: set[str] = set()
    eindeutig: list[_Treffer] = []
    for t in treffer:
        key = t.spieler.id if t.spieler else "?" + normalisieren(t.name_mail)
        if key in gesehen:
            warnungen.append(f"{t.name_mail} mehrfach genannt – zweite Nennung ignoriert")
            continue
        gesehen.add(key)
        eindeutig.append(t)
    treffer = eindeutig

    stamm = [t for t in treffer if not t.bank]
    bank = [t for t in treffer if t.bank]

    # Positionen der unbekannten Stammplätze aus der Formationslücke
    zaehl = {p: 0 for p in FORMATION}
    for t in stamm:
        if t.spieler:
            zaehl[t.spieler.position] += 1
    luecken = {p: FORMATION[p] - zaehl[p] for p in FORMATION}
    start_ids: list[str] = []
    zuordnungen: list[Zuordnung] = []
    for t in stamm:
        if t.spieler:
            start_ids.append(t.spieler.id)
            zuordnungen.append(Zuordnung(t.name_mail, t.spieler, t.art, "Stamm", t.hinweis))
        else:
            pos, grund = _position_fuer_unbekannt(t, treffer, luecken)
            luecken[pos] -= 1
            start_ids.append(unbekannt_id(pos, t.name_mail))
            zuordnungen.append(Zuordnung(t.name_mail, None, "unbekannt", "Stamm", f"{t.hinweis}; {grund} → {pos.value}"))
    bank_ids: list[str] = []
    for t in bank:
        if t.spieler:
            bank_ids.append(t.spieler.id)
            zuordnungen.append(Zuordnung(t.name_mail, t.spieler, t.art, "Bank", t.hinweis))
        else:
            zuordnungen.append(Zuordnung(t.name_mail, None, "unbekannt", "Bank", f"{t.hinweis}; Ersatzspieler entfällt"))
            warnungen.append(f"Ersatzspieler „{t.name_mail}“ nicht zuordenbar – entfällt")

    aufst = Aufstellung(manager, start_ids, bank_ids)
    fehler, w2 = pruefe_aufstellung(aufst, basis.spieler, spieltag)
    warnungen.extend(w2)
    return aufst, zuordnungen, ignoriert, warnungen, fehler


def eml_verarbeiten(pfad: str | Path, basis: Spielerbasis, spieltag: int, adressen: dict[str, str]) -> MailAufstellung:
    adresse, name, datum, betreff, text = eml_lesen(pfad)
    manager = manager_bestimmen(adresse, name, betreff, adressen, basis)
    ma = MailAufstellung(Path(pfad).name, adresse, name, datum, betreff, manager, None, text=text)
    if manager is None:
        ma.fehler.append(f"Absender {adresse} keinem Manager zugeordnet – bitte in daten/privat/manager_adressen.csv eintragen")
        return ma
    aufst, zuordnungen, ignoriert, warnungen, fehler = aufstellung_aus_text(text, manager, basis, spieltag)
    ma.aufstellung, ma.zuordnungen, ma.ignoriert, ma.warnungen, ma.fehler = aufst, zuordnungen, ignoriert, warnungen, fehler
    return ma


def ordner_verarbeiten(ordner: str | Path, basis: Spielerbasis, spieltag: int, adressen: dict[str, str]) -> list[MailAufstellung]:
    """Alle .eml eines Ordners; je Manager zählt die jüngste Mail."""
    ergebnisse = [eml_verarbeiten(p, basis, spieltag, adressen) for p in sorted(Path(ordner).glob("*.eml"))]
    juengste: dict[str, MailAufstellung] = {}
    for ma in ergebnisse:
        if ma.manager is None:
            continue
        alt = juengste.get(ma.manager)
        if alt is None or (ma.datum or "") > (alt.datum or ""):
            if alt is not None:
                ma.warnungen.append(f"Ersetzt ältere Mail {alt.datei} ({alt.datum})")
            juengste[ma.manager] = ma
    ohne = [ma for ma in ergebnisse if ma.manager is None]
    return sorted(juengste.values(), key=lambda m: m.manager) + ohne
