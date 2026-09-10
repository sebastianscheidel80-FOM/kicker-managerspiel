# -*- coding: utf-8 -*-
"""Das Goldene Buch – Verfassung des Kicker-Managerspiels 2026/27 (PDF)."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak,
                                Table, TableStyle, KeepTogether, NextPageTemplate)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

F = "/usr/share/fonts/truetype/liberation/"
pdfmetrics.registerFont(TTFont("Serif", F + "LiberationSerif-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Serif-Bold", F + "LiberationSerif-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Serif-Italic", F + "LiberationSerif-Italic.ttf"))
pdfmetrics.registerFont(TTFont("Serif-BoldItalic", F + "LiberationSerif-BoldItalic.ttf"))
pdfmetrics.registerFontFamily("Serif", normal="Serif", bold="Serif-Bold", italic="Serif-Italic", boldItalic="Serif-BoldItalic")

GOLD = colors.HexColor("#B8860B")
GOLD_HELL = colors.HexColor("#D9B25C")
GRUEN = colors.HexColor("#1E3A2F")
CREME = colors.HexColor("#FBF6E7")
TINTE = colors.HexColor("#2B2418")
GRAU = colors.HexColor("#6B6254")

W, H = A4
RAND = 20 * mm

st_body = ParagraphStyle("body", fontName="Serif", fontSize=10.8, leading=15.5, textColor=TINTE, alignment=TA_JUSTIFY, spaceAfter=5)
st_para = ParagraphStyle("para", parent=st_body, spaceBefore=7, spaceAfter=3)
st_h1 = ParagraphStyle("h1", fontName="Serif-Bold", fontSize=19, leading=24, textColor=GRUEN, alignment=TA_CENTER, spaceBefore=18, spaceAfter=4)
st_h1sub = ParagraphStyle("h1sub", fontName="Serif-Italic", fontSize=11, leading=14, textColor=GOLD, alignment=TA_CENTER, spaceAfter=14)
st_h2 = ParagraphStyle("h2", fontName="Serif-Bold", fontSize=12.5, leading=16, textColor=GRUEN, spaceBefore=12, spaceAfter=3)
st_zitat = ParagraphStyle("zitat", fontName="Serif-Italic", fontSize=10.5, leading=14.5, textColor=GRAU, leftIndent=14, rightIndent=14, alignment=TA_JUSTIFY, spaceAfter=6)
st_small = ParagraphStyle("small", fontName="Serif", fontSize=9, leading=12, textColor=GRAU, alignment=TA_CENTER)
st_tab = ParagraphStyle("tab", fontName="Serif", fontSize=9.6, leading=12.5, textColor=TINTE)
st_tabh = ParagraphStyle("tabh", parent=st_tab, fontName="Serif-Bold", textColor=GRUEN)


def rahmen(canv, doc):
    canv.saveState()
    canv.setFillColor(CREME)
    canv.rect(0, 0, W, H, stroke=0, fill=1)
    canv.setStrokeColor(GOLD)
    canv.setLineWidth(1.6)
    canv.rect(RAND - 8 * mm, RAND - 8 * mm, W - 2 * RAND + 16 * mm, H - 2 * RAND + 16 * mm)
    canv.setLineWidth(0.6)
    canv.rect(RAND - 6 * mm, RAND - 6 * mm, W - 2 * RAND + 12 * mm, H - 2 * RAND + 12 * mm)
    # Ecken-Ornament
    for x, y in ((RAND - 8 * mm, RAND - 8 * mm), (W - RAND + 8 * mm, RAND - 8 * mm), (RAND - 8 * mm, H - RAND + 8 * mm), (W - RAND + 8 * mm, H - RAND + 8 * mm)):
        canv.setFillColor(GOLD)
        canv.circle(x, y, 2.2 * mm, stroke=0, fill=1)
        canv.setFillColor(CREME)
        canv.circle(x, y, 1.0 * mm, stroke=0, fill=1)
    canv.setFont("Serif-Italic", 8.5)
    canv.setFillColor(GRAU)
    canv.drawCentredString(W / 2, RAND - 12 * mm, f"Das Goldene Buch des Kicker-Managerspiels · Saison 2026/27 · Seite {doc.page}")
    canv.drawCentredString(W / 2, H - RAND + 10 * mm, "Verbindlich ist REGELN_1.md v1.3 – dieses Buch erklärt sie, mit einem Augenzwinkern")
    canv.restoreState()


def titelseite(canv, doc):
    canv.saveState()
    canv.setFillColor(CREME)
    canv.rect(0, 0, W, H, stroke=0, fill=1)
    canv.setStrokeColor(GOLD)
    for i, lw in ((10, 2.2), (13, 0.8), (15, 0.8)):
        canv.setLineWidth(lw)
        canv.rect(i * mm, i * mm, W - 2 * i * mm, H - 2 * i * mm)
    # Siegel
    cx, cy = W / 2, H * 0.30
    canv.setFillColor(GOLD)
    canv.circle(cx, cy, 24 * mm, stroke=0, fill=1)
    canv.setFillColor(GOLD_HELL)
    canv.circle(cx, cy, 21 * mm, stroke=0, fill=1)
    canv.setFillColor(GOLD)
    canv.circle(cx, cy, 17 * mm, stroke=0, fill=1)
    canv.setFillColor(CREME)
    canv.setFont("Serif-Bold", 22)
    canv.drawCentredString(cx, cy + 4 * mm, "3-5-2")
    canv.setFont("Serif-Italic", 8.5)
    canv.drawCentredString(cx, cy - 4 * mm, "seit 1997")
    canv.drawCentredString(cx, cy - 9 * mm, "sechs Manager · ein Kicker")
    canv.restoreState()


def deckblatt():
    s_t1 = ParagraphStyle("t1", fontName="Serif-Bold", fontSize=34, leading=40, textColor=GRUEN, alignment=TA_CENTER)
    s_t2 = ParagraphStyle("t2", fontName="Serif-Italic", fontSize=15, leading=20, textColor=GOLD, alignment=TA_CENTER)
    s_t3 = ParagraphStyle("t3", fontName="Serif", fontSize=11.5, leading=16, textColor=TINTE, alignment=TA_CENTER)
    return [
        Spacer(1, 62 * mm),
        Paragraph("Das Goldene Buch", s_t1),
        Spacer(1, 4 * mm),
        Paragraph("Verfassung des Kicker-Managerspiels", s_t2),
        Spacer(1, 2 * mm),
        Paragraph("Bundesliga-Saison 2026/27", s_t2),
        Spacer(1, 16 * mm),
        Paragraph("beschlossen von den Hohen Vertragsparteien<br/>"
                  "<b>Fischköppe · Great Licors · Hallodries · Hansa Fürze · Käsefüße · Vickings</b>", s_t3),
        Spacer(1, 6 * mm),
        Paragraph("in der Fassung der Regeldatei v1.3 vom 10. September 2026", s_t3),
        Spacer(1, 95 * mm),
        Paragraph("Wer dieses Buch liest, hat keine Ausrede mehr.", ParagraphStyle("m", parent=s_t3, fontName="Serif-Italic", textColor=GRAU)),
    ]


def P(text, style=st_body):
    return Paragraph(text, style)


def para(nr, titel, *absaetze):
    out = [Paragraph(f"§ {nr} &nbsp;{titel}", st_h2)]
    for i, a in enumerate(absaetze, 1):
        out.append(P(f"({i}) {a}" if len(absaetze) > 1 else a, st_body))
    return [KeepTogether(out)]


def tabelle(kopf, zeilen, breiten):
    data = [[Paragraph(k, st_tabh) for k in kopf]] + [[Paragraph(str(z), st_tab) for z in r] for r in zeilen]
    t = Table(data, colWidths=breiten, hAlign="CENTER")
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, GOLD),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, GOLD),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.Color(1, 1, 1, 0), colors.HexColor("#F3EBD3")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def buch(titel, untertitel):
    return [Paragraph(titel, st_h1), Paragraph(untertitel, st_h1sub)]


story = deckblatt()
story.append(NextPageTemplate("innen"))
story.append(PageBreak())

# ---------------------------------------------------------------- Präambel
story += buch("Präambel", "Warum es dieses Buch gibt")
story.append(P("Wir, sechs Manager mit je dreißig Millionen imaginärer Euro, einem gemeinsamen Kicker-Abonnement "
               "und einer seit Jahren nicht abschließend geklärten Frage, wer eigentlich der Beste ist, geben uns "
               "diese Verfassung. Sie soll Streit beenden, bevor er beginnt, Tippfehler bestrafen, bevor sie sich "
               "lohnen, und dem Auswertungstool sagen, was es zu rechnen hat. Über allem steht ein Grundsatz: "
               "Gewertet wird, was der kicker schreibt. Nicht, was wir gesehen haben. Nicht, was der Trainer gesagt hat. "
               "Nicht, was im Fernsehen kommentiert wurde. Der kicker.", st_body))
story.append(P("Dieses Buch ist die lesbare Fassung. Verbindlich, im Zweifel und vor jedem Schiedsgericht der Runde, "
               "bleibt die Regeldatei REGELN_1.md in ihrer jeweils gültigen Version. Wo dieses Buch scherzt, "
               "meint es die Regel trotzdem ernst.", st_zitat))

# ---------------------------------------------------------------- Erstes Buch
story += buch("Erstes Buch – Die Grundordnung", "Von Liga, Managern und Geld, das es nicht gibt")
story += para(1, "Die Liga",
              "Gespielt wird die 1. Bundesliga, Saison 2026/27. Andere Ligen existieren für die Zwecke dieses Buches nicht; "
              "wer einen Spieler kauft, der im Winter nach England geht, hat ihn gekauft und nicht die Bundesliga.")
story += para(2, "Die Hohen Vertragsparteien",
              "Sechs Manager bilden die Runde: Andreas (Fischköppe), Daniel (Käsefüße), Martin (Hansa Fürze), "
              "Sebastian (Great Licors), Thomas (Hallodries) und Wolfgang (Vickings).",
              "Jeder Manager verwaltet ein Startbudget von 30 Millionen Euro. Was übrig bleibt, bleibt übrig; "
              "Zinsen werden nicht gezahlt.")
story += para(3, "Der Kader",
              "Ein Kader hat üblicherweise 22 bis 26 Spieler. Es gibt keine Positions- und keine Vereinsgrenzen. "
              "Wer vier Bayern-Verteidiger kauft, darf das; er erlebt dann auch viermal denselben Spieltag.",
              "Jeder Spieler gehört genau einem Manager. Das ist keine Empfehlung, das ist Physik.")
story += para(4, "Die Wertung beginnt am 2. Spieltag",
              "Der 1. Spieltag dient der Beobachtung, der 2. Spieltag ist der erste, der zählt. Das Freitagsspiel des "
              "2. Spieltags zählt mit, obwohl sein Ergebnis zur Auktion bereits bekannt ist. Wer daraus einen Vorteil "
              "zieht, hat ihn bezahlt.")

# ---------------------------------------------------------------- Zweites Buch
story += buch("Zweites Buch – Die Auktion", "Wie Spieler zu Managern kommen")
story += para(5, "Vorschlagsrecht und Gebot",
              "Die Manager haben reihum das Vorschlagsrecht und rufen einen beliebigen Spieler auf. Der wird versteigert.",
              "Das Mindestgebot beträgt 300.000 Euro. Der Höchstbietende erhält den Spieler, sein Budget die Rechnung.")
story += para(6, "Der Aufsteiger-Pick",
              "Die schwächsten Manager des Vorjahres wählen vor der Auktion je einen Spieler eines Aufsteigers "
              "(Schalke 04, SV Elversberg, SC Paderborn) zum Fixpreis von 300.000 Euro. Es ist das einzige "
              "Schnäppchen, das dieses Buch kennt, und es wird mit dem Tabellenplatz des Vorjahres bezahlt.")
story += para(7, "Die Spielerbasis",
              "Das Ergebnis der Auktion wird in der Spielerbasis geführt: je Spieler der Manager, der Name in "
              "kicker-Schreibweise, der Verein, die kicker-Position und der Kaufpreis. Die Spielerbasis ist die "
              "Wahrheit über die Kader. Wer darin nicht steht, spielt nicht mit.")

# ---------------------------------------------------------------- Drittes Buch
story += buch("Drittes Buch – Die Aufstellung", "Elf Stammspieler, vier Ersatzspieler, eine Reihenfolge")
story += para(8, "Die Formation",
              "Gespielt wird 3-5-2, immer: ein Torwart, drei Abwehrspieler, fünf Mittelfeldspieler, zwei Stürmer. "
              "Nach kicker-Position, nicht nach Gefühl.",
              "Die Ersatzbank hat vier Plätze. Drei sind frei wählbar, der vierte ist immer ein zweiter Torwart. "
              "Wer keinen zweiten Torwart aufstellt, spielt ohne Netz.")
story += para(9, "Die Position gilt die ganze Saison",
              "Maßgeblich ist die Position, unter der der kicker einen Spieler in der Kaderliste führt. Sie gilt für "
              "die gesamte Saison, unabhängig davon, wo der Spieler tatsächlich herumläuft. Ein als Mittelfeldspieler "
              "geführter Außenverteidiger kassiert keine Gegentore und bekommt Vorlagen doppelt. Das ist kein Fehler "
              "im System, das ist das System.")
story += para(10, "Die Abgabe",
              "Die Aufstellung wird per E-Mail an die Runde geschickt, Freitag vor Anpfiff des Freitagsspiels. Wer am "
              "Freitag ohne Spieler des Freitagsspiels abgibt, darf bis Samstag 15:30 Uhr nachbessern.",
              "Die Reihenfolge der Namen ist Teil der Aufstellung. Sie entscheidet, wer bei mehreren Ausfällen den "
              "Nachrücker bekommt (§ 14) und in welcher Reihenfolge die Bank befragt wird (§ 13).",
              "Ob eine Mail rechtzeitig kam, prüft vorerst Sebastian. Das Tool merkt sich die Sendezeit trotzdem. "
              "Für immer.")
story += para(11, "Fehlende oder ungültige Aufstellung",
              "Liegt keine gültige Aufstellung vor – keine Mail, falsche Formation, fremder Spieler –, gilt die letzte "
              "gültige Aufstellung des Managers weiter. Das Tool vermerkt das im Report, damit alle es sehen.")
story += para(12, "Der Tippfehler",
              "Ein Name, der keinem Spieler des eigenen Kaders zugeordnet werden kann, gilt als Stammspieler ohne "
              "Einsatz: Der zuerst gelistete Ersatzspieler derselben Position rückt nach. Rückt niemand nach, bleibt "
              "der Platz mit Strafnote 5,5 in der Wertung, und bei einem Torwart- oder Abwehrplatz zusätzlich mit den "
              "höchsten Gegentoren, die an diesem Spieltag ein Verein kassiert hat, plus ein Strafgegentor; beim Torwart "
              "alles doppelt.",
              "Ein nicht zuordenbarer Ersatzspieler entfällt ersatzlos. Schreibt sorgfältig.")

# ---------------------------------------------------------------- Viertes Buch
story += buch("Viertes Buch – Die gewertete Elf", "Von Noten, Nachrückern und der Fünfeinhalb")
story += para(13, "Die Nachrückregel",
              "Gewertet werden nur Spieler, die eine kicker-Note erhalten. Hat ein Stammspieler keine Note, rückt der "
              "zuerst gelistete Ersatzspieler derselben kicker-Position nach, sofern er eine Note hat. Hat er keine, "
              "wird der nächste derselben Position befragt. Ein Ersatzspieler rückt höchstens einmal nach; der "
              "Ersatztorwart rückt nur für den Torwart nach, auch wenn er der beste Mann des Spieltags war.")
story += para(14, "Mehr Ausfälle als Ersatz",
              "Fehlen auf einer Position mehr Stammspieler, als Ersatzspieler mit Note vorhanden sind, werden die "
              "Stammspieler in der Reihenfolge der Abgabe bedient. Der zuerst genannte bekommt den ersten Nachrücker. "
              "Wer keinen mehr bekommt, bekommt § 15.")
story += para(15, "Die Strafnote",
              "Kann niemand nachrücken, bleibt der Stammspieler ohne Note in der Wertung und erhält die Note 5,5. "
              "Sie ist schlechter als fast alles, was der kicker vergibt, und genau so ist sie gemeint.",
              "Hat der Spieler gespielt, aber keine Note bekommen (Kurzeinsatz), zählen seine Tore, Vorlagen und die "
              "Gegentore seines Vereins trotzdem. Ein Tor in der 88. Minute ohne Note ist also kein verlorenes Tor.",
              "Hat der Spieler null Minuten gespielt – nicht im Kader, nicht eingewechselt –, zählen für einen Torwart "
              "oder Abwehrspieler die Gegentore seines Vereins plus ein Strafgegentor; beim Torwart alles doppelt. "
              "Wer einen Verletzten aufstellt, verteidigt mit ihm.")
story += para(16, "Nur die Elf zählt",
              "In allen Kategorien zählen ausschließlich die elf gewerteten Spieler. Ein Ersatzspieler, der nicht "
              "nachgerückt ist, mag drei Tore geschossen haben; für die Runde hat er auf der Bank gesessen.")

# ---------------------------------------------------------------- Fünftes Buch
story += buch("Fünftes Buch – Die Wertung", "Fünf Kategorien, sechs Ränge, dreißig Punkte")
story += para(17, "Die fünf Kategorien",
              "Jeder Spieltag wird in fünf Kategorien gewertet, jede gleich viel wert. Der Beste einer Kategorie erhält "
              "sechs Punkte, dann fünf, vier, drei, zwei, eins. Mehr als dreißig Punkte gibt es an keinem Spieltag, "
              "und noch niemand hat sie geholt.")
story.append(Spacer(1, 4))
story.append(tabelle(
    ["Kategorie", "Was zählt", "Gewichtung"],
    [["Durchschnittsnote", "Ø der elf kicker-Noten, Strafnoten inklusive. Niedrigster Schnitt gewinnt.", "alle gleich"],
     ["Gegentore", "Jeder gewertete Abwehrspieler erhält alle Gegentore seines Vereins in diesem Spiel, unabhängig von seiner Einsatzzeit. Wenigste gewinnen.", "Torwart ×2, Abwehr ×1, Rest zählt nicht"],
     ["Tore", "Tore der gewerteten Spieler. Elfmeter zählen normal. Eigentore zählen nicht – weder als Tor noch als Abzug.", "Stürmer ×2, Rest ×1"],
     ["Vorlagen", "Vorlagen nach kicker-Spielschema. Beim Eigentor bekommt der Vorlagengeber der torerzielenden Mannschaft seine Vorlage; beim Elfmeter zählt, was der kicker ausweist.", "Mittelfeld ×2, Rest ×1"],
     ["Elf des Tages", "Anzahl gewerteter eigener Spieler in der kicker-Elf des Tages. Meiste gewinnen.", "alle gleich"]],
    [34 * mm, 96 * mm, 40 * mm]))
story.append(Spacer(1, 6))
story += para(18, "Der Gleichstand",
              "Liegen mehrere Manager in einer Kategorie gleichauf, teilen sie die Punkte der Ränge, die sie gemeinsam "
              "belegen: zwei Erste erhalten je 5,5, drei Erste je 5,0, vier Dritte je 2,5. Gleichstand ist nur, was "
              "exakt gleich ist; ein Notenschnitt von 3,27 gegen 3,27 ist einer, gerundet wird nicht.")
story += para(19, "Keine Karten, keine Gnade, keine Ausnahmen",
              "Gelbe und rote Karten führen zu keinem Abzug. Der Spieler, der mit Rot vom Platz fliegt, bekommt "
              "seine kicker-Note und sonst nichts.")

# ---------------------------------------------------------------- Sechstes Buch
story += buch("Sechstes Buch – Die Saison", "Tabelle, Spieltagssiege, Nachholspiele")
story += para(20, "Die Saisontabelle",
              "Die Saisonwertung ist die Summe aller Spieltagspunkte ab dem 2. Spieltag.",
              "Wer an einem Spieltag die meisten Punkte holt, erhält einen Spieltagssieg. Bei Gleichstand wird er geteilt: "
              "zwei Sieger je einen halben, drei je ein Drittel.",
              "Liegen zwei Manager in der Saisontabelle punktgleich, steht vorn, wer mehr Spieltagssiege hat. Sind auch "
              "die gleich, teilen sie sich den Platz und die Rechnung.")
story += para(21, "Nachholspiele",
              "Fällt ein Spiel aus, wird der Spieltag zunächst vorläufig gewertet: Die Spieler des verlegten Spiels "
              "gelten als ohne Note, die Nachrückregel greift, der Report trägt den Vermerk „vorläufig“. Nach dem "
              "Nachholspiel wird der Spieltag mit den dann vorliegenden Noten neu berechnet. Die vorläufige Wertung "
              "verschwindet, als hätte es sie nie gegeben; die Saisontabelle rechnet sich von selbst neu.")

# ---------------------------------------------------------------- Siebtes Buch
story += buch("Siebtes Buch – Der Winter", "Ein Fenster, halbe Preise, keine Erstattung")
story += para(22, "Das Transferfenster",
              "Es gibt ein Transferfenster: die Winterpause. Es läuft wie der Sommer – Vorschlagsrecht, Auktion, "
              "Mindestgebot 300.000 Euro.",
              "Eigene Spieler können für die Hälfte des ursprünglichen Kaufpreises verkauft werden. Erlös und Restbudget "
              "stehen für Neukäufe bereit.",
              "Verlässt ein Spieler im Winter die Bundesliga, gibt es keine Erstattung. Das Buch nennt das Pech, "
              "der Manager nennt es anders.")

# ---------------------------------------------------------------- Achtes Buch
story += buch("Achtes Buch – Das Auswertungstool", "Das Organ, das rechnet, und die Ordnung, in der es rechnet")
story += para(23, "Aufgabe",
              "Das Auswertungstool bestimmt nach jedem Spieltag die gewertete Elf jedes Managers, rechnet die fünf "
              "Kategorien, die Rangpunkte, die Spieltagssumme und die Saisontabelle. Es tut das nachvollziehbar: Für "
              "jeden Nachrücker und jede Strafnote steht im Report, warum.")
story += para(24, "Der Montag",
              "Die Aufstellungs-Mails werden gesammelt und dem Tool übergeben. Die Noten, Einsätze, Tore, Vorlagen und "
              "Gegentore kommen aus dem kicker-Spielschema jedes Spiels, die Elf des Tages von der kicker-Seite. Jeder "
              "Schritt schreibt eine Datei, die man öffnen, prüfen und korrigieren kann. Danach entsteht der Report.")
story += para(25, "Der Vorrang der Regel",
              "Weicht das Tool von der Regeldatei ab, gilt die Regeldatei, und das Tool wird geändert. Weicht die "
              "Regeldatei von diesem Buch ab, gilt die Regeldatei, und dieses Buch wird geändert. Weicht die Runde von "
              "beidem ab, wird diskutiert, bis eine neue Version der Regeldatei vorliegt.")

# ---------------------------------------------------------------- Schluss
story += buch("Schlussbestimmungen", "Änderungen, Auslegung, Inkrafttreten")
story += para(26, "Änderungen",
              "Regeländerungen werden in der Regeldatei mit Versionsnummer und Änderungsprotokoll festgehalten. Eine "
              "Regel, die nicht in der Regeldatei steht, ist keine Regel, sondern eine Meinung.")
story += para(27, "Auslegung",
              "Bei Unklarheiten wird gefragt, nicht geraten. Wer rät, zahlt beim nächsten Treffen die erste Runde; "
              "dieser Absatz ist nicht Teil der Regeldatei und wird auch nicht ausgewertet.")
story += para(28, "Inkrafttreten",
              "Dieses Buch gilt in der Fassung der Regeldatei v1.3 vom 10. September 2026 und tritt mit dem 2. Spieltag "
              "der Saison 2026/27 in Kraft, an dem die Hallodries mit 23,5 Punkten den ersten Spieltagssieg holten – "
              "was hiermit amtlich ist.")

story.append(Spacer(1, 10 * mm))
story.append(tabelle(
    ["Version", "Datum", "Was sich änderte"],
    [["1.0", "02.09.2026", "Grundregeln vollständig: Auktion, 3-5-2, Ersatzbank, fünf Kategorien, Winterfenster"],
     ["1.1", "02.09.2026", "Namen der sechs Manager"],
     ["1.2", "09.09.2026", "Nachrücker in Abgabereihenfolge, Strafgegentor bei null Minuten, Tippfehler-Regel, letzte gültige Aufstellung, Elfmeter und Eigentor, Spieltagssiege, Auswertungstool"],
     ["1.3", "10.09.2026", "Spieltagssiege als Tiebreaker, Nachholspiele, Vorlage beim Elfmeter nach kicker"]],
    [18 * mm, 24 * mm, 128 * mm]))
story.append(Spacer(1, 8 * mm))
story.append(P("Gegeben zu Zeiten des zweiten Spieltags, im Jahr des Herrn 2026, unter dem Siegel der Formation.", st_small))

doc = BaseDocTemplate("/mnt/user-data/outputs/Das_Goldene_Buch_2026-27.pdf", pagesize=A4,
                      title="Das Goldene Buch des Kicker-Managerspiels 2026/27", author="Die sechs Manager",
                      leftMargin=RAND, rightMargin=RAND, topMargin=RAND, bottomMargin=RAND)
frame_titel = Frame(RAND, RAND, W - 2 * RAND, H - 2 * RAND, id="titel")
frame_innen = Frame(RAND + 2 * mm, RAND + 2 * mm, W - 2 * RAND - 4 * mm, H - 2 * RAND - 4 * mm, id="innen")
doc.addPageTemplates([PageTemplate(id="titel", frames=[frame_titel], onPage=titelseite),
                      PageTemplate(id="innen", frames=[frame_innen], onPage=rahmen)])
doc.build(story)
print("ok")
