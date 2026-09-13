"""Rosca — el toro de `toro`, con las horas impresas alrededor.

`toro` es la mejor de las esferas de geometría y la única sin números: el
instante está donde se cruzan los dos aros, y hay que saberlo para leerlo. Aquí
la superficie lleva encima una banda impresa con las doce horas, así que el aro
de la hora **señala un número** en vez de una posición que hay que estimar.

La banda va en el **ecuador de fuera**, y no es una elección estética. La
curvatura de Gauss de un toro es `cos(v) / (r · (R + r·cos v))`: máxima
justo ahí, en `v = 0`, y negativa por dentro del agujero. Es la zona donde una
tipografía pegada se dobla más y donde mejor se ve que está pegada.

`toro` se queda como está: esto es una esfera aparte.
"""

from ..banda import de_lejos_a_cerca, etiqueta, malla_toro, tinte_niebla
from ..esfera import Malla
from ..camara import Camara
from ..lienzo import Lienzo
from .toro import CAMARA, FOCO, R_DONUT, R_TUBO, Toro

TEX_ANCHO = 2048
TEX_ALTO = 136

# Cuánto del tubo ocupa la banda, en radianes: 0 es el ecuador de fuera y pi/2
# lo más alto del tubo. La banda va en el HOMBRO, no en el ecuador.
#
# La curvatura de Gauss es máxima justo en el ecuador, así que ahí es donde una
# tipografía pegada más se dobla — pero con el ojo a 35 grados el ecuador cae
# en el borde de abajo del contorno y de la banda se veía un cuarto escaso. En
# el hombro la curvatura sigue siendo el 80% de la máxima y se ve casi entera.
V0, V1 = 0.0, 1.30
NU, NV = 128, 8


class Rosca(Toro):
    """El toro con las doce horas impresas en el ecuador de fuera."""

    NOMBRE = "rosca"

    # La malla se aparta: con el tejido a pleno brillo la banda quedaba debajo
    # de una reja y las cifras no se leían.
    TEJIDO = 0.34
    # Y el ojo sube: a 35 grados la banda se veía de canto.
    CAB_BASE = 1.05
    CAB_VAIVEN = 0.20

    def __init__(self, lado):
        Toro.__init__(self, lado)
        # Un pelo menos de zoom que `toro`: mirando más desde arriba el anillo
        # se ensancha, y con 0,66 las cifras de delante se salían por abajo.
        self.cam = Camara(lado, CAMARA, FOCO, 0.58)
        self._pts, self._uv, self._cuadros = malla_toro(
            R_DONUT, R_TUBO, V0, V1, NU, NV)

    def texturas(self):
        return {"banda": etiqueta(TEX_ANCHO, TEX_ALTO)}

    def mallas(self, t):
        # La cámara ya está colocada: `trazos()` se llama antes que `mallas()`
        # y `mirar()` deja el ojo donde toca.
        xy, d = self.cam(self._pts)
        # La niebla, más suave que en `pintada`: en un toro las cifras de los
        # lados ya salen muy escorzadas, y apagándolas encima desaparecían.
        return (Malla("banda", xy, self._uv,
                      de_lejos_a_cerca(self._cuadros, xy, d),
                      tinte_niebla(self.cam, d, 1.2, 2.4, 0.42), 255),)

    def capa(self, t):
        seg = int(t)
        lz = Lienzo(self.lado, sup=1)
        lz.texto(self.lado / 2, self.lado * 0.885,
                 "%d:%02d" % (int(t // 3600) % 12 or 12, int(t // 60) % 60),
                 self.f_hora, 0xF2F5F8, 235)
        lz.texto(self.lado / 2, self.lado * 0.945,
                 "las horas, impresas donde el toro mas se curva",
                 self.f_pie, 0x6E86A0)
        return seg // 60, lz.array()


ESFERA = Rosca
