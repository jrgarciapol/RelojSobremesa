"""Enlazada — la fibración de Hopf con las horas impresas sobre las fibras.

`hopf` no tiene superficie: son círculos en el aire, y una etiqueta necesita
algo donde pegarse. Pero la superficie está, y no hay que inventarla.

**Las fibras sobre un paralelo de `S²` barren un toro de revolución.** Y no
aproximadamente: la fibra sobre `(t, f)` proyectada desde `(0,0,0,1)` cumple

    (rho - sec(t/2))² + z² = tan(t/2)²

para toda `f` y todo punto de la fibra — comprobado a precisión de máquina para
los tres paralelos que dibuja `hopf`. Así que el paralelo `t` tiene su toro,
con `R = sec(t/2)` y `r = tan(t/2)`, y ahí se imprime la banda.

Lo bonito es lo que sale de regalo. Las fibras están **dentro** de ese toro, no
al lado: son circunferencias trazadas sobre la propia banda. Y una
circunferencia que vive en un toro sin ser ni un meridiano ni un paralelo es
una **circunferencia de Villarceau**, el corte de un toro por un plano
bitangente. Las fibras de Hopf sobre un paralelo son exactamente eso.

Así que las cifras no están *delante* de las fibras ni *detrás*: están en la
misma superficie, y las fibras pasan por encima de ellas como los hilos de un
bordado. `hopf` se queda como está: esto es una esfera aparte.
"""

import math

from ..banda import de_lejos_a_cerca, etiqueta, malla_toro, tinte_niebla
from ..esfera import Malla
from ..lienzo import Lienzo
from .hopf import T_MINUTO, Hopf

# El paralelo que lleva la banda: el de en medio de los tres. El de dentro da
# un toro flaco donde las cifras no caben y el de fuera uno tan gordo que se
# come los eslabones del reloj.
T_BANDA = 0.82
R_BANDA = 1.0 / math.cos(T_BANDA / 2)
TUBO_BANDA = math.tan(T_BANDA / 2)

TEX_ANCHO = 2048
TEX_ALTO = 148

# En el hombro del tubo, igual que en `rosca`: en el ecuador la curvatura es
# máxima pero con el ojo bajo se ve de canto.
V0, V1 = 0.0, 1.30
NU, NV = 128, 8

# La altura del tubo a la que `etiqueta()` imprime las cifras: van al 46% de la
# banda contando desde arriba, y la `v` de la imagen va al revés que la del
# tubo.
V_CIFRAS = V0 + (V1 - V0) * (1.0 - 0.46)


def _desfase(t, v):
    """En qué azimut cruza la altura `v` del tubo la fibra sobre `(t, 0)`.

    De la parametrización de la fibra salen la altura y el azimut en función
    del mismo ángulo auxiliar; despejando queda esto, y con `v = 0` da `pi/2`,
    que es el cruce por el ecuador de fuera.
    """
    a, b = math.cos(t / 2), math.sin(t / 2)
    k = 1.0 + b * math.cos(v)
    return math.atan2((1.0 - a * a / k) / b, a * math.sin(v) / k)


DESFASE = _desfase(T_BANDA, V_CIFRAS)


class Enlazada(Hopf):
    """Hopf, con las doce horas impresas en el toro que barre un paralelo."""

    NOMBRE = "enlazada"

    # El ojo sube: con los 24 grados de `hopf` la banda salía de canto.
    CAB_BASE = 0.95
    CAB_VAIVEN = 0.20

    def __init__(self, lado):
        Hopf.__init__(self, lado)
        # Las fibras del paralelo de la banda se quedan —son las que la
        # bordan— pero las de los otros dos estorban: cruzaban las cifras por
        # delante desde fuera de la superficie y parecían arañazos.
        self._fondo = [(t, p) for t, p in self._fondo if t == T_BANDA]
        self._pts, self._uv, self._cuadros = malla_toro(
            R_BANDA, TUBO_BANDA, V0, V1, NU, NV)

    def _eslabones(self, t):
        """La fibra de la hora se muda al toro de la banda, y entonces SEÑALA.

        En `hopf` la banda sería decoración: el eslabón vive en otro toro y no
        toca las cifras nunca. Puesto en el mismo, sí, y en un solo sitio.

        Una fibra sobre el toro de su paralelo es una curva `(1, 1)`: mientras
        da una vuelta al donut da otra al tubo. Así que pasa por **cada altura
        del tubo exactamente una vez**, y en particular por la altura a la que
        están impresas las cifras. Ese punto es la manecilla.

        La cuenta sale cerrada. La fibra sobre `(t, f)` es la de `(t, 0)`
        girada `f` alrededor del eje, así que basta saber en qué azimut cruza
        esa altura cuando `f = 0` y restarlo: `DESFASE`.

        (Una circunferencia sobre un toro que no es ni meridiano ni paralelo es
        una **circunferencia de Villarceau**, el corte por un plano bitangente.
        Las fibras de Hopf sobre un paralelo son exactamente eso.)
        """
        hora = 2 * math.pi * (t / 3600.0 % 12.0) / 12.0
        return ((T_BANDA, hora - DESFASE, 0.09),
                (T_MINUTO, 2 * math.pi * (t / 60.0 % 60.0) / 60.0, 0.47))

    def texturas(self):
        return {"banda": etiqueta(TEX_ANCHO, TEX_ALTO)}

    def mallas(self, t):
        xy, d = self.cam(self._pts)
        return (Malla("banda", xy, self._uv,
                      de_lejos_a_cerca(self._cuadros, xy, d),
                      tinte_niebla(self.cam, d, 1.2, 2.6, 0.42), 255),)

    def capa(self, t):
        lz = Lienzo(self.lado, sup=1)
        lz.texto(self.lado / 2, self.lado * 0.885,
                 "%d:%02d" % (int(t // 3600) % 12 or 12, int(t // 60) % 60),
                 self.f_hora, 0xF2F5F8, 235)
        lz.texto(self.lado / 2, self.lado * 0.945,
                 "las fibras de un paralelo son un toro",
                 self.f_pie, 0x6E86A0)
        return int(t) // 60, lz.array()


ESFERA = Enlazada
