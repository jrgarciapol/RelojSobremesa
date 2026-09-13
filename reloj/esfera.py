"""El molde que cumplen todas las esferas.

Una esfera **no sabe nada de SDL**. Solo dice qué dibujar; quién lo pinta es
cosa de `pantalla` (en la Pi) o de `lamina` (para un PNG).

El dibujo se reparte en cuatro sitios, y el reparto no es capricho: es lo que
decide cuánto trabajo hay **por fotograma**, que es lo que una Pi Zero 2 W
puede o no puede pagar.

    fondo      se rasteriza UNA VEZ y no cambia nunca      (marcas, rosa)
    piezas     se rasterizan UNA VEZ y luego solo se mueven (agujas, orbes)
    capa       se redibuja SOLO cuando cambia su clave      (textos, arcos)
    cuadro     no dibuja nada: coloca piezas ya hechas      (cada fotograma)

Orden de pintado:

    fondo -> detras() -> capa -> cuadro()

`detras()` existe por una razón concreta heredada del reloj: en `pulso` los
orbes viajan **por detrás** de la hora y el choque estalla **por delante**. Sin
esa separación, el estallido de arriba y el de abajo salían distintos porque
tenían textos diferentes detrás.
"""

from collections import namedtuple

# Una pieza colocada: qué, dónde, girada cuánto, teñida de qué y con qué
# opacidad. `escala` multiplica el tamaño con que se rasterizó.
Puesto = namedtuple("Puesto", "pieza x y grados color alfa escala")
Puesto.__new__.__defaults__ = (0.0, None, 255, 1.0)


class Esfera:
    """Base con todo vacío: cada esfera rellena solo lo que use."""

    NOMBRE = "?"

    def __init__(self, lado):
        self.lado = lado
        self.r = lado / 2.0

    # --- lo que se rasteriza una vez ---
    def fondo(self):
        """(alto, ancho, 3) uint8, o None si la esfera arranca en negro."""
        return None

    def piezas(self):
        """{nombre: array RGBA} o {nombre: (array, (px, py))}.

        Sin pivote, la pieza se coloca y se gira **por su centro**, que es lo
        que quiere un orbe. Con pivote, por ese punto: así una aguja puede ser
        una tira estrecha en vez de un cuadrado del tamaño del dial casi
        entero vacío.
        """
        return {}

    # --- lo que se redibuja de vez en cuando ---
    def capa(self, t):
        """(clave, array RGBA) o None.

        Mientras la clave no cambie, no se vuelve a dibujar ni a subir a la
        tarjeta. Para un texto que cambia cada minuto, eso es un redibujado
        por minuto en vez de treinta por segundo.
        """
        return None

    # --- lo que se decide en cada fotograma ---
    def detras(self, t):
        """Piezas que van por DEBAJO de la capa."""
        return ()

    def cuadro(self, t):
        """Piezas que van por ENCIMA de todo."""
        return ()
