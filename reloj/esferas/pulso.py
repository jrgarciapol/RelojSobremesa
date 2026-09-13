"""Pulso — dos orbes que giran al ritmo del corazón, chocan y estallan.

Nacen blancos del mismo punto y recorren media vuelta en sentidos opuestos,
ganando color: uno hacia el **naranja** y otro hacia el **cian**, elegidos para
que los dos luzcan igual (antes eran rojo y azul, y el azul se veía el doble:
44,5% de luminancia contra 21,3%). Al encontrarse estalla un orbe de anillos
con los colores de los dos fundiéndose —frío fuera, cálido después, núcleo
blanco— cuyo tamaño crece con las pulsaciones.

Dos decisiones que vienen del reloj y **no** son cosméticas:

* **El viaje va por detrás de los textos y el choque por delante.** Los dos
  puntos de encuentro son simétricos, pero detrás de uno está el día de la
  semana y detrás del otro la fecha. Dibujado por debajo, el estallido de
  arriba y el de abajo salían recortados de forma muy distinta.
* **La estela mide 1,5 s de recorrido.** A mitad de camino los orbes pasan por
  detrás de la hora y con hora de dos cifras los dígitos tapan la cabeza; con
  la cola larga el trazo asoma por encima y por debajo y el orbe se sigue
  viendo.

## Aquí no hay pulsómetro

Un reloj de sobremesa no lleva sensor. Las pulsaciones son un valor fijo,
`PPM`, ajustable con `--ppm`. Cambia la velocidad, el tamaño de los orbes y el
del estallido, exactamente igual que lo hacía el pulso de verdad.

De regalo, esto **elimina por construcción** el fallo que perseguimos en el
reloj: allí la fase se acumulaba fotograma a fotograma y al despertar la
pantalla los orbes salían disparados unos segundos. Aquí la fase se calcula
directamente de la hora, así que no hay nada que acumular ni que desincronizar.
"""

import math

from ..esfera import Puesto
from ..lienzo import disco_blando, hsv
from .digital import Digital

PPM = 72.0              # pulsaciones por minuto (ver --ppm)

BASE = 256              # el sprite se rasteriza una vez a este tamaño
R_ORB = 211 / 227.0     # radio de la órbita, en fracción del radio del dial

H_WARM, H_COOL = 0.07, 0.53   # naranja #FF8126 y cian #00C0EB al final
DEG_PER_BEAT = 12.0     # grados que avanza por latido
TRAVEL_BEATS = 15.0     # 180 / DEG_PER_BEAT = media vuelta
MERGE_BEATS = 3.0       # choque + colapso
CYCLE_BEATS = TRAVEL_BEATS + MERGE_BEATS
TRAIL_DOTS = 8
TRAIL_SECS = 1.5        # segundos de recorrido que cubre la estela
ANILLOS = 7             # anillos del estallido


def color_orbe(t, calido, v):
    """Del blanco del arranque al tono pleno del final del viaje."""
    tt = min(1.0, max(0.0, t))
    sat = tt ** 0.7
    if calido:
        return hsv(H_WARM, sat * 0.85, v)
    return hsv(H_COOL, sat, v * 0.92)


class Pulso(Digital):
    """Radio del orbe fijo. La velocidad y el estallido sí siguen al pulso."""

    NOMBRE = "pulso"

    # Paleta revisada: el color saturado pertenece a lo que se mueve, así que
    # el texto va con la saturación baja y una jerarquía clara de brillo.
    COLOR_TIME  = 0xFFFFFF   # 100%
    COLOR_GREEN = 0x6FDC8C   # menta, 75%
    COLOR_MES   = 0x93A6B2   # gris azulado, 64%

    def radio_orbe(self, ppm):
        return self.r * 11 / 227.0

    def radio_choque(self, ppm):
        r = 45.0 + (ppm - 60.0) * 1.55
        return self.r * min(250.0, max(18.0, r)) / 227.0

    def piezas(self):
        return {"orbe": disco_blando(BASE, 0.86)}

    def _en(self, grados, radio, color, alfa=255):
        a = math.radians(grados - 90.0)
        return Puesto("orbe",
                      self.r + self.r * R_ORB * math.cos(a),
                      self.r + self.r * R_ORB * math.sin(a),
                      color=color, alfa=alfa, escala=2.0 * radio / BASE)

    def _fase(self, t):
        """(ciclo, posición dentro del ciclo) en latidos.

        Sale directamente de la hora: no se acumula nada entre fotogramas.
        """
        latidos = t * PPM / 60.0
        ciclo = int(latidos // CYCLE_BEATS)
        return ciclo, latidos - ciclo * CYCLE_BEATS

    def detras(self, t):
        """El viaje: cruza la hora sin taparla."""
        ciclo, p = self._fase(t)
        if p >= TRAVEL_BEATS:
            return ()

        r_orbe = self.radio_orbe(PPM)
        bps = PPM / 60.0
        # El sentido se invierte en cada ciclo y el punto de partida es el del
        # choque anterior: así alternan arriba y abajo.
        s = 1 if ciclo % 2 == 0 else -1
        inicio = 0.0 if ciclo % 2 == 0 else 180.0
        avance = DEG_PER_BEAT * p
        frac = p / TRAVEL_BEATS

        largo = min(DEG_PER_BEAT * bps * TRAIL_SECS, avance)

        fuera = []
        for i in range(TRAIL_DOTS, 0, -1):
            f = i / float(TRAIL_DOTS)
            atras = largo * f
            tk = frac - atras / 180.0
            rr = r_orbe * (0.30 + 0.55 * (1 - f))
            dim = 0.25 + 0.55 * (1 - f)
            if rr >= 1:
                fuera.append(self._en(inicio + s * (avance - atras), rr,
                                      color_orbe(tk, True, dim)))
                fuera.append(self._en(inicio - s * (avance - atras), rr,
                                      color_orbe(tk, False, dim)))

        # Cabeza: halo tenue, corona y núcleo a pleno brillo.
        for k, v in ((1.9, 0.25), (1.4, 0.60), (1.0, 1.00)):
            fuera.append(self._en(inicio + s * avance, r_orbe * k,
                                  color_orbe(frac, True, v)))
            fuera.append(self._en(inicio - s * avance, r_orbe * k,
                                  color_orbe(frac, False, v)))
        return fuera

    def cuadro(self, t):
        """El choque: por delante de los textos, que era la intención."""
        ciclo, p = self._fase(t)
        if p < TRAVEL_BEATS:
            return ()

        r_orbe = self.radio_orbe(PPM)
        grande = self.radio_choque(PPM)
        m = (p - TRAVEL_BEATS) / MERGE_BEATS
        if m < 0.28:                       # impacto: crece de golpe
            radio, desvaido = r_orbe + (grande - r_orbe) * (m / 0.28), 1.0
        else:                              # colapso hasta desaparecer
            q = (m - 0.28) / 0.72
            radio, desvaido = grande * (1.0 - q) ** 1.6, 1.0 - 0.5 * q
        if radio < 1:
            return ()

        choque = (0.0 if ciclo % 2 == 0 else 180.0) + 180.0
        fuera = []
        for i in range(ANILLOS):
            rr = radio * (1.0 - i / float(ANILLOS))
            if rr < 1:
                continue
            f = i / (ANILLOS - 1.0)        # 0 = anillo exterior, 1 = núcleo
            if f < 0.5:                    # del frío al cálido
                col = hsv(H_COOL + (H_WARM - H_COOL) * (f / 0.5), 1.0, desvaido)
            else:                          # del cálido al blanco
                col = hsv(H_WARM, 1.0 - (f - 0.5) / 0.5, desvaido)
            fuera.append(self._en(choque, rr, col))
        return fuera


class PulsoXL(Pulso):
    """Igual, pero el **radio del orbe** también crece con las pulsaciones:
    9 px en reposo, 29 a 160 ppm. La estela se mide en múltiplos de ese radio,
    así que pasa de hilo fino a brochazo."""

    NOMBRE = "pulsoxl"

    def radio_orbe(self, ppm):
        r = 9.0 + (ppm - 60.0) * 0.20
        return self.r * min(34.0, max(6.0, r)) / 227.0


ESFERA = Pulso
