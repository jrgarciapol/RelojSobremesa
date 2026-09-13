"""Cifras de trazo, para escribir **sobre** una superficie en tres dimensiones.

Una fuente normal no sirve aquí. Un glifo rasterizado es un rectángulo de
píxeles, y pegarlo sobre una superficie curva exigiría mapear texturas — que es
justo lo que este reloj no hace, porque manda vértices y no imágenes.

Estas cifras son **polilíneas**: unas cuantas coordenadas en una caja de 1 de
ancho por 2 de alto, con el origen abajo a la izquierda y la Y hacia arriba.
Puestas sobre el plano tangente de una superficie salen dibujadas encima, con
su perspectiva y su escorzo, como pintadas.
"""

# Cada cifra son uno o más trazos. Dibujadas a mano: no imitan ninguna
# tipografía, imitan a alguien escribiendo un número con un rotulador.
CIFRAS = {
    "0": [[(0.15, 0.4), (0.15, 1.6), (0.5, 2.0), (0.85, 1.6),
           (0.85, 0.4), (0.5, 0.0), (0.15, 0.4)]],
    "1": [[(0.15, 1.55), (0.55, 2.0), (0.55, 0.0)],
          [(0.15, 0.0), (0.95, 0.0)]],
    "2": [[(0.05, 1.6), (0.35, 2.0), (0.7, 2.0), (0.95, 1.7),
           (0.95, 1.3), (0.05, 0.0), (0.95, 0.0)]],
    "3": [[(0.08, 2.0), (0.9, 2.0), (0.42, 1.18), (0.72, 1.18),
           (0.95, 0.92), (0.95, 0.3), (0.68, 0.0), (0.2, 0.0), (0.02, 0.25)]],
    "4": [[(0.72, 0.0), (0.72, 2.0), (0.02, 0.62), (0.98, 0.62)]],
    "5": [[(0.92, 2.0), (0.12, 2.0), (0.08, 1.18), (0.62, 1.25),
           (0.95, 0.95), (0.95, 0.32), (0.66, 0.0), (0.14, 0.05)]],
    "6": [[(0.9, 1.75), (0.6, 2.0), (0.28, 1.9), (0.1, 1.35),
           (0.08, 0.42), (0.38, 0.0), (0.72, 0.0), (0.95, 0.35),
           (0.9, 0.82), (0.6, 1.08), (0.22, 1.0), (0.08, 0.72)]],
    "7": [[(0.05, 2.0), (0.95, 2.0), (0.38, 0.0)],
          [(0.28, 0.95), (0.78, 0.95)]],
    "8": [[(0.35, 1.1), (0.1, 1.38), (0.12, 1.78), (0.45, 2.0),
           (0.8, 1.8), (0.85, 1.42), (0.6, 1.12), (0.22, 0.88),
           (0.06, 0.5), (0.3, 0.02), (0.72, 0.05), (0.94, 0.42),
           (0.78, 0.85), (0.35, 1.1)]],
    "9": [[(0.1, 0.22), (0.42, 0.0), (0.76, 0.12), (0.92, 0.62),
           (0.92, 1.6), (0.62, 2.0), (0.28, 1.98), (0.06, 1.62),
           (0.12, 1.18), (0.45, 0.95), (0.82, 1.02), (0.92, 1.28)]],
}

ANCHO = 1.0      # de una cifra
HUECO = 0.22     # entre dos cifras del mismo número


def numero(n):
    """Los trazos de un número entero, centrado en (0, 0).

    Devuelve una lista de listas de (u, v), listas para colocarlas en el plano
    tangente que sea. La altura es 2 y el ancho depende de cuántas cifras.
    """
    texto = str(n)
    total = len(texto) * ANCHO + (len(texto) - 1) * HUECO
    x0 = -total / 2.0
    fuera = []
    for c in texto:
        for trazo in CIFRAS[c]:
            fuera.append([(x0 + u, v - 1.0) for u, v in trazo])
        x0 += ANCHO + HUECO
    return fuera
