"""Trazada — la curva se dibuja sola, y lo dibujado se apaga poco a poco.

`paseo` pone un cometa a recorrer una curva que ya está ahí. Aquí no hay curva
de antemano y no hay cometa: **la punta va trazando y lo que queda detrás se
desvanece**, como el fósforo de un osciloscopio.

Y mientras traza, **los parámetros se mueven**. Eso es lo que hace la esfera, y
no es un adorno: cuando la punta da la vuelta y regresa, la curva ya no es la
misma que dejó, así que el trazo nuevo no cae encima del viejo. Lo que se ve no
es una curva con estela — es **la historia de una familia de curvas**, con el
presente brillante y el pasado apagándose. La estela no se cierra nunca.

De ahí salen las dos decisiones que sostienen todo:

**El encuadre se calcula una vez por curva, no en cada instante.** Se toman las
esquinas del cajón de parámetros por los que va a pasar y se encuadran todas
juntas. Encuadrando cada instante por su cuenta, la curva se quedaría quieta y
sería el marco el que se movería — justo lo contrario de lo que se quiere ver.

**Cada paso dibuja su trocito con los parámetros de su instante.** Por eso se
usa `curvas_famosas.en()` y no `muestrear()`: hace falta el punto en bruto, con
el encuadre puesto aparte y a mano.

`paseo` se queda como está: esto es una esfera aparte.
"""

import os

import numpy as np

from ..curvas_famosas import CURVAS, encuadre, en, formula
from ..esfera import Esfera, Trazo
from ..lienzo import Lienzo, hsv, tipo
from .. import variacion

ESCALA = 1.05       # de la curva normalizada al dial
SUBPASOS = 5        # muestras de curva que se añaden en cada paso
MUESTRAS_CAJA = 900     # para calcular el encuadre de la curva del minuto

# El fichero que escribe el laboratorio. Si está, manda; si no, la de partida.
CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "..", "curvas.json")


class Trazada(Esfera):
    """La curva trazándose sola mientras sus parámetros se mueven."""

    NOMBRE = "trazada"
    POR_SEGUNDO = 20

    def __init__(self, lado):
        Esfera.__init__(self, lado)
        self.cfg = (variacion.cargar(CONFIG) if os.path.exists(CONFIG)
                    else variacion.por_defecto())
        self.f_hora = tipo("RobotoMono-Bold.ttf", lado * 40 / 454.0)
        self.f_nombre = tipo("RobotoMono-Bold.ttf", lado * 19 / 454.0)
        self._lado_formula = lado

        self.pasos = max(30, int(self.cfg["persistencia"] * self.POR_SEGUNDO))
        n = self.pasos * SUBPASOS
        self._anillo = np.zeros((n, 2), np.float32)
        self._cursor = 0
        self._paso = None
        self._trazos = ()
        self._cual = None

        # El color de cada punto de la estela depende solo de su antigüedad, y
        # eso no cambia nunca. Calcularlo por fotograma fue lo que en
        # `pellizco` se llevaba el 75% del tiempo.
        edad = np.linspace(1.0, 0.0, n)         # 1 = el más viejo, 0 = ahora
        self._tinta = np.empty((n, 3), np.uint8)
        for i, e in enumerate(edad):
            c = hsv(0.52 + 0.20 * e, 0.62 - 0.25 * (1 - e),
                    (1.0 - e) ** 2.0 * 0.94 + 0.02)
            self._tinta[i] = ((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF)

    # ---------- la curva del minuto ----------
    def _curva(self, minuto):
        """Índice, nombre y encuadre. El encuadre abarca todo el recorrido de
        los parámetros, así que vale para el minuto entero."""
        if self._cual == minuto:
            return self._caja
        i = minuto % len(CURVAS)
        xs, ys = [], []
        for v in variacion.extremos(self.cfg, i):
            x, y = en(i, np.linspace(CURVAS[i].t0, CURVAS[i].t1, MUESTRAS_CAJA), v)
            xs.append(x)
            ys.append(y)
        caja = encuadre(np.concatenate(xs), np.concatenate(ys))
        self._cual = minuto
        self._caja = (i, CURVAS[i].nombre, caja or (0.0, 0.0, 1.0))
        return self._caja

    def _trocito(self, paso):
        """El trozo de curva que se traza en este paso, ya en píxeles."""
        t = paso / float(self.POR_SEGUNDO)
        i, _, (cx, cy, k) = self._curva(int(t // 60))
        c = CURVAS[i]

        # La punta recorre el tramo de `t` de la curva una vez por vuelta.
        f0 = ((paso - 1) / float(self.POR_SEGUNDO)) / self.cfg["vuelta"] % 1.0
        f1 = t / self.cfg["vuelta"] % 1.0
        if f1 < f0:                      # dio la vuelta: se corta aquí
            f0 = 0.0
        u = c.t0 + (c.t1 - c.t0) * np.linspace(f0, f1, SUBPASOS)

        x, y = en(i, u, variacion.valores(self.cfg, i, t))
        r = self.r * ESCALA
        return np.stack([self.r + (x - cx) * k * r / 2.0,
                         self.r - (y - cy) * k * r / 2.0], axis=1).astype(np.float32)

    # ---------- el anillo ----------
    def trazos(self, t):
        paso = int(round(t * self.POR_SEGUNDO))
        if paso == self._paso:
            return self._trazos
        if self._paso is None or not 0 < paso - self._paso <= self.pasos:
            # Arranque, o salto del reloj: se rellena el pasado entero.
            for k in range(paso - self.pasos + 1, paso + 1):
                self._meter(k)
        else:
            for k in range(self._paso + 1, paso + 1):
                self._meter(k)
        self._paso = paso
        self._trazos = self._pintar()
        return self._trazos

    def _meter(self, paso):
        a = self._cursor * SUBPASOS
        self._anillo[a:a + SUBPASOS] = self._trocito(paso)
        self._cursor = (self._cursor + 1) % self.pasos

    def _pintar(self):
        """La estela, partida donde pega un salto.

        Salta en tres sitios: cuando la punta da la vuelta y vuelve al
        principio de la curva, cuando cambia de curva al cambiar el minuto y en
        las asíntotas. Unir esos puntos dejaría una raya cruzando el dial.
        """
        a = self._cursor * SUBPASOS
        pts = np.concatenate([self._anillo[a:], self._anillo[:a]])
        g = self.lado / 454.0

        corte = np.flatnonzero(np.hypot(*np.diff(pts, axis=0).T)
                               > 0.22 * self.lado) + 1
        fuera = []
        for tramo in np.split(np.arange(len(pts)), corte):
            if len(tramo) < 3:
                continue
            fuera.append(Trazo(pts[tramo], self._tinta[tramo], 2.3 * g, 245))
        return fuera

    # ---------- la hora, el nombre y la fórmula ----------
    def _cabe(self, lz, texto, alto):
        """El cuerpo más grande con el que ese texto entra en el dial.

        Las fórmulas van de doce a sesenta caracteres —`r = t^n` y el
        espirógrafo entero— y con un cuerpo fijo o se sale una o queda ridícula
        la otra.
        """
        for cuerpo in (alto, alto * 0.85, alto * 0.72, alto * 0.62):
            f = tipo("RobotoMono-Bold.ttf", cuerpo)
            if lz.ancho_de(texto, f) <= self.lado * 0.94:
                return f
        return tipo("RobotoMono-Bold.ttf", alto * 0.52)

    def capa(self, t):
        paso = int(round(t * self.POR_SEGUNDO))
        minuto = int(t // 60)
        i, nombre, _ = self._curva(minuto)
        f, vals = formula(i, variacion.valores(self.cfg, i, paso / float(self.POR_SEGUNDO)))

        lz = Lienzo(self.lado, sup=1)
        lz.texto(self.lado / 2, self.lado * 0.828,
                 "%d:%02d" % (int(t // 3600) % 12 or 12, minuto % 60),
                 self.f_hora, 0xF2F5F8, 230)
        lz.texto(self.lado / 2, self.lado * 0.888, nombre.upper(),
                 self.f_nombre, 0x8FB0C4)
        lz.texto(self.lado / 2, self.lado * 0.932, f,
                 self._cabe(lz, f, self.lado * 15 / 454.0), 0x6E86A0)
        if vals:
            lz.texto(self.lado / 2, self.lado * 0.968, vals,
                     self._cabe(lz, vals, self.lado * 15 / 454.0), 0xB08A4A)
        # Los valores cambian sin parar, así que la capa se rehace a menudo:
        # dos veces por segundo basta para que las cifras no den saltos.
        return (minuto, paso // (self.POR_SEGUNDO // 2)), lz.array()


ESFERA = Trazada
