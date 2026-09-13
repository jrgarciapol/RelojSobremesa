"""Rosa de los vientos — ocho puntas, anillo de minutos y arco de progreso.

Hora grande en Barriecito y la línea `LUN 9 AGO` en Roboto Mono Bold.

En el reloj la rosa intentaba orientarse con el rumbo, y casi nunca lo
conseguía: **una esfera Garmin no recibe brújula continua**, así que se quedaba
fija al norte salvo que hubiera un rumbo GPS reciente. Un reloj de pared
tampoco tiene brújula, así que aquí el norte es fijo y ya está — que es lo que
de hecho se veía el 95% del tiempo.

`RosaVivid` es la variante saturada: verdes y rojos puros en vez de la paleta
apagada.
"""

import math
import time

from ..esfera import Esfera
from ..lienzo import Lienzo, tipo

C_WHITE = 0xF5F5F2
C_GREEN = 0x3FD98C
C_BLUE  = 0x4C9BF0
C_TICK  = 0x2C2E33
C_TICK5 = 0x5A5D66
C_TRACK = 0x1A1C20

C_VGREEN = 0x00FF00
C_VRED   = 0xFF0000
C_VBLUE  = 0x1E9BFF

DIAS = ("DOM", "LUN", "MAR", "MIE", "JUE", "VIE", "SAB")
MESES = ("ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
         "JUL", "AGO", "SEP", "OCT", "NOV", "DIC")

# Todo en fracción de la pantalla (el original iba en px sobre 454).
M_ROSA, M_TICKS, M_ARCO = 24 / 454.0, 14 / 454.0, 6 / 454.0
C_TIME, C_DATE, C_CARD = 170 / 454.0, 30 / 454.0, 34 / 454.0
DY_TIME, DY_DATE = -16 / 454.0, 112 / 454.0


class Rosa(Esfera):
    NOMBRE = "rosa"
    VIVID = False

    def __init__(self, lado):
        Esfera.__init__(self, lado)
        self.f_time = tipo("Barriecito-Regular.ttf", lado * C_TIME)
        self.f_date = tipo("RobotoMono-Bold.ttf", lado * C_DATE)
        self.f_card = tipo("RobotoMono-Bold.ttf", lado * C_CARD)

    # ---------- lo que no se mueve ----------
    def fondo(self):
        lado, r = self.lado, self.r
        lz = Lienzo(lado, fondo=0x000000)
        self._rosa(lz, r - lado * M_ROSA)
        self._minutos(lz, r - lado * M_TICKS)
        # La pista del arco de progreso sí es fija; el arco vivo va en la capa.
        lz.anillo(r, r, r - lado * M_ARCO, lado * 5 / 454.0, C_TRACK)
        return lz.array()[:, :, :3]

    def _rosa(self, lz, r):
        """Las ocho puntas.

        En el Garmin los flancos se colocaban a **4,6 grados** del eje, medidos
        desde el centro. Suena razonable y no lo es: a la altura del hombro eso
        son `r_in * sin(4,6°)`, o sea el 8% del radio interior. La punta salía
        de dos píxeles de ancho y la rosa se leía como un alambre — que es
        justo lo que se veía en el reloj.

        Aquí el hombro se separa una **fracción del radio interior**, no un
        ángulo: `K_HOMBRO = 0.9` da una cometa de verdad. El resto de la
        geometría es la misma.
        """
        K_HOMBRO = 0.9
        c, r_in = self.r, r * 0.085
        for i in range(8):
            cardinal = (i % 2 == 0)
            largo = r * (0.90 if cardinal else 0.72)
            a = math.radians(i * 45)
            ux, uy = math.sin(a), -math.cos(a)     # eje de la punta
            px, py = math.cos(a), math.sin(a)      # perpendicular
            hw = r_in * K_HOMBRO
            if self.VIVID:
                col = C_VGREEN if cardinal else C_VRED
            else:
                col = 0x132A20 if cardinal else 0x0F2028
                if i == 0:
                    col = C_GREEN          # punta norte destacada
            lz.poligono([(c + ux * largo, c + uy * largo),
                         (c + ux * r_in + px * hw, c + uy * r_in + py * hw),
                         (c - ux * r_in, c - uy * r_in),
                         (c + ux * r_in - px * hw, c + uy * r_in - py * hw)], col)

        aro = 0x005B00 if self.VIVID else 0x1B3A2C
        g = self.lado * 2 / 454.0
        lz.anillo(c, c, r * 0.66, g, aro)
        lz.anillo(c, c, r * 0.32, g, aro)

        for k, etq in enumerate("NESO"):
            ak = math.radians(k * 90)
            lz.texto(c + (r - self.lado * M_ROSA) * math.sin(ak),
                     c - (r - self.lado * M_ROSA) * math.cos(ak),
                     etq, self.f_card, C_VBLUE if self.VIVID else C_BLUE)

    def _minutos(self, lz, r_out):
        c = self.r
        for i in range(60):
            mayor = (i % 5 == 0)
            largo = self.lado * (15 if mayor else 9) / 454.0
            grosor = self.lado * (3 if mayor else 2) / 454.0
            a = math.radians(i * 6 - 90)
            ca, sa = math.cos(a), math.sin(a)
            lz.linea(c + (r_out - largo) * ca, c + (r_out - largo) * sa,
                     c + r_out * ca, c + r_out * sa,
                     grosor, C_TICK5 if mayor else C_TICK)

    # ---------- lo que cambia cada minuto ----------
    def capa(self, t):
        minuto = int(t // 60)
        return minuto, self._pintar(int(t // 3600) % 24, minuto % 60)

    def _pintar(self, hora, minuto):
        lado, r = self.lado, self.r
        lz = Lienzo(lado, sup=2)     # sup=2 por el arco; el texto no lo necesita
        verde = C_VGREEN if self.VIVID else C_GREEN

        if minuto > 0:
            lz.anillo(r, r, r - lado * M_ARCO, lado * 5 / 454.0, verde,
                      desde=0, hasta=360.0 * minuto / 60.0)

        self._hora(lz, r, r + lado * DY_TIME, hora, minuto)

        lt = time.localtime()
        linea = "%s %d %s" % (DIAS[(lt.tm_wday + 1) % 7], lt.tm_mday,
                              MESES[lt.tm_mon - 1])
        lz.texto(r, r + lado * DY_DATE, linea, self.f_date, C_WHITE)
        return lz.array()

    def _hora(self, lz, cx, cy, hora, minuto):
        hh, mm = "%d" % (hora % 12 or 12), "%02d" % minuto
        w_hh = lz.ancho_de(hh, self.f_time)
        cs = lz.ancho_de(":", self.f_time) / 2.0
        x0 = cx - (w_hh + cs * 2 + lz.ancho_de(mm, self.f_time)) / 2.0
        lz.texto(x0, cy, hh, self.f_time, C_WHITE, anclaje="lm")
        lz.texto(x0 + w_hh + cs, cy, ":", self.f_time, C_WHITE)
        lz.texto(x0 + w_hh + cs * 2, cy, mm, self.f_time, C_WHITE, anclaje="lm")


class RosaVivid(Rosa):
    NOMBRE = "rosavivid"
    VIVID = True


ESFERA = Rosa
