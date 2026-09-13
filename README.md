# Reloj de sobremesa / pared

**Relojes creativos para una pantalla grande** (monitor o televisor) movidos
por una Raspberry Pi.

Sale de [`garmin_epic_face_test`](https://github.com/jrgarciapol/garmin_epic_face_test),
donde viven las 15 esferas para el Garmin Epix Pro. Ese repositorio sigue
siendo **la fuente**: las esferas de aquí son ports, y cuando hay una duda de
geometría o de color se mira el `.mc` original.

Lo que cambia al pasar del reloj a la pantalla:

| | Garmin Epix (AMOLED) | Pantalla grande (IPS) |
|---|---|---|
| Refresco | **1 fotograma por segundo** | 60 fps, animación de verdad |
| Píxeles encendidos | techo del 10% en reposo | sin límite |
| Fondo claro | imposible en Always-On | **gratis**: la retro está encendida igual |
| Quemado | hay que desplazar el dibujo cada minuto | no aplica en LCD |
| Rotar un mapa de bits | **no existe** en Connect IQ | una llamada, y por hardware |

O sea que **la baraja de restricciones se invierte**. La estética de papel y
tinta, que en el reloj era inviable, aquí es justo la que toca.

## Cómo se usa

**En Windows: doble clic en `reloj.bat`.** Instala lo que falte la primera vez
y saca un menú. No hay que escribir nada.

A mano, o en Linux y en la Pi:

```sh
pip install -r requirements.txt
```

```sh
python -m reloj --lista                  # qué esferas hay
python -m reloj --esfera letras          # pantalla completa
python -m reloj --esfera disco --ventana # en una ventana de 800

python -m reloj --lamina x.png --hora 10:09:38
python -m reloj --lamina x.png --hora 10:09 1:50 6:30 8:20
python -m reloj --lamina todas.png --esfera TODAS
```

(En Linux y en la Pi, `python3` en vez de `python`.)

Con la ventana abierta no hace falta volver a la consola para nada:

| tecla | |
|---|---|
| **flechas** o **espacio** | pasar de una esfera a la siguiente |
| **g** | guardar un PNG de lo que se está viendo |
| **Esc** o **q** | salir |

Se arranca con **las quince cargadas** y empezando por la que se pida, así que
compararlas es cuestión de ir dando a la flecha. Al cambiar aparece el nombre
arriba a la izquierda y se apaga solo.

Con `--lamina` no abre pantalla ni toca SDL: compone con Pillow y guarda un
PNG. Sirve para trabajar el diseño sin tener la Pi delante — y sin la Pi
siquiera.

## Lo que costaba, medido

Lo de «rasterizar al arrancar y mover en la GPU» estaba bien pensado y **sin
medir**. Al medirlo a 1080 px, que es el dial de una Pi a 1080p, salieron dos
cosas que no eran lentitud sino imposibilidad:

| | antes | ahora |
|---|---|---|
| `disco`, arranque | 14,5 s | **2,1 s** |
| `disco`, memoria pico | **914 MB** | **34 MB** |
| `rosa`, memoria pico | 896 MB | **29 MB** |
| `rosa`, redibujado por minuto | 722 ms | **43 ms** |
| cualquiera, por fotograma | — | **≤ 0,05 ms** |

**La Pi Zero 2 W tiene 512 MB.** Con 900 MB de pico no es que fuera lento: no
arrancaba. (Medido en un Xeon a 2,1 GHz; en la Pi hay que multiplicar los
tiempos por unos diez. Los megas son los mismos.)

Tres arreglos, y ninguno cambia un solo píxel de lo que se ve:

**Reducir por bandas.** Pasar el lienzo supermuestreado entero a `float32`
parece lo natural: a 1080 px con `sup=4` son 4320×4320, o sea 300 MB por copia
y 900 de pico entre las intermedias. Por bandas, el pico ya no depende del
tamaño del dial.

**Las agujas eran cuadrados casi vacíos.** Poner el pivote en el centro de un
lienzo del tamaño del dial hace que girarlas sea trivial, y por eso lo hice
así. Pero una aguja ocupa el **2%** de ese cuadrado: se rasterizaban 18
millones de píxeles para dibujar unos cientos de miles, y las tres agujas eran
3,9 s de los 5,1 del arranque. Ahora el sprite es una tira estrecha con su
pivote donde toca — `SDL_RenderCopyEx` admite un centro de giro cualquiera, así
que no se pierde nada.

**El arco de Rosa se calcula, no se supermuestrea.** PIL no suaviza `arc`, así
que la única forma de que saliera limpio era supermuestrear la capa entera —
una capa que se redibuja **cada minuto**. Eran siete segundos de congelación
por minuto en la Pi. Calculando la cobertura de cada píxel sale mejor (la rampa
es exacta, no promediada) y cuesta diecisiete veces menos.

El banco de medida es `python3 utiles/medir.py 1080`.

## Verlas sin la Raspberry: `reloj.html`

Una reimplementación en Canvas de las quince, en una página suelta. Doble clic
y se abren **en marcha**, con rejilla de 1, 2×2, 3×3 o las quince a la vez,
pantalla completa, un cursor para recorrer el día y otro para las pulsaciones.

Sirve para tres cosas que la versión de Python no da:

* verlas moverse **sin tener la Pi ni el monitor delante**;
* **compararlas en movimiento**, varias a la vez en la misma pantalla;
* abrirlas en el móvil o en el televisor, que es a donde va esto.

Y sale gratis en tipografías: las ocho son de Google Fonts, así que la página
las carga nativas. De regalo, **Honk sale en color**, que es como es de verdad
— Pillow solo pinta su capa base, así que en la versión de Python (y en el
Garmin) salía en contorno.

> **La que manda es la de Python.** Son dos implementaciones de lo mismo y
> pueden separarse. Las constantes llevan los mismos nombres y los mismos
> divisores entre 454 para que se puedan comparar de un vistazo, pero si algo
> no cuadra, la buena es `reloj/esferas/`.

## Cómo está montado

```
reloj/lienzo     rasteriza con Pillow y reduce -> antialiasing de verdad
reloj/esfera     el molde que cumplen todas las esferas
reloj/esferas/   los diseños
reloj/pantalla   sube los arrays a la tarjeta y los mueve por hardware (SDL2)
reloj/lamina     los compone con Pillow, sin pantalla, para el PNG
```

Una esfera **no sabe nada de SDL**: solo dice qué dibujar. El reparto del
trabajo es lo que decide cuánto cuesta **cada fotograma**, que es lo que una Pi
Zero 2 W puede o no puede pagar:

```python
fondo()      se rasteriza UNA VEZ y no cambia nunca       (marcas, rosa)
piezas()     se rasterizan UNA VEZ y luego solo se mueven (agujas, orbes)
capa(t)      se redibuja SOLO cuando cambia su clave      (textos, arcos)
detras(t)    no dibuja nada: coloca piezas ya hechas      (cada fotograma)
cuadro(t)    igual, pero por encima de la capa            (cada fotograma)
```

Colocar una pieza es un `RenderCopyEx`: rotar, escalar y teñir los hace la GPU.
Una aguja es la misma forma en los 360 grados y un orbe es el mismo disco a
cualquier tamaño y color, así que no hay ninguna razón para volver a
rasterizarlos. Un texto que cambia una vez por minuto se redibuja una vez por
minuto, no treinta veces por segundo.

`detras()` existe por una razón concreta heredada del reloj: en `pulso` los
orbes viajan **por detrás** de la hora y el choque estalla **por delante**. Sin
esa separación, el estallido de arriba y el de abajo salían distintos, porque
tenían textos diferentes detrás.

## La pila: SDL2, la misma del simulador de conducción

`pysdl2` + `numpy`, igual que `CarDrivingSimulator`. La razón de fondo es que
**SDL2 pinta sobre KMS/DRM sin escritorio**, así que en la Pi arranca contra la
pantalla pelada: ni X ni Wayland ni entorno de escritorio comiéndose los
512 MB.

### Por qué aquí no vale Godot

Merecía la pena mirarlo, porque el simulador espacial va en Godot y reutilizar
lo aprendido sería lo cómodo. Pero no encaja con **esta** placa:

- **Godot 4 exige Vulkan 1.0, OpenGL 3.3 u OpenGL ES 3.0.** Incluso el
  renderizador «Compatibility», que es el modo humilde, parte de GLES 3.0. La
  documentación pone como mínimo en Raspberry la **Pi 4**.
- La **Pi Zero 2 W lleva una VideoCore IV**, que llega a **OpenGL ES 1.1 y
  2.0** y no más.

No es que vaya lento: es que no arranca. Con Godot hay dos salidas, y ninguna
es «apañarlo»:

1. **Cambiar de placa.** Una Pi 4 o Pi 5 mueve Godot 4 sin problema.
2. **Cambiar de reloj.** Para las esferas geométricas —Disco, Letras, Pulso—
   Godot no aporta nada que SDL2 no dé ya.

Donde Godot **sí** sería la herramienta correcta es en el reloj del personaje:
un rig con dos huesos apuntando a la hora y al minuto es literalmente para lo
que sirve un motor de juego, y resuelve de raíz el problema que nos atascó
haciéndolo a base de renders de Blender. Pero eso pide Pi 4 como mínimo.

## Las quince esferas

Están **todas** las del Garmin. Quince nombres, seis módulos:

| Módulo | Esferas | Qué gana en pantalla grande |
|---|---|---|
| `disco` | `disco` | antialiasing real y **segundero de barrido** |
| `rosa` | `rosa`, `rosavivid` | la rosa deja de ser un alambre (ver abajo) |
| `letras` | `letras` | nada que arreglar: ya estaba bien |
| `orbita` | `orbita` | el orbe **rueda** en vez de saltar de segundo en segundo |
| `pulso` | `pulso`, `pulsoxl` | la fase sale de la hora, no se acumula (ver abajo) |
| `digital` | las ocho tipografías | ocho proyectos Connect IQ pasan a ser un módulo |

Toda la geometría va en **fracción de la pantalla**, así que la misma esfera
vale para un monitor de 24" o una pantallita de 5". Los números originales
estaban en píxeles sobre los 454 del Epix, y se conservan divididos por 454
para que se pueda comprobar de dónde salen.

### Tres cosas que aquí se pudieron arreglar

**El segundero de Disco.** Una esfera Connect IQ se redibuja una vez por
segundo, así que un barrido continuo era imposible. Aquí el ángulo sale del
reloj con decimales.

**La estrella de Rosa era un alambre.** En el reloj los flancos de cada punta
se colocaban a 4,6 grados del eje, medidos desde el centro. Suena razonable y
no lo es: a la altura del hombro eso son `r_in · sen(4,6°)`, el **8%** del
radio interior — una punta de dos píxeles de ancho. Ahora el hombro se separa
una fracción del radio interior en vez de un ángulo, y sale una cometa.

**Los orbes de Pulso ya no se disparan al arrancar.** En el reloj la fase se
acumulaba fotograma a fotograma, así que al despertar la pantalla los orbes
corrían unos segundos hasta estabilizarse. Aquí la fase se calcula
directamente de la hora: no hay nada que acumular ni que desincronizar.

### Dos cosas que aquí no hay

**Pulsómetro.** Un reloj de sobremesa no lleva sensor, así que `pulso` y
`pulsoxl` usan un valor fijo, ajustable con `--ppm`. Marca la velocidad, el
tamaño de los orbes y el del estallido, igual que hacía el pulso de verdad.

**Brújula.** `rosa` mira siempre al norte. Tampoco cambia gran cosa: en el
reloj una esfera Garmin no recibe brújula continua, así que se quedaba fija al
norte el 95% del tiempo.

### Las tipografías

Cada una lleva **su propio cuerpo**, ajustado a ojo en el Garmin: Rampart 152,
Barriecito 196, Smokum 208. No son intercambiables — poniéndoles el mismo
cuerpo a todas, Bangers y Rampart se salen del marco por los dos lados.

Los TTF están en `tipos/`, todos con licencia SIL Open Font (`tipos/OFL.txt`).
En Connect IQ había que generar un atlas de mapa de bits por cuerpo, porque no
sabe escalar una fuente en marcha; aquí FreeType rasteriza el TTF al tamaño que
le pidas, y por eso ocho proyectos caben en un módulo.

## `modelos/`

La línea del personaje 3D (`Mira2.fbx`) queda aparcada aquí. Necesita dos cosas
que hoy no hay: una sesión con acceso al disco local, para las cuatro texturas
que el FBX pide (`BC.psd`, `sborka_03 - Default_Normal.png`, `MG_bc.tga`,
`MG_nm.tga`), y —si acaba siendo animada— una Pi 4 con Godot.

El modelo es de Pigcraft y va con licencia CC-BY: si llega a usarse, hay que
acreditarlo.
