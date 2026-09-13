#!/usr/bin/env python3
"""Mete el catálogo de curvas ya muestreado dentro de `reloj.html`.

Las sesenta y una curvas están definidas **una sola vez**, en Python
(`reloj/curvas_famosas.py`). Reescribirlas en JavaScript sería garantizar que
las dos versiones se separen: sesenta y una fórmulas con sus rangos, sus
asíntotas y sus recortes por percentiles, mantenidas por duplicado.

Así que no se copian las fórmulas: se copian **los puntos**. Este script
muestrea todas las curvas con el mismo código que usa la Pi y escribe el
resultado en el HTML, entre dos marcas. Si el catálogo cambia, se vuelve a
correr y se acabó.

    python3 utiles/exporta_curvas.py
"""

import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, ".."))

from reloj.curvas_famosas import CURVAS, muestrear   # noqa: E402

HTML = os.path.join(AQUI, "..", "reloj.html")
INICIO = "/*CURVAS-INICIO*/"
FIN = "/*CURVAS-FIN*/"
MUESTRAS = 420      # por curva: bastante para que se vea lisa, poco para pesar


def main():
    fuera = []
    for i in range(len(CURVAS)):
        nombre, piezas = muestrear(i, MUESTRAS)
        # Coordenadas intercaladas y a tres decimales: la mitad de bytes que
        # una lista de pares, y a esta escala no se nota un pelo.
        fuera.append([nombre, [[round(float(v), 3) for p in pieza for v in p]
                               for pieza in piezas]])

    datos = json.dumps(fuera, ensure_ascii=False, separators=(",", ":"))
    bloque = "%s\nconst CURVAS_MAC = %s;\n%s" % (INICIO, datos, FIN)

    s = open(HTML, encoding="utf-8").read()
    a, b = s.index(INICIO), s.index(FIN) + len(FIN)
    open(HTML, "w", encoding="utf-8").write(s[:a] + bloque + s[b:])

    print("%d curvas · %d KB en el HTML" % (len(fuera), len(datos) // 1024))


if __name__ == "__main__":
    main()
