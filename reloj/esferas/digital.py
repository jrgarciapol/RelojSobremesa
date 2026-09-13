"""Digital — día de la semana arriba, hora enorme, fecha abajo.

En el Garmin esto eran **ocho proyectos separados**, uno por tipografía, cada
uno con su manifiesto, su id de app y sus cuatro atlas de mapa de bits
generados a mano. Aquí es **un módulo y una lista**: Connect IQ no sabe escalar
una fuente en marcha, así que cada cuerpo tenía que ser un atlas propio;
FreeType rasteriza el TTF al tamaño que le pidas.

Por eso también las medidas van en fracción de la pantalla, y no en píxeles
sobre 454: la misma esfera sirve para cualquier tamaño de monitor.
"""

import time

from ..esfera import Esfera
from ..lienzo import Lienzo, tipo

# Las ocho del banco de pruebas, con el nombre que llevaban allí y **su propio
# cuerpo**. Los tres números son hora / número del día / mes, medidos sobre los
# 454 px del Epix.
#
# No son decorativos ni se pueden unificar: a igualdad de cuerpo nominal, cada
# tipografía ocupa un ancho distinto. Poniéndoles 196 a todas, Rampart y
# Bangers se salían del marco por los dos lados. Estos valores vienen ajustados
# a ojo uno por uno desde el reloj, así que se respetan tal cual.
FUENTES = {
    #                                          hora  día  mes
    "bangers":    ("Bangers-Regular.ttf",       170,  94,  85),
    "barriecito": ("Barriecito-Regular.ttf",    196, 108,  92),
    "caesar":     ("CaesarDressing-Regular.ttf", 172,  95,  86),
    "honk":       ("Honk-Regular.ttf",          174,  96,  87),
    "londrina":   ("LondrinaShadow-Regular.ttf", 192, 106,  92),
    "rampart":    ("RampartOne-Regular.ttf",    152,  84,  76),
    "smokum":     ("Smokum-Regular.ttf",        208, 110,  92),
    "sueellen":   ("SueEllenFrancisco-Regular.ttf", 208, 110, 92),
}

DIAS = ("DOM", "LUN", "MAR", "MIE", "JUE", "VIE", "SAB")
MESES = ("ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
         "JUL", "AGO", "SEP", "OCT", "NOV", "DIC")

# Alturas, en fracción de la pantalla. Los cuerpos van en `FUENTES`, y también
# se dividen entre 454, que es el ancho del Epix para el que se ajustaron.
Y_WDAY, Y_TIME, Y_DATE = 0.200, 0.500, 0.815
EPIX = 454.0
HUECO = 14 / EPIX        # entre el número del día y el mes


class Digital(Esfera):
    """Base. Cada tipografía es una subclase de una línea, al final."""

    FUENTE = "Barriecito-Regular.ttf"
    CUERPOS = (196, 108, 92)     # hora, número del día, mes

    # Los colores van de clase, no de módulo, porque `orbita` y `pulso`
    # heredan esta misma maquetación y solo cambian la paleta.
    COLOR_TIME  = 0xFFFFFF   # blanco puro
    COLOR_GREEN = 0x00FF00   # día de la semana y número del día del mes
    COLOR_MES   = 0x1E9BFF   # acento azul
    ALFA        = 255        # `eliptica` lo baja para que la curva se vea detrás

    def __init__(self, lado):
        Esfera.__init__(self, lado)
        c_time, c_num, c_mon = self.CUERPOS
        self.f_time = tipo(self.FUENTE, lado * c_time / EPIX)
        self.f_num = tipo(self.FUENTE, lado * c_num / EPIX)
        self.f_mon = tipo(self.FUENTE, lado * c_mon / EPIX)

    def capa(self, t):
        """Todo el contenido cambia como mucho una vez por minuto, así que la
        esfera entera es una sola capa cacheada por el minuto en curso."""
        lt = time.localtime()
        clave = (int(t // 60), lt.tm_yday)
        return clave, self._pintar(int(t // 3600) % 24, int(t // 60) % 60, lt)

    def _pintar(self, hora, minuto, lt):
        lado = self.lado
        # `sup=1`: FreeType ya antialiasa los glifos, y esta capa se redibuja
        # en marcha. Supermuestrear texto sería pagar 16 veces por nada.
        lz = Lienzo(lado, sup=1)
        cx = lado / 2.0

        lz.texto(cx, lado * Y_WDAY, DIAS[(lt.tm_wday + 1) % 7], self.f_mon,
                 self.COLOR_GREEN, self.ALFA)
        self._hora(lz, cx, lado * Y_TIME, hora, minuto)
        self._fecha(lz, cx, lado * Y_DATE, lt.tm_mday, lt.tm_mon)
        return lz.array()

    def _hora(self, lz, cx, cy, hora, minuto):
        """Tres bloques —HH · : · MM— con los dos puntos ceñidos a media caja.

        Medir HH y MM por separado es lo que permite que 9:24 y 10:24 queden
        las dos centradas sin cero delante.
        """
        hh, mm = "%d" % hora, "%02d" % minuto
        w_hh = lz.ancho_de(hh, self.f_time)
        hueco = lz.ancho_de(":", self.f_time) / 2.0
        x0 = cx - (w_hh + hueco + lz.ancho_de(mm, self.f_time)) / 2.0

        lz.texto(x0, cy, hh, self.f_time, self.COLOR_TIME, self.ALFA, "lm")
        lz.texto(x0 + w_hh + hueco / 2.0, cy, ":", self.f_time, self.COLOR_TIME, self.ALFA)
        lz.texto(x0 + w_hh + hueco, cy, mm, self.f_time, self.COLOR_TIME, self.ALFA, "lm")

    def _fecha(self, lz, cx, cy, dia, mes):
        num, mon = "%d" % dia, MESES[mes - 1]
        w_num = lz.ancho_de(num, self.f_num)
        hueco = self.lado * HUECO
        x0 = cx - (w_num + hueco + lz.ancho_de(mon, self.f_mon)) / 2.0

        lz.texto(x0, cy, num, self.f_num, self.COLOR_GREEN, self.ALFA, "lm")
        lz.texto(x0 + w_num + hueco, cy, mon, self.f_mon, self.COLOR_MES, self.ALFA, "lm")


# Una subclase por tipografía, generadas en el sitio: son idénticas salvo el
# TTF, y escribir ocho clases a mano solo daría ocho sitios donde equivocarse.
VARIANTES = {}
for _nombre, (_ttf, *_cuerpos) in FUENTES.items():
    VARIANTES[_nombre] = type(
        "Digital" + _nombre.capitalize(), (Digital,),
        {"NOMBRE": _nombre, "FUENTE": _ttf, "CUERPOS": tuple(_cuerpos),
         "__doc__": "Digital con la tipografía %s." % _ttf})

ESFERA = VARIANTES["barriecito"]
