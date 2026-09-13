"""Pellizco — `rotulada`, pero respirando: una vuelta al lazo por minuto.

`eliptica` tarda **una hora** en dar la vuelta al lazo de parámetros, y con
razón: allí la forma **es** el reloj, el azimut del lazo es la hora. El precio
es que a velocidad real no se mueve nada — medido, en un segundo cambia el
0,67% de los píxeles del dial, y la mitad de eso son las cifras.

En `rotulada` ese precio ya no hay por qué pagarlo, y esa es toda la idea de
esta esfera. **La hora la da la cuenta sobre la cinta**, no la forma. Así que
la velocidad del lazo queda libre, y aquí se pone en **una vuelta por minuto**.

Lo que eso destapa es el acontecimiento que `eliptica` esconde. El lazo cruza
el discriminante `4a³ + 27b² = 0` dos veces por vuelta —en las fases 0,389 y
0,611— y el óvalo vive el 22% del recorrido. A una vuelta por hora eso es un
nacimiento cada media hora y no se ve nunca; a una por minuto es **un latido**:
el óvalo se desprende de la rama, vive trece segundos y se reabsorbe.

Y la fase arranca justo en el primer cruce, así que **la curva se pellizca
cuando cambia el minuto**. El segundero es la propia geometría.

Lo demás no se toca: la misma cinta, el mismo reparto por el parámetro
elíptico, los mismos colores. Lo único que cambia es el reloj del lazo.

Con la familia moviéndose de verdad hay sesenta curvas a la vista, y
recalcularlas todas en cada paso sería tirar el trabajo: entre un paso y el
siguiente **cincuenta y nueve son las mismas**, solo que una posición más
viejas. Así que van en un anillo y se calcula una por paso.

Y el color de cada hueco del anillo tampoco cambia nunca: el de delante siempre
es el brillante y el del fondo siempre el apagado. Calcularlos en cada paso
costaba **el 75% del tiempo de la esfera** —sesenta llamadas a `hsv_arr` para
sesenta colores fijos— y sale del perfil, no de mirarlo. Con las dos cosas
cuesta 0,34 ms por paso: es la más barata de las esferas de geometría, y eso
siendo la más viva.

`rotulada` se queda como está: esto es una esfera aparte.
"""

import numpy as np

from ..banda import cinta
from ..esfera import Malla, Puesto, Trazo
from ..lienzo import Lienzo, hsv
from .eliptica import parametros, trozos
from .rotulada import ANCHO_CINTA, Rotulada, parametro

VUELTA = 60.0       # segundos por vuelta al lazo de parámetros
# El primer cruce del discriminante. Empezando ahí, el pellizco cae en el
# segundo cero de cada minuto.
FASE_0 = 0.389
ESTELA = 60         # cuántas curvas del pasado se ven a la vez
# Las curvas viejas van apagadas y detrás: no necesitan los cuatrocientos
# puntos con que se calculan. Solo la de ahora se dibuja entera; las demás, de
# tres en tres. No ahorra geometría —eso está medido, no cambia nada— pero
# manda a pintar un tercio de los vértices, y eso sí: un 12% del tiempo de
# componer un dial de 1080.
PASO_VIEJAS = 3


class Pellizco(Rotulada):
    """La curva rotulada, con el lazo a una vuelta por minuto."""

    NOMBRE = "pellizco"
    POR_SEGUNDO = 12

    def __init__(self, lado):
        Rotulada.__init__(self, lado)
        self._anillo = []       # de la más vieja a la más nueva
        self._paso = None
        self._trazos = ()
        # El aspecto de cada hueco de la estela no cambia nunca: el de delante
        # siempre es el brillante y el del fondo siempre el apagado. Calcularlo
        # en cada paso costaba el 75% del tiempo de la esfera —sesenta llamadas
        # a `hsv_arr` por paso para sesenta colores fijos.
        self._pinta = []
        for i in range(ESTELA):
            f = 1.0 - i / (ESTELA - 1.0)
            self._pinta.append((
                hsv(0.52 + 0.16 * f, 0.72, 0.14 + 0.86 * (1.0 - f) ** 2.2),
                lado * (1.0 + 2.4 * (1.0 - f) ** 3) / 454.0,
                255 if f == 0 else 190))

    # ---------- una forma, la de un paso ----------
    def _fase(self, paso):
        return (FASE_0 + paso / (self.POR_SEGUNDO * VUELTA)) % 1.0

    def _forma(self, paso):
        """Los trozos ya en píxeles, más la rama con su parámetro elíptico."""
        a, b = parametros(self._fase(paso))
        piezas = trozos(a, b)
        if not piezas:
            return (), None, None
        x, y = piezas[-1]
        return ([self._mundo(px, py) for px, py in piezas],
                self._mundo(x, y), parametro(x, a, b))

    # ---------- el anillo ----------
    def trazos(self, t):
        paso = int(round(t * self.POR_SEGUNDO))
        if paso == self._paso:
            return self._trazos
        if self._paso is None or not 0 < paso - self._paso <= ESTELA:
            # Arranque, o salto del reloj virtual: no hay pasado que reciclar.
            self._anillo = [self._forma(paso - k) for k in range(ESTELA - 1, -1, -1)]
        else:
            self._anillo += [self._forma(k)
                             for k in range(self._paso + 1, paso + 1)]
            self._anillo = self._anillo[-ESTELA:]
        self._paso = paso
        self._camino, self._u = self._anillo[-1][1], self._anillo[-1][2]
        self._mallas = None
        self._trazos = self._pintar()
        return self._trazos

    def _pintar(self):
        """Los mismos colores y grosores que `rotulada`: lo que cambia es el
        reloj del lazo, no el aspecto."""
        fuera = []
        for i, (piezas, _, _) in enumerate(self._anillo):
            color, grosor, alfa = self._pinta[i]
            ahora = i == len(self._anillo) - 1
            for pts in piezas:
                fuera.append(Trazo(pts if ahora else pts[::PASO_VIEJAS],
                                   color, grosor, alfa))
        return fuera

    # ---------- la cinta, sobre la curva de ahora ----------
    def mallas(self, t):
        self.trazos(t)                            # deja el anillo al día
        if self._mallas is not None:
            return self._mallas
        if self._camino is None:
            self._mallas = ()
            return self._mallas
        pts, uv, idx = cinta(self._camino, self._u, self.lado * ANCHO_CINTA)
        blanco = np.full((len(pts), 3), 255, np.uint8)
        self._mallas = (Malla("horas", pts, uv, idx, blanco, 255),)
        return self._mallas

    def cuadro(self, t):
        if self._camino is None or self._u is None:
            return ()
        f = (t / 3600.0 % 12.0) / 12.0
        i = min(int(np.searchsorted(self._u, f)), len(self._camino) - 1)
        px, py = self._camino[i]
        return (Puesto("cuenta", float(px), float(py), 0.0, 0xFFE9C0, 245),)

    def capa(self, t):
        lz = Lienzo(self.lado, sup=1)
        lz.texto(self.lado / 2, self.lado * 0.885,
                 "%d:%02d" % (int(t // 3600) % 12 or 12, int(t // 60) % 60),
                 self.f_hora, 0xF2F5F8, 235)
        lz.texto(self.lado / 2, self.lado * 0.945,
                 "se pellizca al cambiar el minuto",
                 self.f_pie, 0x6E86A0)
        return int(t) // 60, lz.array()


ESFERA = Pellizco
