"""Bordada — la ley de grupo sobre `F_p`, bordada en el toro que es su tablero.

Primero lo intenté por lo obvio: pegar la cinta impresa **a lo largo del
recorrido**, como en `rotulada`. No se puede, y el número lo dice. El recorrido
son sesenta cuerdas de doscientos píxeles cada una, así que a cada cuerda le
toca un sesentavo de la etiqueta estirado cinco veces —hasta catorce en la
peor— y lo que sale es un destello blanco. Anclando las doce horas en sus
puntos del grupo y repartiendo el resto por longitud de arco tampoco: los
doceavos del recorrido tienen longitudes que se llevan **44 a 1**, así que unas
horas se solapan y otras se van al otro extremo. No hay reparametrización que
lo arregle; el soporte es el que está mal.

Y el soporte bueno estaba delante. **El tablero es un toro.** Los puntos de la
curva viven en `F_p × F_p`, y eso son dos círculos: `x` módulo `p` e `y` módulo
`p`. El cuadrado plano de `finita` es la mentira cómoda — corta el toro por dos
sitios y hace que las cuerdas se acaben en los bordes. Enrollado, **las cuerdas
dan la vuelta**: una recta del plano afín sobre `F_p` es una geodésica cerrada,
y aquí se la ve serpentear por la superficie y volver por el otro lado.

Sobre esa superficie la etiqueta se pega como en `rosca`, y ahí sí se lee: el
ángulo alrededor del donut es `x/p`, o sea el dial, y las doce horas caen
repartidas por igual.

`finita` se queda como está: esto es una esfera aparte.
"""

import math

import numpy as np

from ..banda import de_lejos_a_cerca, etiqueta, malla_toro, tinte_niebla
from ..camara import Camara
from ..esfera import Malla, Trazo
from ..lienzo import Lienzo, hsv_arr, tipo
from .eliptica import PRIMOS, Finita, orbita

R_DONUT = 1.00
R_TUBO = 0.42
CAMARA, FOCO, ZOOM = 3.55, 2.70, 0.58

VUELTA = 240.0      # la cámara, como en `toro`
CABECEO = 90.0
CAB_BASE, CAB_VAIVEN = 1.05, 0.20

TEX_ANCHO = 2048
TEX_ALTO = 136
V0, V1 = 0.0, 1.30
NU, NV = 128, 8

POR_CUERDA = 12     # muestras en que se parte cada cuerda al enrollarla


def _en_toro(u, v):
    ancho = R_DONUT + R_TUBO * np.cos(v)
    return np.stack([ancho * np.cos(u), ancho * np.sin(u),
                     R_TUBO * np.sin(v)], axis=-1)


def _enrollar(pts, p):
    """El recorrido del tablero, subido al toro.

    Cada cuerda se levanta al **recubridor universal** por el camino más corto:
    de las infinitas maneras de ir de `x1` a `x2` módulo `p` se toma la que
    menos da la vuelta. Es lo que hace que la cuerda cruce el borde del tablero
    y siga por el otro lado en vez de cortarse ahí, que es lo que de verdad
    hace una recta sobre `F_p`.
    """
    d = pts[1:] - pts[:-1]
    d = (d + p / 2.0) % p - p / 2.0          # el salto más corto, con signo
    w = np.linspace(0.0, 1.0, POR_CUERDA, endpoint=False)[None, :, None]
    cam = (pts[:-1, None, :] + d[:, None, :] * w).reshape(-1, 2)
    cam = np.vstack([cam, pts[-1:]])
    return _en_toro(2 * math.pi * cam[:, 0] / p, 2 * math.pi * cam[:, 1] / p)


class Bordada(Finita):
    """El recorrido de la ley de grupo, bordado sobre el toro del tablero."""

    NOMBRE = "bordada"
    POR_SEGUNDO = 8

    def __init__(self, lado):
        Finita.__init__(self, lado)
        self.cam = Camara(lado, CAMARA, FOCO, ZOOM)
        self.f_reloj = tipo("RobotoMono-Bold.ttf", lado * 46 / 454.0)
        self._pts, self._uv, self._cuadros = malla_toro(
            R_DONUT, R_TUBO, V0, V1, NU, NV)
        self._cual = None
        self._hilo = None
        self._clave = None
        self._trazos = ()

    def texturas(self):
        return {"horas": etiqueta(TEX_ANCHO, TEX_ALTO)}

    # ---------- el recorrido, una vez por minuto ----------
    def _recorrido(self, t):
        hora, minuto = int(t // 3600) % 24, int(t // 60) % 60
        if self._cual != (hora, minuto):
            self._cual = (hora, minuto)
            p = PRIMOS[hora % 12]
            pts = orbita(p, minuto, 1)
            self._hilo = None if len(pts) < 2 else _enrollar(pts, p)
        return self._hilo

    # ---------- lo que se dibuja ----------
    def trazos(self, t):
        clave = round(t * self.POR_SEGUNDO)
        if clave != self._clave:
            self._clave = clave
            self._trazos = self._calcular(clave / float(self.POR_SEGUNDO))
        return self._trazos

    def _calcular(self, t):
        self.cam.mirar(2 * math.pi * t / VUELTA,
                       CAB_BASE + CAB_VAIVEN * math.sin(2 * math.pi * t / CABECEO))
        hilo = self._recorrido(t)
        if hilo is None:
            return ()
        xy, d = self.cam(hilo)
        # El tono avanza con el recorrido: se ve por dónde empezó y por dónde
        # va, que es la mitad de la gracia. El brillo lo pone la profundidad.
        u = np.linspace(0.0, 1.0, len(xy))
        col = hsv_arr(0.48 + 0.34 * u, 0.68,
                      0.34 + 0.66 * self.cam.niebla(d, 1.3, 1.9))
        g = self.lado / 454.0
        return (Trazo(xy, col, 4.4 * g, 50),
                Trazo(xy, col, 1.6 * g, 230))

    def mallas(self, t):
        xy, d = self.cam(self._pts)
        return (Malla("horas", xy, self._uv,
                      de_lejos_a_cerca(self._cuadros, xy, d),
                      tinte_niebla(self.cam, d, 1.2, 2.4, 0.42), 255),)

    def capa(self, t):
        hora, minuto = int(t // 3600) % 24, int(t // 60) % 60
        lz = Lienzo(self.lado, sup=1)
        lz.texto(self.lado / 2, self.lado * 0.885,
                 "%d:%02d" % (hora % 12 or 12, minuto), self.f_reloj,
                 0xF2F5F8, 235)
        lz.texto(self.lado / 2, self.lado * 0.945,
                 "el tablero F%d x F%d es un toro"
                 % (PRIMOS[hora % 12], PRIMOS[hora % 12]),
                 self.f_pie, 0x8DA2B8)
        return int(t // 60), lz.array()


ESFERA = Bordada
