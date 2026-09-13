"""Curvas elípticas.

Inspirado en el proyecto de Nadir Hajouji y Steve Trettel
(<https://elliptic-curves.art>), que las dibuja con trazado de rayos.

La conexión con un reloj no es decorativa, es estructural: **una curva elíptica
es un toro**. Sobre los complejos, `E` es el cociente `C/L` de una retícula, y
un toro son exactamente dos ángulos — que es exactamente lo que es un reloj. La
ley de grupo de la curva no es más que sumar ángulos.

Dos esferas, que son las dos caras de la misma ecuación:

    eliptica   el lugar REAL de  y² = x³ + ax + b,  con (a, b) girando
    finita     la misma curva sobre `F_p`, recorrida por su ley de grupo
"""

import math

import numpy as np

from ..esfera import Esfera, Trazo
from ..lienzo import Lienzo, hsv, tipo
from .digital import Digital


def _color(tono, sat, brillo, n):
    """Un array (n, 3) de un solo color, que es lo que espera `Trazo`."""
    c = hsv(tono, sat, brillo)
    return np.tile(np.uint8([(c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF]), (n, 1))


# =====================================================================
#  eliptica — el lugar real, como familia
# =====================================================================

# Ventana del plano. Medidas las raíces a lo largo de todo el ciclo, nunca
# salen de [-1.42, 1.42]; lo que necesita sitio es la RAMA, que se abre hacia
# la derecha desde la raíz mayor. Con la ventana cortada en 1.55 la rama se
# quedaba en un muñón pegado al borde a media tarde.
X0, X1 = -2.60, 2.60
YTOPE = 2.40

ESTELA = 16            # cuántas curvas de la familia se ven a la vez
ANCHO_ESTELA = 0.10    # qué fracción del ciclo abarcan


def parametros(fase):
    """(a, b) recorriendo un lazo cerrado en el espacio de parámetros.

    El lazo está elegido para **cruzar el discriminante** `4a³ + 27b² = 0`.
    Ese cruce no es un detalle: es donde la curva se pellizca y el óvalo nace o
    muere. Es el acontecimiento de la esfera, y ocurre una vez por hora.
    """
    return (1.3 * math.cos(2 * math.pi * fase) - 0.5,
            1.1 * math.sin(2 * math.pi * fase))


def _raices(a, b, c=0.0):
    """Raíces reales de x³ + ax + (b - c), de menor a mayor."""
    r = np.roots([1.0, 0.0, a, b - c])
    return np.sort(r[np.abs(r.imag) < 1e-9].real)


def _lazo(a, b, x0, x1, n=200):
    """El trozo de curva sobre [x0, x1], recorrido de una tirada.

    `x0` es siempre una raíz, donde y = 0. El recorrido entra por la rama
    NEGATIVA desde `x1`, pasa por la raíz y sale por la positiva. Así el trazo
    queda abierto por los dos extremos y **no hay segmento de cierre**.

    Hacerlo al revés —ida por +y y vuelta por -y— es lo que sale escribir, y
    deja una raya vertical en `x1` uniendo las dos puntas. En el óvalo no se
    nota, porque los dos extremos son raíces y el salto mide cero; en la rama,
    que se corta donde acaba la ventana, es una barra luminosa pegada al borde.

    El muestreo va con **espaciado coseno**: en las raíces la tangente es
    vertical, y con puntos equiespaciados en x el canto sale a escalones.
    """
    u = np.linspace(0.0, 1.0, n)
    x = x0 + (x1 - x0) * (1.0 - np.cos(math.pi * u)) / 2.0
    y = np.sqrt(np.maximum(x**3 + a * x + b, 0.0))
    return np.concatenate([x[::-1], x]), np.concatenate([-y[::-1], y])


def trozos(a, b):
    """Los uno o dos trozos del lugar real que caben en la ventana."""
    r = _raices(a, b)
    if not len(r):
        return []
    alto = _raices(a, b, YTOPE * YTOPE)      # dónde se sale por arriba
    tope = min(alto[-1], X1) if len(alto) else X1

    if len(r) == 3:
        return [_lazo(a, b, r[0], r[1]),     # el óvalo
                _lazo(a, b, r[2], tope)]     # la rama
    return [_lazo(a, b, r[-1], tope)]


class Eliptica(Digital):
    """El lugar real de `y² = x³ + ax + b`, dibujado como **familia**.

    Una sola curva es una línea sola en una pantalla grande. Lo que se dibuja
    son las últimas dieciséis: la de ahora encendida y las anteriores
    apagándose, así que la esfera enseña de dónde viene la forma y hacia dónde
    va. La familia entera da una vuelta por hora, y al cruzar el discriminante
    se la ve pellizcarse y soltar el óvalo.
    """

    NOMBRE = "eliptica"

    # La curva es la protagonista: la hora se retira a un blanco velado y las
    # líneas se ven a través de las cifras.
    COLOR_TIME  = 0xFFFFFF
    COLOR_GREEN = 0x64D8C6
    COLOR_MES   = 0x6E7A93
    ALFA = 170

    # La familia da UNA VUELTA POR HORA. A 30 fps eso son 108.000 fotogramas
    # por vuelta: entre uno y el siguiente la curva no se mueve nada que se
    # pueda ver, y recalcularla treinta veces por segundo cuesta 3,4 ms —unos
    # 34 en la Pi, justo el límite de los 30 fps sin margen ninguno.
    #
    # Con dos recálculos por segundo salen 7.200 formas distintas por vuelta,
    # de sobra para que se vea fluido, y el coste medio baja quince veces. Es
    # el mismo principio que `capa`: no rehacer lo que no ha cambiado.
    POR_SEGUNDO = 2

    def __init__(self, lado):
        Digital.__init__(self, lado)
        self._clave = None
        self._trazos = ()

    def _mundo(self, x, y):
        """Plano matemático -> píxeles del dial, con la escala del eje x."""
        k = self.lado / (X1 - X0)
        return np.stack([(x - X0) * k,
                         self.r - y * k], axis=1).astype(np.float32)

    def trazos(self, t):
        clave = round(t * self.POR_SEGUNDO)
        if clave != self._clave:
            self._clave = clave
            self._trazos = self._calcular(clave / float(self.POR_SEGUNDO))
        return self._trazos

    def _calcular(self, t):
        fase = (t / 3600.0) % 1.0
        fuera = []
        # De la más vieja a la más nueva, para que la de ahora quede encima.
        for k in range(ESTELA - 1, -1, -1):
            f = k / (ESTELA - 1.0)                    # 0 = ahora, 1 = la más vieja
            a, b = parametros(fase - f * ANCHO_ESTELA)
            brillo = 0.14 + 0.86 * (1.0 - f) ** 2.2
            grosor = self.lado * (1.0 + 2.4 * (1.0 - f) ** 3) / 454.0
            tono = 0.52 + 0.16 * f                    # del cian al violeta
            for x, y in trozos(a, b):
                pts = self._mundo(x, y)
                fuera.append(Trazo(pts, _color(tono, 0.72, brillo, len(pts)),
                                   grosor, 255 if k == 0 else 190))
        return fuera


# =====================================================================
#  finita — la ley de grupo sobre F_p
# =====================================================================

# Un primo por hora. Pequeños a propósito: el dibujo lo hacen las cuerdas, no
# la cantidad de puntos, y con p grande el recorrido se vuelve una maraña.
PRIMOS = (23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71)


def _suma(P, Q, a, p):
    """La ley de grupo. `None` es el punto del infinito, el neutro."""
    if P is None:
        return Q
    if Q is None:
        return P
    x1, y1 = P
    x2, y2 = Q
    if x1 == x2 and (y1 + y2) % p == 0:
        return None
    if P == Q:
        lam = (3 * x1 * x1 + a) * pow(2 * y1, -1, p) % p
    else:
        lam = (y2 - y1) * pow(x2 - x1, -1, p) % p
    x3 = (lam * lam - x1 - x2) % p
    return x3, (lam * (x1 - x3) - y1) % p


def _pasos(P, a, b, p):
    """`P, 2P, 3P, ...` hasta volver al principio o pasar por el infinito."""
    pasos, Q = [P], P
    for _ in range(2 * p + 8):
        Q = _suma(Q, P, a, p)
        if Q is None:                        # pasó por el infinito: se cierra
            pasos.append(P)
            break
        pasos.append(Q)
        if Q == P:
            break
    return pasos


def orbita(p, a, b):
    """El recorrido de multiplos del generador de **mayor orden**.

    Esto es lo que hace bello el dibujo, y no los puntos sueltos: la ley de
    grupo va saltando por la curva de una forma que parece caprichosa y no lo
    es, y uniendo saltos consecutivos con una cuerda sale una figura de hilos.

    Buscar el mejor generador y no el primero que aparezca no es refinamiento:
    a las 5:41 el primer punto de la curva sobre F43 da un recorrido de
    **cuatro** pasos —una raya— y el mejor da **51**. La diferencia entre una
    figura y nada. Cuesta unos milisegundos y solo se hace una vez por minuto.
    """
    mejor = []
    for x in range(p):
        d = (x * x * x + a * x + b) % p
        for y in range(p):
            if y * y % p == d:
                r = _pasos((x, y), a, b, p)
                if len(r) > len(mejor):
                    mejor = r
                break                        # basta un punto por cada x
    return np.array(mejor, float) if mejor else np.zeros((0, 2))


class Finita(Esfera):
    """`y² = x³ + ax + b` sobre `F_p`, recorrida por su ley de grupo.

    El primo lo pone la hora y el coeficiente `a` el minuto, así que **cada
    minuto es una figura distinta**: 12 x 60 y ninguna se repite. La hora se
    lee en la densidad, el minuto en el dibujo.
    """

    NOMBRE = "finita"
    MARGEN = 0.09

    def __init__(self, lado):
        Esfera.__init__(self, lado)
        self.f_hora = tipo("Barriecito-Regular.ttf", lado * 120 / 454.0)
        self.f_pie = tipo("RobotoMono-Bold.ttf", lado * 19 / 454.0)

    def capa(self, t):
        """Solo la hora y el pie: las cuerdas van en `trazos`, por debajo."""
        hora, minuto = int(t // 3600) % 24, int(t // 60) % 60
        lz = Lienzo(self.lado, sup=1)
        p = PRIMOS[hora % 12]
        lz.texto(self.lado / 2, self.lado * 0.50,
                 "%d:%02d" % (hora % 12 or 12, minuto), self.f_hora,
                 0xFFFFFF, 215)
        lz.texto(self.lado / 2, self.lado * 0.915,
                 "y² = x³ + %dx + 1   sobre F%d" % (minuto, p),
                 self.f_pie, 0x8DA2B8)
        return int(t // 60), lz.array()

    def trazos(self, t):
        hora, minuto = int(t // 3600) % 24, int(t // 60) % 60
        p = PRIMOS[hora % 12]
        pts = orbita(p, minuto, 1)
        if len(pts) < 2:
            return ()

        util = self.lado * (1.0 - 2 * self.MARGEN)
        xy = (self.lado * self.MARGEN + pts / (p - 1.0) * util).astype(np.float32)

        # El tono avanza con el recorrido: se ve por dónde empezó y por dónde
        # va, que es la mitad de la gracia.
        u = np.linspace(0.0, 1.0, len(xy))
        col = np.empty((len(xy), 3), np.uint8)
        for i, uu in enumerate(u):
            c = hsv(0.48 + 0.34 * uu, 0.68, 1.0)
            col[i] = ((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF)

        g = self.lado / 454.0
        return (Trazo(xy, col, 5.0 * g, 55),      # el halo
                Trazo(xy, col, 1.7 * g, 235))     # la cuerda


ESFERA = Eliptica
