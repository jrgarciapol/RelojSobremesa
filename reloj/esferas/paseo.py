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
ESTELA = 130        # muestras de estela
LARGO_ESTELA = 0.15     # qué fracción del ARCO de la curva ocupa la cinta
ALTO_ESTELA = 0.85  # cuánto se levanta del plano la cola más vieja
APAGADO = 1.1

# El cometa no va a velocidad constante: corre donde la curva se cierra y se
# arrastra donde se estira. Es la intuición kepleriana —en el perihelio, que es
# donde la órbita más se cierra, el planeta va disparado— y aquí además cumple
# una función: la gracia de estas curvas está en los recodos, y a velocidad
# constante el cometa se los pasa en dos fotogramas y se pasa el resto del rato
# recorriendo la recta que se va al infinito.
#
# No es literalmente la ley de áreas: en el afelio también hay curvatura y ahí
# el planeta va lentísimo. Es velocidad proporcional a la curvatura, a secas.
V_RECTA = 0.20      # velocidad en los tramos rectos, con la de los recodos a 1
CURVA_TOPE = 85     # percentil de curvatura que se toma como «recodo cerrado»

VUELTA = 260.0      # la cámara
CABECEO = 71.0
# El cabeceo mira CASI DE FRENTE al plano de la curva, no casi de canto.
# La curva vive en el plano z=0, y la cámara con cabeceo 0 lo ve de perfil: una
# cardioide preciosa se convertía en una raya. A 66 grados se lee entera y aún
# queda escorzo suficiente para que se note que hay un plano en el espacio.
PICADO = 1.15
BALANCEO = 0.17


def reparametrizar(p):
    """Los dos relojes del camino: el del tiempo y el de la cinta métrica.

    Devuelve `(T, S)`, los dos acumulados y normalizados a [0, 1]. `T[i]` es la
    fracción de la VUELTA gastada al llegar al punto `i` —repartida por
    curvatura, que es lo que hace que el cometa corra en los recodos— y `S[i]`
    es la fracción del RECORRIDO, o sea la longitud de arco.

    Hacen falta los dos y para cosas distintas. La cabeza va por `T`. La cola
    va por `S`, porque una cola mide lo mismo se vaya rápido o despacio: con la
    cola medida en tiempo se encogía justo en los recodos, que es donde el
    cometa frena y donde más ganas hay de verla.

    La curvatura es la de Menger —el inverso del radio de la circunferencia que
    pasa por tres puntos seguidos—, que sale de un área y tres distancias y no
    pide derivar nada. Se normaliza por PERCENTIL, no por el máximo: una cúspide
    tiene curvatura infinita y con el máximo por divisor todo lo demás quedaría
    a cero y el cometa no se movería.
    """
    a, b, c = np.roll(p, 1, 0), p, np.roll(p, -1, 0)
    ab, cb, ca = b - a, c - b, c - a
    ds = np.hypot(cb[:, 0], cb[:, 1])
    # Los saltos entre trozos (una asíntota) son enormes y falsean el reparto:
    # se recortan al tramo típico para que el salto no se coma la vuelta.
    ds = np.minimum(ds, 6.0 * np.median(ds))

    area = np.abs(ab[:, 0] * ca[:, 1] - ab[:, 1] * ca[:, 0]) / 2.0
    largos = (np.hypot(ab[:, 0], ab[:, 1]) * np.hypot(cb[:, 0], cb[:, 1])
              * np.hypot(ca[:, 0], ca[:, 1]))
    k = np.where(largos > 1e-9, 4.0 * area / np.maximum(largos, 1e-9), 0.0)

    tope = np.percentile(k, CURVA_TOPE)
    kn = np.clip(k / tope, 0.0, 1.0) if tope > 1e-9 else np.zeros_like(k)
    v = V_RECTA + (1.0 - V_RECTA) * kn

    t, s = np.cumsum(ds / v), np.cumsum(ds)
    return t / t[-1], s / s[-1]


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
        self._reloj = self._cinta = None
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
        self._reloj, self._cinta = reparametrizar(self._camino[:, :2])
        return mundo, self._camino, nombre

    def _cometa(self, f, edad):
        """Los índices de la cabeza en el instante `f` y los de su cola.

        La cabeza sale del reloj de curvatura; la cola, de la cinta métrica,
        contada hacia atrás desde donde haya caído la cabeza.
        """
        n = len(self._reloj)
        i0 = np.searchsorted(self._reloj, f % 1.0) % n
        atras = (self._cinta[i0] - LARGO_ESTELA * edad) % 1.0
        return np.searchsorted(self._cinta, atras) % n

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
            col = hsv_arr(0.54, 0.52, 0.30 + 0.55 * self.cam.niebla(d, 1.5, 1.7))
            fuera.append(Trazo(xy, col, 2.2 * g, 235))

        # El cometa. La cabeza va sobre el plano; la cola se despega y sube,
        # que es la dimensión que a una curva plana le falta.
        cabeza = (t / VUELTA_COMETA) % 1.0
        edad = np.linspace(0.0, 1.0, ESTELA)
        cola = camino[self._cometa(cabeza, edad)].copy()
        # La estela sale TANGENTE al plano. Con `edad ** 0.85` la pendiente en
        # la cabeza es infinita y la cola salía disparada en perpendicular,
        # como una antena. Con el suavizado de Hermite —pendiente cero en los
        # dos extremos— despega rozando la curva y luego se levanta.
        cola[:, 2] += ALTO_ESTELA * edad * edad * (3.0 - 2.0 * edad)

        xy, d = self.cam(cola)
        cerca = self.cam.niebla(d, 1.3, 1.7)
        # De oro a rojo, no de naranja a amarillo: el tono subía hacia el verde
        # y con el brillo ya caído la estela salía color caqui, apagada. Un
        # cometa va al revés — blanco en la cabeza y rojo en la cola.
        col = hsv_arr(0.125 - 0.105 * edad, 0.45 + 0.50 * edad,
                      (1.0 - edad) ** APAGADO * (0.62 + 0.38 * cerca))
        # Tres pasadas sobre TROZOS cada vez más largos de la estela: la gorda
        # solo cubre el principio, la fina llega hasta el final. Así la cinta
        # se afila hacia atrás sin dibujar cada tramo con su propio ancho.
        for hasta, ancho, alfa in ((0.28, 9.0, 45), (0.60, 4.2, 100),
                                   (1.00, 1.9, 250)):
            m = max(2, int(ESTELA * hasta))
            fuera.append(Trazo(xy[:m], col[:m], ancho * g, alfa))

        # La cabeza, un punto redondo y brillante, con su halo.
        w = np.linspace(0, 2 * math.pi, 32)
        p = xy[0]
        for radio, ancho, alfa in ((9.0, 5.0, 60), (5.0, 2.4, 255)):
            fuera.append(Trazo(np.stack([p[0] + radio * g * np.cos(w),
                                         p[1] + radio * g * np.sin(w)],
                                        axis=1).astype(np.float32),
                               0xFFF0D0, ancho * g, alfa))
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
