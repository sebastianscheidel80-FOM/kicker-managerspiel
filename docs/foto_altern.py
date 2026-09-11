# -*- coding: utf-8 -*-
"""Verfremdet ein Foto zu einer alten Schwarz-Weiß-Aufnahme (leichter Sepia-Stich, Körnung, Vignette, Kratzer, Papierrand).

Aufruf: python docs/foto_altern.py <eingabe.jpg> <ausgabe.jpg>
"""
import sys
import random

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps


def altern(quelle: str, ziel: str, breite: int = 1600, seed: int = 1997) -> None:
    rnd = random.Random(seed)
    img = Image.open(quelle).convert("RGB")
    img = ImageOps.exif_transpose(img)
    img.thumbnail((breite, breite))

    # 1. Schwarz-Weiß mit weicherem Kontrast und leichter Unschärfe (alte Optik)
    g = ImageOps.grayscale(img)
    g = ImageEnhance.Contrast(g).enhance(0.82)
    g = ImageEnhance.Brightness(g).enhance(1.05)
    g = g.filter(ImageFilter.GaussianBlur(0.9))
    g = ImageOps.autocontrast(g, cutoff=1)

    # 2. Körnung
    a = np.asarray(g).astype(np.float32)
    noise = np.random.default_rng(seed).normal(0, 11, a.shape)
    a = np.clip(a + noise, 0, 255)

    # 3. Vignette (Ränder dunkler, wie bei alten Objektiven)
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w]
    dx = (xx - w / 2) / (w / 2)
    dy = (yy - h / 2) / (h / 2)
    r = np.sqrt(dx ** 2 + dy ** 2)
    vign = np.clip(1 - 0.55 * np.clip(r - 0.45, 0, None) ** 1.6, 0.35, 1)
    a = a * vign

    # 4. Leichte Ausbleichung (Schwarz wird nie ganz schwarz, Weiß nie ganz weiß)
    a = 22 + a * (228 - 22) / 255

    g = Image.fromarray(a.astype(np.uint8), "L")

    # 5. Kratzer und Staub
    d = ImageDraw.Draw(g)
    for _ in range(14):
        x0 = rnd.randint(0, w)
        y0 = rnd.randint(0, h)
        length = rnd.randint(h // 6, h // 2)
        x1 = x0 + rnd.randint(-30, 30)
        y1 = min(h, y0 + length)
        d.line((x0, y0, x1, y1), fill=rnd.randint(190, 235), width=1)
    for _ in range(260):
        x = rnd.randint(0, w - 1)
        y = rnd.randint(0, h - 1)
        d.ellipse((x, y, x + rnd.randint(1, 3), y + rnd.randint(1, 3)), fill=rnd.choice((40, 60, 215, 230)))

    # 6. Sepia-Stich: dezent, damit es nach vergilbtem Silbergelatine-Abzug aussieht
    sepia = ImageOps.colorize(g, black=(28, 22, 16), white=(238, 226, 200), mid=(128, 112, 88))

    # 7. Papierrand mit leicht unregelmäßiger Kante
    rand = int(w * 0.035)
    papier = Image.new("RGB", (w + 2 * rand, h + 2 * rand), (236, 226, 204))
    pd = ImageDraw.Draw(papier)
    for i in range(0, papier.width, 3):
        pd.line((i, 0, i, rnd.randint(0, 3)), fill=(210, 198, 172))
        pd.line((i, papier.height - rnd.randint(1, 4), i, papier.height), fill=(210, 198, 172))
    papier.paste(sepia, (rand, rand))
    papier = papier.filter(ImageFilter.GaussianBlur(0.3))
    papier.save(ziel, quality=88)


if __name__ == "__main__":
    altern(sys.argv[1], sys.argv[2])
    print("ok")
