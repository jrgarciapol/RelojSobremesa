"""Salida por SDL2: sube los arrays a la tarjeta y los mueve por hardware.

Misma pila que el simulador de conducción (`pysdl2` + `numpy`), y por la misma
razón: SDL2 pinta sobre KMS/DRM sin escritorio, así que en la Pi arranca contra
la pantalla pelada, sin X ni Wayland.

Por fotograma solo hay `RenderCopyEx`: rotar, escalar y teñir los hace la GPU.
El coste de rasterizar se pagó al arrancar.
"""

import ctypes
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


def ahora():
    """Segundos desde medianoche, hora local, con decimales."""
    t = time.time()
    lt = time.localtime(t)
    return lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec + (t % 1.0)


def correr(Clase, lado=None, ventana=False, fps=30, hora=None):
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

    esf = Clase(lado)
    ox, oy = (ancho - lado) // 2, (alto - lado) // 2

    f = esf.fondo()
    tex_fondo = _textura(ren, f)[0] if f is not None else None
    piezas = {n: _textura(ren, a) for n, a in esf.piezas().items()}

    tex_capa, clave_capa = None, object()
    dst_dial = sdl2.SDL_Rect(ox, oy, lado, lado)
    ev = sdl2.SDL_Event()
    espera = 1.0 / fps

    def poner(p):
        tex, (w, h) = piezas[p.pieza]
        w, h = max(1, int(w * p.escala)), max(1, int(h * p.escala))
        dst = sdl2.SDL_Rect(int(ox + p.x - w / 2.0), int(oy + p.y - h / 2.0), w, h)
        if p.color is None:
            sdl2.SDL_SetTextureColorMod(tex, 255, 255, 255)
        else:
            sdl2.SDL_SetTextureColorMod(tex, (p.color >> 16) & 0xFF,
                                        (p.color >> 8) & 0xFF, p.color & 0xFF)
        sdl2.SDL_SetTextureAlphaMod(tex, int(p.alfa))
        centro = sdl2.SDL_Point(w // 2, h // 2)
        sdl2.SDL_RenderCopyEx(ren, tex, None, ctypes.byref(dst), p.grados,
                              ctypes.byref(centro), sdl2.SDL_FLIP_NONE)

    try:
        while True:
            while sdl2.SDL_PollEvent(ctypes.byref(ev)):
                if ev.type == sdl2.SDL_QUIT:
                    return
                if (ev.type == sdl2.SDL_KEYDOWN
                        and ev.key.keysym.sym in (sdl2.SDLK_ESCAPE, sdl2.SDLK_q)):
                    return

            t = ahora() if hora is None else hora

            sdl2.SDL_SetRenderDrawColor(ren, 0, 0, 0, 255)
            sdl2.SDL_RenderClear(ren)
            if tex_fondo is not None:
                sdl2.SDL_RenderCopy(ren, tex_fondo, None, ctypes.byref(dst_dial))

            for p in esf.detras(t):
                poner(p)

            c = esf.capa(t)
            if c is not None:
                if c[0] != clave_capa:
                    if tex_capa is not None:
                        sdl2.SDL_DestroyTexture(tex_capa)
                    tex_capa = _textura(ren, c[1])[0]
                    clave_capa = c[0]
                sdl2.SDL_RenderCopy(ren, tex_capa, None, ctypes.byref(dst_dial))

            for p in esf.cuadro(t):
                poner(p)

            sdl2.SDL_RenderPresent(ren)
            time.sleep(espera)
    finally:
        for tex, _ in piezas.values():
            sdl2.SDL_DestroyTexture(tex)
        for tex in (tex_fondo, tex_capa):
            if tex is not None:
                sdl2.SDL_DestroyTexture(tex)
        sdl2.SDL_DestroyRenderer(ren)
        sdl2.SDL_DestroyWindow(win)
        sdl2.SDL_Quit()
