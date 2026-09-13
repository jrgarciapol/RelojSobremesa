"""El toro — la curva elíptica como lo que de verdad es.

Las dos esferas anteriores dibujaban el lugar REAL de `y² = x³ + ax + b`: una
curva en un plano. Pero eso es una sombra. Los puntos **complejos** de una
curva elíptica forman `C/L`, y eso es un **toro**: la superficie que se ve en
las imágenes de <https://elliptic-curves.art>.

Y un toro tiene exactamente dos ángulos. La hora y el minuto.

Así que aquí el reloj no está *sobre* la superficie, encima de un fondo bonito:
el reloj **es** la superficie. La posición alrededor del donut es la hora, la
posición alrededor del tubo es el minuto, y el punto donde se cruzan los dos
aros es el instante.

La retícula es **hexagonal**, no cuadrada: `L = Z + tZ` con `t = exp(i·pi/3)`.
Eso da tres familias de rectas a 60 grados en vez de dos a 90, que es el tejido
triangular de sus `weierstrass-hex`. Cuesta lo mismo y se parece mucho más.
"""

import math

import numpy as np

from ..esfera import Esfera, Trazo
from ..lienzo import Lienzo, hsv_arr, tipo

R_DONUT = 1.00      # radio del agujero al centro del tubo
R_TUBO = 0.42
CAMARA = 3.55       # distancia del ojo
FOCO = 2.70
# El toro mide 1.42 de ancho (R_DONUT + R_TUBO), pero lo que decide el encuadre
# no es esa medida sino la perspectiva: la parte que se acerca a la cámara sale
# aumentada. Calculado sobre la distancia media se salía por los lados, así que
# el valor está puesto a ojo sobre el resultado.
ZOOM = 0.66

MALLA = 11          # rectas por familia
PUNTOS = 84         # muestras por recta

# La cámara da una vuelta cada cuatro minutos y cabecea cada noventa segundos.
# Son tiempos primos entre sí a propósito: el vaivén no se repite igual dos
# veces seguidas y la superficie no parece un GIF en bucle.
VUELTA = 240.0
CABECEO = 90.0


def _en_toro(u, v):
    """(u, v) en radianes -> punto del toro. `u` recorre el donut, `v` el tubo."""
    ancho = R_DONUT + R_TUBO * np.cos(v)
    return np.stack([ancho * np.cos(u), ancho * np.sin(u),
                     R_TUBO * np.sin(v)], axis=-1)


class Toro(Esfera):
    """La superficie de la curva elíptica, girando, con la hora encima."""

    NOMBRE = "toro"

    TEJIDO = 0.66       # brillo de la malla
    # La cámara da una vuelta en cuatro minutos: 1,5 grados por segundo. A ocho
    # recálculos por segundo eso son pasos de 0,19 grados, imperceptibles, y el
    # coste medio baja a 1 ms (unos 10 en la Pi, un tercio del fotograma).
    POR_SEGUNDO = 8

    def __init__(self, lado):
        Esfera.__init__(self, lado)
        self.f_hora = tipo("RobotoMono-Bold.ttf", lado * 46 / 454.0)
        self.f_pie = tipo("RobotoMono-Bold.ttf", lado * 17 / 454.0)
        self._clave = None
        self._trazos = ()
        self._malla = self._tejer()

    # ---------- la retícula hexagonal, en coordenadas (u, v) ----------
    def _tejer(self):
        """Las tres familias de rectas de la retícula hexagonal.

        En una retícula `Z + tZ` con `t = exp(i·pi/3)` los tres vectores más
        cortos son `1`, `t` y `t - 1`. Dibujar solo dos familias da una malla
        de cuadros; con las tres sale el tejido triangular, que es lo que se ve
        en sus imágenes y lo que hace que la superficie se lea como superficie
        y no como alambre.
        """
        w = np.linspace(0.0, 1.0, PUNTOS)
        tau = 2 * math.pi
        fuera = []
        for k in range(MALLA):
            c = k / float(MALLA)
            fuera.append((tau * w, np.full(PUNTOS, tau * c)))          # 1
            fuera.append((np.full(PUNTOS, tau * c), tau * w))          # t
            fuera.append((tau * (c - w), tau * w))                     # t - 1
        return fuera

    # ---------- cámara ----------
    def _proyectar(self, p, giro, nada):
        """Rota, aplica perspectiva y devuelve (píxeles, profundidad)."""
        ca, sa = math.cos(giro), math.sin(giro)
        cb, sb = math.cos(nada), math.sin(nada)

        x1 = p[..., 0] * ca - p[..., 1] * sa
        y1 = p[..., 0] * sa + p[..., 1] * ca
        z1 = p[..., 2]

        y2 = y1 * cb - z1 * sb
        z2 = y1 * sb + z1 * cb

        d = y2 + CAMARA
        k = FOCO / np.maximum(d, 0.35) * ZOOM * self.r
        xy = np.stack([self.r + x1 * k, self.r - z2 * k], axis=-1)
        return xy.astype(np.float32), d

    def _tinte(self, v, d, brillo):
        """Color por vértice: el TONO lo da la vuelta al tubo, el BRILLO la
        profundidad. Sin z-buffer, la niebla es lo único que dice qué está
        delante — y basta, porque el ojo lee una malla que se apaga al fondo
        como una superficie curva."""
        cerca = np.clip((CAMARA + 1.0 - d) / 2.0, 0.0, 1.0) ** 1.7
        return hsv_arr(0.53 + 0.20 * (np.cos(v) * 0.5 + 0.5),
                       0.62, brillo * (0.10 + 0.90 * cerca))

    # ---------- lo que se dibuja ----------
    def trazos(self, t):
        clave = round(t * self.POR_SEGUNDO)
        if clave != self._clave:
            self._clave = clave
            self._trazos = self._calcular(clave / float(self.POR_SEGUNDO))
        return self._trazos

    def _calcular(self, t):
        giro = 2 * math.pi * (t / VUELTA)
        nada = 0.62 + 0.22 * math.sin(2 * math.pi * t / CABECEO)
        g = self.lado / 454.0
        fuera = []

        for u, v in self._malla:
            xy, d = self._proyectar(_en_toro(u, v), giro, nada)
            fuera.append(Trazo(xy, self._tinte(v, d, self.TEJIDO), 1.7 * g, 225))

        # Los dos aros del reloj. El de la HORA rodea el tubo y su posición
        # alrededor del donut se lee como una manecilla vista desde arriba; el
        # del MINUTO rodea el donut y su altura en el tubo dice el minuto.
        w = np.linspace(0.0, 2 * math.pi, 200)
        hora = (t / 3600.0 % 12.0) / 12.0 * 2 * math.pi
        minuto = (t / 60.0 % 60.0) / 60.0 * 2 * math.pi

        for u, v, tono in ((np.full(200, hora), w, 0.10),
                           (w, np.full(200, minuto), 0.47)):
            xy, d = self._proyectar(_en_toro(u, v), giro, nada)
            cerca = np.clip((CAMARA + 1.0 - d) / 2.0, 0.0, 1.0) ** 1.4
            col = hsv_arr(np.full(200, tono), 0.80, 0.25 + 0.75 * cerca)
            fuera.append(Trazo(xy, col, 5.5 * g, 70))     # halo
            fuera.append(Trazo(xy, col, 2.1 * g, 255))    # aro

        # El instante: donde se cruzan los dos aros.
        xy, d = self._proyectar(_en_toro(np.array([hora]), np.array([minuto])),
                                giro, nada)
        p = xy[0]
        anillo = np.stack([p[0] + 7 * g * np.cos(w), p[1] + 7 * g * np.sin(w)],
                          axis=1).astype(np.float32)
        fuera.append(Trazo(anillo, 0xFFF4D8, 2.4 * g, 240))
        return fuera

    def capa(self, t):
        """La hora escrita, pequeña y abajo: un reloj de pared que no se puede
        leer es una escultura. Pero la superficie es la protagonista, así que
        no se le pone delante un bloque de cifras."""
        seg = int(t)
        lz = Lienzo(self.lado, sup=1)
        lz.texto(self.lado / 2, self.lado * 0.885,
                 "%d:%02d" % (int(t // 3600) % 12 or 12, int(t // 60) % 60),
                 self.f_hora, 0xF2F5F8, 235)
        lz.texto(self.lado / 2, self.lado * 0.945,
                 # Roboto Mono no trae ni tau ni pi: salían dos huecos.
                 "C / (Z + tZ)   con   t = exp(i pi / 3)",
                 self.f_pie, 0x6E86A0)
        return seg // 60, lz.array()


ESFERA = Toro
