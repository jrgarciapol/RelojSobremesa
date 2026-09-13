"""La superficie elíptica — los cortes de `eliptica`, pero ya con su cuerpo.

`eliptica` dibuja el lugar real de `y² = x³ + ax + b` con `(a, b)` recorriendo
un lazo cerrado, y lo pinta como una familia de curvas planas. Esas curvas son
**cortes de algo**, y ese algo existe: como el lazo se cierra, la familia barre
una superficie de verdad. En geometría algebraica eso tiene nombre —una
**superficie elíptica**, una familia de curvas elípticas sobre una base— y no
hay que fingirla, se construye.

Aquí la base es un círculo, y ese círculo **es la esfera del reloj**: el
ángulo de barrido es la hora. Así que:

    dar la vuelta a la superficie = dar la vuelta al día
    el corte en cada azimut       = la curva de esa hora
    los NÚMEROS van pintados encima, sobre el plano tangente

Y se ve algo que en el dibujo plano solo se intuía: al cruzar el discriminante
`4a³ + 27b² = 0` la superficie **se pellizca** y suelta un asa. Ese pellizco es
lo que en la teoría se llama una fibra singular, y aquí se ve a simple vista.
"""

import math

import numpy as np

from ..camara import Camara
from ..esfera import Esfera, Trazo
from ..lienzo import Lienzo, hsv_arr, tipo
from ..trazos_tipo import numero
from .eliptica import YTOPE, _lazo, _raices, parametros

CORTES = 32         # cortes alrededor del anillo
N_RAMA = 80         # muestras por media rama (el trazo sale con el doble)
LARGOS = 15         # líneas longitudinales
R_ANILLO = 1.05     # del eje al centro del corte
ESCALA = 0.30       # del plano de la curva al mundo
X_TOPE = 2.0        # hasta dónde se deja crecer la rama

ALTO_NUM = 0.46     # alto de las cifras, en unidades del mundo
R_NUM = 1.60        # a qué radio se pintan

VUELTA = 300.0
CABECEO = 83.0


def _en_anillo(azimut, x, y):
    """Un punto del corte, colocado en el plano vertical de ese azimut."""
    rad = R_ANILLO + ESCALA * x
    return np.stack([rad * math.cos(azimut), rad * math.sin(azimut),
                     ESCALA * y], axis=-1)


class Superficie(Esfera):
    """Los cortes de la curva elíptica barriendo el día, con las horas
    escritas sobre la propia superficie."""

    NOMBRE = "superficie"
    # La cámara da una vuelta en cinco minutos: 1,2 grados por segundo. A seis
    # recálculos por segundo son pasos de 0,2 grados, invisibles, y con 7.800
    # vértices por fotograma la diferencia en la Pi es de 23 ms a 13.
    POR_SEGUNDO = 6

    def __init__(self, lado):
        Esfera.__init__(self, lado)
        self.cam = Camara(lado, distancia=4.2, foco=2.7, zoom=0.62)
        self.f_hora = tipo("RobotoMono-Bold.ttf", lado * 40 / 454.0)
        self.f_pie = tipo("RobotoMono-Bold.ttf", lado * 17 / 454.0)

        # La superficie NO depende de la hora: el azimut es la hora, no el
        # instante. Así que se construye una vez y solo se vuelve a proyectar
        # cuando la cámara se mueve.
        self._cortes = [(k / float(CORTES), self._corte(k / float(CORTES)))
                        for k in range(CORTES)]
        # Las longitudinales: el punto `i` de cada corte, cosido en un anillo
        # cerrado. Son las que hacen que se vea una superficie.
        ramas = np.array([c[0] for _, c in self._cortes if c[0] is not None])
        paso = max(1, ramas.shape[1] // LARGOS)
        self._largos = [np.vstack([ramas[:, i], ramas[:1, i]])
                        for i in range(0, ramas.shape[1], paso)]
        self._cifras = self._rotular()
        self._clave = None
        self._trazos = ()

    def _corte(self, fase):
        """(rama, óvalo) del corte en esa fase, ya en el mundo.

        La rama sale **siempre con el mismo número de puntos**, y eso no es un
        detalle: es lo que permite unir el punto `i` de un corte con el punto
        `i` del siguiente y tener líneas longitudinales. Sin ellas la esfera se
        lee como una valla de listones, no como una superficie.

        El óvalo no siempre existe —nace y muere al cruzar el discriminante—
        así que ese no se puede coser, y va suelto.
        """
        a, b = parametros(fase)
        r = _raices(a, b)
        az = 2 * math.pi * fase
        if not len(r):
            return None, None

        alto = _raices(a, b, YTOPE * YTOPE)
        tope = min(alto[-1] if len(alto) else X_TOPE, X_TOPE)
        x, y = _lazo(a, b, r[-1], tope, N_RAMA)
        rama = _en_anillo(az, x, y)

        ovalo = None
        if len(r) == 3:
            x, y = _lazo(a, b, r[0], r[1], N_RAMA // 2)
            ovalo = _en_anillo(az, x, y)
        return rama, ovalo

    def _rotular(self):
        """Las doce horas, pintadas sobre el plano tangente de la superficie.

        El plano tangente en el ecuador exterior lo forman la dirección
        azimutal y la vertical, así que basta colocar cada (u, v) de la cifra
        con esos dos vectores. De ahí sale el escorzo: los números de detrás se
        ven de canto, como pintados en la pared de un cilindro.
        """
        fuera = []
        for h in range(1, 13):
            az = 2 * math.pi * (h % 12) / 12.0
            centro = np.array([R_NUM * math.cos(az), R_NUM * math.sin(az), 0.0])
            eje_u = np.array([-math.sin(az), math.cos(az), 0.0])   # azimutal
            eje_v = np.array([0.0, 0.0, 1.0])                      # vertical
            for trazo in numero(h):
                p = np.array([centro + eje_u * (u * ALTO_NUM / 2)
                              + eje_v * (v * ALTO_NUM / 2) for u, v in trazo])
                fuera.append((h, p))
        return fuera

    def trazos(self, t):
        clave = round(t * self.POR_SEGUNDO)
        if clave != self._clave:
            self._clave = clave
            self._trazos = self._calcular(clave / float(self.POR_SEGUNDO))
        return self._trazos

    def _calcular(self, t):
        self.cam.mirar(2 * math.pi * t / VUELTA,
                       0.50 + 0.20 * math.sin(2 * math.pi * t / CABECEO))
        g = self.lado / 454.0
        hora = (t / 3600.0) % 12.0
        fuera = []

        # Las longitudinales, primero y apagadas: son el tejido de la
        # superficie, no el dibujo.
        for pts in self._largos:
            xy, d = self.cam(pts)
            col = hsv_arr(0.60, 0.55, 0.08 + 0.30 * self.cam.niebla(d, 1.6, 1.9))
            fuera.append(Trazo(xy, col, 0.9 * g, 140))

        # Los cortes, con el de la hora encendido.
        for fase, (rama, ovalo) in self._cortes:
            cerca_hora = abs(((fase * 12 - hora + 6) % 12) - 6)   # en horas
            viva = max(0.0, 1.0 - cerca_hora / 0.5)
            for pts in (rama, ovalo):
                if pts is None:
                    continue
                xy, d = self.cam(pts)
                niebla = self.cam.niebla(d, 1.6, 1.9)
                col = hsv_arr(0.53 + 0.14 * viva, 0.70 - 0.45 * viva,
                              (0.16 + 0.46 * niebla) * (1 + 1.6 * viva))
                fuera.append(Trazo(xy, col, (1.1 + 2.2 * viva) * g,
                                   255 if viva > 0 else 165))

        # Las horas, escritas sobre la superficie.
        for h, pts in self._cifras:
            xy, d = self.cam(pts)
            niebla = self.cam.niebla(d, 1.4, 1.9)
            esta = (int(hora) % 12 or 12) == h
            col = hsv_arr(0.11 if esta else 0.55, 0.42 if esta else 0.14,
                          (0.34 + 0.66 * niebla) * (1.0 if esta else 0.80))
            fuera.append(Trazo(xy, col, (3.4 if esta else 2.0) * g, 255))

        # El minuto: una cuenta recorriendo el corte de la hora en curso.
        fuera += self._cuenta(t, g)
        return fuera

    def _cuenta(self, t, g):
        """Un punto que da una vuelta al corte de la hora cada hora."""
        pts, _ = self._corte(((t / 3600.0) % 12.0) / 12.0)
        if pts is None:
            return []
        i = int((t / 60.0 % 60.0) / 60.0 * (len(pts) - 1))
        xy, _ = self.cam(pts[i:i + 1])
        p = xy[0]
        w = np.linspace(0, 2 * math.pi, 40)
        anillo = np.stack([p[0] + 6 * g * np.cos(w),
                           p[1] + 6 * g * np.sin(w)], axis=1).astype(np.float32)
        return [Trazo(anillo, 0xFFE9C0, 2.2 * g, 245)]

    def capa(self, t):
        lz = Lienzo(self.lado, sup=1)
        lz.texto(self.lado / 2, self.lado * 0.90,
                 "%d:%02d" % (int(t // 3600) % 12 or 12, int(t // 60) % 60),
                 self.f_hora, 0xF2F5F8, 225)
        lz.texto(self.lado / 2, self.lado * 0.955,
                 "una vuelta al dia, una curva por hora",
                 self.f_pie, 0x6E86A0)
        return int(t) // 60, lz.array()


ESFERA = Superficie
