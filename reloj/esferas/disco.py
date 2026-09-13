"""Disco — analógica minimalista, ámbar sobre negro, sin cifras.

Misma geometría que la esfera del Garmin (`Disco/`), con las medidas pasadas a
fracción del radio para que sirva igual en un monitor de 24" que en una
pantallita de 5".

Lo que gana en pantalla grande:

* **antialiasing de verdad** — en el reloj las agujas finas salían dentadas;
* **segundero de barrido**, continuo. Una esfera Connect IQ se redibuja una vez
  por segundo, así que un barrido era literalmente imposible allí.
"""

import math

from ..esfera import Esfera, Puesto
from ..lienzo import Lienzo, aguja

# ---- Paleta, idéntica a la del Garmin ----
FONDO   = 0x000000
TICK    = 0x7A5E10   # las ocho marcas menores
TICK_Q  = 0xC9A21E   # 12, 3, 6 y 9: más vivas
TINTA   = 0xF7C81E   # cuerpo de las agujas, ámbar
BISEL   = 0xFFE49A   # la media aguja que da a la luz
PIVOTE  = 0xFFF0C4
SEGUNDO = 0xC9A21E   # el segundero, en el ámbar apagado de las marcas

# ---- Geometría, en fracción del radio (el original iba en px sobre R = 227) ----
L_MIN, L_HOUR, L_SEG = 215 / 227.0, 142 / 227.0, 222 / 227.0
COLA, R_DISCO, R_PIVOTE = 34 / 227.0, 27 / 227.0, 5 / 227.0

W_MIN_COLA,  W_MIN_CUERPO,  K_SH_MIN  = 13 / 227.0, 10 / 227.0, 0.66
W_HOUR_COLA, W_HOUR_CUERPO, K_SH_HOUR = 16 / 227.0, 13 / 227.0, 0.60
W_SEG_COLA,  W_SEG_CUERPO,  K_SH_SEG  = 5 / 227.0,  3 / 227.0,  0.90

TICK_W_Q, TICK_W = 26 / 227.0, 17 / 227.0
TICK_R_IN_Q = 0.775   # las de los cuartos, más largas
TICK_R_IN   = 0.855
TICK_R_OUT  = 0.955   # todas acaban a la misma altura


class Disco(Esfera):
    NOMBRE = "disco"

    def fondo(self):
        r, lz = self.r, Lienzo(self.lado, fondo=FONDO)
        self._marcas(lz, r)
        self._disco(lz, r)
        return lz.array()[:, :, :3]

    def _marcas(self, lz, r):
        for i in range(12):
            a = math.radians(i * 30.0 - 90.0)
            ux, uy = math.cos(a), math.sin(a)
            px, py = -uy, ux
            cuarto = (i % 3 == 0)
            hw = r * (TICK_W_Q if cuarto else TICK_W) / 2.0
            r1 = r * (TICK_R_IN_Q if cuarto else TICK_R_IN)
            r2 = r * TICK_R_OUT
            lz.poligono([(r + ux * r1 + px * hw, r + uy * r1 + py * hw),
                         (r + ux * r2 + px * hw, r + uy * r2 + py * hw),
                         (r + ux * r2 - px * hw, r + uy * r2 - py * hw),
                         (r + ux * r1 - px * hw, r + uy * r1 - py * hw)],
                        TICK_Q if cuarto else TICK)

    def _disco(self, lz, r):
        """Siete anillos concéntricos, cada uno más oscuro y descentrado hacia
        abajo a la derecha: es lo que finge la luz cayendo desde arriba a la
        izquierda cuando no hay degradados."""
        rd, n = r * R_DISCO, 7
        for i in range(n):
            f = i / (n - 1.0)
            v = 0x5E + int((0x1C - 0x5E) * f)
            lz.circulo(r - rd * 0.10 * (1 - f), r - rd * 0.13 * (1 - f),
                       rd * (1.0 - i * 0.09), (v << 16) | ((v + 1) << 8) | (v + 2))

    def piezas(self):
        r, lado = self.r, self.lado
        lz = Lienzo(lado)
        lz.circulo(r, r, r * R_PIVOTE, PIVOTE)
        return {
            "hora": aguja(r * L_HOUR, r * COLA, r * W_HOUR_COLA,
                          r * W_HOUR_CUERPO, K_SH_HOUR, TINTA, BISEL),
            "minuto": aguja(r * L_MIN, r * COLA, r * W_MIN_COLA,
                            r * W_MIN_CUERPO, K_SH_MIN, TINTA, BISEL),
            "segundo": aguja(r * L_SEG, r * COLA * 1.6, r * W_SEG_COLA,
                             r * W_SEG_CUERPO, K_SH_SEG, SEGUNDO),
            "pivote": lz.array(),
        }

    def cuadro(self, t):
        r = self.r
        return (Puesto("hora", r, r, (t / 3600.0 % 12.0) * 30.0),
                Puesto("minuto", r, r, (t / 60.0 % 60.0) * 6.0),
                Puesto("segundo", r, r, (t % 60.0) * 6.0),
                Puesto("pivote", r, r))


ESFERA = Disco
