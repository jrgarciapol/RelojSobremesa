"""Curvas célebres, del índice de MacTutor.

<https://mathshistory.st-andrews.ac.uk/Curves/>

Cada entrada es un nombre, una parametrización y el tramo del parámetro. Nada
más: escalarlas y encuadrarlas lo hace `muestrear`, porque cada una vive en su
propio tamaño —la espiral de Arquímedes crece sin parar y la lemniscata cabe en
un cuadrado— y no tiene sentido ajustar sesenta a mano.

Varias tienen **asíntotas**: el cisoide, el estrofoide, el folium. Muestreadas
a lo bruto salen con una raya que cruza la pantalla uniendo los dos lados del
infinito; `muestrear` las corta donde pegan el salto y las encuadra por
percentiles, para que mande la parte interesante y no la rama que se escapa.

Hubo que dejar fuera cinco —la concoide de Nicomedes, la kappa, la cruciforme,
la nariz de bala y el tridente de Newton— porque su parte interesante es
diminuta al lado de sus asíntotas y, se encuadren como se encuadren, salen como
una raya. Un catálogo con cinco palos no es mejor que uno sin ellos.
"""

import math

import numpy as np

TAU = 2 * math.pi


def _pol(r, t):
    """De polares a cartesianas, que es como vienen la mitad de ellas."""
    return r * np.cos(t), r * np.sin(t)


# nombre · parametrización · desde · hasta
CURVAS = [
    ("Circunferencia", lambda t: (np.cos(t), np.sin(t)), 0, TAU),
    ("Elipse", lambda t: (1.6 * np.cos(t), np.sin(t)), 0, TAU),
    ("Astroide", lambda t: (np.cos(t)**3, np.sin(t)**3), 0, TAU),
    ("Cardioide", lambda t: _pol(1 + np.cos(t), t), 0, TAU),
    ("Nefroide", lambda t: (3*np.cos(t) - np.cos(3*t),
                            3*np.sin(t) - np.sin(3*t)), 0, TAU),
    ("Deltoide", lambda t: (2*np.cos(t) + np.cos(2*t),
                            2*np.sin(t) - np.sin(2*t)), 0, TAU),
    ("Lemniscata de Bernoulli",
     lambda t: (np.cos(t) / (1 + np.sin(t)**2),
                np.sin(t) * np.cos(t) / (1 + np.sin(t)**2)), 0, TAU),
    ("Lemniscata de Gerono", lambda t: (np.cos(t), np.sin(t) * np.cos(t)), 0, TAU),
    ("Caracol de Pascal", lambda t: _pol(0.6 + np.cos(t), t), 0, TAU),
    ("Trisectriz de Ceva", lambda t: _pol(1 + 2*np.cos(2*t), t), 0, TAU),

    ("Cicloide", lambda t: (t - np.sin(t), 1 - np.cos(t)), 0, 6*math.pi),
    ("Epicicloide de 5 puntas",
     lambda t: (6*np.cos(t) - np.cos(6*t), 6*np.sin(t) - np.sin(6*t)), 0, TAU),
    ("Hipocicloide de 5 puntas",
     lambda t: (4*np.cos(t) + np.cos(4*t), 4*np.sin(t) - np.sin(4*t)), 0, TAU),
    ("Epitrocoide",
     lambda t: (5*np.cos(t) - 3*np.cos(5*t), 5*np.sin(t) - 3*np.sin(5*t)), 0, TAU),
    ("Hipotrocoide",
     lambda t: (5*np.cos(t) + 3*np.cos(5*t), 5*np.sin(t) - 3*np.sin(5*t)), 0, TAU),
    ("Espirógrafo",
     lambda t: (7*np.cos(t) + 4*np.cos(7*t/4), 7*np.sin(t) - 4*np.sin(7*t/4)),
     0, 8*math.pi),

    ("Rosa de tres pétalos", lambda t: _pol(np.cos(3*t), t), 0, math.pi),
    ("Rosa de cuatro pétalos", lambda t: _pol(np.cos(2*t), t), 0, TAU),
    ("Rosa de cinco pétalos", lambda t: _pol(np.cos(5*t), t), 0, math.pi),
    ("Rosa de ocho pétalos", lambda t: _pol(np.cos(4*t), t), 0, TAU),
    ("Rodonea 7/3", lambda t: _pol(np.cos(7*t/3), t), 0, 6*math.pi),

    ("Espiral de Arquímedes", lambda t: _pol(t, t), 0, 6*math.pi),
    ("Espiral logarítmica", lambda t: _pol(np.exp(0.16*t), t), 0, 8*math.pi),
    ("Espiral de Fermat", lambda t: _pol(np.sqrt(np.abs(t)) * np.sign(t), t),
     -8*math.pi, 8*math.pi),
    ("Espiral hiperbólica", lambda t: _pol(1.0/t, t), 0.35, 10*math.pi),
    ("Lituus", lambda t: _pol(1.0/np.sqrt(t), t), 0.06, 8*math.pi),
    ("Cocleoide", lambda t: _pol(np.sin(t)/t, t), 0.05, 6*math.pi),
    ("Involuta de la circunferencia",
     lambda t: (np.cos(t) + t*np.sin(t), np.sin(t) - t*np.cos(t)), 0, 5*math.pi),
    ("Clotoide", None, 0, 1),          # se calcula aparte: lleva integrales

    ("Catenaria", lambda t: (t, np.cosh(t)), -2.2, 2.2),
    ("Tractriz", lambda t: (t - np.tanh(t), 1.0/np.cosh(t)), -4.5, 4.5),
    ("Bruja de Agnesi", lambda t: (2*t, 2.0/(1 + t*t)), -5, 5),
    ("Serpentina", lambda t: (t, t/(1 + t*t)), -6, 6),
    ("Cúbica de Tschirnhausen",
     lambda t: (3*(t*t - 3), t*(t*t - 3)), -3.2, 3.2),
    ("Folium de Descartes",
     lambda t: (3*t/(1 + t**3), 3*t*t/(1 + t**3)), -20, 20),
    ("Cisoide de Diocles",
     lambda t: (2*t*t/(1 + t*t), 2*t**3/(1 + t*t)), -6, 6),
    ("Estrofoide recto",
     lambda t: ((t*t - 1)/(t*t + 1), t*(t*t - 1)/(t*t + 1)), -5, 5),
    ("Trisectriz de Maclaurin",
     lambda t: ((t*t - 3)/(t*t + 1), t*(t*t - 3)/(t*t + 1)), -6, 6),
    ("Kampyle de Eudoxo",
     lambda t: (1.0/np.cos(t), np.tan(t)/np.cos(t)), -1.15, 1.15),

    ("Bicornio", lambda t: (np.sin(t),
                            np.cos(t)**2 * (2 + np.cos(t)) / (3 + np.sin(t)**2)),
     0, TAU),
    ("Sextica de Cayley", lambda t: _pol(4*np.cos(t/3)**3, t), 0, 6*math.pi),
    ("Nefroide de Freeth", lambda t: _pol(1 + 2*np.sin(t/2), t), 0, 4*math.pi),
    ("Hipopede", lambda t: _pol(np.sqrt(np.maximum(
        4*(1.2 - np.sin(t)**2), 0)), t), 0, TAU),
    ("Óvalo de Cassini", lambda t: _pol(np.sqrt(np.maximum(
        np.cos(2*t) + np.sqrt(np.maximum(1.06 - np.sin(2*t)**2, 0)), 0)), t),
     0, TAU),
    ("Curva de la mariposa", lambda t: _pol(
        np.exp(np.cos(t)) - 2*np.cos(4*t) + np.sin(t/12)**5, t), 0, 24*math.pi),
    ("Superelipse", lambda t: (np.sign(np.cos(t)) * np.abs(np.cos(t))**0.5,
                               np.sign(np.sin(t)) * np.abs(np.sin(t))**0.5),
     0, TAU),
    ("Curva de Talbot", lambda t: (
        (1 + 1.2*np.sin(t)**2) * np.cos(t),
        (1 - 2*0.6 + 1.2*np.sin(t)**2) * np.sin(t)), 0, TAU),
    ("Curva de Lissajous 3:2",
     lambda t: (np.sin(3*t), np.sin(2*t + math.pi/4)), 0, TAU),
    ("Curva de Lissajous 5:4",
     lambda t: (np.sin(5*t), np.sin(4*t + math.pi/3)), 0, TAU),
    ("Trifolio", lambda t: _pol(-np.cos(3*t) * (1 + np.cos(t)) * 0.5
                                - 0.3*np.cos(t), t), 0, TAU),
    ("Curva en forma de ocho", lambda t: (np.sin(2*t), np.sin(t)), 0, TAU),
    ("Pesa", lambda t: (np.sin(t), np.sin(t)**2 * np.cos(t)), 0, TAU),
    ("Cuadratriz de Hipias",
     lambda t: (t / np.tan(t * math.pi / 2), t), 0.001, 0.999),
    ("Bifolio", lambda t: _pol(4 * np.sin(t)**2 * np.cos(t), t), 0, math.pi),
    ("Piriforme", lambda t: (1 + np.sin(t),
                             np.cos(t) * (1 + np.sin(t))), 0, TAU),
    ("Lágrima", lambda t: (np.cos(t), np.sin(t) * np.sin(t/2)**4), 0, TAU),
    ("Hipocicloide de 6 puntas",
     lambda t: (5*np.cos(t) + np.cos(5*t), 5*np.sin(t) - np.sin(5*t)), 0, TAU),
    ("Epicicloide de 3 puntas",
     lambda t: (4*np.cos(t) - np.cos(4*t), 4*np.sin(t) - np.sin(4*t)), 0, TAU),
    ("Curva de Lissajous 7:5",
     lambda t: (np.sin(7*t), np.sin(5*t + math.pi/5)), 0, TAU),
    ("Rodonea 5/2", lambda t: _pol(np.cos(5*t/2), t), 0, 4*math.pi),
    ("Astroide alargada",
     lambda t: (np.cos(t)**3, 1.7 * np.sin(t)**3), 0, TAU),
]


def _clotoide(n):
    """La espiral de Cornu. No tiene fórmula cerrada: son las integrales de
    Fresnel, así que se acumulan numéricamente."""
    s = np.linspace(-4.2, 4.2, n)
    d = s[1] - s[0]
    return (np.cumsum(np.cos(s * s * math.pi / 2)) * d,
            np.cumsum(np.sin(s * s * math.pi / 2)) * d)


LIMITE = 40.0     # más lejos que esto, la rama se va al infinito y se corta


def muestrear(indice, n=1400):
    """(nombre, lista de polilíneas) ya centradas y a escala del cuadrado
    unidad, listas para colocar donde sea.

    Las que tienen asíntota se parten: entre dos muestras que pegan un salto
    grande no hay curva, hay un agujero por el que se escapó al infinito.
    Uniéndolas quedaría una raya cruzando la pantalla.
    """
    nombre, f, t0, t1 = CURVAS[indice % len(CURVAS)]
    if f is None:
        x, y = _clotoide(n)
    else:
        t = np.linspace(t0, t1, n)
        with np.errstate(divide="ignore", invalid="ignore"):
            x, y = f(t)
        x, y = np.asarray(x, float), np.asarray(y, float)

    bien = np.isfinite(x) & np.isfinite(y) & (np.abs(x) < LIMITE) & (np.abs(y) < LIMITE)
    if bien.sum() < 8:
        return nombre, []

    # Encuadrar por PERCENTILES, no por el mínimo y el máximo.
    #
    # Con el rango completo mandan las ramas asintóticas: la concoide, la
    # kappa, la nariz de bala y la curva del diablo salían todas como una raya
    # vertical, porque su parte interesante mide uno y su asíntota mide
    # cuarenta. Recortando por el 3% y el 97% se encuadra el grueso de la curva
    # y las colas se van fuera del cuadro, que es a donde iban de todas formas.
    xb, yb = x[bien], y[bien]
    x0, x1_ = np.percentile(xb, [3, 97])
    y0, y1_ = np.percentile(yb, [3, 97])
    cx, cy = (x0 + x1_) / 2, (y0 + y1_) / 2
    k = 2.0 / max(x1_ - x0, y1_ - y0, 1e-6)
    x, y = (x - cx) * k, (y - cy) * k

    # Lo que se escapa muy lejos ya no aporta: estorba al partir en tramos.
    bien &= (np.abs(x) < 2.6) & (np.abs(y) < 2.6)

    # Cortar donde salta.
    salto = np.hypot(np.diff(x), np.diff(y)) > 0.30
    corte = np.flatnonzero(salto | ~bien[:-1] | ~bien[1:]) + 1

    piezas = []
    for tramo in np.split(np.arange(len(x)), corte):
        tramo = tramo[bien[tramo]]
        if len(tramo) > 6:
            piezas.append(np.stack([x[tramo], y[tramo]], axis=1))
    return nombre, piezas


NOMBRES = [c[0] for c in CURVAS]
