"""Como `grabada`, pero con una **imagen** pegada sobre la superficie.

`grabada` proyecta bien, pero solo puede proyectar polilíneas: las cifras están
dibujadas a palotes porque un glifo de verdad es un rectángulo de píxeles y no
se sabía pegar sobre algo curvo.

Aquí sí. Se rasteriza **una banda desenrollada** —la superficie abierta en
plano, como quien despega la etiqueta de una lata— con las horas en Barriecito,
sus marcas y su raya. Después esa banda se vuelve a enrollar sobre la
superficie mapeándola sobre triángulos.

Eso es lo que hace cualquier motor 3D con una textura, y en la Pi **sale
gratis**: `SDL_RenderGeometryRaw` aceptaba textura y coordenadas `uv` desde el
principio; lo que faltaba era dárselas en vez de pasarle `None` y ceros.

Lo que se gana no es solo tipografía. Sobre la superficie se puede pegar
cualquier imagen.
"""

import numpy as np

from ..banda import etiqueta, tinte_niebla
from ..esfera import Malla
from .superficie import Superficie

# La banda, desenrollada. Ancha porque da la vuelta entera al día.
TEX_ANCHO = 2048
TEX_ALTO = 288

# El trozo de corte que ocupa la banda. Va en la **pared exterior de abajo**,
# no en el ala del borde. La cámara mira desde arriba, así que del ala se ve la
# cara de dentro: la banda salía impresa por detrás, del revés y en espejo.
# En la pared exterior se ve por su cara buena.
# Más arriba que el borde de abajo: ahí la pared es casi recta y la banda
# se lee plana. Subida a la cintura, donde el toroide más se curva, la
# tipografía se dobla y se ve que está pegada a algo.
V0, V1 = 0.175, 0.470
NU, NV = 192, 6           # cuadros de la malla: a lo largo y a lo ancho


class Pintada(Superficie):
    """La superficie con una banda impresa enrollada encima."""

    NOMBRE = "pintada"

    def _rotular(self):
        """Sin cifras de trazo: aquí las pone la textura."""
        return []

    # ---------- la banda, rasterizada una vez ----------
    def texturas(self):
        return {"banda": etiqueta(TEX_ANCHO, TEX_ALTO)}

    # ---------- la malla sobre la que se enrolla ----------
    def _malla(self):
        """Una rejilla de cuadros en las coordenadas de la superficie.

        Cada vértice lleva su `(fase, v)`, que es a la vez su sitio en el mundo
        y su sitio en la imagen. Por eso la banda queda pegada: las dos cosas
        salen del mismo par de números.
        """
        rej = np.array([self._corte(k / float(NU))[0] for k in range(NU + 1)])
        n_v = rej.shape[1]

        pts, uv = [], []
        for i in range(NU + 1):
            for j in range(NV + 1):
                v = V0 + (V1 - V0) * j / NV
                b = v * (n_v - 1)
                j0 = min(int(b), n_v - 2)
                f = b - j0
                pts.append(rej[i % NU, j0] * (1 - f) + rej[i % NU, j0 + 1] * f)
                # La `v` de la imagen va al revés que la de la superficie: la
                # banda se lee de arriba abajo y el corte sube.
                uv.append((i / float(NU), 1.0 - j / float(NV)))

        idx = []
        for i in range(NU):
            for j in range(NV):
                a = i * (NV + 1) + j
                b = a + (NV + 1)
                idx += [a, b, a + 1, b, b + 1, a + 1]
        return np.array(pts), np.array(uv, np.float32), np.array(idx, np.int32)

    def __init__(self, lado):
        Superficie.__init__(self, lado)
        self._pts, self._uv, self._idx = self._malla()

    def mallas(self, t):
        xy, d = self.cam(self._pts)
        # La niebla se aplica modulando el color de cada vértice: la banda se
        # apaga por detrás igual que el resto de la superficie.
        return (Malla("banda", xy, self._uv, self._idx,
                      tinte_niebla(self.cam, d), 255),)


ESFERA = Pintada
