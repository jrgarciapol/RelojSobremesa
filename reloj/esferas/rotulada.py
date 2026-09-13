"""Rotulada — la curva elíptica con las doce horas impresas encima.

`eliptica` es plana: no hay superficie donde pegar una etiqueta. Pero sí hay
dónde: **la propia curva**. La cinta se pega a lo largo de ella y las cifras se
doblan con su forma, se estiran donde la curva se estira y se aprietan donde se
aprieta. Cuando el lazo cruza el discriminante y la curva se pellizca, la
rotulación se pellizca con ella.

Y dónde cae cada hora no se reparte a ojo. La coordenada natural de una curva
elíptica es el **parámetro elíptico**

    u = ∫ dx / 2y

que es en la que la ley de grupo es sumar: `P + Q` es `u_P + u_Q`. Repartir las
doce horas por igual en `u` es repartirlas por igual **en el grupo**, así que
esto es un dial de verdad — la esfera de un reloj que resulta tener forma de
curva elíptica. La cuenta se ve: en longitud de arco las horas caerían en otro
sitio, y se separan bastante.

Con una salvedad honrada: la rama se va al infinito y la ventana la corta, así
que el dial es **el arco que se ve**, no el periodo entero. La cola desde el
borde hasta el infinito se lleva un tercio largo del semiperiodo, y con las
horas repartidas por el periodo real cuatro de las doce caerían fuera de la
pantalla.

`eliptica` se queda como está: esto es una esfera aparte.
"""

import numpy as np

from ..banda import cinta, etiqueta
from ..esfera import Malla, Puesto
from ..lienzo import Lienzo, disco_blando, tipo
from .eliptica import Eliptica, parametros, trozos

TEX_ANCHO = 2048
TEX_ALTO = 128
ANCHO_CINTA = 26 / 454.0    # del dial
CUENTA = 26 / 454.0         # el diámetro de la cuenta que marca la hora


def parametro(x, a, b):
    """El parámetro elíptico a lo largo de la rama, normalizado a [0, 1].

    Se integra por el punto medio de cada tramo: en la raíz `y` vale cero y
    dividir por ella ahí daría infinito. La integral converge de todos modos
    —cerca de una raíz simple `dx/y` va como `dx/√(x-r)`— y el muestreo de
    `_lazo`, que es por coseno, hace justo el cambio de variable que la alisa:
    con `x - r` proporcional al cuadrado del índice, el integrando sale
    constante.
    """
    xm = (x[:-1] + x[1:]) / 2.0
    ym = np.sqrt(np.maximum(xm ** 3 + a * xm + b, 0.0))
    du = np.abs(np.diff(x)) / (2.0 * np.maximum(ym, 1e-9))
    u = np.concatenate([[0.0], np.cumsum(du)])
    return u / max(u[-1], 1e-12)


class Rotulada(Eliptica):
    """La curva elíptica, rotulada a lo largo por su parámetro."""

    NOMBRE = "rotulada"

    def __init__(self, lado):
        Eliptica.__init__(self, lado)
        self.f_hora = tipo("RobotoMono-Bold.ttf", lado * 46 / 454.0)
        self.f_pie = tipo("RobotoMono-Bold.ttf", lado * 17 / 454.0)
        self._clave_m = None
        self._mallas = ()
        self._camino = None
        self._u = None

    def capa(self, t):
        """La hora, pequeña y abajo.

        `eliptica` hereda de `digital` la maquetación entera —cifras de media
        pantalla— y ahí funciona porque detrás solo hay líneas. Aquí no: lo que
        se ha venido a ver es la rotulación sobre la curva, y un bloque de
        cifras del tamaño del dial se la come. El reloj se aparta.
        """
        lz = Lienzo(self.lado, sup=1)
        lz.texto(self.lado / 2, self.lado * 0.885,
                 "%d:%02d" % (int(t // 3600) % 12 or 12, int(t // 60) % 60),
                 self.f_hora, 0xF2F5F8, 235)
        lz.texto(self.lado / 2, self.lado * 0.945,
                 "las horas, repartidas por el parametro",
                 self.f_pie, 0x6E86A0)
        return int(t) // 60, lz.array()

    def texturas(self):
        return {"horas": etiqueta(TEX_ANCHO, TEX_ALTO)}

    def piezas(self):
        return {"cuenta": disco_blando(max(5, int(self.lado * CUENTA)) | 1, 0.5)}

    # ---------- la cinta ----------
    def mallas(self, t):
        clave = round(t * self.POR_SEGUNDO)
        if clave != self._clave_m:
            self._clave_m = clave
            self._mallas = self._tejer(clave / float(self.POR_SEGUNDO))
        return self._mallas

    def _tejer(self, t):
        a, b = parametros((t / 3600.0) % 1.0)
        piezas = trozos(a, b)
        if not piezas:
            self._camino = self._u = None
            return ()
        # La rama, no el óvalo: el óvalo nace y muere una vez por hora y un
        # dial que desaparece media hora no es un dial.
        x, y = piezas[-1]
        self._camino = self._mundo(x, y)
        self._u = parametro(x, a, b)
        pts, uv, idx = cinta(self._camino, self._u, self.lado * ANCHO_CINTA)
        blanco = np.full((len(pts), 3), 255, np.uint8)
        return (Malla("horas", pts, uv, idx, blanco, 255),)

    # ---------- la cuenta que marca la hora ----------
    def cuadro(self, t):
        """Va donde le toca **en el parámetro**, así que señala su número.

        Es lo que convierte la cinta en un reloj y no en un adorno: las doce
        horas están repartidas por igual en `u` y la cuenta avanza también en
        `u`, de modo que a la una en punto está sobre el 1.
        """
        if self._camino is None or self._u is None:
            return ()
        f = (t / 3600.0 % 12.0) / 12.0
        i = min(int(np.searchsorted(self._u, f)), len(self._camino) - 1)
        px, py = self._camino[i]
        return (Puesto("cuenta", float(px), float(py), 0.0, 0xFFE9C0, 245),)


ESFERA = Rotulada
