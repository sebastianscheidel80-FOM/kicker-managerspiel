"""Die sieben Testfälle aus 02_Aufgabe_Auswertungstool.md, Abschnitt 4,
plus Randfälle zu den Regeln aus REGELN_1.md v1.2.

Lesehilfe: Jeder Test baut zwei bis drei Manager mit Standardkadern (siehe
helpers.py), verändert gezielt eine Kleinigkeit und prüft, was die Engine
daraus macht.
"""
from fractions import Fraction

import pytest

from kickerspiel.engine import (
    REGELN_2026_27,
    EngineFehler,
    Herkunft,
    Kategorie,
    Regelwerk,
    pruefe_aufstellung,
    rangpunkte,
    saisontabelle,
    werte_spieltag,
)
from kickerspiel.model import Aufstellung, Position, Spieler, Spielerdaten, Vereinsdaten, unbekannt_id

from helpers import F, aufstellung, daten, kader, setze


def zwei_manager():
    index = {**kader("A"), **kader("B")}
    return index, [aufstellung("A"), aufstellung("B")]


def platz(erg, manager, sid_or_name):
    for p in erg.manager[manager].elf:
        if (p.spieler and p.spieler.id == sid_or_name) or p.name == sid_or_name:
            return p
    raise AssertionError(f"{sid_or_name} nicht in der gewerteten Elf von {manager}")


def ids(erg, manager):
    return [p.spieler.id if p.spieler else p.name for p in erg.manager[manager].elf]


# ---------------------------------------------------------------------------
# Testfall 1: Stammspieler ohne Note, erster Ersatz-ABW mit Note
#             → Ersatz rückt nach, kein 5,5
# ---------------------------------------------------------------------------
def test_1_ersatz_rueckt_nach():
    index, aufst = zwei_manager()
    d = daten(index)
    setze(d, "A_abw1", note=None, eingesetzt=False)          # Stamm-ABW ohne Note
    setze(d, "A_e1", note=2.0, tore=1)                        # Ersatz 1 ist ABW, hat Note

    erg = werte_spieltag(aufst, d, index)
    p = platz(erg, "A", "A_e1")
    assert p.herkunft == Herkunft.NACHRUECKER
    assert p.ersetzt.id == "A_abw1" and p.bankplatz == 1
    assert "A_abw1" not in ids(erg, "A")
    assert not any(q.strafnote for q in erg.manager["A"].elf)
    # Note und Tor des Nachrückers zählen, der Schnitt sinkt entsprechend
    assert erg.manager["A"].notensumme == F(3.0) * 10 + F(2.0)
    assert erg.manager["A"].werte[Kategorie.TORE] == 1
    assert any("rückt nach (Bank 1)" in z for z in erg.manager["A"].protokoll)


# ---------------------------------------------------------------------------
# Testfall 2: Zwei Stamm-ABW ohne Note, nur ein Ersatz-ABW
#             → einer rückt nach, der andere bekommt 5,5 (Aufstellungsreihenfolge)
# ---------------------------------------------------------------------------
def test_2_zwei_ausfaelle_ein_ersatz():
    index, aufst = zwei_manager()
    d = daten(index)
    setze(d, "A_abw1", note=None, eingesetzt=False)
    setze(d, "A_abw2", note=None, eingesetzt=False)
    setze(d, "A_e1", note=2.5)

    erg = werte_spieltag(aufst, d, index)
    e1 = platz(erg, "A", "A_e1")
    assert e1.herkunft == Herkunft.NACHRUECKER and e1.ersetzt.id == "A_abw1"   # der zuerst genannte
    abw2 = platz(erg, "A", "A_abw2")
    assert abw2.herkunft == Herkunft.STRAFNOTE and abw2.note == F(5.5)
    assert "A_abw1" not in ids(erg, "A")
    assert sum(1 for q in erg.manager["A"].elf if q.strafnote) == 1


# ---------------------------------------------------------------------------
# Testfall 3: Ersatz-ABW ohne Note, zweiter Ersatz-ABW mit Note → der zweite rückt nach
# ---------------------------------------------------------------------------
def test_3_zweiter_ersatz_rueckt_nach():
    index = {**kader("A", bank=[Position.ABW, Position.ABW, Position.MIT]), **kader("B")}
    aufst = [aufstellung("A"), aufstellung("B")]
    d = daten(index)
    setze(d, "A_abw3", note=None, eingesetzt=False)
    setze(d, "A_e1", note=None, eingesetzt=False)             # Ersatz 1 (ABW) ohne Note
    setze(d, "A_e2", note=3.5)                                # Ersatz 2 (ABW) mit Note

    erg = werte_spieltag(aufst, d, index)
    p = platz(erg, "A", "A_e2")
    assert p.herkunft == Herkunft.NACHRUECKER and p.ersetzt.id == "A_abw3" and p.bankplatz == 2
    assert "A_e1" not in ids(erg, "A")
    assert any("Ersatz 1 A e1 (ABW) hat keine Note – übersprungen" in z for z in erg.manager["A"].protokoll)


# ---------------------------------------------------------------------------
# Testfall 4: Stamm-ST spielt 5 Minuten, trifft, keine Note, kein Ersatz-ST
#             → Note 5,5, Tor zählt doppelt
# ---------------------------------------------------------------------------
def test_4_kurzeinsatz_tor_zaehlt_doppelt():
    index = {**kader("A", bank=[Position.ABW, Position.MIT, Position.MIT]), **kader("B")}
    aufst = [aufstellung("A"), aufstellung("B")]
    d = daten(index)
    setze(d, "A_stu1", note=None, tore=1, eingesetzt=True)   # Kurzeinsatz mit Tor

    erg = werte_spieltag(aufst, d, index)
    p = platz(erg, "A", "A_stu1")
    assert p.herkunft == Herkunft.STRAFNOTE and p.note == F(5.5)
    assert p.tore == 1 and p.tore_gew == 2
    assert p.strafgegentore == 0                              # Stürmer: nie Strafgegentor
    assert erg.manager["A"].werte[Kategorie.TORE] == 2
    assert erg.manager["A"].notensumme == F(3.0) * 10 + F(5.5)
    assert any("Kurzeinsatz: 1 Tor(e)" in z for z in erg.manager["A"].protokoll)


# ---------------------------------------------------------------------------
# Testfall 5: Zwei Manager mit 0 Gegentoren → je 5,5 Punkte, der Dritte bekommt 4
# ---------------------------------------------------------------------------
def test_5_gleichstand_gegentore():
    index = {**kader("A"), **kader("B"), **kader("C")}
    aufst = [aufstellung("A"), aufstellung("B"), aufstellung("C")]
    d = daten(index, gegentore={"V_A": 0, "V_B": 0, "V_C": 2})

    erg = werte_spieltag(aufst, d, index)
    rp = {m: erg.manager[m].rangpunkte[Kategorie.GEGENTORE] for m in "ABC"}
    assert rp == {"A": F(5.5), "B": F(5.5), "C": F(4)}
    assert erg.manager["A"].raenge[Kategorie.GEGENTORE] == 1
    assert erg.manager["B"].raenge[Kategorie.GEGENTORE] == 1
    assert erg.manager["C"].raenge[Kategorie.GEGENTORE] == 3


# ---------------------------------------------------------------------------
# Testfall 6: Torwart-Gegentore doppelt; Ersatz-TW rückt nur nach, wenn Stamm-TW keine Note hat
# ---------------------------------------------------------------------------
def test_6a_torwart_gegentore_doppelt():
    index, aufst = zwei_manager()
    d = daten(index, gegentore={"V_A": 2, "V_B": 0})
    erg = werte_spieltag(aufst, d, index)
    tw = platz(erg, "A", "A_tor1")
    assert tw.gegentore_verein == 2 and tw.gegentore_gew == 4
    # 4 (TW) + 3 × 2 (ABW) = 10; Mittelfeld und Sturm zählen nicht
    assert erg.manager["A"].werte[Kategorie.GEGENTORE] == 10
    assert erg.manager["B"].werte[Kategorie.GEGENTORE] == 0


def test_6b_ersatz_tw_bleibt_draussen_wenn_stamm_tw_note_hat():
    index, aufst = zwei_manager()
    d = daten(index)
    setze(d, "A_tor1", note=5.0)          # schlechte Note, aber eine Note
    setze(d, "A_tw2", note=1.0)           # Ersatz-TW glänzt – zählt trotzdem nicht
    setze(d, "A_abw1", note=None, eingesetzt=False)   # ABW-Lücke, Ersatz-TW darf dort nicht hin
    setze(d, "A_e1", note=None, eingesetzt=False)     # der einzige Ersatz-ABW hat auch keine Note
    erg = werte_spieltag(aufst, d, index)
    assert platz(erg, "A", "A_tor1").herkunft == Herkunft.STAMM
    assert "A_tw2" not in ids(erg, "A")
    assert platz(erg, "A", "A_abw1").strafnote


def test_6c_ersatz_tw_rueckt_fuer_stamm_tw_nach():
    index, aufst = zwei_manager()
    d = daten(index, gegentore={"V_A": 3, "V_B": 1})
    setze(d, "A_tor1", note=None, eingesetzt=False)
    setze(d, "A_tw2", note=2.0)
    erg = werte_spieltag(aufst, d, index)
    tw = platz(erg, "A", "A_tw2")
    assert tw.herkunft == Herkunft.NACHRUECKER and tw.ersetzt.id == "A_tor1" and tw.bankplatz == 4
    assert tw.gegentore_gew == 6


# ---------------------------------------------------------------------------
# Testfall 7: Spieler mit kicker-Position MF, der real Abwehr spielt
#             → keine Gegentore, Vorlagen doppelt
# ---------------------------------------------------------------------------
def test_7_positionsarbitrage_mittelfeld():
    index, aufst = zwei_manager()
    d = daten(index, gegentore={"V_A": 3, "V_B": 1})
    setze(d, "A_mit1", note=2.0, vorlagen=2)      # laut kicker MIT, spielt real Außenverteidiger
    erg = werte_spieltag(aufst, d, index)
    p = platz(erg, "A", "A_mit1")
    assert p.gegentore_gew == 0 and p.gegentore_verein == 0
    assert p.vorlagen == 2 and p.vorlagen_gew == 4
    assert erg.manager["A"].werte[Kategorie.VORLAGEN] == 4
    assert erg.manager["A"].werte[Kategorie.GEGENTORE] == 3 * 2 + 3 * 3   # nur TW und ABW


# ---------------------------------------------------------------------------
# Randfälle zu v1.2
# ---------------------------------------------------------------------------
def test_strafgegentor_nur_bei_null_minuten():
    index = {**kader("A", bank=[Position.MIT, Position.MIT, Position.STU]), **kader("B")}
    aufst = [aufstellung("A"), aufstellung("B")]
    d = daten(index, gegentore={"V_A": 2, "V_B": 1})
    setze(d, "A_abw1", note=None, eingesetzt=False)   # 0 Minuten → 2 + 1 Strafgegentor
    setze(d, "A_abw2", note=None, eingesetzt=True)    # Kurzeinsatz → nur 2
    erg = werte_spieltag(aufst, d, index)
    a1, a2 = platz(erg, "A", "A_abw1"), platz(erg, "A", "A_abw2")
    assert (a1.gegentore_verein, a1.strafgegentore, a1.gegentore_gew) == (2, 1, 3)
    assert (a2.gegentore_verein, a2.strafgegentore, a2.gegentore_gew) == (2, 0, 2)
    assert a1.note == a2.note == F(5.5)


def test_strafgegentor_torwart_doppelt():
    index = {**kader("A"), **kader("B")}
    a = aufstellung("A")
    a.bank = ["A_e1", "A_e2", "A_e3"]                 # kein Ersatz-TW
    d = daten(index, gegentore={"V_A": 4, "V_B": 1})
    setze(d, "A_tor1", note=None, eingesetzt=False)
    erg = werte_spieltag([a, aufstellung("B")], d, index)
    tw = platz(erg, "A", "A_tor1")
    assert tw.gegentore == 5 and tw.gegentore_gew == 10   # (4 + 1) × 2
    assert any("Nur 3 Ersatzspieler" in w for w in erg.manager["A"].warnungen)


def test_nicht_zuordenbarer_abwehrplatz():
    index, aufst = zwei_manager()
    a = aufst[0]
    a.start[1] = unbekannt_id(Position.ABW, "Schlotterbek")   # Tippfehler statt A_abw1
    a.bank = ["A_e2", "A_e3", "A_tw2"]                          # kein Ersatz-ABW
    d = daten(index, gegentore={"V_A": 1, "V_B": 5})            # höchste Gegentore des Spieltags: 5
    erg = werte_spieltag(aufst, d, index)
    p = platz(erg, "A", "Schlotterbek")
    assert p.herkunft == Herkunft.UNBEKANNT and p.note == F(5.5)
    assert p.gegentore_verein == 5 and p.strafgegentore == 1 and p.gegentore_gew == 6
    assert any("Name nicht zuordenbar" in z for z in erg.manager["A"].protokoll)


def test_nicht_zuordenbarer_platz_mit_nachruecker():
    index, aufst = zwei_manager()
    a = aufst[0]
    a.start[1] = unbekannt_id(Position.ABW, "Schlotterbek")
    d = daten(index)
    erg = werte_spieltag(aufst, d, index)
    p = platz(erg, "A", "A_e1")                                # Ersatz-ABW rückt nach
    assert p.herkunft == Herkunft.NACHRUECKER and p.ersetzt is None
    assert "Schlotterbek" not in ids(erg, "A")


def test_nicht_zuordenbarer_torwart_verdoppelt():
    index, aufst = zwei_manager()
    a = aufst[0]
    a.start[0] = unbekannt_id(Position.TOR, "Nojer")
    a.bank = ["A_e1", "A_e2", "A_e3"]
    d = daten(index, gegentore={"V_A": 0, "V_B": 3})
    erg = werte_spieltag(aufst, d, index)
    p = platz(erg, "A", "Nojer")
    assert p.gegentore_gew == (3 + 1) * 2


def test_gleichstand_drei_erste_und_vier_dritte():
    p, r = rangpunkte({"A": 0, "B": 0, "C": 0, "D": 1, "E": 2, "F": 3}, niedriger_besser=True)
    assert p["A"] == p["B"] == p["C"] == F(5) and r["A"] == 1
    assert p["D"] == 3 and r["D"] == 4
    p, r = rangpunkte({"A": 3, "B": 1, "C": 0, "D": 0, "E": 0, "F": 0}, niedriger_besser=False)
    assert p["A"] == 6 and p["B"] == 5
    assert p["C"] == p["F"] == F(2.5) and r["C"] == 3
    p, _ = rangpunkte({m: 0 for m in "ABCDEF"}, niedriger_besser=False)
    assert all(v == F(3.5) for v in p.values())


def test_notenschnitt_exakter_gleichstand():
    index = {**kader("A"), **kader("B"), **kader("C")}
    aufst = [aufstellung("A"), aufstellung("B"), aufstellung("C")]
    d = daten(index)
    setze(d, "A_mit1", note=2.5); setze(d, "A_mit2", note=3.5)    # Summe 33 wie B
    setze(d, "C_mit1", note=2.5)                                     # Summe 32,5 → besser
    erg = werte_spieltag(aufst, d, index)
    assert erg.manager["A"].werte[Kategorie.NOTE] == erg.manager["B"].werte[Kategorie.NOTE]
    assert erg.manager["A"].rangpunkte[Kategorie.NOTE] == F(4.5)
    assert erg.manager["C"].rangpunkte[Kategorie.NOTE] == 6


def test_edt_zaehlt_nur_gewertete_spieler():
    index, aufst = zwei_manager()
    d = daten(index)
    setze(d, "A_mit1", note=1.0, edt=True)
    setze(d, "A_e2", note=1.5, edt=True)          # Ersatz, nicht nachgerückt → zählt nicht
    erg = werte_spieltag(aufst, d, index)
    assert erg.manager["A"].werte[Kategorie.EDT] == 1


def test_ungueltige_formation_wird_abgelehnt():
    index, aufst = zwei_manager()
    aufst[0].start[4] = "A_abw1"                 # ABW doppelt, MIT fehlt
    with pytest.raises(EngineFehler, match="Formation"):
        werte_spieltag(aufst, daten(index), index)


def test_fremder_spieler_wird_abgelehnt():
    index, aufst = zwei_manager()
    aufst[0].start[10] = "B_stu1"
    fehler, _ = pruefe_aufstellung(aufst[0], index)
    assert any("gehört nicht zu A" in f for f in fehler)


def test_fehlende_daten_werden_gemeldet():
    index, aufst = zwei_manager()
    d = daten(index)
    del d.spieler["A_mit3"]
    erg = werte_spieltag(aufst, d, index)
    assert platz(erg, "A", "A_e2").herkunft == Herkunft.NACHRUECKER    # Ersatz-MIT rückt nach
    assert any("Keine kicker-Daten" in w for w in erg.manager["A"].warnungen)


def test_spieltagssumme_und_sieg():
    index, aufst = zwei_manager()
    d = daten(index, gegentore={"V_A": 0, "V_B": 2})
    setze(d, "A_stu1", note=1.0, tore=2, edt=True)
    erg = werte_spieltag(aufst, d, index)
    a, b = erg.manager["A"], erg.manager["B"]
    assert a.summe == 6 * 4 + F(5.5)            # Vorlagen geteilt (beide 0), Rest gewinnt A
    assert b.summe == 5 * 4 + F(5.5)
    assert a.platz == 1 and b.platz == 2
    assert erg.spieltagssieg == {"A": 1, "B": 0}
    assert sum(m.summe for m in erg.manager.values()) == 5 * (6 + 5)


def test_saisontabelle_summiert_und_teilt_siege():
    index, aufst = zwei_manager()
    d1 = daten(index, spieltag=2, gegentore={"V_A": 0, "V_B": 2})
    d2 = daten(index, spieltag=3)                # alles gleich → geteilter Sieg
    e1, e2 = werte_spieltag(aufst, d1, index), werte_spieltag(aufst, d2, index)
    s = saisontabelle([e1, e2])
    za, zb = s.zeile("A"), s.zeile("B")
    assert za.punkte == e1.manager["A"].summe + e2.manager["A"].summe
    assert za.spieltagssiege == F(1.5) and zb.spieltagssiege == F(0.5)
    assert za.kumuliert[3] == za.punkte and za.verlauf[2] == e1.manager["A"].summe
    assert za.platz == 1 and zb.platz == 2
    assert s.beitraege["A_tor1"].einsaetze == 2


def test_regelwerk_vorsaison_ohne_strafgegentor():
    index, aufst = zwei_manager()
    d = daten(index, gegentore={"V_A": 2, "V_B": 1})
    setze(d, "A_abw1", note=None, eingesetzt=False)
    setze(d, "A_e1", note=None, eingesetzt=False)
    erg = werte_spieltag(aufst, d, index, Regelwerk(strafgegentor=0))
    p = platz(erg, "A", "A_abw1")
    assert p.strafnote and p.strafgegentore == 0 and p.gegentore_gew == 2
