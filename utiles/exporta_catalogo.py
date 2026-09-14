#!/usr/bin/env python3
"""Mete el catálogo de curvas —las expresiones, no los puntos— en el HTML.

`exporta_curvas.py`, el de antes, mandaba **puntos muestreados**: valía para
`paseo`, que dibuja las curvas con sus valores de siempre, y no vale para nada
que mueva los parámetros. Una tabla de puntos para tres parámetros continuos no
cabe en ninguna parte.

Así que lo que viaja ahora es el **texto de las fórmulas**. Son cuatro kilobytes
en vez de trescientos quince, y el navegador evalúa exactamente las mismas
sesenta y una curvas que la Pi, con los parámetros que le pongan. La definición
sigue estando en un solo sitio: `reloj/curvas_famosas.py`.

    python3 utiles/exporta_catalogo.py
"""

import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, ".."))

from reloj.curvas_famosas import CURVAS       # noqa: E402
from reloj import variacion                   # noqa: E402

INICIO = "/*CATALOGO-INICIO*/"
FIN = "/*CATALOGO-FIN*/"
DESTINOS = ("curvas.html", "reloj.html")


def catalogo():
    return [{"nombre": c.nombre,
             "expr": c.expr,
             "pars": [[q.letra, q.defecto, q.minimo, q.maximo] for q in c.pars],
             "t0": c.t0, "t1": c.t1} for c in CURVAS]


def main():
    datos = json.dumps(catalogo(), ensure_ascii=False, separators=(",", ":"))
    cfg = json.dumps(variacion.por_defecto(), ensure_ascii=False,
                     separators=(",", ":"))
    bloque = ("%s\nconst CATALOGO = %s;\nconst CFG_BASE = %s;\n%s"
              % (INICIO, datos, cfg, FIN))

    for nombre in DESTINOS:
        ruta = os.path.join(AQUI, "..", nombre)
        if not os.path.exists(ruta):
            continue
        s = open(ruta, encoding="utf-8").read()
        if INICIO not in s:
            print("  %s no tiene las marcas, me lo salto" % nombre)
            continue
        a, b = s.index(INICIO), s.index(FIN) + len(FIN)
        open(ruta, "w", encoding="utf-8").write(s[:a] + bloque + s[b:])
        print("  %s <- %d curvas, %d KB" % (nombre, len(CURVAS),
                                            len(bloque) // 1024))


if __name__ == "__main__":
    main()
