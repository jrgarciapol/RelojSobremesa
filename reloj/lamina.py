"""La misma esfera, compuesta con Pillow y guardada en PNG.

Sirve para verla sin pantalla —en un servidor, o en una sesión de trabajo— y
para comparar varias horas o varias esferas de un vistazo. Usa exactamente los
mismos arrays y el mismo orden de pintado que la salida por SDL.
"""

import math

import numpy as np
from PIL import Image, ImageDraw


def _teñir(im, color, alfa):
    if color is not None:
        r, g, b = (color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF
        px = np.asarray(im, dtype=np.uint16).copy()
        px[:, :, 0] = px[:, :, 0] * r // 255
        px[:, :, 1] = px[:, :, 1] * g // 255
        px[:, :, 2] = px[:, :, 2] * b // 255
        im = Image.fromarray(px.astype(np.uint8), "RGBA")
    if alfa < 255:
        a = im.getchannel("A").point(lambda v: v * alfa // 255)
        im = im.copy()
        im.putalpha(a)
    return im


def _girar_en(im, pivote, grados):
    """Gira `im` alrededor de `pivote` y devuelve (imagen, nuevo pivote).

    PIL solo sabe girar sobre el centro, así que primero se centra la pieza en
    un cuadrado bastante grande para que no se salga nada. SDL no necesita esto
    —admite un centro de giro cualquiera—, pero aquí no hay prisa.
    """
    px, py = pivote
    R = int(math.ceil(max(math.hypot(x - px, y - py) for x, y in
                          ((0, 0), (im.width, 0), (0, im.height),
                           (im.width, im.height))))) + 1
    cuadro = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
    cuadro.alpha_composite(im, (R - int(round(px)), R - int(round(py))))
    return cuadro.rotate(-grados, resample=Image.BICUBIC), (R, R)


def _pintar_trazo(base, tr):
    """Aquí no hay GPU ni prisa: se dibuja segmento a segmento con Pillow, que
    además redondea las uniones."""
    pts = np.asarray(tr.puntos, float)
    if len(pts) < 2:
        return
    d = ImageDraw.Draw(base, "RGBA")
    g = max(1, int(round(tr.grosor)))
    if isinstance(tr.color, (int, np.integer)):
        c = ((tr.color >> 16) & 0xFF, (tr.color >> 8) & 0xFF, tr.color & 0xFF,
             int(tr.alfa))
        d.line([tuple(p) for p in pts], fill=c, width=g, joint="curve")
    else:
        col = np.asarray(tr.color, np.uint8)
        for i in range(len(pts) - 1):
            r, v, a = col[i]
            d.line([tuple(pts[i]), tuple(pts[i+1])],
                   fill=(int(r), int(v), int(a), int(tr.alfa)), width=g)


def _coef_perspectiva(destino, origen):
    """Los ocho coeficientes que PIL quiere para llevar `destino` a `origen`.

    `Image.transform(..., PERSPECTIVE, ...)` va al revés de lo que uno espera:
    para cada píxel del destino calcula de dónde sacarlo en el origen. Así que
    hay que resolver el sistema en ese sentido.
    """
    m = []
    for (x, y), (u, v) in zip(destino, origen):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        m.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    b = np.array(origen, np.float64).reshape(8)
    return np.linalg.solve(np.array(m, np.float64), b)


def _pintar_malla(base, tex, ma):
    """Cada cuadro de la malla, con su trozo de imagen deformado.

    Aquí no hay GPU. Se recorre cuadro a cuadro: se calcula la perspectiva que
    lleva su rectángulo en la imagen a sus cuatro esquinas en pantalla, y se
    pega con una máscara. Son cuadros pequeños, así que sale en décimas de
    segundo — y esto solo se usa para los PNG, no para la pantalla.
    """
    if tex is None:
        return
    src = Image.fromarray(tex, "RGBA")
    W, H = src.size
    xy = np.asarray(ma.xy, float)
    uv = np.asarray(ma.uv, float) * [W - 1, H - 1]
    idx = np.asarray(ma.indices).reshape(-1, 3)

    # Los índices vienen por triángulos; se juntan de dos en dos, que es como
    # se generaron, para poder usar una perspectiva por cuadro.
    for k in range(0, len(idx) - 1, 2):
        q = [idx[k][0], idx[k][1], idx[k + 1][1], idx[k][2]]
        d, o = xy[q], uv[q]
        x0, y0 = np.floor(d.min(0)).astype(int)
        x1, y1 = np.ceil(d.max(0)).astype(int)
        w, h = x1 - x0, y1 - y0
        if w < 1 or h < 1 or w > 2000 or h > 2000:
            continue
        try:
            c = _coef_perspectiva(d - [x0, y0], o)
        except np.linalg.LinAlgError:
            continue
        trozo = src.transform((w, h), Image.PERSPECTIVE, c, Image.BILINEAR)
        mascara = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mascara).polygon([tuple(p - [x0, y0]) for p in d], fill=255)
        trozo.putalpha(Image.composite(trozo.getchannel("A"), mascara, mascara))
        base.alpha_composite(trozo, (x0, y0))


def componer(Clase, lado, t):
    esf = Clase(lado)
    f = esf.fondo()
    base = (Image.fromarray(f, "RGB").convert("RGBA") if f is not None
            else Image.new("RGBA", (lado, lado), (0, 0, 0, 255)))
    piezas = {}
    for n, dato in esf.piezas().items():
        arr, piv = dato if isinstance(dato, tuple) else (dato, None)
        piezas[n] = (arr, piv)

    def poner(p):
        arr, piv = piezas[p.pieza]
        im = Image.fromarray(arr, "RGBA")
        if piv is None:
            piv = (im.width / 2.0, im.height / 2.0)
        if p.escala != 1.0:
            n = (max(1, int(im.width * p.escala)), max(1, int(im.height * p.escala)))
            piv = (piv[0] * p.escala, piv[1] * p.escala)
            im = im.resize(n, Image.LANCZOS)
        if p.grados:
            im, piv = _girar_en(im, piv, p.grados)
        im = _teñir(im, p.color, p.alfa)
        base.alpha_composite(im, (int(p.x - piv[0]), int(p.y - piv[1])))

    for tr in esf.trazos(t):
        _pintar_trazo(base, tr)

    texturas = esf.texturas()
    for ma in esf.mallas(t):
        _pintar_malla(base, texturas.get(ma.textura), ma)

    for p in esf.detras(t):
        poner(p)
    c = esf.capa(t)
    if c is not None:
        base.alpha_composite(Image.fromarray(c[1], "RGBA"))
    for p in esf.cuadro(t):
        poner(p)

    return base.convert("RGB")


def hoja(trozos, columnas=2, hueco=20, fondo=(18, 18, 18)):
    """Varias imágenes en una rejilla, para compararlas de un vistazo."""
    w = max(im.width for im in trozos)
    h = max(im.height for im in trozos)
    filas = (len(trozos) + columnas - 1) // columnas
    out = Image.new("RGB", (columnas * w + (columnas - 1) * hueco,
                            filas * h + (filas - 1) * hueco), fondo)
    for k, im in enumerate(trozos):
        out.paste(im, ((k % columnas) * (w + hueco), (k // columnas) * (h + hueco)))
    return out


def reloj_a_segundos(txt):
    """'10:09' o '10:09:30' -> segundos desde medianoche."""
    p = [float(x) for x in txt.split(":")]
    while len(p) < 3:
        p.append(0.0)
    return p[0] * 3600 + p[1] * 60 + p[2]
