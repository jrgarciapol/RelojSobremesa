"""Como `superficie`, pero con los números **proyectados de verdad**.

En `superficie` las cifras están colocadas en el plano tangente de un cilindro
de radio fijo que pasa cerca de la superficie. Se le parece mucho —tienen su
escorzo, las de atrás se ven del revés— pero **flotan**: no tocan la superficie
más que de casualidad, y no se enteran de su forma.

Aquí se hace lo otro. La superficie tiene sus propias coordenadas:

    fase   la vuelta al anillo, que es la hora
    v      el recorrido a lo largo del corte, de 0 a 1

Las cifras se dibujan **en ese plano `(fase, v)`** y luego se empujan por la
parametrización. El resultado es que están sobre la superficie por
construcción, no por aproximación: la siguen donde sube, se estiran donde se
ensancha y **se retuercen donde se pellizca**. Que un número se deforme al
pasar por la fibra singular no es un fallo del dibujo, es la superficie.

Es lo mismo que hace una textura en un motor 3D, pero sin textura: la cifra ya
era una polilínea, así que basta con mapear sus vértices.
"""

import math

import numpy as np

from ..trazos_tipo import numero
from .superficie import Superficie

REJILLA = 288       # azimuts precalculados para poder interpolar
# Las dos coordenadas de la superficie NO están a la misma escala: dar la
# vuelta al anillo son unas diez unidades de mundo y recorrer un corte unas
# tres. Con el mismo factor en las dos, las cifras salen chafadas —anchas y
# bajas—, que es lo que pasaba a ojo antes de medirlo.
V_CIFRA = 0.795     # dónde caen las cifras a lo largo del corte
ESC_FASE = 0.015    # cuánto abarca una cifra dando la vuelta
ESC_V = 0.105       # y a lo largo del corte


class Grabada(Superficie):
    """Las horas grabadas en la superficie, en sus propias coordenadas."""

    NOMBRE = "grabada"

    def _rotular(self):
        # Una rejilla densa de la superficie, para poder preguntarle por un
        # punto cualquiera y no solo por los cortes que se dibujan.
        malla = np.array([self._corte(k / float(REJILLA))[0]
                          for k in range(REJILLA)])          # (AZ, M, 3)
        n_az, n_v = malla.shape[0], malla.shape[1]

        def en_superficie(fase, v):
            """Bilineal sobre la rejilla. `fase` da la vuelta, `v` se recorta."""
            a = np.mod(np.asarray(fase), 1.0) * n_az
            i0 = np.floor(a).astype(int) % n_az
            i1 = (i0 + 1) % n_az
            fa = (a - np.floor(a))[:, None]

            b = np.clip(np.asarray(v), 0.0, 1.0) * (n_v - 1)
            j0 = np.floor(b).astype(int)
            j1 = np.minimum(j0 + 1, n_v - 1)
            fb = (b - np.floor(b))[:, None]

            return ((malla[i0, j0] * (1 - fb) + malla[i0, j1] * fb) * (1 - fa)
                    + (malla[i1, j0] * (1 - fb) + malla[i1, j1] * fb) * fa)

        fuera = []
        for h in range(1, 13):
            fase_h = (h % 12) / 12.0
            for trazo in numero(h):
                u = np.array([p[0] for p in trazo])
                w = np.array([p[1] for p in trazo])
                fuera.append((h, en_superficie(fase_h + u * ESC_FASE,
                                               V_CIFRA + w * ESC_V)))
        return fuera


ESFERA = Grabada
