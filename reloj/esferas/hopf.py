"""La fibración de Hopf — un reloj de eslabones.

De la galería de <https://elliptic-curves.art> (`hopf-torus`, `hopf-interval`).

La fibración de Hopf manda la esfera de tres dimensiones `S³` a la de dos,
`S²`, y **cada punto de `S²` es un círculo entero** de `S³`. Proyectados a
nuestro espacio esos círculos siguen siendo círculos redondos, y tienen una
propiedad que no se cansa uno de mirar: **dos cualesquiera están enlazados, y
exactamente una vez**. Nunca sueltos, nunca dos veces.

De ahí sale el reloj, y no es una metáfora:

    la HORA   es un punto de S², y su círculo
    el MINUTO es otro punto de S², y su círculo

Dos puntos distintos, dos círculos **encadenados**. La hora y el minuto no
están uno al lado del otro: están enlazados, y girando. Detrás, las fibras de
cuatro paralelos de `S²` — cada paralelo da un toro de círculos anidados, que
es la imagen clásica.

`h(z1, z2) = (2·z1·conj(z2), |z1|² - |z2|²)`, y la fibra sobre el punto de
coordenadas esféricas `(t, f)` es

    z1 = cos(t/2)·e^(i·s)      z2 = sin(t/2)·e^(i(s - f))      s en [0, 2pi)
"""

import math

import numpy as np

from ..camara import Camara
from ..esfera import Esfera, Trazo
from ..lienzo import Lienzo, hsv_arr, tipo

# Paralelos de S² que dan las fibras de fondo, y cuántas por paralelo.
#
# Ninguno se acerca a `pi`: la fibra sobre el polo sur pasa por el punto desde
# el que se proyecta, así que sale disparada al infinito y se ve como una recta
# que cruza la pantalla. El radio de la fibra es sqrt((1+sin(t/2))/(1-sin(t/2)))
# y con t = 1.22 vale 2.2. Más allá los círculos exteriores se comen la
# escena: barren toda la pantalla y tapan los eslabones del reloj.
# Cuatro paralelos con ocho fibras cada uno salían como una maraña: había
# círculos por todas partes y ninguno se leía como parte de nada. Lo que hace
# ver los toros anidados no es la variedad de tamaños sino tener **bastantes
# fibras en cada paralelo** — con catorce, el toro se insinúa solo.
PARALELOS = (0.42, 0.82, 1.22)
POR_PARALELO = 14
PUNTOS = 112

TONOS = {0.42: 0.55, 0.82: 0.72, 1.22: 0.88}   # cian, violeta, magenta

T_HORA = 0.62       # el paralelo de la hora: círculo pequeño, va por dentro
T_MINUTO = 1.05     # el del minuto: mayor, va por fuera

VUELTA = 300.0      # la cámara da una vuelta cada cinco minutos
CABECEO = 97.0      # y cabecea cada noventa y siete segundos


def fibra(t, f, n=PUNTOS):
    """El círculo de `S³` sobre el punto `(t, f)` de `S²`, ya en nuestro
    espacio por proyección estereográfica desde `(0,0,0,1)`."""
    s = np.linspace(0.0, 2 * math.pi, n)
    a, b = math.cos(t / 2), math.sin(t / 2)
    x0, x1 = a * np.cos(s), a * np.sin(s)
    x2, x3 = b * np.cos(s - f), b * np.sin(s - f)
    d = 1.0 - x3
    return np.stack([x0 / d, x1 / d, x2 / d], axis=1)


class Hopf(Esfera):
    """Fibración de Hopf: la hora y el minuto, encadenados."""

    NOMBRE = "hopf"
    POR_SEGUNDO = 8
    # El cabeceo, como atributos para que una subclase pueda subir el ojo sin
    # copiar `_calcular` entera.
    CAB_BASE = 0.42
    CAB_VAIVEN = 0.26

    def __init__(self, lado):
        Esfera.__init__(self, lado)
        self.cam = Camara(lado, distancia=4.6, foco=2.7, zoom=0.70)
        self.f_hora = tipo("RobotoMono-Bold.ttf", lado * 46 / 454.0)
        self.f_pie = tipo("RobotoMono-Bold.ttf", lado * 17 / 454.0)
        # Las fibras de fondo no dependen de la hora: se calculan una vez y
        # solo se vuelven a proyectar cuando la cámara se mueve.
        self._fondo = [(t, fibra(t, 2 * math.pi * k / POR_PARALELO))
                       for t in PARALELOS for k in range(POR_PARALELO)]
        self._clave = None
        self._trazos = ()

    def trazos(self, t):
        clave = round(t * self.POR_SEGUNDO)
        if clave != self._clave:
            self._clave = clave
            self._trazos = self._calcular(clave / float(self.POR_SEGUNDO))
        return self._trazos

    def _calcular(self, t):
        self.cam.mirar(2 * math.pi * t / VUELTA,
                       self.CAB_BASE + self.CAB_VAIVEN
                       * math.sin(2 * math.pi * t / CABECEO))
        g = self.lado / 454.0
        fuera = []

        for lat, pts in self._fondo:
            xy, d = self.cam(pts)
            cerca = self.cam.niebla(d, 1.6, 2.2)
            # El tono lo da el paralelo: así se ven los toros anidados como
            # capas y no como una maraña de círculos sueltos.
            # Un tono claramente distinto por paralelo. Con los tres tonos
            # juntos no se distinguía una capa de otra y todo era violeta.
            col = hsv_arr(TONOS[lat], 0.70, 0.10 + 0.62 * cerca)
            fuera.append(Trazo(xy, col, 1.4 * g, 150))

        # Los dos eslabones. Están enlazados por construcción: dos fibras sobre
        # puntos distintos de S² tienen número de enlace 1, siempre.
        for lat, ang, tono in self._eslabones(t):
            xy, d = self.cam(fibra(lat, ang, 220))
            cerca = self.cam.niebla(d, 1.3, 2.2)
            col = hsv_arr(np.full(220, tono), 0.82, 0.28 + 0.72 * cerca)
            fuera.append(Trazo(xy, col, 6.0 * g, 60))     # halo
            fuera.append(Trazo(xy, col, 2.3 * g, 255))    # eslabón
        return fuera

    def _eslabones(self, t):
        """Sobre qué puntos de S² van las fibras de la hora y del minuto.

        Aparte para que una subclase pueda moverlas sin copiar `_calcular`.
        """
        return ((T_HORA, 2 * math.pi * (t / 3600.0 % 12.0) / 12.0, 0.09),
                (T_MINUTO, 2 * math.pi * (t / 60.0 % 60.0) / 60.0, 0.47))

    def capa(self, t):
        lz = Lienzo(self.lado, sup=1)
        lz.texto(self.lado / 2, self.lado * 0.885,
                 "%d:%02d" % (int(t // 3600) % 12 or 12, int(t // 60) % 60),
                 self.f_hora, 0xF2F5F8, 235)
        lz.texto(self.lado / 2, self.lado * 0.945,
                 "S3 -> S2   ·   dos fibras, un enlace",
                 self.f_pie, 0x6E86A0)
        return int(t) // 60, lz.array()


ESFERA = Hopf
