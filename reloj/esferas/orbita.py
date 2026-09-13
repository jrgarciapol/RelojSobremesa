"""Órbita — la maquetación digital con un orbe recorriendo el borde del dial.

Una vuelta por minuto (6° por segundo), con estela de cinco puntos y el tono
recorriendo el espectro en cada vuelta. Pasa **por detrás** de la hora.

En el Garmin el orbe saltaba de segundo en segundo, porque una esfera se
redibuja una vez por segundo y no más. Aquí el ángulo sale del reloj con
decimales, así que el recorrido es **continuo**.
"""

import math

from ..esfera import Puesto
from ..lienzo import disco_blando, hsv
from .digital import Digital

R_ORB = 211 / 227.0     # radio de la órbita, en fracción del radio del dial
BASE = 128              # el sprite se rasteriza una vez a este tamaño
ESTELA = 5

# Radios en fracción del radio del dial (el original iba en px sobre 227).
R_HALO, R_CORONA, R_NUCLEO = 13 / 227.0, 9 / 227.0, 6 / 227.0


class Orbita(Digital):
    NOMBRE = "orbita"

    def piezas(self):
        return {"orbe": disco_blando(BASE, 0.80)}

    def _orbe(self, seg, r_frac, v, tono):
        """Coloca el disco escalado al radio pedido y teñido del tono."""
        a = math.radians(seg * 6.0 - 90.0)
        rr = self.r * r_frac
        return Puesto("orbe",
                      self.r + self.r * R_ORB * math.cos(a),
                      self.r + self.r * R_ORB * math.sin(a),
                      color=hsv(tono, 1.0, v), escala=2.0 * rr / BASE)

    def detras(self, t):
        """Por detrás de la hora, igual que en el reloj."""
        seg = t % 60.0
        fuera = []
        # Estela: del más lejano y apagado al más cercano.
        for k in range(ESTELA, 0, -1):
            s = (seg - k) % 60.0
            f = 1.0 - k / 6.0
            fuera.append(self._orbe(s, (3 + 3 * f) / 227.0,
                                    0.30 + 0.55 * f, s / 60.0))
        # Orbe: halo tenue, corona y núcleo a pleno brillo.
        h = seg / 60.0
        fuera.append(self._orbe(seg, R_HALO, 0.28, h))
        fuera.append(self._orbe(seg, R_CORONA, 0.62, h))
        fuera.append(self._orbe(seg, R_NUCLEO, 1.00, h))
        return fuera


ESFERA = Orbita
