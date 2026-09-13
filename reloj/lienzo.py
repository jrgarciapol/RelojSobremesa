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

import math
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

        Y va **por bandas**. Convertir el lienzo entero a float32 de golpe
        parece lo natural y es justo lo que no cabe: a 1080 px con `sup=4` el
        lienzo interno son 4320x4320, o sea 300 MB por copia y unos 900 MB de
        pico entre las intermedias. La Pi Zero 2 W tiene **512 MB**, así que
        no es que fuera lento: es que no arrancaba. Por bandas el pico no
        depende del tamaño del dial.
        """
        s = self.sup
        if s == 1:
            return np.ascontiguousarray(np.asarray(self.im, dtype=np.uint8))

        out = np.empty((self.alto, self.ancho, 4), np.uint8)
        # Bandas de unos 8 MB por intermedia, salga el dial del tamaño que salga.
        filas = max(1, int(8e6 / (self.ancho * s * s * 16)))

        for y0 in range(0, self.alto, filas):
            y1 = min(self.alto, y0 + filas)
            a = np.asarray(self.im.crop((0, y0 * s, self.ancho * s, y1 * s)),
                           dtype=np.float32)
            al = a[:, :, 3:4] / 255.0
            pm = np.concatenate([a[:, :, :3] * al, a[:, :, 3:4]], axis=2)
            pm = pm.reshape(y1 - y0, s, self.ancho, s, 4).mean(axis=(1, 3))
            al = pm[:, :, 3:4] / 255.0
            rgb = np.divide(pm[:, :, :3], al, out=np.zeros_like(pm[:, :, :3]),
                            where=al > 1e-4)
            out[y0:y1, :, :3] = np.clip(rgb + 0.5, 0, 255).astype(np.uint8)
            out[y0:y1, :, 3] = np.clip(pm[:, :, 3] + 0.5, 0, 255).astype(np.uint8)
        return out

    def arco(self, cx, cy, r, grosor, color, desde=0.0, hasta=360.0, alfa=255):
        """Un arco con antialiasing **calculado**, no supermuestreado.

        PIL no suaviza `arc`, así que la única forma de que el arco de Rosa
        saliera limpio era supermuestrear la capa entera — y esa capa se
        redibuja cada minuto. Costaba 0,7 s por minuto en un portátil, o sea
        unos siete segundos de congelación en la Pi. Cada minuto.

        Aquí se calcula la cobertura de cada píxel a partir de su distancia al
        anillo y su ángulo. Sale mejor que supermuestreando (la rampa es
        exacta, no promediada) y permite bajar toda la capa a `sup=1`.
        """
        n_y, n_x = self.alto * self.sup, self.ancho * self.sup
        s = self.sup
        yy, xx = np.mgrid[0:n_y, 0:n_x].astype(np.float32)
        dx, dy = xx - cx * s, yy - cy * s
        d = np.hypot(dx, dy)

        # Rampa de un píxel a cada lado del canto: eso es el antialiasing.
        cob = np.clip(grosor * s / 2.0 - np.abs(d - r * s) + 0.5, 0.0, 1.0)

        if (hasta - desde) < 360.0:
            ang = np.degrees(np.arctan2(dx, -dy)) % 360.0
            margen = np.degrees(1.0 / max(1.0, r * s))   # un píxel, en grados
            dentro = np.clip((ang - desde) / margen, 0.0, 1.0) \
                * np.clip((hasta - ang) / margen, 0.0, 1.0)
            cob *= dentro

        capa = np.zeros((n_y, n_x, 4), np.uint8)
        capa[:, :, 0] = (color >> 16) & 0xFF
        capa[:, :, 1] = (color >> 8) & 0xFF
        capa[:, :, 2] = color & 0xFF
        capa[:, :, 3] = (cob * alfa).astype(np.uint8)
        self.im.alpha_composite(Image.fromarray(capa, "RGBA"))


def aguja(largo, cola, w_cola, w_cuerpo, k_hombro, tinta, bisel=None, margen=2):
    """Una aguja apuntando a las 12. Devuelve (array, pivote).

    Cinco vértices, igual que en el Garmin: punta · hombro izq · cola izq ·
    cola der · hombro der. De la cola al hombro apenas estrecha; del hombro a
    la punta se afila. El `bisel` es la mitad iluminada, que es lo que finge
    el volumen cuando no hay degradados.

    El lienzo es **justo la aguja**, no el dial entero. Parecía natural darle
    el tamaño del dial y poner el pivote en el centro —así girarla es girar
    sobre el centro y no hay nada que calcular— pero una aguja ocupa el 2% de
    ese cuadrado: a 1080 px se rasterizaban 18 millones de píxeles para dibujar
    unos cientos de miles, y las tres agujas de Disco costaban 3,9 s de los
    5,1 del arranque.

    Ahora el sprite es una tira estrecha y el pivote va donde toca. SDL admite
    un centro de giro arbitrario (`SDL_RenderCopyEx`), así que no se pierde
    nada.
    """
    ancho = int(math.ceil(max(w_cola, w_cuerpo))) + 2 * margen
    alto = int(math.ceil(largo + cola)) + 2 * margen
    cx = ancho / 2.0
    cy = margen + largo           # el pivote: la punta queda `largo` más arriba
    ht, hb = w_cola / 2.0, w_cuerpo / 2.0
    by = cy + cola                # extremo de la cola (hacia abajo)
    sy = cy - largo * k_hombro    # hombro

    pts = [(cx, cy - largo), (cx + hb, sy), (cx + ht, by),
           (cx - ht, by), (cx - hb, sy)]

    lz = Lienzo(ancho, alto)
    lz.poligono(pts, tinta)
    if bisel is not None:
        lz.poligono([pts[0], pts[1], pts[2], (cx, by)], bisel)
    return lz.array(), (cx, cy)


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
