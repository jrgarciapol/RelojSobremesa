"""Reloj de sobremesa / pared.

    python -m reloj                          pantalla completa
    python -m reloj --ventana                en una ventana de 800
    python -m reloj --esfera letras          arranca en esa
    python -m reloj --lista                  qué esferas hay
    python -m reloj --velocidad 600          una hora de reloj cada 6 s

Con la ventana abierta:

    flechas / espacio    pasar de una esfera a la siguiente
    g                    guardar un PNG de lo que se ve
    Esc  o  q            salir

Y sin abrir pantalla ni tocar SDL, componiendo con Pillow:

    python -m reloj --lamina x.png --hora 10:09:38
    python -m reloj --lamina h.png --hora 10:09 1:50 6:30 8:20
    python -m reloj --lamina todas.png --esfera TODAS
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
    p.add_argument("--velocidad", type=float, default=1.0,
                   help="multiplica el paso del tiempo (x600: una hora en 6 s)")
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

    # Se le pasan TODAS, para poder pasear por ellas con las flechas sin
    # cerrar la ventana; arranca en la pedida.
    nombres = list(DISPONIBLES)
    if a.esfera.upper() == "TODAS":
        arranque = 0
    else:
        cargar(a.esfera)              # valida el nombre antes de abrir nada
        arranque = nombres.index(a.esfera)

    from . import pantalla
    pantalla.correr(nombres, arranque, lado=a.lado, ventana=a.ventana,
                    fps=a.fps, velocidad=a.velocidad)


if __name__ == "__main__":
    main()
