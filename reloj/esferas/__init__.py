"""Catálogo de esferas.

Veintiocho nombres salidos de dieciocho módulos, porque muchas son variantes de
otra: las ocho `digital` son la misma maquetación con distinta tipografía, y
`rosavivid`, `pulsoxl`, `finita`, `rosca`, `enlazada`, `rotulada`, `pellizco` y
`bordada` son subclases de su hermana. En el Garmin cada una de las quince originales era un proyecto Connect
IQ entero, con su manifiesto y su propio id de app.
"""

import importlib

CATALOGO = {}   # nombre público -> módulo donde vive


def _registrar(modulo, nombres):
    for n in nombres:
        CATALOGO[n] = modulo


_registrar("disco", ["disco"])
_registrar("eliptica", ["eliptica", "finita"])
_registrar("rotulada", ["rotulada"])
_registrar("pellizco", ["pellizco"])
_registrar("bordada", ["bordada"])
_registrar("toro", ["toro"])
_registrar("rosca", ["rosca"])
_registrar("hopf", ["hopf"])
_registrar("enlazada", ["enlazada"])
_registrar("superficie", ["superficie"])
_registrar("grabada", ["grabada"])
_registrar("pintada", ["pintada"])
_registrar("paseo", ["paseo"])
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
    ("curvas célebres", ("paseo",)),
    ("geometría", ("pintada", "grabada", "superficie", "enlazada", "hopf",
                   "rosca", "toro", "pellizco", "rotulada", "eliptica",
                   "bordada", "finita")),
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
