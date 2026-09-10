"""Tests für Mail-Parser und kicker-Parser anhand der Formate des 2. Spieltags 2026/27."""
from pathlib import Path

from kickerspiel.kicker_parser import elf_des_tages_parsen, schema_parsen, spieltagsdaten_bauen, zuordnen, KickerImport
from kickerspiel.mail_parser import aufstellung_aus_text, zitat_abschneiden
from kickerspiel.model import Position, Spieler, ist_unbekannt
from kickerspiel.spielerbasis import Spielerbasis, _aliase_fuer, ohne_initial

FIX = Path(__file__).parent / "fixtures"


def basis_bauen() -> Spielerbasis:
    """Kleiner Kader für Manager 'Thomas' in drei Schreibweisen (Kurzname, Kaderliste, Auktion)."""
    b = Spielerbasis()
    rows = [
        ("Frankfurt", "Atubolu", "Atubolu Noah", "Atubolu", "TOR"),
        ("Frankfurt", "Kaua Santos", "Kaua Santos", "Kaua Santos", "TOR"),
        ("Dortmund", "Anton", "Anton Waldemar", "Anton", "ABW"),
        ("Leverkusen", "Medina", "Medina Facundo", "Medina", "ABW"),
        ("Leverkusen", "Quansah", "Quansah Jarell", "Quansah", "ABW"),
        ("Hoffenheim", "Coufal", "Coufal Vladimir", "Coufal", "ABW"),
        ("Hoffenheim", "Avdullahu", "Avdullahu Leon", "Avdullahu", "MIT"),
        ("Elversberg", "Petkov", "Petkov Lukas", "Petkov", "MIT"),
        ("Freiburg", "M. Eggestein", "Eggestein Maximilian", "M. Eggestein", "MIT"),
        ("Stuttgart", "Prömel", "Prömel Grischa", "Prömel", "MIT"),
        ("Stuttgart", "Führich", "Führich Chris", "Führich", "MIT"),
        ("Mainz", "Kai. Sano", "Sano Kaishu", "Kai. Sano", "MIT"),
        ("Leverkusen", "Aleix Garcia", "Aleix Garcia", "Aleix Garcia", "MIT"),
        ("Frankfurt", "Ebnoutalib", "Ebnoutalib Younes", "Ebnoutalib", "STU"),
        ("Leverkusen", "Schick", "Schick Patrik", "Schick", "STU"),
        ("Stuttgart", "Undav", "Undav Deniz", "Undav", "STU"),
        ("Union", "Latte Lath", "Latte Lath Emmanuel", "Latte Lath", "STU"),
    ]
    for verein, kurz, kader, auktion, pos in rows:
        sid = f"{verein}:{kurz}"
        b.spieler[sid] = Spieler(sid, kurz, verein, Position(pos), "Thomas")
        b.aliase[sid] = _aliase_fuer(kurz, kader, auktion)
    b.teams["Thomas"] = "Hallodries"
    return b


MAIL_THOMAS = """Atubolu

(Kau Santos)

Anton V

Medina T

Quansah V

(Coufal) V

Avdullah T

Petkov VV

Eggestein T

Prömel T

Führich

(Kai Sano)

Ebnoutalib

Schick TTV

(Undav)
"""

MAIL_KOMMA = """Atubolu, (Kaua Santos)
Anton, Medina, Quansah, (Coufal)
Avdullahu, Petkov, M. Eggestein, Prömel, Führich, (Garcia)
Ebnoutalib, Schick, (Latte Lath)

Es läuft in der Bundesliga !!!!!!

Gesendet: Samstag, 5. September 2026 um 17:56
Von: jemand@example.org
Atubolu
"""

MAIL_PIPE = """Atubolu
|Kaua Santos

Anton
Medina
Quansah

Avdullahu
Petkov
Eggestein
Prömel
Führich
|Sano

Ebnoutalib
Schick
|Undav
||Latte Lath
"""


def test_zitat_wird_abgeschnitten():
    t = zitat_abschneiden("Neuer\n\nAm 05.09.26, 16:55 schrieb Martin <m@x.de>:\nKobel")
    assert "Kobel" not in t and "Neuer" in t


def test_format_thomas_kuerzel_und_klammern():
    a, zu, ign, warn, fehler = aufstellung_aus_text(MAIL_THOMAS, "Thomas", basis_bauen(), 2)
    assert fehler == []
    assert [s.split(":")[1] for s in a.start] == ["Atubolu", "Anton", "Medina", "Quansah", "Avdullahu", "Petkov", "M. Eggestein", "Prömel", "Führich", "Ebnoutalib", "Schick"]
    assert [s.split(":")[1] for s in a.bank] == ["Kaua Santos", "Coufal", "Kai. Sano", "Undav"]
    tolerant = {z.name_mail: z.spieler.name for z in zu if z.art == "tolerant"}
    assert tolerant == {"Kau Santos": "Kaua Santos", "Avdullah": "Avdullahu", "Kai Sano": "Kai. Sano"}


def test_format_komma_mit_zitat_und_kommentar():
    a, zu, ign, warn, fehler = aufstellung_aus_text(MAIL_KOMMA, "Thomas", basis_bauen(), 2)
    assert fehler == []
    assert len(a.start) == 11 and [s.split(":")[1] for s in a.bank] == ["Kaua Santos", "Coufal", "Aleix Garcia", "Latte Lath"]
    assert any("Bundesliga" in x for x in ign)
    assert sum(1 for s in a.start if s.endswith("Atubolu")) == 1       # zitierte Vormail zählt nicht


def test_format_pipe_bank():
    a, zu, ign, warn, fehler = aufstellung_aus_text(MAIL_PIPE, "Thomas", basis_bauen(), 2)
    assert fehler == []
    assert [s.split(":")[1] for s in a.bank] == ["Kaua Santos", "Kai. Sano", "Undav", "Latte Lath"]


def test_tippfehler_wird_unbekannter_platz():
    text = MAIL_PIPE.replace("Quansah", "Schlotterbek")
    a, zu, ign, warn, fehler = aufstellung_aus_text(text, "Thomas", basis_bauen(), 2)
    assert fehler == []
    unbekannt = [s for s in a.start if ist_unbekannt(s)]
    assert unbekannt == ["?ABW:Schlotterbek"]          # Position aus der Formationslücke


def test_schema_frankfurt_augsburg():
    sp = schema_parsen((FIX / "schema_frankfurt_augsburg.txt").read_text(encoding="utf-8"))
    assert (sp.heim, sp.gast, sp.tore_heim, sp.tore_gast) == ("Frankfurt", "Augsburg", 1, 4)
    assert len([s for s in sp.spieler if s.status == "Startelf"]) == 22
    by = {(s.verein, s.name): s for s in sp.spieler}
    assert by[("Augsburg", "Ibrahimovic")].tore == 1 and by[("Augsburg", "Ibrahimovic")].vorlagen == 1
    assert by[("Frankfurt", "Ebnoutalib")].vorlagen == 1
    assert by[("Frankfurt", "Pimpong")].note is None and by[("Frankfurt", "Pimpong")].eingesetzt
    assert by[("Frankfurt", "Kaua Santos")].eingesetzt is False
    assert by[("Augsburg", "Claude-Maurice")].note == "2,5" and by[("Augsburg", "Claude-Maurice")].tore == 1
    assert sp.warnungen == []


def test_schema_eigentor_und_nachspielzeit():
    sp = schema_parsen((FIX / "schema_stuttgart_koeln.txt").read_text(encoding="utf-8"))
    by = {(s.verein, s.name): s for s in sp.spieler}
    et = [t for t in sp.tore if t.eigentor][0]
    assert et.verein == "Köln" and et.schuetze == "Hendriks" and et.vorlage == "Bülter"
    assert by[("Köln", "Bülter")].vorlagen == 1 and by[("Stuttgart", "Hendriks")].tore == 0
    assert [t.minute for t in sp.tore][-1] == "90'+1"
    assert by[("Stuttgart", "Vagnoman")].tore == 1 and by[("Stuttgart", "Vagnoman")].vorlagen == 1
    assert by[("Stuttgart", "Demirovic")].note is None and by[("Stuttgart", "Demirovic")].tore == 1
    assert sp.warnungen == []


def test_elf_des_tages():
    spiele = [schema_parsen((FIX / n).read_text(encoding="utf-8")) for n in ("schema_frankfurt_augsburg.txt", "schema_stuttgart_koeln.txt")]
    edt, warn = elf_des_tages_parsen((FIX / "elf_des_tages_st02.txt").read_text(encoding="utf-8"), spiele)
    assert ("Augsburg", "Ibrahimovic") in edt


def test_zuordnung_und_spieltagsdaten():
    basis = basis_bauen()
    spiele = [schema_parsen((FIX / "schema_stuttgart_koeln.txt").read_text(encoding="utf-8"))]
    imp = KickerImport(2, spiele, [])
    zuordnen(imp, basis)
    daten = spieltagsdaten_bauen(imp, basis)
    assert daten.vereine["Stuttgart"].gegentore == 1 and daten.vereine["Köln"].gegentore == 4
    assert daten.spieler["Stuttgart:Prömel"].tore == 1 and daten.spieler["Stuttgart:Prömel"].note is not None
    assert daten.spieler["Stuttgart:Undav"].note is not None
    assert daten.spieler["Stuttgart:Führich"].eingesetzt is True


def test_ohne_initial():
    assert ohne_initial("R. Koch") == "Koch"
    assert ohne_initial("J.-S. Lee") == "Lee"
    assert ohne_initial("Kai. Sano") == "Sano"
    assert ohne_initial("La. Günther") == "Günther"
    assert ohne_initial("Latte Lath") == "Latte Lath"
