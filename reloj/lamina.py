"""La misma esfera, compuesta con Pillow y guardada en PNG.

Sirve para verla sin pantalla —en un servidor, o en una sesión de trabajo— y
para comparar varias horas o varias esferas de un vistazo. Usa exactamente los
mismos arrays y el mismo orden de pintado que la salida por SDL.
"""

import numpy as np
from PIL import Image


def _teñir(im, color, alfa):
    if color is not None:
        r, g, b = (color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF
        px = np.asarray(im, dtype=np.uint16).copy()
        px[:, :, 0] = px[:, :, 0] * r // 255
        px[:, :, 1] = px[:, :, 1] * g // 255
        px[:, :, 2] = px[:, :, 2] * b // 255
        im = Image.fromarray(px.astype(np.uint8), "RGBA")
    if alfa < 255:
        a = im.getchannel("A").point(lambda v: v * alfa // 255)
        im = im.copy()
        im.putalpha(a)
    return im


def componer(Clase, lado, t):
    esf = Clase(lado)
    f = esf.fondo()
    base = (Image.fromarray(f, "RGB").convert("RGBA") if f is not None
            else Image.new("RGBA", (lado, lado), (0, 0, 0, 255)))
    piezas = esf.piezas()

    def poner(p):
        im = Image.fromarray(piezas[p.pieza], "RGBA")
        if p.escala != 1.0:
            n = (max(1, int(im.width * p.escala)), max(1, int(im.height * p.escala)))
            im = im.resize(n, Image.LANCZOS)
        if p.grados:
            im = im.rotate(-p.grados, resample=Image.BICUBIC, expand=False)
        im = _teñir(im, p.color, p.alfa)
        base.alpha_composite(im, (int(p.x - im.width / 2.0),
                                  int(p.y - im.height / 2.0)))

    for p in esf.detras(t):
        poner(p)
    c = esf.capa(t)
    if c is not None:
        base.alpha_composite(Image.fromarray(c[1], "RGBA"))
    for p in esf.cuadro(t):
        poner(p)

    return base.convert("RGB")


def hoja(trozos, columnas=2, hueco=20, fondo=(18, 18, 18)):
    """Varias imágenes en una rejilla, para compararlas de un vistazo."""
    w = max(im.width for im in trozos)
    h = max(im.height for im in trozos)
    filas = (len(trozos) + columnas - 1) // columnas
    out = Image.new("RGB", (columnas * w + (columnas - 1) * hueco,
                            filas * h + (filas - 1) * hueco), fondo)
    for k, im in enumerate(trozos):
        out.paste(im, ((k % columnas) * (w + hueco), (k // columnas) * (h + hueco)))
    return out


def reloj_a_segundos(txt):
    """'10:09' o '10:09:30' -> segundos desde medianoche."""
    p = [float(x) for x in txt.split(":")]
    while len(p) < 3:
        p.append(0.0)
    return p[0] * 3600 + p[1] * 60 + p[2]
