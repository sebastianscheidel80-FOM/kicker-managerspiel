"""Datenmodell des Auswertungstools.

Reine Datenklassen ohne Datei- oder Oberflächenabhängigkeit. Alles, was die
Regel-Engine (engine.py) als Eingabe braucht, ist hier definiert. Noten werden
intern als Bruch (Fraction) geführt, damit Schnitte und Gleichstände exakt
verglichen werden können (REGELN_1.md v1.2).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Optional, Union


class Position(str, Enum):
    """kicker-Position aus der Kaderliste – gilt die ganze Saison."""

    TOR = "TOR"
    ABW = "ABW"
    MIT = "MIT"
    STU = "STU"

    @classmethod
    def parse(cls, text: str) -> "Position":
        t = str(text).strip().upper()
        aliase = {
            "TOR": cls.TOR, "TW": cls.TOR, "TORWART": cls.TOR, "TORHÜTER": cls.TOR, "TORHUETER": cls.TOR,
            "ABW": cls.ABW, "ABWEHR": cls.ABW, "VERTEIDIGUNG": cls.ABW, "DEF": cls.ABW,
            "MIT": cls.MIT, "MF": cls.MIT, "MITTELFELD": cls.MIT, "MID": cls.MIT,
            "STU": cls.STU, "ST": cls.STU, "STURM": cls.STU, "ANGRIFF": cls.STU, "STÜRMER": cls.STU,
        }
        if t not in aliase:
            raise ValueError(f"Unbekannte Position: {text!r}")
        return aliase[t]


# Formation 3-5-2: 1 TOR, 3 ABW, 5 MIT, 2 STU (REGELN_1.md, Abschnitt 3)
FORMATION: dict[Position, int] = {
    Position.TOR: 1,
    Position.ABW: 3,
    Position.MIT: 5,
    Position.STU: 2,
}
POSITIONSREIHENFOLGE = [Position.TOR, Position.ABW, Position.MIT, Position.STU]
ERSATZBANK_GROESSE = 4

# Ein Stammplatz, dessen Name keinem Spieler zugeordnet werden konnte
# (REGELN_1.md 3, „Nicht zuordenbarer Spieler“), steht in der Aufstellung als
# Kennung "?POS:Name laut Mail", z. B. "?ABW:Schlotterbek". Die Position kommt
# aus der Lücke in der Formation.
UNBEKANNT_PREFIX = "?"


def ist_unbekannt(spieler_id: str) -> bool:
    return spieler_id.startswith(UNBEKANNT_PREFIX)


def unbekannt_id(position: Position, name: str) -> str:
    return f"{UNBEKANNT_PREFIX}{position.value}:{name}"


def unbekannt_aufloesen(spieler_id: str) -> tuple[Position, str]:
    """"?ABW:Schlotterbek" -> (Position.ABW, "Schlotterbek")"""
    rest = spieler_id[len(UNBEKANNT_PREFIX):]
    pos, _, name = rest.partition(":")
    return Position.parse(pos), name


NoteEingabe = Union[Fraction, float, int, str, None]


def note_parsen(wert: NoteEingabe) -> Optional[Fraction]:
    """Wandelt eine kicker-Note in einen exakten Bruch um.

    Erlaubt sind 1,0 bis 6,0 in halben Schritten. None, "" oder "keine Note"
    bedeuten: keine Note.
    """
    if wert is None:
        return None
    if isinstance(wert, str):
        t = wert.strip().lower().replace(",", ".")
        if t in ("", "-", "–", "keine", "keine note", "kn", "o.n.", "ohne note", "none"):
            return None
        wert = t
    try:
        bruch = Fraction(str(wert))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"Ungültige Note: {wert!r}") from exc
    if bruch.denominator not in (1, 2) or not (1 <= bruch <= 6):
        raise ValueError(f"Ungültige Note: {wert!r} (erlaubt: 1,0 bis 6,0 in halben Schritten)")
    return bruch


@dataclass(frozen=True)
class Spieler:
    """Ein versteigerter Spieler aus der Spielerbasis."""

    id: str
    name: str                            # kicker-Kurzname (Schema), z. B. "R. Koch"
    verein: str
    position: Position
    manager: str
    kaufpreis: Optional[float] = None
    ab_spieltag: int = 1                 # Winterwechsel: ab wann gehört er dem Manager
    bis_spieltag: Optional[int] = None   # Winterwechsel: bis wann (einschließlich)

    def gehoert_zu(self, manager: str, spieltag: Optional[int] = None) -> bool:
        if self.manager != manager:
            return False
        if spieltag is None:
            return True
        if spieltag < self.ab_spieltag:
            return False
        if self.bis_spieltag is not None and spieltag > self.bis_spieltag:
            return False
        return True


@dataclass
class Aufstellung:
    """Aufstellung eines Managers für einen Spieltag.

    start: 11 Spieler-IDs in der Reihenfolge der Abgabe (Reihenfolge entscheidet,
           wer bei mehr Ausfällen als Ersatzspielern den Nachrücker bekommt).
           Nicht zuordenbare Namen stehen als "?POS:Name" (siehe unbekannt_id).
    bank:  bis zu 4 Spieler-IDs in Bankreihenfolge (der zuerst gelistete Ersatz
           derselben Position rückt zuerst nach; der 4. soll ein Torwart sein).
    quelle: "abgabe" (regulär abgegeben) oder "uebernommen" (letzte gültige
            Aufstellung wurde übernommen, weil keine gültige Abgabe vorlag).
    """

    manager: str
    start: list[str]
    bank: list[str] = field(default_factory=list)
    quelle: str = "abgabe"
    hinweis: str = ""

    def alle_ids(self) -> list[str]:
        return list(self.start) + list(self.bank)


@dataclass
class Spielerdaten:
    """kicker-Daten eines Spielers an einem Spieltag.

    eingesetzt: nur relevant, wenn keine Note vorliegt. True = hat gespielt
    (Kurzeinsatz, kein Strafgegentor), False = 0 Minuten (Strafgegentor),
    None = unbekannt (wird wie 0 Minuten behandelt und im Protokoll vermerkt).
    """

    note: NoteEingabe = None
    tore: int = 0
    vorlagen: int = 0
    edt: bool = False           # in der kicker-Elf des Tages
    eingesetzt: Optional[bool] = None

    def __post_init__(self) -> None:
        self.note = note_parsen(self.note)
        self.tore = int(self.tore or 0)
        self.vorlagen = int(self.vorlagen or 0)
        self.edt = bool(self.edt)
        if self.tore < 0 or self.vorlagen < 0:
            raise ValueError("Tore und Vorlagen können nicht negativ sein")
        if self.note is not None:
            self.eingesetzt = True

    @property
    def hat_note(self) -> bool:
        return self.note is not None


@dataclass
class Vereinsdaten:
    """Spieltagsdaten eines Vereins."""

    gegentore: int = 0
    gespielt: bool = True       # False = Spiel abgesagt/verlegt

    def __post_init__(self) -> None:
        self.gegentore = int(self.gegentore or 0)
        if self.gegentore < 0:
            raise ValueError("Gegentore können nicht negativ sein")


@dataclass
class Spieltagsdaten:
    """Alle erfassten kicker-Daten eines Spieltags."""

    spieltag: int
    spieler: dict[str, Spielerdaten] = field(default_factory=dict)   # Spieler-ID -> Daten
    vereine: dict[str, Vereinsdaten] = field(default_factory=dict)   # Verein -> Daten

    def max_gegentore(self) -> int:
        """Höchste Gegentore eines Vereins an diesem Spieltag (für nicht zuordenbare Plätze)."""
        werte = [v.gegentore for v in self.vereine.values() if v.gespielt]
        return max(werte) if werte else 0
