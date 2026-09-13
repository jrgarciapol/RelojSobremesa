#!/usr/bin/env python3
"""Cuánto cuesta cada esfera: tiempo de arranque, memoria pico y fotograma."""
import gc
import os
import sys
import time
import tracemalloc

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from reloj.esferas import DISPONIBLES, cargar

LADO = int(sys.argv[1]) if len(sys.argv) > 1 else 1080

print("lado = %d px   (una Pi Zero 2 W a 1080p da un dial de 1080)" % LADO)
print()
print("%-12s %8s %9s %9s %9s" % ("esfera", "arranq", "pico MB", "capa ms", "cuadro"))
print("-" * 52)

for n in DISPONIBLES:
    gc.collect()
    Clase = cargar(n)
    tracemalloc.start()
    t0 = time.perf_counter()
    esf = Clase(LADO)
    f = esf.fondo()
    piezas = esf.piezas()
    arranque = time.perf_counter() - t0
    pico = tracemalloc.get_traced_memory()[1] / 1e6
    tracemalloc.stop()

    t0 = time.perf_counter()
    c = esf.capa(36578.0)
    capa = (time.perf_counter() - t0) * 1000 if c is not None else 0.0

    t0 = time.perf_counter()
    for i in range(30):
        esf.detras(36578.0 + i * 0.033)
        esf.cuadro(36578.0 + i * 0.033)
    cuadro = (time.perf_counter() - t0) / 30 * 1000

    print("%-12s %7.2fs %8.0f %8.0f %7.2fms" % (n, arranque, pico, capa, cuadro))
    del esf, f, piezas, c
