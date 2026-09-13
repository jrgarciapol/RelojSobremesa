"""Cámara para las esferas en tres dimensiones.

Rota el mundo, aplica perspectiva y devuelve **también la profundidad**, que es
lo que las esferas usan para la niebla. No hay z-buffer y no hace falta: el ojo
lee una malla que se apaga al fondo como una superficie curva, y una malla es
transparente por definición, así que ocultar caras sería mentir.
"""

import math

import numpy as np


class Camara:
    """Un ojo que mira al origen desde `distancia`, girando y cabeceando.

    `zoom` decide cuánto ocupa la escena. Da la tentación de calcularlo del
    tamaño del objeto, y sale mal: la perspectiva divide por la profundidad, o
    sea que la parte que se acerca sale aumentada. Se ajusta mirando.
    """

    def __init__(self, lado, distancia=3.55, foco=2.70, zoom=0.66):
        self.r = lado / 2.0
        self.distancia = distancia
        self.foco = foco
        self.zoom = zoom
        self.mirar(0.0, 0.6)

    def mirar(self, giro, cabeceo):
        self._ca, self._sa = math.cos(giro), math.sin(giro)
        self._cb, self._sb = math.cos(cabeceo), math.sin(cabeceo)
        return self

    def __call__(self, p):
        """(N, 3) en el mundo -> ((N, 2) en píxeles, (N,) profundidad)."""
        ca, sa, cb, sb = self._ca, self._sa, self._cb, self._sb
        x1 = p[..., 0] * ca - p[..., 1] * sa
        y1 = p[..., 0] * sa + p[..., 1] * ca
        z1 = p[..., 2]

        y2 = y1 * cb - z1 * sb
        z2 = y1 * sb + z1 * cb

        d = y2 + self.distancia
        k = self.foco / np.maximum(d, 0.35) * self.zoom * self.r
        xy = np.stack([self.r + x1 * k, self.r - z2 * k], axis=-1)
        return xy.astype(np.float32), d

    def niebla(self, d, dureza=1.7, fondo=1.0):
        """0 = al fondo del todo, 1 = pegado al ojo."""
        cerca = np.clip((self.distancia + fondo - d) / (2.0 * fondo), 0.0, 1.0)
        return cerca ** dureza
