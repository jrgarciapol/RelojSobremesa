"""Salida por SDL2: sube los arrays a la tarjeta y los mueve por hardware.

Misma pila que el simulador de conducción (`pysdl2` + `numpy`), y por la misma
razón: SDL2 pinta sobre KMS/DRM sin escritorio, así que en la Pi arranca contra
la pantalla pelada, sin X ni Wayland.

Por fotograma solo hay `RenderCopyEx`: rotar, escalar y teñir los hace la GPU.
El coste de rasterizar se pagó al arrancar.

Dos cosas más viven aquí y las dos las trajo la Steam Deck:

**Los mandos.** Lanzado desde la consola, la Deck manda sus botones como
teclas y las flechas funcionan. Lanzado desde Steam —que es lo que hay que
hacer para verlo en Modo Juego— Steam Input se interpone y lo que llega ya no
son teclas sino un **gamepad virtual**. Si nadie escucha esos eventos no
responde nada, y encima no hay forma de salir, porque el teclado tampoco está.

**El desplazamiento contra el quemado.** En OLED el desgaste es diferencial y
un reloj es el caso peor: las mismas líneas caen siempre en los mismos píxeles.
"""

import ctypes
import math
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


def _pintar_malla(ren, tex, ma, ox, oy):
    """Triángulos con imagen pegada. Lo hace la GPU."""
    xy = np.ascontiguousarray(np.asarray(ma.xy, np.float32)
                              + np.float32([ox, oy]))
    uv = np.ascontiguousarray(np.asarray(ma.uv, np.float32))
    idx = np.ascontiguousarray(np.asarray(ma.indices, np.int32))

    col = np.empty((len(xy), 4), np.uint8)
    if ma.color is None:
        col[:, :3] = 255
    elif isinstance(ma.color, (int, np.integer)):
        col[:, 0] = (ma.color >> 16) & 0xFF
        col[:, 1] = (ma.color >> 8) & 0xFF
        col[:, 2] = ma.color & 0xFF
    else:
        col[:, :3] = np.asarray(ma.color, np.uint8)
    col[:, 3] = ma.alfa

    sdl2.SDL_RenderGeometryRaw(
        ren, tex,
        xy.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 8,
        col.ctypes.data_as(ctypes.POINTER(sdl2.SDL_Color)), 4,
        uv.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), 8,
        len(xy),
        idx.ctypes.data_as(ctypes.c_void_p), len(idx), 4)


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
        self.texturas = {n: _textura(ren, a)[0]
                         for n, a in self.esf.texturas().items()}
        self.capa = None
        self.clave = object()

    def soltar(self):
        for tex, _, _ in self.piezas.values():
            sdl2.SDL_DestroyTexture(tex)
        for tex in list(self.texturas.values()) + [self.fondo, self.capa]:
            if tex is not None:
                sdl2.SDL_DestroyTexture(tex)


def _rotulo(ren, texto, lado, pie=None):
    """El nombre de la esfera, para enseñarlo un momento al cambiar.

    `pie` es la chuleta de los botones: solo se pone si hay mando, porque con
    teclado las teclas ya se saben y estorbaría.
    """
    from .lienzo import Lienzo, tipo
    cuerpo = max(12, lado * 0.045)
    alto = cuerpo * (2.9 if pie else 2.0)
    lz = Lienzo(int(lado * 0.7), int(alto), sup=1)
    lz.texto(4, cuerpo, texto, tipo("RobotoMono-Bold.ttf", cuerpo), 0xFFFFFF,
             anclaje="lm")
    if pie:
        lz.texto(4, cuerpo * 2.1, pie,
                 tipo("RobotoMono-Bold.ttf", cuerpo * 0.46), 0x8FB0C4,
                 anclaje="lm")
    return _textura(ren, lz.array())


# ------------------------------------------------------------------ mandos --
# Lo que llega por Steam Input es un gamepad virtual del 360, así que con la
# capa de `GameController` basta y los botones salen ya con nombre. Pero si el
# aparato no tiene mapeo —un mando raro, o la Deck expuesta en crudo— esa capa
# no abre nada y hay que caer al joystick pelado: botones y cruceta a secas.
# La diferencia importa poco para lo que se pide aquí, que son cuatro órdenes.
_EJE_UMBRAL = 18000         # de los 32767 de un eje: ni el roce ni forcejeando


class _Mandos:
    """Traduce mandos a las cuatro órdenes de la esfera.

    `suceso()` devuelve None, "+1", "-1", "foto" o "salir". Los ejes se tratan
    por flanco —hay que soltar el palo para que vuelva a contar— porque si no,
    un empujón mantenido pasa las veintinueve esferas de un tirón.
    """

    def __init__(self):
        self.pads = {}          # id de instancia -> (handle, es_controller)
        self.eje = {}           # id de instancia -> -1, 0, +1
        for i in range(sdl2.SDL_NumJoysticks()):
            self.abrir(i)

    def hay(self):
        return bool(self.pads)

    def abrir(self, indice):
        if sdl2.SDL_IsGameController(indice):
            h = sdl2.SDL_GameControllerOpen(indice)
            if not h:
                return
            iid = sdl2.SDL_JoystickInstanceID(
                sdl2.SDL_GameControllerGetJoystick(h))
            self.pads[iid] = (h, True)
        else:
            h = sdl2.SDL_JoystickOpen(indice)
            if not h:
                return
            self.pads[sdl2.SDL_JoystickInstanceID(h)] = (h, False)

    def cerrar(self, iid):
        par = self.pads.pop(iid, None)
        if par is None:
            return
        h, es_controller = par
        if es_controller:
            sdl2.SDL_GameControllerClose(h)
        else:
            sdl2.SDL_JoystickClose(h)

    def soltar(self):
        for iid in list(self.pads):
            self.cerrar(iid)

    # ---------- eventos ----------
    def suceso(self, ev):
        t = ev.type
        if t == sdl2.SDL_CONTROLLERDEVICEADDED:
            self.abrir(ev.cdevice.which)
        elif t == sdl2.SDL_JOYDEVICEADDED:
            if not sdl2.SDL_IsGameController(ev.jdevice.which):
                self.abrir(ev.jdevice.which)
        elif t in (sdl2.SDL_CONTROLLERDEVICEREMOVED, sdl2.SDL_JOYDEVICEREMOVED):
            self.cerrar(ev.jdevice.which)
        elif t == sdl2.SDL_CONTROLLERBUTTONDOWN:
            return self._boton(ev.cbutton.button)
        elif t == sdl2.SDL_CONTROLLERAXISMOTION:
            if ev.caxis.axis in (sdl2.SDL_CONTROLLER_AXIS_LEFTX,
                                 sdl2.SDL_CONTROLLER_AXIS_RIGHTX):
                return self._palo(ev.caxis.which, ev.caxis.value)
        elif t == sdl2.SDL_JOYBUTTONDOWN:
            if self._crudo(ev.jbutton.which):
                return self._boton_crudo(ev.jbutton.button)
        elif t == sdl2.SDL_JOYHATMOTION:
            if self._crudo(ev.jhat.which):
                if ev.jhat.value & (sdl2.SDL_HAT_RIGHT | sdl2.SDL_HAT_DOWN):
                    return "+1"
                if ev.jhat.value & (sdl2.SDL_HAT_LEFT | sdl2.SDL_HAT_UP):
                    return "-1"
        elif t == sdl2.SDL_JOYAXISMOTION:
            if self._crudo(ev.jaxis.which) and ev.jaxis.axis == 0:
                return self._palo(ev.jaxis.which, ev.jaxis.value)
        return None

    def _crudo(self, iid):
        """Solo los que no son `GameController`: si lo son, sus eventos ya
        llegan por el otro lado y atenderlos dos veces sería contar doble."""
        par = self.pads.get(iid)
        return par is not None and not par[1]

    def _boton(self, b):
        if b in (sdl2.SDL_CONTROLLER_BUTTON_DPAD_RIGHT,
                 sdl2.SDL_CONTROLLER_BUTTON_DPAD_DOWN,
                 sdl2.SDL_CONTROLLER_BUTTON_A,
                 sdl2.SDL_CONTROLLER_BUTTON_RIGHTSHOULDER):
            return "+1"
        if b in (sdl2.SDL_CONTROLLER_BUTTON_DPAD_LEFT,
                 sdl2.SDL_CONTROLLER_BUTTON_DPAD_UP,
                 sdl2.SDL_CONTROLLER_BUTTON_LEFTSHOULDER):
            return "-1"
        if b in (sdl2.SDL_CONTROLLER_BUTTON_B,
                 sdl2.SDL_CONTROLLER_BUTTON_BACK):
            return "salir"
        if b in (sdl2.SDL_CONTROLLER_BUTTON_X,
                 sdl2.SDL_CONTROLLER_BUTTON_Y):
            return "foto"
        return None

    def _boton_crudo(self, b):
        """Sin mapeo no hay nombres, solo números. El orden de los cuatro
        botones de cara es el de siempre: A, B, X, Y."""
        return {0: "+1", 1: "salir", 2: "foto", 3: "foto"}.get(b)

    def _palo(self, iid, valor):
        lado = 0 if abs(valor) < _EJE_UMBRAL else (1 if valor > 0 else -1)
        if lado == self.eje.get(iid, 0):
            return None
        self.eje[iid] = lado
        return {1: "+1", -1: "-1"}.get(lado)


# ------------------------------------------------- deriva contra el quemado --
# En OLED el desgaste es diferencial: el píxel que lleva horas encendido
# envejece más que el que está apagado, y un reloj es el caso peor porque las
# mismas líneas caen siempre en los mismos píxeles. El Epix lo resolvía
# desplazando el dibujo cada minuto; aquí se hace lo mismo pero sin saltos.
#
# El dial deriva por una figura de Lissajous de periodos **primos entre sí**,
# así que la trayectoria no se cierra y no repite posiciones. Con 8 px de
# amplitud la velocidad máxima es 2*pi*8/397 = 0,13 px/s: a ojo el dial está
# clavado, y aun así ningún píxel conserva el mismo contenido más de unos
# segundos. El dial se encoge lo justo para que la deriva nunca lo recorte.
DERIVA = (397.0, 613.0)     # segundos de cada eje
DERIVA_POR_MIL = 10         # amplitud por defecto, en milésimas del lado


def _deriva(t, amplitud):
    """Cuánto se corre el dial en este instante, en píxeles enteros."""
    if amplitud <= 0:
        return 0, 0
    return (int(round(amplitud * math.sin(2 * math.pi * t / DERIVA[0]))),
            int(round(amplitud * math.sin(2 * math.pi * t / DERIVA[1]))))


def correr(nombres, indice=0, lado=None, ventana=False, fps=30, hora=None,
           guardar_en=".", velocidad=1.0, deriva=None):
    """Muestra `nombres[indice]` y deja pasear por el resto con las flechas.

    `velocidad` multiplica el paso del tiempo. No es un juguete: la familia de
    `eliptica` da una vuelta por HORA y la cámara del toro tarda cinco minutos,
    así que a velocidad real no hay forma de juzgar si el movimiento funciona.
    A x600 la vuelta entera dura seis segundos.

    `deriva` es la amplitud en píxeles del vaivén contra el quemado; None la
    saca del tamaño de la pantalla y 0 lo desactiva.
    """
    from .esferas import cargar

    if isinstance(nombres, str):
        nombres = [nombres]

    if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) != 0:
        raise SystemExit(sdl2.SDL_GetError().decode())
    # Los mandos aparte y sin dar por muerto el reloj si fallan: sin udev, o
    # dentro de según qué contenedor, el subsistema no abre y el teclado sigue
    # valiendo. Quedarse sin esferas por no poder abrir un mando sería absurdo.
    sdl2.SDL_InitSubSystem(sdl2.SDL_INIT_GAMECONTROLLER)

    # Filtrado bilineal: sin esto la rotación de las agujas sale a escalones y
    # se pierde justo el antialiasing que fuimos a buscar.
    sdl2.SDL_SetHint(sdl2.SDL_HINT_RENDER_SCALE_QUALITY, b"1")

    modo = sdl2.SDL_DisplayMode()
    sdl2.SDL_GetCurrentDisplayMode(0, ctypes.byref(modo))
    if deriva is None:
        deriva = int(round(min(modo.w, modo.h) * DERIVA_POR_MIL / 1000.0))
    deriva = max(0, int(deriva))

    if ventana:
        # La ventana crece lo que se vaya a mover, así que el dial pedido sale
        # del tamaño pedido: `--lado 800` siguen siendo 800 px de dial.
        lado = lado or 800
        ancho = alto = lado + 2 * deriva
        flags = 0
    else:
        ancho, alto = modo.w, modo.h
        # Y aquí al revés, porque la pantalla no da de sí: el dial se encoge lo
        # que haga falta. En la Deck, 800 - 16 = 784 px.
        lado = lado or (min(ancho, alto) - 2 * deriva)
        flags = sdl2.SDL_WINDOW_FULLSCREEN_DESKTOP
    # Con un `--lado` a mano puede no quedar sitio para todo el vaivén; se
    # recorta al hueco que haya en vez de sacar el dial de la pantalla.
    deriva = max(0, min(deriva, (ancho - lado) // 2, (alto - lado) // 2))

    win = sdl2.SDL_CreateWindow(b"reloj", sdl2.SDL_WINDOWPOS_CENTERED,
                                sdl2.SDL_WINDOWPOS_CENTERED, ancho, alto, flags)
    ren = sdl2.SDL_CreateRenderer(
        win, -1, sdl2.SDL_RENDERER_ACCELERATED | sdl2.SDL_RENDERER_PRESENTVSYNC)
    sdl2.SDL_ShowCursor(sdl2.SDL_DISABLE)

    ox0, oy0 = (ancho - lado) // 2, (alto - lado) // 2
    ox, oy = ox0, oy0
    dst_dial = sdl2.SDL_Rect(ox, oy, lado, lado)
    ev = sdl2.SDL_Event()
    espera = 1.0 / fps

    # Reloj virtual: parte de la hora real y avanza `velocidad` veces más
    # rápido. A x1 es la hora de verdad.
    t_virtual, t_real = ahora(), time.time()

    mandos = _Mandos()
    pie = "A / cruceta cambia    B sale    X guarda" if mandos.hay() else None

    m = _Montaje(ren, cargar(nombres[indice]), lado)
    rot, rot_wh = _rotulo(ren, nombres[indice], lado, pie)
    rot_hasta = time.time() + (4.0 if pie else 2.5)

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
        rot, rot_wh = _rotulo(ren, nombres[indice], lado, pie)
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
                if ev.type == sdl2.SDL_KEYDOWN:
                    k = ev.key.keysym.sym
                    if k in (sdl2.SDLK_ESCAPE, sdl2.SDLK_q):
                        return
                    if k in (sdl2.SDLK_RIGHT, sdl2.SDLK_DOWN, sdl2.SDLK_SPACE):
                        cambiar(+1)
                    elif k in (sdl2.SDLK_LEFT, sdl2.SDLK_UP):
                        cambiar(-1)
                    elif k == sdl2.SDLK_g:
                        foto()
                    continue
                orden = mandos.suceso(ev)
                if orden == "salir":
                    return
                if orden == "+1":
                    cambiar(+1)
                elif orden == "-1":
                    cambiar(-1)
                elif orden == "foto":
                    foto()

            if hora is not None:
                t = hora
            else:
                r = time.time()
                t_virtual = (t_virtual + (r - t_real) * velocidad) % 86400.0
                t_real = r
                t = t_virtual

            # La deriva va con el reloj de la pared, no con el virtual: a x600
            # el vaivén se vería, y lo que se quiere es justo lo contrario.
            dx, dy = _deriva(time.time(), deriva)
            ox, oy = ox0 + dx, oy0 + dy
            dst_dial.x, dst_dial.y = ox, oy

            sdl2.SDL_SetRenderDrawColor(ren, 0, 0, 0, 255)
            sdl2.SDL_RenderClear(ren)
            if m.fondo is not None:
                sdl2.SDL_RenderCopy(ren, m.fondo, None, ctypes.byref(dst_dial))

            for tr in m.esf.trazos(t):
                _pintar_trazo(ren, tr, ox, oy)

            for ma in m.esf.mallas(t):
                _pintar_malla(ren, m.texturas.get(ma.textura), ma, ox, oy)

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
        mandos.soltar()
        m.soltar()
        sdl2.SDL_DestroyTexture(rot)
        sdl2.SDL_DestroyRenderer(ren)
        sdl2.SDL_DestroyWindow(win)
        sdl2.SDL_Quit()
