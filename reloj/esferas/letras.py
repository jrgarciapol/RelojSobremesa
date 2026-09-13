"""Letras — la hora escrita en castellano, como la diría una persona.

    1:15  ->  UNA / Y / CUARTO
    2:45  ->  TRES / MENOS / CUARTO
    9:35  ->  DIEZ / MENOS / VEINTI / CINCO
   12:00  ->  DOCE / EN / PUNTO

Tres reglas de castellano, que son la parte delicada:

1. **Redondeo a 5 minutos.** A las 4:57 dice CINCO MENOS CINCO, que es como
   hablamos. El precio: la esfera puede ir hasta 2,5 minutos desfasada.
2. **Sin artículo.** UNA Y CUARTO, no LA UNA Y CUARTO. Ahorra una línea y evita
   decidir entre «la una» y «las dos».
3. **El «menos» salta de hora** a partir de y treinta y cinco: a las 9:35 se lee
   DIEZ MENOS VEINTICINCO. Es correcto, pero despista los primeros días.

VEINTICINCO es casi el doble de larga que cualquier otra palabra, así que se
parte en VEINTI / CINCO y esos ratos del día usan cuatro líneas.
"""

from ..esfera import Esfera
from ..lienzo import Lienzo, tipo

FUENTE = "Barriecito-Regular.ttf"

# ---- Paleta hueso y ámbar ----
# El enlace iba apagado y más pequeño, tratándolo como gramática de relleno.
# Error: «Y» frente a «MENOS» son MEDIA HORA de diferencia, así que es la
# palabra más informativa de las tres. Va al mismo cuerpo que las demás y en
# un ámbar quemado: se separa por el TONO, no por estar apagado.
COLOR_HOUR = 0xF3E7D3   # hueso
COLOR_LINK = 0xFF8C1B   # ámbar quemado, a tope de brillo
COLOR_MIN  = 0xFFB020   # ámbar vivo

# Reparto vertical y cuerpo, en fracción de la pantalla (original sobre 454).
Y3 = (0.240, 0.500, 0.760)
Y4 = (0.175, 0.385, 0.605, 0.825)
C3, C4 = 116 / 454.0, 100 / 454.0

HORAS = ("DOCE", "UNA", "DOS", "TRES", "CUATRO", "CINCO",
         "SEIS", "SIETE", "OCHO", "NUEVE", "DIEZ", "ONCE")


def frase(hora, minuto):
    """(hora, enlace, minutos) ya redondeado y con el salto de hora hecho."""
    m = ((minuto + 2) // 5) * 5
    h = hora + (1 if m >= 35 else 0)

    if m in (0, 60):
        enlace, mins = "EN", "PUNTO"
    else:
        enlace = "Y" if m <= 30 else "MENOS"
        n = m if m <= 30 else 60 - m
        mins = {30: "MEDIA", 15: "CUARTO", 5: "CINCO",
                10: "DIEZ", 20: "VEINTE", 25: "VEINTICINCO"}[n]

    return HORAS[h % 12], enlace, mins


class Letras(Esfera):
    NOMBRE = "letras"

    def __init__(self, lado):
        Esfera.__init__(self, lado)
        self.f3 = tipo(FUENTE, lado * C3)
        self.f4 = tipo(FUENTE, lado * C4)

    def capa(self, t):
        minuto = int(t // 60)
        return minuto, self._pintar(int(t // 3600) % 24, minuto % 60)

    def _pintar(self, hora, minuto):
        h, enlace, mins = frase(hora, minuto)
        # `sup=1`: los glifos ya salen antialiasados de FreeType.
        lz = Lienzo(self.lado, sup=1)
        cx = self.lado / 2.0

        if mins == "VEINTICINCO":
            lineas = zip(Y4, (h, enlace, "VEINTI", "CINCO"),
                         (COLOR_HOUR, COLOR_LINK, COLOR_MIN, COLOR_MIN))
            f = self.f4
        else:
            lineas = zip(Y3, (h, enlace, mins),
                         (COLOR_HOUR, COLOR_LINK, COLOR_MIN))
            f = self.f3

        for y, palabra, color in lineas:
            lz.texto(cx, self.lado * y, palabra, f, color)
        return lz.array()


ESFERA = Letras
