"""Salida por SDL2: sube los arrays a la tarjeta y los mueve por hardware.

Misma pila que el simulador de conducción (`pysdl2` + `numpy`), y por la misma
razón: SDL2 pinta sobre KMS/DRM sin escritorio, así que en la Pi arranca contra
la pantalla pelada, sin X ni Wayland.

Por fotograma solo hay `RenderCopyEx`: rotar, escalar y teñir los hace la GPU.
El coste de rasterizar se pagó al arrancar.
"""

import ctypes
import os
import time

import numpy as np
import sdl2


def _textura(ren, arr):
    """numpy (h, w, 3|4) uint8 -> (SDL_Texture, (ancho, alto)).

    El array tiene que seguir vivo mientras exista la superficie, así que se
    libera la superficie **antes** de salir de la función.
    """
    arr = np.ascontiguousarray(arr)
    h, w = arr.shape[:2]
    if arr.shape[2] == 3:
        arr = np.ascontiguousarray(
            np.dstack([arr, np.full((h, w, 1), 255, np.uint8)]))
    # numpy guarda R,G,B,A en ese orden de bytes; en little-endian eso es un
    # uint32 ABGR.
    sup = sdl2.SDL_CreateRGBSurfaceWithFormatFrom(
        arr.ctypes.data_as(ctypes.c_void_p), w, h, 32, w * 4,
        sdl2.SDL_PIXELFORMAT_ABGR8888)
    tex = sdl2.SDL_CreateTextureFromSurface(ren, sup)
    sdl2.SDL_FreeSurface(sup)
    sdl2.SDL_SetTextureBlendMode(tex, sdl2.SDL_BLENDMODE_BLEND)
    return tex, (w, h)


def _tira(pts, grosor):
    """Convierte una polilínea en una tira de triángulos.

    La GPU no dibuja líneas gruesas: dibuja triángulos. Cada vértice se
    desplaza a un lado y a otro por la **normal media** de sus dos segmentos
    —el inglete—, que es lo que evita que las esquinas se abran en las curvas
    cerradas.
    """
    d = np.diff(pts, axis=0)
    ln = np.maximum(np.hypot(d[:, 0], d[:, 1])[:, None], 1e-6)
    u = d / ln
    nseg = np.stack([-u[:, 1], u[:, 0]], axis=1)

    nv = np.empty_like(pts)
    nv[0], nv[-1] = nseg[0], nseg[-1]
    nv[1:-1] = nseg[:-1] + nseg[1:]
    nv /= np.maximum(np.hypot(nv[:, 0], nv[:, 1])[:, None], 1e-6)

    n = len(pts)
    xy = np.empty((2 * n, 2), np.float32)
    xy[0::2] = pts + nv * (grosor / 2.0)
    xy[1::2] = pts - nv * (grosor / 2.0)

    i = np.arange(n - 1) * 2
    idx = np.empty((n - 1, 6), np.int32)
    idx[:, 0], idx[:, 1], idx[:, 2] = i, i + 1, i + 2
    idx[:, 3], idx[:, 4], idx[:, 5] = i + 1, i + 3, i + 2
    return xy, idx.reshape(-1)


def _pintar_trazo(ren, tr, ox, oy):
    pts = np.asarray(tr.puntos, np.float32)
    if len(pts) < 2:
        return
    pts = pts + np.float32([ox, oy])
    xy, idx = _tira(pts, tr.grosor)

    col = np.empty((len(xy), 4), np.uint8)
    if isinstance(tr.color, (int, np.integer)):
        col[:, 0] = (tr.color >> 16) & 0xFF
        col[:, 1] = (tr.color >> 8) & 0xFF
        col[:, 2] = tr.color & 0xFF
    else:
        c = np.asarray(tr.color, np.uint8)
        col[0::2, :3] = c
        col[1::2, :3] = c
    col[:, 3] = tr.alfa

    uv = np.zeros_like(xy)
    sdl2.SDL_RenderGeometryRaw(
        ren, None,
        xy.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 8,
        col.ctypes.data_as(ctypes.POINTER(sdl2.SDL_Color)), 4,
        uv.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 8,
        len(xy),
        idx.ctypes.data_as(ctypes.c_void_p), len(idx), 4)


def ahora():
    """Segundos desde medianoche, hora local, con decimales."""
    t = time.time()
    lt = time.localtime(t)
    return lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec + (t % 1.0)



class _Montaje:
    """Las texturas de UNA esfera. Cambiar de esfera es tirar esto y rehacerlo.

    Rehacerlo cuesta lo que cueste rasterizarla —décimas de segundo— y solo
    pasa cuando se pulsa una flecha, así que no compite con el bucle.
    """

    def __init__(self, ren, Clase, lado):
        self.ren = ren
        self.esf = Clase(lado)
        f = self.esf.fondo()
        self.fondo = _textura(ren, f)[0] if f is not None else None
        # Una pieza puede venir sola (gira por su centro) o con su pivote.
        self.piezas = {}
        for n, dato in self.esf.piezas().items():
            arr, piv = dato if isinstance(dato, tuple) else (dato, None)
            tex, (w, h) = _textura(ren, arr)
            self.piezas[n] = (tex, (w, h), piv or (w / 2.0, h / 2.0))
        self.capa = None
        self.clave = object()

    def soltar(self):
        for tex, _, _ in self.piezas.values():
            sdl2.SDL_DestroyTexture(tex)
        for tex in (self.fondo, self.capa):
            if tex is not None:
                sdl2.SDL_DestroyTexture(tex)


def _rotulo(ren, texto, lado):
    """El nombre de la esfera, para enseñarlo un momento al cambiar."""
    from .lienzo import Lienzo, tipo
    cuerpo = max(12, lado * 0.045)
    lz = Lienzo(int(lado * 0.7), int(cuerpo * 2.0), sup=1)
    lz.texto(4, cuerpo, texto, tipo("RobotoMono-Bold.ttf", cuerpo), 0xFFFFFF,
             anclaje="lm")
    return _textura(ren, lz.array())


def correr(nombres, indice=0, lado=None, ventana=False, fps=30, hora=None,
           guardar_en=".", velocidad=1.0):
    """Muestra `nombres[indice]` y deja pasear por el resto con las flechas.

    `velocidad` multiplica el paso del tiempo. No es un juguete: la familia de
    `eliptica` da una vuelta por HORA y la cámara del toro tarda cinco minutos,
    así que a velocidad real no hay forma de juzgar si el movimiento funciona.
    A x600 la vuelta entera dura seis segundos.
    """
    from .esferas import cargar

    if isinstance(nombres, str):
        nombres = [nombres]

    if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) != 0:
        raise SystemExit(sdl2.SDL_GetError().decode())

    # Filtrado bilineal: sin esto la rotación de las agujas sale a escalones y
    # se pierde justo el antialiasing que fuimos a buscar.
    sdl2.SDL_SetHint(sdl2.SDL_HINT_RENDER_SCALE_QUALITY, b"1")

    modo = sdl2.SDL_DisplayMode()
    sdl2.SDL_GetCurrentDisplayMode(0, ctypes.byref(modo))
    if ventana:
        lado = lado or 800
        ancho = alto = lado
        flags = 0
    else:
        ancho, alto = modo.w, modo.h
        lado = lado or min(ancho, alto)
        flags = sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP

    win = sdl2.SDL_CreateWindow(b"reloj", sdl2.SDL_WINDOWPOS_CENTERED,
                                sdl2.SDL_WINDOWPOS_CENTERED, ancho, alto, flags)
    ren = sdl2.SDL_CreateRenderer(
        win, -1, sdl2.SDL_RENDERER_ACCELERATED | sdl2.SDL_RENDERER_PRESENTVSYNC)
    sdl2.SDL_ShowCursor(sdl2.SDL_DISABLE)

    ox, oy = (ancho - lado) // 2, (alto - lado) // 2
    dst_dial = sdl2.SDL_Rect(ox, oy, lado, lado)
    ev = sdl2.SDL_Event()
    espera = 1.0 / fps

    # Reloj virtual: parte de la hora real y avanza `velocidad` veces más
    # rápido. A x1 es la hora de verdad.
    t_virtual, t_real = ahora(), time.time()

    m = _Montaje(ren, cargar(nombres[indice]), lado)
    rot, rot_wh = _rotulo(ren, nombres[indice], lado)
    rot_hasta = time.time() + 2.5

    def poner(p):
        tex, (w, h), (pvx, pvy) = m.piezas[p.pieza]
        w, h = max(1, int(w * p.escala)), max(1, int(h * p.escala))
        pvx, pvy = pvx * p.escala, pvy * p.escala
        # El destino se coloca para que el PIVOTE caiga en (p.x, p.y), y el
        # giro se hace sobre ese mismo punto.
        dst = sdl2.SDL_Rect(int(ox + p.x - pvx), int(oy + p.y - pvy), w, h)
        if p.color is None:
            sdl2.SDL_SetTextureColorMod(tex, 255, 255, 255)
        else:
            sdl2.SDL_SetTextureColorMod(tex, (p.color >> 16) & 0xFF,
                                        (p.color >> 8) & 0xFF, p.color & 0xFF)
        sdl2.SDL_SetTextureAlphaMod(tex, int(p.alfa))
        centro = sdl2.SDL_Point(int(pvx), int(pvy))
        sdl2.SDL_RenderCopyEx(ren, tex, None, ctypes.byref(dst), p.grados,
                              ctypes.byref(centro), sdl2.SDL_FLIP_NONE)

    def cambiar(paso):
        nonlocal m, rot, rot_wh, rot_hasta, indice
        indice = (indice + paso) % len(nombres)
        m.soltar()
        sdl2.SDL_DestroyTexture(rot)
        m = _Montaje(ren, cargar(nombres[indice]), lado)
        rot, rot_wh = _rotulo(ren, nombres[indice], lado)
        rot_hasta = time.time() + 2.5

    def foto():
        """Guarda lo que se ve ahora mismo, para poder enseñarlo."""
        from . import lamina
        from .esferas import cargar as _c
        nombre = os.path.join(
            guardar_en, "%s-%s.png" % (nombres[indice],
                                       time.strftime("%H%M%S")))
        lamina.componer(_c(nombres[indice]), lado, ahora()).save(nombre)
        print("guardado " + nombre)

    try:
        while True:
            while sdl2.SDL_PollEvent(ctypes.byref(ev)):
                if ev.type == sdl2.SDL_QUIT:
                    return
                if ev.type != sdl2.SDL_KEYDOWN:
                    continue
                k = ev.key.keysym.sym
                if k in (sdl2.SDLK_ESCAPE, sdl2.SDLK_q):
                    return
                if k in (sdl2.SDLK_RIGHT, sdl2.SDLK_DOWN, sdl2.SDLK_SPACE):
                    cambiar(+1)
                elif k in (sdl2.SDLK_LEFT, sdl2.SDLK_UP):
                    cambiar(-1)
                elif k == sdl2.SDLK_g:
                    foto()

            if hora is not None:
                t = hora
            else:
                r = time.time()
                t_virtual = (t_virtual + (r - t_real) * velocidad) % 86400.0
                t_real = r
                t = t_virtual

            sdl2.SDL_SetRenderDrawColor(ren, 0, 0, 0, 255)
            sdl2.SDL_RenderClear(ren)
            if m.fondo is not None:
                sdl2.SDL_RenderCopy(ren, m.fondo, None, ctypes.byref(dst_dial))

            for tr in m.esf.trazos(t):
                _pintar_trazo(ren, tr, ox, oy)

            for p in m.esf.detras(t):
                poner(p)

            c = m.esf.capa(t)
            if c is not None:
                if c[0] != m.clave:
                    if m.capa is not None:
                        sdl2.SDL_DestroyTexture(m.capa)
                    m.capa = _textura(ren, c[1])[0]
                    m.clave = c[0]
                sdl2.SDL_RenderCopy(ren, m.capa, None, ctypes.byref(dst_dial))

            for p in m.esf.cuadro(t):
                poner(p)

            # El nombre de la esfera, que se apaga solo a los 2,5 s.
            queda = rot_hasta - time.time()
            if queda > 0 and len(nombres) > 1:
                sdl2.SDL_SetTextureAlphaMod(rot, int(255 * min(1.0, queda / 0.6)))
                r = sdl2.SDL_Rect(ox + int(lado * 0.04),
                                  oy + int(lado * 0.03), *rot_wh)
                sdl2.SDL_RenderCopy(ren, rot, None, ctypes.byref(r))

            sdl2.SDL_RenderPresent(ren)
            time.sleep(espera)
    finally:
        m.soltar()
        sdl2.SDL_DestroyTexture(rot)
        sdl2.SDL_DestroyRenderer(ren)
        sdl2.SDL_DestroyWindow(win)
        sdl2.SDL_Quit()
