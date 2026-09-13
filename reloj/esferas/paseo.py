"""Paseo — un cometa recorriendo las curvas célebres.

El catálogo de MacTutor <https://mathshistory.st-andrews.ac.uk/Curves/> tiene
sesenta y una curvas con nombre propio, y aquí **cambia de curva cada minuto**:
el índice es el minuto del día módulo sesenta y uno, así que en poco más de una
hora se han visto todas y ninguna se ha repetido. Detrás de la hora, un punto
va recorriéndola y dejando estela.

La dimensión que les falta se la pone la estela, no la curva. Son curvas
**planas** y deformarlas para darles volumen sería quitarles lo que las hace
reconocibles — una cardioide torcida ya no es una cardioide. Así que la curva
se queda en su plano, y lo que sale del plano es **el rastro del cometa**, que
se va levantando conforme envejece. La cámara pasea despacio alrededor, así que
el plano se ve en perspectiva y la cinta de la estela se lee en el aire.
"""

import math

import numpy as np

from ..camara import Camara
from ..curvas_famosas import CURVAS, muestrear
from ..esfera import Esfera, Trazo
from ..lienzo import Lienzo, hsv_arr, tipo

# La curva normalizada mide 2 de ancho. Con la perspectiva dividiendo por la
# profundidad, a escala 1 ocupaba un tercio del dial.
ESCALA = 1.10       # de la curva normalizada al mundo
VUELTA_COMETA = 9.0     # segundos que tarda el cometa en recorrerla entera
ESTELA = 90         # muestras de estela
ALTO_ESTELA = 0.95  # cuánto se levanta del plano la cola más vieja

VUELTA = 260.0      # la cámara
CABECEO = 71.0
# El cabeceo mira CASI DE FRENTE al plano de la curva, no casi de canto.
# La curva vive en el plano z=0, y la cámara con cabeceo 0 lo ve de perfil: una
# cardioide preciosa se convertía en una raya. A 66 grados se lee entera y aún
# queda escorzo suficiente para que se note que hay un plano en el espacio.
PICADO = 1.15
BALANCEO = 0.17


class Paseo(Esfera):
    """Una curva célebre por minuto, con un cometa recorriéndola."""

    NOMBRE = "paseo"
    POR_SEGUNDO = 15    # el cometa sí se mueve rápido

    def __init__(self, lado):
        Esfera.__init__(self, lado)
        self.cam = Camara(lado, distancia=4.0, foco=2.7, zoom=0.95)
        self.f_hora = tipo("RobotoMono-Bold.ttf", lado * 46 / 454.0)
        self.f_nombre = tipo("RobotoMono-Bold.ttf", lado * 21 / 454.0)
        self._cual = None
        self._clave = None
        self._trazos = ()

    # ---------- la curva del minuto ----------
    def _curva(self, minuto):
        """Las piezas en el mundo, más el camino seguido por el cometa.

        El camino es todas las piezas encadenadas: el cometa salta de una a
        otra igual que salta la curva por su asíntota, y ese salto se ve.
        """
        if self._cual == minuto:
            return self._piezas, self._camino, self._nombre
        nombre, piezas = muestrear(minuto, 1100)
        mundo = [np.stack([p[:, 0] * ESCALA, p[:, 1] * ESCALA,
                           np.zeros(len(p))], axis=1) for p in piezas]
        self._cual = minuto
        self._nombre = nombre
        self._piezas = mundo
        self._camino = (np.vstack(mundo) if mundo
                        else np.zeros((1, 3)))
        return mundo, self._camino, nombre

    def trazos(self, t):
        clave = round(t * self.POR_SEGUNDO)
        if clave != self._clave:
            self._clave = clave
            self._trazos = self._calcular(clave / float(self.POR_SEGUNDO))
        return self._trazos

    def _calcular(self, t):
        self.cam.mirar(2 * math.pi * t / VUELTA,
                       PICADO + BALANCEO * math.sin(2 * math.pi * t / CABECEO))
        g = self.lado / 454.0
        piezas, camino, _ = self._curva(int(t // 60) % len(CURVAS))
        fuera = []

        # La curva, apagada: es la pista, no el corredor.
        for pts in piezas:
            xy, d = self.cam(pts)
            col = hsv_arr(0.54, 0.52, 0.26 + 0.52 * self.cam.niebla(d, 1.5, 1.7))
            fuera.append(Trazo(xy, col, 1.9 * g, 225))

        # El cometa. La cabeza va sobre el plano; la cola se despega y sube,
        # que es la dimensión que a una curva plana le falta.
        n = len(camino)
        cabeza = (t / VUELTA_COMETA) % 1.0
        i = np.arange(ESTELA)
        pos = ((cabeza - i / float(n)) % 1.0 * n).astype(int) % n
        cola = camino[pos].copy()
        edad = i / float(ESTELA - 1)
        cola[:, 2] += ALTO_ESTELA * edad ** 1.6

        xy, d = self.cam(cola)
        cerca = self.cam.niebla(d, 1.3, 1.7)
        col = hsv_arr(0.10 + 0.16 * edad, 0.55 + 0.35 * edad,
                      (1.0 - edad) ** 1.5 * (0.35 + 0.65 * cerca))
        fuera.append(Trazo(xy, col, 7.0 * g, 55))
        fuera.append(Trazo(xy, col, 2.6 * g, 240))

        # La cabeza, un punto redondo y brillante.
        w = np.linspace(0, 2 * math.pi, 28)
        p = xy[0]
        fuera.append(Trazo(np.stack([p[0] + 5 * g * np.cos(w),
                                     p[1] + 5 * g * np.sin(w)],
                                    axis=1).astype(np.float32),
                           0xFFF0D0, 2.2 * g, 250))
        return fuera

    def capa(self, t):
        """La hora pequeña abajo, y debajo el nombre de la curva.

        La primera versión llevaba la maquetación digital entera —cifras de
        media pantalla— y se comía la curva, que es justo lo que se ha venido a
        ver. Aquí el reloj se aparta.
        """
        minuto = int(t // 60)
        lz = Lienzo(self.lado, sup=1)
        lz.texto(self.lado / 2, self.lado * 0.885,
                 "%d:%02d" % (int(t // 3600) % 12 or 12, minuto % 60),
                 self.f_hora, 0xF2F5F8, 235)
        _, _, nombre = self._curva(minuto % len(CURVAS))
        lz.texto(self.lado / 2, self.lado * 0.950, nombre.upper(),
                 self.f_nombre, 0x8FB0C4)
        return minuto, lz.array()


ESFERA = Paseo
