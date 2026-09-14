"""Cómo varían los parámetros de una curva con el reloj.

Una configuración dice, para cada parámetro de cada curva, **entre qué dos
valores se mueve** y **a qué velocidad**. La velocidad no va en segundos sino
en un **multiplicador del reloj**, que es lo que la ata al resto del proyecto:

    periodo = BASE / multiplicador

con `BASE` = 60 s, que es justo lo que cada curva está en pantalla. Así que un
multiplicador de 1 significa **una ida y vuelta completa mientras se ve esa
curva**; 0,5, media; 2, dos. No hay que pensar en segundos en ningún momento.

El recorrido es un coseno y no un diente de sierra: un parámetro que llega al
extremo y da media vuelta de golpe se ve como un tirón, y aquí lo que se mira
es precisamente cómo se deforma la curva.

Y cada parámetro arranca con un desfase distinto. Si no, los dos parámetros de
una Lissajous suben y bajan a la vez y la curva solo crece y mengua; desfasados
recorren una figura en el espacio de parámetros, que es lo que hace que la
estela no se cierre nunca sobre sí misma.
"""

import json
import math

from .curvas_famosas import CURVAS

BASE = 60.0         # segundos de referencia: lo que dura una curva en pantalla

# Multiplicadores de partida para el primero, el segundo y el tercer parámetro.
# Son inconmensurables entre sí a propósito —la razón áurea y su cuadrado— para
# que la pareja no vuelva a repetir la misma combinación en todo el minuto.
MULTIPLOS = (1.0, 0.618, 1.618)

# Cuánto del rango del catálogo se usa por defecto. Los topes de `pars` son
# donde la curva deja de reconocerse; quedarse en el 70% centrado en el valor
# de siempre deja margen y no la lleva nunca al borde.
PARTE = 0.70


def por_defecto():
    """Una configuración de partida sacada del propio catálogo.

    No hay nada escrito a mano: los rangos salen de los que ya declara cada
    curva, encogidos y centrados en su valor de siempre, y las velocidades de
    `MULTIPLOS`. Es el punto de partida para tocarlo en el laboratorio.
    """
    curvas = {}
    for c in CURVAS:
        if not c.pars:
            continue
        d = {}
        for i, q in enumerate(c.pars):
            radio = (q.maximo - q.minimo) / 2.0 * PARTE
            # Centrado en el valor de siempre, pero sin salirse del rango.
            centro = min(max(q.defecto, q.minimo + radio), q.maximo - radio)
            d[q.letra] = {
                "min": round(centro - radio, 4),
                "max": round(centro + radio, 4),
                "mult": MULTIPLOS[i % len(MULTIPLOS)],
            }
        curvas[c.nombre] = d
    # `vuelta` son los segundos que tarda la punta en trazar la curva entera, y
    # de ahí salen las trazadas por minuto: 60/3 = 20. No hace falta un segundo
    # número para la persistencia porque no hay estela que dure: **se quedan
    # todas las del minuto**, y al cambiar de curva la pizarra queda limpia.
    return {"version": 1, "vuelta": 3.0, "curvas": curvas}


def cargar(ruta):
    """Una configuración de disco, completada con la de partida.

    Completar importa: una configuración escrita a mano o exportada de una
    versión anterior del catálogo puede no traer todas las curvas, y una curva
    sin entrada tiene que seguir dibujándose con sus valores de siempre en vez
    de reventar.
    """
    cfg = por_defecto()
    with open(ruta, encoding="utf-8") as f:
        suya = json.load(f)
    if "vuelta" in suya:
        cfg["vuelta"] = float(suya["vuelta"])
    for nombre, pars in (suya.get("curvas") or {}).items():
        cfg["curvas"].setdefault(nombre, {}).update(pars)
    return cfg


def valores(cfg, indice, t):
    """Los parámetros de la curva `indice` en el instante `t`."""
    return _reparto(cfg, indice,
                    lambda i, mult: 2 * math.pi * (t * mult / BASE + i / 3.0))


def ciclos(mult):
    """Vueltas **enteras** que da un parámetro en un bucle cerrado.

    Un bucle de trazadas tiene que cerrar: la última deja los parámetros justo
    donde los cogió la primera, y por eso vuelve a empezar sin costura. Con
    multiplicadores cualesquiera eso no pasa nunca —0,618 no cierra—, así que
    ahí se redondean a vueltas enteras. La razón áurea y su cuadrado, 0,618 y
    1,618, quedan en **1 y 2**: se pierde la inconmensurabilidad, que era para
    que la estela continua no se repitiera, y se conserva lo que aquí importa,
    que un parámetro vaya al doble que el otro.
    """
    return max(1, int(round(abs(mult))))


def valores_paso(cfg, indice, j, n):
    """Los parámetros en el paso `j` de un bucle cerrado de `n` pasos.

    `j = 0` y `j = n` dan lo mismo. Es lo que usa `trazada`: el parámetro no se
    mueve mientras se dibuja una curva, salta de una a la siguiente.
    """
    return _reparto(cfg, indice,
                    lambda i, mult: 2 * math.pi * (j * ciclos(mult) / float(n)
                                                   + i / 3.0))


def _reparto(cfg, indice, fase_de):
    """El coseno entre `min` y `max`, con la fase que diga quien llame.

    Lo único que separa el recorrido continuo del de saltos es de dónde sale la
    fase, así que el resto —los desfases por parámetro, el multiplicador cero,
    la curva sin entrada en la configuración— se escribe una vez.
    """
    c = CURVAS[indice % len(CURVAS)]
    suya = (cfg.get("curvas") or {}).get(c.nombre, {})
    fuera = {}
    for i, q in enumerate(c.pars):
        r = suya.get(q.letra)
        if not r:
            fuera[q.letra] = q.defecto
            continue
        mult = float(r.get("mult", 1.0))
        if mult <= 0:
            fuera[q.letra] = (float(r["min"]) + float(r["max"])) / 2.0
            continue
        # El desfase reparte los parámetros por la vuelta en vez de moverlos
        # todos a la vez.
        lo, hi = float(r["min"]), float(r["max"])
        fuera[q.letra] = lo + (hi - lo) * (1.0 - math.cos(fase_de(i, mult))) / 2.0
    return fuera


def extremos(cfg, indice):
    """Las esquinas del cajón de parámetros por los que va a pasar la curva.

    Sirven para encuadrarla **una vez** y que no baile: si se encuadrara en
    cada instante, la curva se quedaría quieta y sería el marco el que se
    movería, que es justo lo contrario de lo que se quiere ver.
    """
    c = CURVAS[indice % len(CURVAS)]
    suya = (cfg.get("curvas") or {}).get(c.nombre, {})
    base = {q.letra: q.defecto for q in c.pars}
    fuera = [dict(base)]
    for q in c.pars:
        r = suya.get(q.letra)
        if not r:
            continue
        for v in (float(r["min"]), float(r["max"])):
            fuera.append(dict(base, **{q.letra: v}))
    return fuera
