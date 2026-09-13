"""Dibujo sobre numpy, con antialiasing de verdad.

En el Garmin las agujas se dibujaban con `fillPolygon` y el antialiasing que
quisiera darnos el reloj. Aquí no hay prisa: casi todo se dibuja **una sola vez
al arrancar**, así que se puede rasterizar a 4x y reducir.

`sup` es el supermuestreo, y conviene elegirlo:

* **4** para polígonos y círculos — es lo que quita los dientes de sierra;
* **1** para texto — FreeType ya rasteriza los glifos con antialiasing propio,
  así que supermuestrear texto es pagar 16 veces por nada. Y esto importa: las
  capas de texto se redibujan en marcha, no al arrancar.
"""

import os
from collections import namedtuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

TIPOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tipos")

_cache_tipo = {}

# Un tipo NO es una fuente ya cargada, sino la intención de usar ese fichero a
# ese cuerpo. La fuente de verdad la resuelve el lienzo, que es el único que
# sabe a cuántos aumentos está dibujando.
#
# Parece un rodeo y no lo es: si `tipo()` devolviera una ImageFont ya hecha, en
# un lienzo a 4 aumentos las coordenadas se multiplicarían por 4 y la fuente
# no, así que el texto saldría a la cuarta parte. Es un fallo que no avisa —
# sale una esfera con las letras pequeñas, no una excepción.
Tipo = namedtuple("Tipo", "fichero cuerpo")


def tipo(fichero, cuerpo):
    return Tipo(fichero, float(cuerpo))


def _fuente(t, sup):
    clave = (t.fichero, round(t.cuerpo * sup))
    if clave not in _cache_tipo:
        _cache_tipo[clave] = ImageFont.truetype(
            os.path.join(TIPOS, t.fichero), clave[1])
    return _cache_tipo[clave]


def _rgba(c, a=255):
    """0xRRGGBB -> (r, g, b, a)."""
    return ((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF, int(a))


class Lienzo:
    """Un rectángulo que se dibuja a `sup` aumentos y se reduce al final."""

    def __init__(self, ancho, alto=None, fondo=None, sup=4):
        self.ancho = int(ancho)
        self.alto = int(alto if alto is not None else ancho)
        self.sup = sup
        self.im = Image.new("RGBA", (self.ancho * sup, self.alto * sup),
                            _rgba(fondo) if fondo is not None else (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def poligono(self, pts, color, alfa=255):
        s = self.sup
        self.d.polygon([(x * s, y * s) for x, y in pts], fill=_rgba(color, alfa))

    def circulo(self, cx, cy, r, color, alfa=255):
        s = self.sup
        self.d.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s],
                       fill=_rgba(color, alfa))

    def anillo(self, cx, cy, r, grosor, color, alfa=255, desde=None, hasta=None):
        """Círculo o arco hueco. Los ángulos van en grados horarios desde las
        12, que es como piensa un reloj; PIL los quiere desde las 3."""
        s = self.sup
        caja = [(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s]
        if desde is None:
            self.d.ellipse(caja, outline=_rgba(color, alfa), width=max(1, int(grosor * s)))
        else:
            self.d.arc(caja, desde - 90, hasta - 90, fill=_rgba(color, alfa),
                       width=max(1, int(grosor * s)))

    def linea(self, x1, y1, x2, y2, grosor, color, alfa=255):
        s = self.sup
        self.d.line([x1 * s, y1 * s, x2 * s, y2 * s], fill=_rgba(color, alfa),
                    width=max(1, int(grosor * s)))

    def texto(self, x, y, txt, fuente, color, alfa=255, anclaje="mm"):
        """`anclaje` es el de Pillow: 'mm' centrado, 'lm' pegado por la
        izquierda, los dos con la vertical al medio de la equis."""
        self.d.text((x * self.sup, y * self.sup), txt,
                    font=_fuente(fuente, self.sup),
                    fill=_rgba(color, alfa), anchor=anclaje)

    def ancho_de(self, txt, fuente):
        c = self.d.textbbox((0, 0), txt, font=_fuente(fuente, self.sup),
                            anchor="lm")
        return (c[2] - c[0]) / float(self.sup)

    def array(self):
        """Reduce a tamaño final y devuelve (alto, ancho, 4) uint8 RGBA.

        La reducción va sobre **alfa premultiplicado**. Si no, los píxeles
        transparentes (que por dentro son negros) tiñen de negro el borde de
        cada forma al promediarlos con los opacos. Sobre fondo negro no se
        notaría, pero no todas las esferas lo son.
        """
        a = np.asarray(self.im, dtype=np.float32)
        if self.sup > 1:
            al = a[:, :, 3:4] / 255.0
            pm = np.concatenate([a[:, :, :3] * al, a[:, :, 3:4]], axis=2)
            s = self.sup
            pm = pm.reshape(self.alto, s, self.ancho, s, 4).mean(axis=(1, 3))
            al = pm[:, :, 3:4] / 255.0
            rgb = np.divide(pm[:, :, :3], al, out=np.zeros_like(pm[:, :, :3]),
                            where=al > 1e-4)
            a = np.concatenate([rgb, pm[:, :, 3:4]], axis=2)
        return np.ascontiguousarray(np.clip(a + 0.5, 0, 255).astype(np.uint8))


def aguja(lado, largo, cola, w_cola, w_cuerpo, k_hombro, tinta, bisel=None):
    """Una aguja apuntando a las 12, con el pivote en el centro del lienzo.

    Cinco vértices, igual que en el Garmin: punta · hombro izq · cola izq ·
    cola der · hombro der. De la cola al hombro apenas estrecha; del hombro a
    la punta se afila. El `bisel` es la mitad iluminada, que es lo que finge
    el volumen cuando no hay degradados.
    """
    c = lado / 2.0
    ht, hb = w_cola / 2.0, w_cuerpo / 2.0
    by = c + cola                 # extremo de la cola (hacia abajo)
    sy = c - largo * k_hombro     # hombro

    pts = [(c, c - largo), (c + hb, sy), (c + ht, by), (c - ht, by), (c - hb, sy)]

    lz = Lienzo(lado)
    lz.poligono(pts, tinta)
    if bisel is not None:
        lz.poligono([pts[0], pts[1], pts[2], (c, by)], bisel)
    return lz.array()


def disco_blando(lado, dureza=0.62):
    """Un disco blanco con el borde desvanecido, pensado para teñirlo luego.

    Los orbes de `pulso` y `orbita` son todos **el mismo disco**: cambia el
    color, el brillo y el tamaño, pero no la forma. Con uno solo, teñido y
    escalado por la tarjeta, no hay que rasterizar cientos — que es justo lo
    que haría inviable animar esto en una Pi Zero.
    """
    r = np.linspace(-1.0, 1.0, lado, dtype=np.float32)
    x, y = np.meshgrid(r, r)
    d = np.hypot(x, y)
    a = np.clip((1.0 - d) / max(1e-3, 1.0 - dureza), 0.0, 1.0)
    a = (a * a * (3 - 2 * a) * 255).astype(np.uint8)      # suavizado
    return np.ascontiguousarray(
        np.dstack([np.full((lado, lado), 255, np.uint8)] * 3 + [a]))


def hsv(h, s, v):
    """HSV -> 0xRRGGBB. Portado tal cual del Monkey C de `Pulso`."""
    h = h - int(h)
    if h < 0:
        h += 1.0
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    r, g, b = [(v, t, p), (q, v, p), (p, v, t),
               (p, q, v), (t, p, v), (v, p, q)][i]
    return (int(r * 255) << 16) | (int(g * 255) << 8) | int(b * 255)
