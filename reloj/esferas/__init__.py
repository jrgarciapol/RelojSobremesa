"""Catálogo de esferas.

Quince nombres salidos de seis módulos: las ocho `digital` son la misma
maquetación con distinta tipografía, y `rosavivid` y `pulsoxl` son subclases de
tres líneas de su hermana. En el Garmin cada una de esas quince era un
proyecto Connect IQ entero, con su manifiesto y su propio id de app.
"""

import importlib

CATALOGO = {}   # nombre público -> módulo donde vive


def _registrar(modulo, nombres):
    for n in nombres:
        CATALOGO[n] = modulo


_registrar("disco", ["disco"])
_registrar("eliptica", ["eliptica", "finita"])
_registrar("toro", ["toro"])
_registrar("hopf", ["hopf"])
_registrar("superficie", ["superficie"])
_registrar("grabada", ["grabada"])
_registrar("letras", ["letras"])
_registrar("orbita", ["orbita"])
_registrar("pulso", ["pulso", "pulsoxl"])
_registrar("rosa", ["rosa", "rosavivid"])
_registrar("digital", ["bangers", "barriecito", "caesar", "honk",
                       "londrina", "rampart", "smokum", "sueellen"])

DISPONIBLES = tuple(sorted(CATALOGO))

# Por familias, que es como se miran cuando se comparan.
FAMILIAS = (
    ("analógicas", ("disco", "rosa", "rosavivid")),
    ("geometría", ("grabada", "superficie", "hopf", "toro", "eliptica", "finita")),
    ("en palabras", ("letras",)),
    ("con movimiento", ("orbita", "pulso", "pulsoxl")),
    ("digitales, por tipografía", ("bangers", "barriecito", "caesar", "honk",
                                   "londrina", "rampart", "smokum", "sueellen")),
)


def cargar(nombre):
    """Devuelve la CLASE de la esfera, sin instanciar: la instancia necesita
    saber el lado, y eso lo decide quien vaya a pintar."""
    if nombre not in CATALOGO:
        raise SystemExit("No conozco la esfera %r. Hay: %s"
                         % (nombre, ", ".join(DISPONIBLES)))
    mod = importlib.import_module("." + CATALOGO[nombre], __name__)

    if hasattr(mod, "VARIANTES") and nombre in mod.VARIANTES:
        return mod.VARIANTES[nombre]
    for obj in vars(mod).values():
        if isinstance(obj, type) and getattr(obj, "NOMBRE", None) == nombre:
            return obj
    return mod.ESFERA
