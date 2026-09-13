"""Reloj de sobremesa / pared.

    python -m reloj                          pantalla completa
    python -m reloj --ventana                en una ventana de 800
    python -m reloj --esfera letras
    python -m reloj --lista                  qué esferas hay

    python -m reloj --lamina x.png --hora 10:09:38
    python -m reloj --lamina h.png --hora 10:09 1:50 6:30 8:20
    python -m reloj --lamina todas.png --esfera TODAS

Con `--lamina` no hace falta pantalla ni SDL: compone con Pillow y guarda.
"""

import argparse

from . import lamina
from .esferas import DISPONIBLES, FAMILIAS, cargar


def main():
    p = argparse.ArgumentParser(
        prog="python -m reloj", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--esfera", default="disco",
                   help="nombre, o TODAS para una hoja de contactos")
    p.add_argument("--lista", action="store_true", help="lista las esferas y sale")
    p.add_argument("--ventana", action="store_true",
                   help="en ventana en vez de pantalla completa")
    p.add_argument("--lado", type=int, default=None,
                   help="lado del dial en px (por defecto, el de la pantalla)")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--ppm", type=float, default=None,
                   help="pulsaciones por minuto para pulso/pulsoxl (no hay sensor)")
    p.add_argument("--lamina", metavar="PNG",
                   help="no abre pantalla: guarda un PNG y sale")
    p.add_argument("--hora", nargs="+", default=["10:09:38"],
                   help="una o varias horas para --lamina")
    p.add_argument("--columnas", type=int, default=None)
    a = p.parse_args()

    if a.lista:
        for familia, nombres in FAMILIAS:
            print("%-28s %s" % (familia + ":", "  ".join(nombres)))
        return

    if a.ppm is not None:
        from .esferas import pulso
        pulso.PPM = a.ppm

    if a.lamina:
        lado = a.lado or 800
        ts = [lamina.reloj_a_segundos(h) for h in a.hora]
        if a.esfera.upper() == "TODAS":
            # Una por esfera, todas a la misma hora: es la comparación útil.
            trozos = [lamina.componer(cargar(n), lado, ts[0]) for n in DISPONIBLES]
            cols = a.columnas or 5
        else:
            Clase = cargar(a.esfera)
            trozos = [lamina.componer(Clase, lado, t) for t in ts]
            cols = a.columnas or (1 if len(ts) == 1 else 2)
        im = trozos[0] if len(trozos) == 1 else lamina.hoja(trozos, cols)
        im.save(a.lamina)
        print("%s  (%dx%d)" % (a.lamina, im.width, im.height))
        return

    from . import pantalla
    pantalla.correr(cargar(a.esfera), lado=a.lado, ventana=a.ventana, fps=a.fps)


if __name__ == "__main__":
    main()
