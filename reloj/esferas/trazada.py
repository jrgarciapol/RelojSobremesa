"""Trazada — la curva se dibuja sola, y las veinte del minuto se quedan.

`paseo` pone un cometa a recorrer una curva que ya está ahí. Aquí no hay curva
de antemano y no hay cometa: **la punta va trazando**, y cuando termina de
recorrer la curva entera **los parámetros pegan un salto** y empieza a trazar
la siguiente. Las anteriores no se borran: se quedan detrás, apagándose.

Eso es lo que hace la esfera, y no es un adorno. Lo que se ve no es una curva
con estela — es **una familia entera a la vista**, con el presente brillante y
el pasado apagándose, como en `pellizco` y por eso con sus mismos azules.

De ahí salen las cuatro decisiones que sostienen todo:

**El parámetro no se mueve mientras se dibuja.** Si se moviera, cada trazada
saldría torcida —el principio con unos valores y el final con otros— y no sería
la curva de nadie. Quieto, cada trazada **es** una curva de la familia, y lo
que se compara al verlas juntas son curvas de verdad.

**El bucle cierra.** Veinte trazadas por minuto, y la vigésima deja los
parámetros justo donde los cogió la primera. Para eso los multiplicadores se
redondean a vueltas enteras (`variacion.ciclos`): 0,618 y 1,618 quedan en 1 y
2, se pierde la inconmensurabilidad —que era para que una estela continua no se
repitiera— y se gana que el bucle vuelva al principio sin costura.

**Veinte, porque es lo que cabe en el minuto.** Cada curva está en pantalla un
minuto; la trazada dura `60/20 = 3 s`. Así el minuto se ve **llenarse**: empieza
con una sola curva y termina con la familia entera, y al cambiar de curva la
pizarra queda limpia. El segundero es el propio dibujo.

**El encuadre se calcula una vez por minuto, sobre las veinte.** No sobre las
esquinas del cajón de parámetros, que sobran: sobre los veinte juegos de
valores que de verdad se van a dibujar. Encuadrando cada trazada por su cuenta,
la curva se quedaría quieta y sería el marco el que se movería — justo lo
contrario de lo que se quiere ver.

`paseo` se queda como está: esto es una esfera aparte.
"""

import os

import numpy as np

from ..curvas_famosas import CURVAS, encuadre, en, formula
from ..esfera import Esfera, Trazo
from ..lienzo import Lienzo, hsv, tipo
from .. import variacion

ESCALA = 1.05       # de la curva normalizada al dial
MUESTRAS = 900      # puntos de una trazada completa
# Las trazadas viejas van apagadas y detrás: no necesitan los novecientos
# puntos con que se calculan. Solo la que se está dibujando va entera. Es el
# mismo reparto que en `pellizco`, y por lo mismo: no ahorra geometría, manda a
# pintar un tercio de los vértices.
PASO_VIEJAS = 3
# Un salto mayor que esto entre dos puntos seguidos no es curva, es una
# asíntota: hay que partir ahí o queda una raya cruzando el dial.
SALTO = 0.22

# El fichero que escribe el laboratorio. Si está, manda; si no, la de partida.
CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "..", "curvas.json")


def _partir(pts, umbral):
    """Los tramos de una polilínea, cortados donde pega un salto."""
    if len(pts) < 3:
        return ()
    corte = np.flatnonzero(np.hypot(*np.diff(pts, axis=0).T) > umbral) + 1
    return tuple(pts[t] for t in np.split(np.arange(len(pts)), corte)
                 if len(t) >= 3)


class Trazada(Esfera):
    """La familia entera del minuto, trazada de una en una."""

    NOMBRE = "trazada"
    POR_SEGUNDO = 20

    def __init__(self, lado):
        Esfera.__init__(self, lado)
        self.cfg = (variacion.cargar(CONFIG) if os.path.exists(CONFIG)
                    else variacion.por_defecto())
        self.f_hora = tipo("RobotoMono-Bold.ttf", lado * 40 / 454.0)
        self.f_nombre = tipo("RobotoMono-Bold.ttf", lado * 19 / 454.0)

        # Cuántas trazadas caben en el minuto. `vuelta` es una petición, no una
        # orden: se redondea a un número entero de trazadas por minuto para que
        # el bucle cierre justo cuando cambia la curva.
        self.cuantas = min(40, max(4, int(round(variacion.BASE
                                                / max(0.5, self.cfg["vuelta"])))))
        self.dura = 60.0 / self.cuantas

        # El aspecto de cada hueco de la estela no cambia nunca: el de delante
        # siempre es el brillante y el del fondo siempre el apagado. Son los
        # colores de `pellizco`, indexados por EDAD —0 es la que se está
        # trazando ahora— en vez de por posición en el anillo, porque aquí el
        # anillo empieza vacío en cada minuto y se va llenando.
        self._pinta = []
        for edad in range(self.cuantas):
            f = edad / (self.cuantas - 1.0)
            self._pinta.append((
                hsv(0.52 + 0.16 * f, 0.72, 0.14 + 0.86 * (1.0 - f) ** 2.2),
                lado * (1.0 + 2.4 * (1.0 - f) ** 3) / 454.0,
                255 if edad == 0 else 190))

        self._cual = None       # el minuto que hay montado
        self._hechas = []       # trazadas completas, de la más vieja a la nueva
        self._clave = None
        self._trazos = ()

    # ---------- la curva del minuto ----------
    def _curva(self, minuto):
        """Índice, nombre y encuadre del minuto, montados una sola vez.

        El encuadre sale de las trazadas que de verdad se van a dibujar, no de
        las esquinas del cajón de parámetros: como los valores recorren una
        figura dentro del cajón y no el cajón entero, encuadrar por las
        esquinas dejaba la curva más pequeña de lo que hace falta.
        """
        if self._cual == minuto:
            return self._caja
        i = minuto % len(CURVAS)
        c = CURVAS[i]
        u = np.linspace(c.t0, c.t1, MUESTRAS)
        xs, ys = [], []
        for j in range(self.cuantas):
            x, y = en(i, u, variacion.valores_paso(self.cfg, i, j, self.cuantas))
            xs.append(x)
            ys.append(y)
        caja = encuadre(np.concatenate(xs), np.concatenate(ys))
        self._cual = minuto
        self._caja = (i, c.nombre, caja or (0.0, 0.0, 1.0))
        self._hechas = []
        self._clave = None
        return self._caja

    def _trazar(self, i, caja, j, parte=1.0):
        """La trazada `j` del bucle, dibujada hasta la fracción `parte`."""
        c = CURVAS[i]
        n = MUESTRAS if parte >= 1.0 else max(2, int(MUESTRAS * parte))
        u = np.linspace(c.t0, c.t0 + (c.t1 - c.t0) * min(1.0, parte), n)
        x, y = en(i, u, variacion.valores_paso(self.cfg, i, j, self.cuantas))
        cx, cy, k = caja
        r = self.r * ESCALA
        return np.stack([self.r + (x - cx) * k * r / 2.0,
                         self.r - (y - cy) * k * r / 2.0], axis=1).astype(np.float32)

    # ---------- el reparto del minuto ----------
    def _donde(self, t):
        """Minuto, trazada dentro del minuto y cuánto lleva dibujada."""
        minuto = int(t // 60)
        dentro = t - minuto * 60.0
        j = min(self.cuantas - 1, int(dentro / self.dura))
        return minuto, j, (dentro - j * self.dura) / self.dura

    def trazos(self, t):
        minuto, j, parte = self._donde(t)
        i, _, caja = self._curva(minuto)

        # Las completas se calculan una vez y se guardan ya partidas y
        # diezmadas: entre un fotograma y el siguiente no cambian.
        while len(self._hechas) < j:
            k = len(self._hechas)
            pts = self._trazar(i, caja, k)
            self._hechas.append(tuple(p[::PASO_VIEJAS]
                                      for p in _partir(pts, SALTO * self.lado)))

        # Y la de ahora, entera y en cada fotograma: es la que se mueve.
        clave = (minuto, j, int(parte * MUESTRAS))
        if clave == self._clave:
            return self._trazos
        self._clave = clave

        fuera = []
        # De la más vieja a la más nueva, para que la nueva quede encima.
        for k, tramos in enumerate(self._hechas):
            color, grosor, alfa = self._pinta[min(j - k, self.cuantas - 1)]
            for pts in tramos:
                fuera.append(Trazo(pts, color, grosor, alfa))
        color, grosor, alfa = self._pinta[0]
        for pts in _partir(self._trazar(i, caja, j, parte), SALTO * self.lado):
            fuera.append(Trazo(pts, color, grosor, alfa))
        self._trazos = fuera
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
        minuto, j, _ = self._donde(t)
        i, nombre, _ = self._curva(minuto)
        f, vals = formula(i, variacion.valores_paso(self.cfg, i, j, self.cuantas))

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
        # Los valores solo cambian al saltar de trazada, así que la capa se
        # rehace veinte veces por minuto y no dos por segundo.
        return (minuto, j), lz.array()


ESFERA = Trazada
