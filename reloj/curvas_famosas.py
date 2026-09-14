"""Curvas célebres, del índice de MacTutor.

<https://mathshistory.st-andrews.ac.uk/Curves/>

Cada curva se guarda como **texto**: `x` e `y` (o `r`) escritos como se
escribirían en un papel, más sus parámetros con el rango donde tienen sentido.

Eso no es una floritura, es lo que sostiene el resto. La fórmula que se enseña
en la esfera y en el laboratorio **es la definición**, no una copia de ella, así
que no pueden discrepar. Y el navegador puede evaluar las mismas sesenta y una
curvas con los parámetros que sea sin que nadie las reescriba en JavaScript: el
mismo texto lo evalúan numpy y `Math`, cada uno con su tabla de funciones. Es la
tercera vez en este proyecto que aparece el problema de tener lo mismo escrito
dos veces; esta es la única solución que lo cierra del todo.

**Los parámetros son de forma, no de escala.** Como `muestrear` normaliza el
tamaño y el centro, un parámetro que solo multiplica se vuelve invisible. El
radio de una circunferencia no se ve; la razón de los ejes de una elipse, sí.
Por eso la circunferencia es la única sin parámetros: no tiene ninguna libertad
de forma, y fingir una sería mentir.

**Los valores por defecto son los de siempre.** Cada uno reproduce exactamente
la curva que había antes de parametrizar el catálogo, para que `paseo` siga
dibujando lo mismo — comprobado lámina a lámina.

Varias tienen **asíntotas**: el cisoide, el estrofoide, el folium. Muestreadas
a lo bruto salen con una raya que cruza la pantalla uniendo los dos lados del
infinito; `muestrear` las corta donde pegan el salto y las encuadra por
percentiles, para que mande la parte interesante y no la rama que se escapa.

Hubo que dejar fuera cinco —la concoide de Nicomedes, la kappa, la cruciforme,
la nariz de bala y el tridente de Newton— porque su parte interesante es
diminuta al lado de sus asíntotas y, se encuadren como se encuadren, salen como
una raya. Un catálogo con cinco palos no es mejor que uno sin ellos.

Las fórmulas van en ASCII a propósito: la Roboto Mono del proyecto no trae
alfabeto griego —`toro` ya se topó con ello— y una fórmula con dos huecos donde
deberían ir `pi` y `theta` es peor que una escrita a máquina.
"""

import math
from collections import namedtuple

import numpy as np

PI = math.pi
TAU = 2 * math.pi

# Un parámetro: la letra con que sale en la fórmula, su valor de siempre y el
# rango dentro del que tiene sentido moverlo.
Par = namedtuple("Par", "letra defecto minimo maximo")

# Una curva: cómo se llama, sus expresiones, sus parámetros y el tramo de `t`.
# `expr` es {"x":..., "y":...} o {"r":...}, o None para la clotoide, que no
# tiene fórmula cerrada.
Curva = namedtuple("Curva", "nombre expr pars t0 t1")


def X(x, y):
    return {"x": x, "y": y}


def R(r):
    return {"r": r}


def _pot(v, n):
    """`v` elevado a `n` conservando el signo.

    Con exponentes no enteros `(-0.5) ** 2.3` es un nan, y en cuanto un
    parámetro deja de ser entero media docena de curvas se quedaban sin la
    mitad negativa. Elevando el valor absoluto y devolviendo el signo, la
    fórmula sigue valiendo y la curva no se parte.
    """
    return np.sign(v) * np.abs(v) ** n


# Las funciones que puede usar una expresión. La misma lista, con los mismos
# nombres, se le da al navegador en el laboratorio.
FUNCIONES = {
    "cos": np.cos, "sin": np.sin, "tan": np.tan, "exp": np.exp,
    "sqrt": np.sqrt, "cosh": np.cosh, "sinh": np.sinh, "tanh": np.tanh,
    "abs": np.abs, "sign": np.sign, "max": np.maximum, "min": np.minimum,
    "atan": np.arctan, "pot": _pot, "pi": PI,
}


def _c(nombre, expr, pars, t0=0.0, t1=TAU):
    return Curva(nombre, expr, tuple(Par(*p) for p in pars), t0, t1)


CURVAS = [
    _c("Circunferencia", X("cos(t)", "sin(t)"), ()),
    _c("Elipse", X("a*cos(t)", "sin(t)"), (("a", 1.6, 0.3, 3.0),)),
    _c("Astroide", X("pot(cos(t),n)", "b*pot(sin(t),n)"),
       (("n", 3.0, 0.4, 6.0), ("b", 1.0, 0.4, 2.5))),
    _c("Cardioide", R("1 + b*cos(t)"), (("b", 1.0, 0.0, 2.5),)),
    _c("Nefroide", X("k*cos(t) - cos(k*t)", "k*sin(t) - sin(k*t)"),
       (("k", 3.0, 1.5, 7.0),)),
    _c("Deltoide", X("k*cos(t) + cos(k*t)", "k*sin(t) - sin(k*t)"),
       (("k", 2.0, 1.5, 7.0),)),
    _c("Lemniscata de Bernoulli",
       X("cos(t)/(1 + c*sin(t)**2)", "sin(t)*cos(t)/(1 + c*sin(t)**2)"),
       (("c", 1.0, 0.2, 3.0),)),
    _c("Lemniscata de Gerono", X("cos(t)", "b*sin(t)*cos(t)"),
       (("b", 1.0, 0.3, 2.5),)),
    _c("Caracol de Pascal", R("a + cos(t)"), (("a", 0.6, 0.0, 2.0),)),
    _c("Trisectriz de Ceva", R("1 + b*cos(k*t)"),
       (("b", 2.0, 0.5, 3.0), ("k", 2.0, 1.0, 5.0))),

    _c("Cicloide", X("t - a*sin(t)", "1 - a*cos(t)"), (("a", 1.0, 0.2, 2.0),),
       0, 6 * PI),
    _c("Epicicloide de 5 puntas", X("k*cos(t) - cos(k*t)", "k*sin(t) - sin(k*t)"),
       (("k", 6.0, 3.0, 9.0),)),
    _c("Hipocicloide de 5 puntas", X("k*cos(t) + cos(k*t)", "k*sin(t) - sin(k*t)"),
       (("k", 4.0, 2.0, 8.0),)),
    _c("Epitrocoide", X("a*cos(t) - b*cos(a*t)", "a*sin(t) - b*sin(a*t)"),
       (("a", 5.0, 2.0, 8.0), ("b", 3.0, 0.5, 5.0))),
    _c("Hipotrocoide", X("a*cos(t) + b*cos(a*t)", "a*sin(t) - b*sin(a*t)"),
       (("a", 5.0, 2.0, 8.0), ("b", 3.0, 0.5, 5.0))),
    _c("Espirógrafo", X("a*cos(t) + b*cos(a*t/b)", "a*sin(t) - b*sin(a*t/b)"),
       (("a", 7.0, 3.0, 11.0), ("b", 4.0, 1.0, 6.0)), 0, 8 * PI),

    _c("Rosa de tres pétalos", R("cos(k*t)"), (("k", 3.0, 1.0, 9.0),), 0, PI),
    _c("Rosa de cuatro pétalos", R("cos(k*t)"), (("k", 2.0, 1.0, 9.0),)),
    _c("Rosa de cinco pétalos", R("cos(k*t)"), (("k", 5.0, 1.0, 9.0),), 0, PI),
    _c("Rosa de ocho pétalos", R("cos(k*t)"), (("k", 4.0, 1.0, 9.0),)),
    _c("Rodonea 7/3", R("cos(k*t)"), (("k", 7 / 3.0, 0.5, 4.5),), 0, 6 * PI),

    _c("Espiral de Arquímedes", R("pot(t,n)"), (("n", 1.0, -1.2, 1.6),), 0, 6 * PI),
    _c("Espiral logarítmica", R("exp(b*t)"), (("b", 0.16, 0.02, 0.45),), 0, 8 * PI),
    _c("Espiral de Fermat", R("pot(t,n)"), (("n", 0.5, 0.2, 1.2),), -8 * PI, 8 * PI),
    _c("Espiral hiperbólica", R("1/pot(t,n)"), (("n", 1.0, 0.4, 2.0),),
       0.35, 10 * PI),
    _c("Lituus", R("1/pot(t,n)"), (("n", 0.5, 0.2, 1.6),), 0.06, 8 * PI),
    _c("Cocleoide", R("sin(a*t)/t"), (("a", 1.0, 0.5, 3.0),), 0.05, 6 * PI),
    _c("Involuta de la circunferencia",
       X("cos(t) + a*t*sin(t)", "sin(t) - a*t*cos(t)"),
       (("a", 1.0, 0.3, 2.0),), 0, 5 * PI),
    # Sin fórmula cerrada: son las integrales de Fresnel, se acumulan aparte.
    _c("Clotoide", None, (("s", 4.2, 1.5, 7.0),), 0, 1),

    _c("Catenaria", X("t", "cosh(a*t)/a"), (("a", 1.0, 0.3, 3.0),), -2.2, 2.2),
    _c("Tractriz", X("t - a*tanh(t)", "a/cosh(t)"), (("a", 1.0, 0.3, 2.0),),
       -4.5, 4.5),
    _c("Bruja de Agnesi", X("2*t", "2/(1 + c*t**2)"), (("c", 1.0, 0.2, 4.0),),
       -5, 5),
    _c("Serpentina", X("t", "t/(1 + c*t**2)"), (("c", 1.0, 0.2, 4.0),), -6, 6),
    _c("Cúbica de Tschirnhausen", X("3*(t**2 - a)", "t*(t**2 - a)"),
       (("a", 3.0, 1.0, 6.0),), -3.2, 3.2),
    _c("Folium de Descartes",
       X("3*t/(1 + pot(t,n))", "3*t**2/(1 + pot(t,n))"),
       (("n", 3.0, 2.0, 5.0),), -20, 20),
    _c("Cisoide de Diocles", X("2*t**2/(1 + c*t**2)", "2*t**3/(1 + c*t**2)"),
       (("c", 1.0, 0.3, 3.0),), -6, 6),
    _c("Estrofoide recto", X("(t**2 - a)/(t**2 + 1)", "t*(t**2 - a)/(t**2 + 1)"),
       (("a", 1.0, 0.2, 4.0),), -5, 5),
    _c("Trisectriz de Maclaurin",
       X("(t**2 - a)/(t**2 + 1)", "t*(t**2 - a)/(t**2 + 1)"),
       (("a", 3.0, 1.0, 6.0),), -6, 6),
    _c("Kampyle de Eudoxo", X("1/cos(t)", "a*tan(t)/cos(t)"),
       (("a", 1.0, 0.3, 2.5),), -1.15, 1.15),

    _c("Bicornio", X("sin(t)", "cos(t)**2*(a + cos(t))/(3 + sin(t)**2)"),
       (("a", 2.0, 0.5, 4.0),)),
    _c("Sextica de Cayley", R("4*cos(t/k)**3"), (("k", 3.0, 1.5, 5.0),),
       0, 6 * PI),
    _c("Nefroide de Freeth", R("1 + b*sin(t/2)"), (("b", 2.0, 0.5, 3.0),),
       0, 4 * PI),
    _c("Hipopede", R("sqrt(max(4*(c - sin(t)**2), 0))"),
       (("c", 1.2, 0.4, 2.0),)),
    # En c = 1 el óvalo se parte en dos: es la transición de Cassini, y el
    # rango la cruza a propósito.
    _c("Óvalo de Cassini",
       R("sqrt(max(cos(2*t) + sqrt(max(c - sin(2*t)**2, 0)), 0))"),
       (("c", 1.06, 0.85, 2.2),)),
    # El tope de `k` no es estético: la mariposa recorre 24*pi y con k alto
    # necesita más muestras de las que le da `paseo`. Medido, por encima de
    # 5,5 se parte en decenas de trocitos a 1100 muestras.
    _c("Curva de la mariposa",
       R("exp(cos(t)) - 2*cos(k*t) + sin(t/12)**5"),
       (("k", 4.0, 2.0, 5.5),), 0, 24 * PI),
    _c("Superelipse", X("pot(cos(t),m)", "pot(sin(t),m)"),
       (("m", 0.5, 0.2, 3.0),)),
    _c("Curva de Talbot",
       X("(1 + a*sin(t)**2)*cos(t)", "(1 - 2*b + a*sin(t)**2)*sin(t)"),
       (("a", 1.2, 0.3, 2.5), ("b", 0.6, 0.1, 1.2))),
    _c("Curva de Lissajous 3:2", X("sin(a*t)", "sin(b*t + d)"),
       (("a", 3.0, 1.0, 8.0), ("b", 2.0, 1.0, 8.0), ("d", PI / 4, 0.0, PI))),
    _c("Curva de Lissajous 5:4", X("sin(a*t)", "sin(b*t + d)"),
       (("a", 5.0, 1.0, 8.0), ("b", 4.0, 1.0, 8.0), ("d", PI / 3, 0.0, PI))),
    _c("Trifolio", R("-cos(k*t)*(1 + cos(t))/2 - c*cos(t)"),
       (("k", 3.0, 1.0, 6.0), ("c", 0.3, 0.0, 1.0))),
    _c("Curva en forma de ocho", X("sin(a*t)", "sin(t)"),
       (("a", 2.0, 1.0, 5.0),)),
    _c("Pesa", X("sin(t)", "pot(sin(t),n)*cos(t)"), (("n", 2.0, 1.0, 5.0),)),
    _c("Cuadratriz de Hipias", X("t/tan(t*k*pi/2)", "t"),
       (("k", 1.0, 0.5, 2.0),), 0.001, 0.999),
    _c("Bifolio", R("4*pot(sin(t),n)*cos(t)"), (("n", 2.0, 1.0, 4.0),), 0, PI),
    _c("Piriforme", X("a + sin(t)", "cos(t)*(a + sin(t))"),
       (("a", 1.0, 0.5, 2.0),)),
    _c("Lágrima", X("cos(t)", "sin(t)*pot(sin(t/2),n)"),
       (("n", 4.0, 1.0, 8.0),)),
    _c("Hipocicloide de 6 puntas", X("k*cos(t) + cos(k*t)", "k*sin(t) - sin(k*t)"),
       (("k", 5.0, 2.0, 8.0),)),
    _c("Epicicloide de 3 puntas", X("k*cos(t) - cos(k*t)", "k*sin(t) - sin(k*t)"),
       (("k", 4.0, 2.0, 8.0),)),
    _c("Curva de Lissajous 7:5", X("sin(a*t)", "sin(b*t + d)"),
       (("a", 7.0, 1.0, 9.0), ("b", 5.0, 1.0, 9.0), ("d", PI / 5, 0.0, PI))),
    _c("Rodonea 5/2", R("cos(k*t)"), (("k", 2.5, 0.5, 4.5),), 0, 4 * PI),
    _c("Astroide alargada", X("cos(t)**3", "b*sin(t)**3"),
       (("b", 1.7, 0.5, 3.0),)),
]


# Las expresiones se compilan una vez. Evaluarlas con `eval` en cada fotograma
# costaría el análisis sintáctico sesenta veces por segundo para nada.
_COMPILADAS = {}


def _codigo(texto):
    if texto not in _COMPILADAS:
        _COMPILADAS[texto] = compile(texto, "<curva>", "eval")
    return _COMPILADAS[texto]


def defectos(indice):
    """Los valores de siempre de una curva, listos para `muestrear`."""
    return {q.letra: q.defecto for q in CURVAS[indice % len(CURVAS)].pars}


def _bonita(texto):
    """La expresión como se escribe a mano: `**` pasa a `^` y `pot(u,n)` a
    `u^n`, que es lo que significa. Se cuentan los paréntesis para no
    equivocarse con los anidados."""
    texto = texto.replace("**", "^")
    while "pot(" in texto:
        i = texto.index("pot(")
        j, hondo, coma = i + 4, 1, None
        while j < len(texto) and hondo:
            if texto[j] == "(":
                hondo += 1
            elif texto[j] == ")":
                hondo -= 1
            elif texto[j] == "," and hondo == 1:
                coma = j
            j += 1
        if coma is None:
            break
        texto = (texto[:i] + texto[i + 4:coma] + "^" + texto[coma + 1:j - 1]
                 + texto[j:])
    return texto


def formula(indice, vals=None):
    """La fórmula escrita, y aparte los valores que llevan sus parámetros."""
    c = CURVAS[indice % len(CURVAS)]
    if c.expr is None:
        texto = "x = INT cos(s^2*pi/2) ds,  y = INT sin(s^2*pi/2) ds"
    elif "r" in c.expr:
        texto = "r = " + _bonita(c.expr["r"])
    else:
        texto = "x = %s,  y = %s" % (_bonita(c.expr["x"]),
                                     _bonita(c.expr["y"]))
    if not c.pars:
        return texto, ""
    v = dict(defectos(indice), **(vals or {}))
    return texto, "   ".join("%s=%.2f" % (q.letra, v[q.letra]) for q in c.pars)


def _clotoide(n, s_max):
    """La espiral de Cornu. No tiene fórmula cerrada: son las integrales de
    Fresnel, así que se acumulan numéricamente."""
    s = np.linspace(-s_max, s_max, n)
    d = s[1] - s[0]
    return (np.cumsum(np.cos(s * s * PI / 2)) * d,
            np.cumsum(np.sin(s * s * PI / 2)) * d)


LIMITE = 40.0     # más lejos que esto, la rama se va al infinito y se corta


def en(indice, t, vals=None):
    """La curva evaluada en los `t` que se pidan, con estos parámetros."""
    c = CURVAS[indice % len(CURVAS)]
    v = dict(defectos(indice), **(vals or {}))
    t = np.asarray(t, float)
    if c.expr is None:
        # La clotoide es una integral: se calcula entera y se interpola, que
        # para trazarla es lo mismo.
        xx, yy = _clotoide(1400, v["s"])
        w = np.linspace(0.0, 1.0, len(xx))
        f = (t - c.t0) / (c.t1 - c.t0)
        return np.interp(f, w, xx), np.interp(f, w, yy)

    ambito = dict(FUNCIONES, t=t, **v)
    with np.errstate(divide="ignore", invalid="ignore"):
        if "r" in c.expr:
            r = eval(_codigo(c.expr["r"]), {"__builtins__": {}}, ambito)
            x, y = r * np.cos(t), r * np.sin(t)
        else:
            x = eval(_codigo(c.expr["x"]), {"__builtins__": {}}, ambito)
            y = eval(_codigo(c.expr["y"]), {"__builtins__": {}}, ambito)
    return (np.broadcast_to(np.asarray(x, float), t.shape).copy(),
            np.broadcast_to(np.asarray(y, float), t.shape).copy())


def bruto(indice, n=1400, vals=None):
    """Los puntos crudos `(x, y)`, sin encuadrar ni partir."""
    c = CURVAS[indice % len(CURVAS)]
    return en(indice, np.linspace(c.t0, c.t1, n), vals)


def encuadre(x, y):
    """Centro y escala para llevar una nube de puntos al cuadrado unidad.

    Por **percentiles**, no por el mínimo y el máximo. Con el rango completo
    mandan las ramas asintóticas: la concoide, la kappa, la nariz de bala y la
    curva del diablo salían todas como una raya vertical, porque su parte
    interesante mide uno y su asíntota mide cuarenta. Recortando por el 3% y el
    97% se encuadra el grueso de la curva y las colas se van fuera del cuadro,
    que es a donde iban de todas formas.
    """
    bien = np.isfinite(x) & np.isfinite(y) & (np.abs(x) < LIMITE) & (np.abs(y) < LIMITE)
    if bien.sum() < 8:
        return None
    xb, yb = x[bien], y[bien]
    x0, x1 = np.percentile(xb, [3, 97])
    y0, y1 = np.percentile(yb, [3, 97])
    return ((x0 + x1) / 2, (y0 + y1) / 2, 2.0 / max(x1 - x0, y1 - y0, 1e-6))


def muestrear(indice, n=1400, vals=None):
    """(nombre, lista de polilíneas) ya centradas y a escala del cuadrado
    unidad, listas para colocar donde sea.

    Las que tienen asíntota se parten: entre dos muestras que pegan un salto
    grande no hay curva, hay un agujero por el que se escapó al infinito.
    Uniéndolas quedaría una raya cruzando la pantalla.
    """
    nombre = CURVAS[indice % len(CURVAS)].nombre
    x, y = bruto(indice, n, vals)
    caja = encuadre(x, y)
    if caja is None:
        return nombre, []
    cx, cy, k = caja
    x, y = (x - cx) * k, (y - cy) * k

    bien = np.isfinite(x) & np.isfinite(y)
    # Lo que se escapa muy lejos ya no aporta: estorba al partir en tramos.
    bien &= (np.abs(x) < 2.6) & (np.abs(y) < 2.6)

    salto = np.hypot(np.diff(x), np.diff(y)) > 0.30
    corte = np.flatnonzero(salto | ~bien[:-1] | ~bien[1:]) + 1

    piezas = []
    for tramo in np.split(np.arange(len(x)), corte):
        tramo = tramo[bien[tramo]]
        if len(tramo) > 6:
            piezas.append(np.stack([x[tramo], y[tramo]], axis=1))
    return nombre, piezas


NOMBRES = [c.nombre for c in CURVAS]
