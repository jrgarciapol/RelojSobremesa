"""La banda horaria: una etiqueta impresa que se enrolla sobre una superficie.

`pintada` estrenó la idea —rasterizar la superficie desenrollada, como quien
despega la etiqueta de una lata, y volver a enrollarla sobre triángulos— y
ahora la usan tres esferas. Lo que se repetía era la etiqueta, así que vive
aquí y no en cada una.

Y aquí está también lo que un toro necesita y una pared abierta no: **ordenar
los cuadros de lejos a cerca**. En `pintada` la banda va sobre una pared que se
ve por una sola cara y da igual el orden. Un toro es cerrado: la mitad de los
cuadros están detrás, y pintados en el orden de la malla tapan a los de
delante. No hay z-buffer y no hace falta uno — con quinientos cuadros, el
algoritmo del pintor cuesta un `argsort` por fotograma.
"""

import numpy as np

from .lienzo import Lienzo, tipo

HUESO = 0xF3E7D3
AMBAR = 0xFFB020
RAYA = 0x4A5A6E


def etiqueta(ancho, alto):
    """La banda de doce horas, desenrollada y rasterizada.

    Todo va en fracciones del alto, así que la misma función sirve para una
    banda ancha y baja (un toro, que da mucha vuelta y poca altura) y para una
    más cuadrada.
    """
    lz = Lienzo(ancho, alto, sup=1)
    f_hora = tipo("Barriecito-Regular.ttf", alto * 0.62)
    f_pie = tipo("RobotoMono-Bold.ttf", alto * 0.11)

    # Dos rayas de guía, arriba y abajo, para que se vea que la banda está
    # impresa y enrollada y no flotando.
    for y in (alto * 0.10, alto * 0.90):
        lz.linea(0, y, ancho, y, alto * 0.012, RAYA)

    for k in range(60):
        x = ancho * k / 60.0
        largo = alto * (0.11 if k % 5 else 0.20)
        lz.linea(x, alto * 0.90, x, alto * 0.90 - largo,
                 alto * (0.010 if k % 5 else 0.020),
                 RAYA if k % 5 else AMBAR)

    # Las doce horas. La de las 12 cae en la costura, así que se pinta a los
    # dos lados: si no, al enrollar la banda saldría medio número.
    for h in range(1, 13):
        x = ancho * (h % 12) / 12.0
        for dx in (-ancho, 0, ancho):
            lz.texto(x + dx, alto * 0.46, str(h), f_hora, HUESO)
        lz.texto(x + ancho / 24.0, alto * 0.955,
                 "%02d" % ((h % 12) * 5), f_pie, RAYA)
    return lz.array()


def malla_toro(radio, tubo, v0, v1, nu, nv):
    """Una rejilla de cuadros sobre un trozo de toro de revolución.

    `u` da la vuelta al donut y es la HORA, o sea la coordenada larga de la
    etiqueta; `v` rodea el tubo entre `v0` y `v1`, con `v = 0` en el ecuador de
    fuera, que es donde el toro más se curva.

    Devuelve `(puntos, uv, cuadros)`. Los cuadros van aparte de los triángulos
    porque el orden en que se pintan se decide cada fotograma.
    """
    u = np.linspace(0.0, 2 * np.pi, nu + 1)
    v = np.linspace(v0, v1, nv + 1)
    U, V = np.meshgrid(u, v, indexing="ij")

    ancho = radio + tubo * np.cos(V)
    pts = np.stack([ancho * np.cos(U), ancho * np.sin(U),
                    tubo * np.sin(V)], axis=-1).reshape(-1, 3)
    # La `v` de la imagen va al revés que la del tubo: la banda se lee de
    # arriba abajo y el tubo sube.
    uv = np.stack([U / (2 * np.pi),
                   1.0 - (V - v0) / (v1 - v0)], axis=-1)
    uv = uv.reshape(-1, 2).astype(np.float32)

    a = np.arange(nu)[:, None] * (nv + 1) + np.arange(nv)[None, :]
    b = a + (nv + 1)
    cuadros = np.stack([a, b, a + 1, b + 1], axis=-1).reshape(-1, 4)
    return pts, uv, cuadros


def de_lejos_a_cerca(cuadros, xy, d):
    """Los triángulos que se ven, del fondo hacia delante.

    Dos cosas, y las dos hacen falta en un toro:

    **Fuera los cuadros que dan la espalda.** En la mitad de atrás la
    superficie nos enseña su cara interior, y una etiqueta vista por dentro
    sale en espejo: la primera versión tenía un `8` del revés flotando sobre
    el agujero. Se detecta sin normales ni productos vectoriales en el mundo —
    si el cuadro está de espaldas, sus vértices salen girados al revés en
    pantalla, y eso es el signo de un determinante de dos por dos.

    **Y los que quedan, ordenados de lejos a cerca.** Sin z-buffer manda el
    orden de pintado, así que lo de delante va al final. Con quinientos
    cuadros, es un `argsort`.
    """
    a, b, c = cuadros[:, 0], cuadros[:, 1], cuadros[:, 2]
    ab, ac = xy[b] - xy[a], xy[c] - xy[a]
    delante = ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0] < 0
    q = cuadros[delante]
    if not len(q):
        return np.zeros(0, np.int32)
    q = q[np.argsort(-d[q].mean(axis=1))]
    return np.stack([q[:, 0], q[:, 1], q[:, 2],
                     q[:, 1], q[:, 3], q[:, 2]], axis=-1).ravel().astype(np.int32)


def tinte_niebla(cam, d, dureza=1.5, fondo=1.9, suelo=0.22):
    """Color por vértice para que la banda se apague por detrás igual que la
    superficie que la lleva. Gris: multiplica a la textura, no la tiñe."""
    n = cam.niebla(d, dureza, fondo)
    col = np.clip((suelo + (1.0 - suelo) * n)[:, None] * 255, 0, 255).astype(np.uint8)
    return np.repeat(col, 3, axis=1)
