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

python -m reloj --velocidad 600          # una hora de reloj cada 6 segundos
```

`--velocidad` no es un juguete: la familia de `eliptica` da una vuelta por
**hora**, la cámara de las esferas 3D tarda entre cuatro y cinco minutos en dar
la vuelta y `paseo` cambia de curva cada minuto, así que a velocidad real no hay
forma de juzgar si el movimiento funciona. En la página hay los mismos
multiplicadores en botones, y en `reloj.bat` es la opción 5.

(En Linux y en la Pi, `python3` en vez de `python`.)

**En una Steam Deck: `./deck.sh`**, en modo escritorio desde Konsole. Mismo
menú que el `.bat`.

SteamOS tiene la raíz de **solo lectura y en A/B**: cada actualización escribe
una imagen nueva en la partición dormida y arranca en ella, así que **todo lo
que no esté en `/home` desaparece**. Por eso `deck.sh` no instala nada en el
sistema — ni `pacman`, ni `steamos-readonly disable` — sino que usa un entorno
virtual dentro de la carpeta del proyecto, que vive en `/home` y sobrevive.
SDL2 tampoco hace falta instalarlo: `pysdl2-dll` trae sus propios binarios
dentro del paquete de Python.

Y si ya tienes un entorno con esta pila —el del simulador de conducción usa
exactamente la misma— lo busca y lo reutiliza en vez de montar otro. Para
forzar uno concreto, `RELOJ_PYTHON=/ruta/al/python ./deck.sh`.

La pantalla de la Deck es de 1280×800, así que a pantalla completa el dial sale
de **800 px**: casi el mismo tamaño con el que está medido todo el proyecto.
Y es **OLED**, que es el panel para el que se dibujaron estas esferas.

Con la ventana abierta no hace falta volver a la consola para nada:

| tecla | |
|---|---|
| **flechas** o **espacio** | pasar de una esfera a la siguiente |
| **g** | guardar un PNG de lo que se está viendo |
| **Esc** o **q** | salir |

Se arranca con **todas cargadas** y empezando por la que se pida, así que
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

Una reimplementación en Canvas de las veintinueve, en una página suelta. Doble
clic y se abren **en marcha**, con rejilla de 1, 2×2, 3×3 o todas a la vez,
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
trazos(t)    polilíneas calculadas al vuelo               (curvas)
texturas()   se rasterizan UNA VEZ y se pegan a triángulos (bandas)
mallas(t)    triángulos con imagen encima                  (superficies)
detras(t)    no dibuja nada: coloca piezas ya hechas      (cada fotograma)
cuadro(t)    igual, pero por encima de la capa            (cada fotograma)
```

`trazos()` es lo único que **no** se rasteriza antes: una curva que cambia de
forma no es la misma imagen girada, así que no hay sprite que valga. A cambio,
lo que viaja a la tarjeta son unos miles de vértices y no un millón de píxeles;
la GPU los convierte en triángulos con el inglete calculado en numpy.

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

## Las esferas

Están **todas** las del Garmin, más ocho nuevas. Veintitrés nombres, trece módulos:

| Módulo | Esferas | Qué gana en pantalla grande |
|---|---|---|
| `disco` | `disco` | antialiasing real y **segundero de barrido** |
| `rosa` | `rosa`, `rosavivid` | la rosa deja de ser un alambre (ver abajo) |
| `letras` | `letras` | nada que arreglar: ya estaba bien |
| `orbita` | `orbita` | el orbe **rueda** en vez de saltar de segundo en segundo |
| `pulso` | `pulso`, `pulsoxl` | la fase sale de la hora, no se acumula (ver abajo) |
| `digital` | las ocho tipografías | ocho proyectos Connect IQ pasan a ser un módulo |
| `eliptica` | `eliptica`, `finita` | **nuevas**: no vienen del reloj (ver abajo) |
| `toro` | `toro` | **nueva**: la superficie, en 3D |
| `hopf` | `hopf` | **nueva**: la fibración de Hopf |
| `superficie` | `superficie` | **nueva**: los cortes, con cuerpo |
| `grabada` | `grabada` | **nueva**: los números proyectados de verdad |
| `pintada` | `pintada` | **nueva**: una imagen enrollada encima |
| `paseo` | `paseo` | **nueva**: las curvas célebres de MacTutor |

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

## Las curvas célebres

**`paseo`** recorre el índice de MacTutor,
<https://mathshistory.st-andrews.ac.uk/Curves/>: sesenta y una curvas con
nombre propio. **Cambia de curva cada minuto** —el índice es el minuto del día
módulo sesenta y uno— así que en poco más de una hora se han visto todas y
ninguna se ha repetido. Detrás de la hora, un cometa la recorre dejando estela.

**La dimensión que falta se la pone la estela, no la curva.** Son curvas planas
y deformarlas para darles volumen sería quitarles lo que las hace reconocibles:
una cardioide torcida ya no es una cardioide. Así que la curva se queda en su
plano y lo que sale del plano es el rastro, que se levanta conforme envejece.

**El cometa corre donde la curva se cierra.** No va a velocidad constante: la
velocidad es proporcional a la curvatura, así que se lanza en los recodos y se
arrastra en las rectas. Es la intuición kepleriana —en el perihelio, que es
donde la órbita más se cierra, el planeta va disparado— aunque no sea
literalmente la ley de áreas: en el afelio también hay curvatura y ahí el
planeta va lentísimo. Y cumple una función: la gracia de estas curvas está en
los recodos, y a paso fijo el cometa se los pasaba en dos fotogramas y se
tiraba el resto del rato recorriendo la asíntota. Una circunferencia, con
curvatura constante, sigue yendo a paso fijo, que es como tiene que ser.

La curvatura es la de **Menger** —el inverso del radio de la circunferencia que
pasa por tres puntos seguidos—, que sale de un área y tres distancias sin
derivar nada. Se normaliza por **percentil**: una cúspide tiene curvatura
infinita y dividiendo por el máximo todo lo demás quedaría a cero y el cometa
no se movería.

**La cabeza va por el reloj de curvatura; la cola, por la cinta métrica.** Una
cola mide lo mismo se vaya rápido o despacio, así que se cuenta en longitud de
arco. Medida en tiempo se encogía justo en los recodos, que es donde el cometa
frena y donde más ganas hay de verla.

**La estela sale tangente al plano.** Subía con `edad ** 0.85`, cuya pendiente
en la cabeza es infinita: la cola salía en perpendicular, como una antena. Con
el suavizado de Hermite —pendiente cero en los dos extremos— despega rozando la
curva y luego se levanta.

**`trazada`** — la curva se dibuja sola, y lo dibujado se apaga poco a poco.

`paseo` pone un cometa a recorrer una curva que ya está ahí. Aquí no hay curva
de antemano y no hay cometa: la punta va trazando y lo que queda detrás se
desvanece, como el fósforo de un osciloscopio.

Y mientras traza, **los parámetros se mueven**. Eso no es un adorno, es la
esfera entera: cuando la punta da la vuelta y regresa, la curva ya no es la
misma que dejó, así que el trazo nuevo no cae encima del viejo. Lo que se ve no
es una curva con estela — es **la historia de una familia de curvas**, con el
presente brillante y el pasado apagándose. La estela no se cierra nunca.

De ahí salen las dos decisiones que lo sostienen. **El encuadre se calcula una
vez por curva**, abarcando las esquinas del cajón de parámetros por los que va a
pasar: encuadrando cada instante por su cuenta, la curva se quedaría quieta y
sería el marco el que se movería, justo lo contrario de lo que se quiere ver. Y
**cada paso dibuja su trocito con los parámetros de su instante**, que es lo que
deja el rastro de la deriva.

Debajo de la hora va el **nombre y la fórmula**, con los valores que llevan los
parámetros en ese momento.

### Las curvas, como texto

Parametrizarlas obligó a rehacer el catálogo, y la forma de hacerlo resolvió de
paso un problema que llevaba tres capítulos apareciendo.

Cada curva se guarda como **texto**: `x` e `y` (o `r`) escritos como se
escribirían en un papel. La fórmula que se enseña en la esfera y en el
laboratorio **es la definición**, no una copia, así que no pueden discrepar. Y
el navegador evalúa las mismas sesenta y una curvas con los parámetros que sea
sin que nadie las reescriba en JavaScript: el mismo texto lo evalúan numpy y
`Math`, cada uno con su tabla de funciones.

Comprobado: sesenta y una curvas, cuarenta puntos cada una, parámetros en el
centro del rango — **la diferencia máxima entre numpy y Chromium es 1e-12**.
Son la misma implementación.

Eso permitió tirar los 315 KB de puntos muestreados que `exporta_curvas.py`
metía en el HTML para `paseo`: ahora viajan **12 KB de fórmulas**.

**Los parámetros son de forma, no de escala.** Como cada curva se encuadra
sola, un parámetro que solo multiplica se vuelve invisible: el radio de una
circunferencia no se ve, la razón de los ejes de una elipse sí. Por eso la
circunferencia es la única sin parámetros — no tiene ninguna libertad de forma,
y fingir una sería mentir. Y **los valores por defecto son los de siempre**, de
modo que `paseo` sigue dibujando exactamente lo mismo: comprobado lámina a
lámina, diferencia cero.

### El laboratorio: `curvas.html`

Los rangos y las velocidades no se adivinan, se miran. `curvas.html` es una
página aparte con la vista previa de `trazada` a tamaño grande y, al lado, para
la curva que sea: su fórmula, y por cada parámetro **desde**, **hasta** y
**velocidad**.

La velocidad no va en segundos sino en un **multiplicador del reloj**:

    periodo = 60 s / multiplicador

y 60 s es justo lo que cada curva está en pantalla. Así que **1** es una ida y
vuelta completa mientras se ve esa curva, **0,5** media, **2** dos y **0** la
deja quieta. No hay que pensar en segundos en ningún momento.

El recorrido es un coseno y no un diente de sierra —un parámetro que llega al
extremo y da media vuelta de golpe se ve como un tirón— y cada parámetro
arranca con un desfase distinto: si no, los dos de una Lissajous suben y bajan a
la vez y la curva solo crece y mengua.

Abajo sale la configuración en JSON. Se copia y se pega, o se guarda como
`curvas.json` en la carpeta del proyecto: `trazada` lo lee al arrancar, y si no
está usa esos mismos valores de partida. (El botón de descarga solo funciona
abriendo el fichero desde el disco; el visor publicado bloquea las descargas, y
para eso está Copiar.)

Tres cosas que salieron de dibujarlas todas y mirarlas:

**Encuadrar por percentiles, no por el mínimo y el máximo.** Con el rango
completo mandan las ramas asintóticas: el cisoide, el estrofoide y el folium
salían como una raya vertical, porque su parte interesante mide uno y su
asíntota cuarenta. Recortando por el 3% y el 97% se encuadra el grueso y las
colas se van fuera, que es a donde iban.

**Cinco no entraron.** La concoide de Nicomedes, la kappa, la cruciforme, la
nariz de bala y el tridente de Newton no se leen se encuadren como se
encuadren. Un catálogo con cinco palos no es mejor que uno sin ellos.

**La cámara mira el plano casi de frente.** La primera versión usaba el cabeceo
de las esferas 3D, unos 26 grados, y a esa altura un plano se ve de canto: una
cardioide preciosa salía como una raya. A 66 grados se lee entera y aún queda
escorzo para que se note que hay un plano en el espacio.

Cuesta 0,41 ms por fotograma a 1080, unos 4 en la Pi: es la esfera 3D más
barata del banco —`pintada` cuesta 27 y `superficie` 34— porque la curva del
minuto, su curvatura y sus dos acumulados se calculan una vez y luego solo se
proyecta.

## Curvas elípticas

Dos esferas que no vienen del Garmin, inspiradas en el proyecto de Nadir
Hajouji y Steve Trettel, <https://elliptic-curves.art>.

La conexión con un reloj no es decorativa, es **estructural**: una curva
elíptica *es* un toro. Sobre los complejos, `E` es el cociente `C/L` de una
retícula, y un toro son exactamente dos ángulos — que es exactamente lo que es
un reloj. La ley de grupo de la curva no es más que sumar ángulos.

**`eliptica`** — el lugar real de `y² = x³ + ax + b`, con `(a, b)` recorriendo
un lazo cerrado, una vuelta por hora. El lazo está elegido para **cruzar el
discriminante** `4a³ + 27b² = 0`: ahí la curva se pellizca y el óvalo nace o
muere. Es el acontecimiento de la esfera, y pasa una vez por hora.

No se dibuja una curva sino **las dieciséis últimas**, la de ahora encendida y
las anteriores apagándose: una sola línea se pierde en una pantalla grande, y
la familia enseña de dónde viene la forma y hacia dónde va.

**`superficie`** — los cortes de `eliptica`, pero ya con su cuerpo.

`eliptica` pinta la familia de curvas reales como líneas planas. Pero esas
curvas son **cortes de algo**, y ese algo existe: como el lazo de parámetros se
cierra, la familia barre una superficie de verdad. En geometría algebraica eso
tiene nombre —una **superficie elíptica**, una familia de curvas elípticas
sobre una base— así que no hay que fingirla: se construye.

La base es un círculo, y ese círculo **es la esfera del reloj**. El azimut es
la hora, el corte en cada azimut es la curva de esa hora, y **los números van
pintados sobre la superficie**: colocados en su plano tangente, con su
perspectiva. Por eso los de atrás se ven del revés, que es lo que le pasa a
algo pintado en una pared curva.

Y se ve lo que en el dibujo plano solo se intuía: al cruzar el discriminante la
superficie **se pellizca** y suelta un asa. Eso es una fibra singular, y aquí
está a simple vista.

Dos cosas que hicieron falta. Las cifras son **polilíneas**, no una fuente
(`reloj/trazos_tipo.py`): un glifo rasterizado es un rectángulo de píxeles y
pegarlo sobre una superficie curva pediría mapear texturas, que es justo lo que
este reloj no hace. Y la rama de cada corte sale **siempre con el mismo número
de puntos**, que es lo que permite coser el punto `i` de un corte con el `i`
del siguiente: sin esas líneas longitudinales la esfera se lee como una valla
de listones, no como una superficie.

**`grabada`** — igual que `superficie`, pero con los números **proyectados**.

En `superficie` las cifras están en el plano tangente de un **cilindro** de
radio fijo que pasa cerca de la superficie. Se le parece mucho —tienen su
escorzo, las de atrás se ven del revés— pero **flotan**: no tocan la superficie
más que de casualidad y no se enteran de su forma.

Aquí se dibujan en las **coordenadas propias de la superficie** —la fase, que
es la hora, y el recorrido a lo largo del corte— y se empujan por la
parametrización. Así están encima **por construcción**: la siguen donde sube,
se estiran donde se ensancha y se retuercen donde se pellizca. Que un número se
deforme al pasar por la fibra singular no es un fallo del dibujo, es la
superficie.

Las dos coordenadas no están a la misma escala —la vuelta al anillo son unas
diez unidades de mundo y un corte unas tres— así que con el mismo factor en las
dos las cifras salen chafadas. Hay un factor por eje.

**`pintada`** — una **imagen** pegada sobre la superficie.

`grabada` proyecta bien, pero solo polilíneas: las cifras van a palotes porque
un glifo de verdad es un rectángulo de píxeles. Aquí se rasteriza **una banda
desenrollada** —la superficie abierta en plano, como la etiqueta de una lata—
con las horas en Barriecito, sus marcas de minuto y su raíl, y se vuelve a
enrollar mapeándola sobre triángulos.

Eso es lo que hace cualquier motor 3D con una textura, y **en la Pi sale
gratis**: `SDL_RenderGeometryRaw` aceptaba textura y coordenadas `uv` desde el
principio; lo que faltaba era dárselas en vez de pasarle `None` y ceros. Sobre
la superficie ya se puede pegar cualquier imagen, no solo tipografía.

La banda va en la **pared exterior de abajo**, no en el ala del borde. La
cámara mira desde arriba, así que del ala se ve la cara de dentro: la primera
versión salía impresa por detrás, del revés y en espejo.

La banda va a la **cintura del toroide**, no al borde de abajo: ahí la pared es
casi recta y la banda se lee plana, y subida a donde la superficie más se curva
la tipografía se dobla y se ve que está pegada a algo.

En el navegador cuesta más, porque **Canvas 2D no sabe dibujar un triángulo con
textura**: hay que recortar cada uno y aplicarle la afín a mano. Por eso su
malla es más basta —96 × 4 cuadros en vez de 192 × 6— y por eso ahí las tres
esferas con banda tienen **dos mallas y eligen por el tamaño del dial**: en una
celda de cien píxeles de la rejilla de veinticinco, cuatrocientos cuadros se
gastan en detalle que no cabe. Es la única diferencia real entre las dos
versiones.

**`hopf`** — un reloj de eslabones.

La fibración de Hopf manda `S³` a `S²`, y **cada punto de `S²` es un círculo
entero** de `S³`. Proyectados a nuestro espacio siguen siendo círculos, y dos
cualesquiera están **enlazados exactamente una vez**. Nunca sueltos, nunca dos
veces.

De ahí sale el reloj sin forzar nada: la hora es un punto de `S²` y su círculo;
el minuto, otro punto y otro círculo. Dos puntos distintos, **dos círculos
encadenados** que giran uno dentro del otro. Detrás, las fibras de tres
paralelos: cada paralelo da un toro de círculos anidados.

Dos cosas que salieron de mirarlo. Con cuatro paralelos y ocho fibras cada uno
era una maraña — lo que hace ver los toros no es la variedad de tamaños sino
tener **bastantes fibras en cada paralelo**, y con catorce el toro se insinúa
solo. Y ningún paralelo puede acercarse a `π`: la fibra sobre el polo sur pasa
por el punto desde el que se proyecta, así que se va al infinito y sale como
una recta cruzando la pantalla.

**`toro`** — la curva como lo que de verdad es.

Las otras dos dibujan el lugar **real**: una curva en un plano. Pero eso es una
sombra. Los puntos **complejos** forman `C/L`, y eso es una superficie — el
toro que se ve en sus imágenes. Y un toro tiene exactamente dos ángulos.

Así que aquí el reloj no está *encima* de un fondo bonito: **el reloj es la
superficie**. La posición alrededor del donut es la hora, la posición alrededor
del tubo es el minuto, y donde se cruzan los dos aros está el instante. La
cámara da una vuelta cada cuatro minutos y cabecea cada noventa segundos —
tiempos primos entre sí, para que el vaivén no se repita igual dos veces y no
parezca un GIF en bucle.

La retícula es **hexagonal**, `L = Z + tZ` con `t = exp(iπ/3)`. Los tres
vectores más cortos son `1`, `t` y `t-1`, así que hay **tres** familias de
rectas a 60 grados en vez de dos a 90. Con dos sale una malla de cuadros; con
las tres, el tejido triangular de sus `weierstrass-hex` — y la superficie se
lee como superficie y no como alambre. Cuesta lo mismo.

No hay z-buffer: la profundidad la dice la **niebla**, y basta. El ojo lee una
malla que se apaga al fondo como una superficie curva.

**`rosca`** — el mismo toro, con las horas impresas alrededor.

`toro` es la única esfera de geometría **sin números**: el instante está donde
se cruzan los dos aros, y hay que saberlo para leerlo. Aquí la superficie lleva
la banda impresa de `pintada`, así que el aro de la hora **señala un número**.

La banda va en el **hombro del tubo**, y la razón es medible. La curvatura de
Gauss de un toro es `cos(v) / (r·(R + r·cos v))`: máxima en el ecuador de
fuera, que sería el sitio — pero con el ojo a 35 grados el ecuador cae en el
borde de abajo del contorno y de la banda se veía un cuarto escaso. En el
hombro la curvatura sigue siendo el 80% de la máxima y se ve casi entera, así
que el ojo también sube.

Y aquí hizo falta algo que en `pintada` no: **quitar las caras que dan la
espalda**. Una pared abierta se ve por un lado y el orden da igual; un toro es
cerrado, y por detrás enseña su cara interior — la primera versión tenía un `8`
del revés flotando sobre el agujero. Se detecta sin normales: si el cuadro está
de espaldas, sus vértices salen girados al revés en pantalla. Los que quedan se
pintan **de lejos a cerca**, que con quinientos cuadros es un `argsort`.

**`enlazada`** — Hopf con las horas impresas **sobre** las fibras.

`hopf` no tiene superficie: son círculos en el aire, y una etiqueta necesita
algo donde pegarse. Pero la superficie está y no hay que inventarla — **las
fibras sobre un paralelo barren un toro de revolución**, con `R = sec(t/2)` y
`r = tan(t/2)`. No aproximadamente: comprobado a precisión de máquina para los
tres paralelos que dibuja `hopf`.

Lo bonito sale de regalo. Una circunferencia sobre un toro que no es ni
meridiano ni paralelo es una **circunferencia de Villarceau**, el corte por un
plano bitangente, y las fibras de Hopf sobre un paralelo son exactamente eso.
Así que las cifras no están delante ni detrás de las fibras: están en la misma
superficie, y las fibras pasan por encima como los hilos de un bordado.

Y la fibra de la hora se muda a ese toro, y entonces **señala**. Es una curva
`(1, 1)` —mientras da una vuelta al donut da otra al tubo— así que pasa por la
altura a la que están impresas las cifras **exactamente una vez**. La fibra
sobre `(t, f)` es la de `(t, 0)` girada `f` alrededor del eje, así que basta
restar el desfase de esa altura y la hora toca su número: medido, nueve
milésimas de grado de error sobre las doce.

**`finita`** — la misma curva sobre `F_p`, recorrida por su ley de grupo:
`P, 2P, 3P…` uniendo saltos consecutivos con una cuerda. El primo lo pone la
hora y el coeficiente `a` el minuto, así que son **12 × 60 figuras y ninguna se
repite**.

**`rotulada`** — la curva elíptica con las doce horas impresas encima.

`eliptica` es plana: no hay superficie donde pegar una etiqueta. Pero sí hay
dónde — **la propia curva**. La cinta se pega a lo largo de ella y las cifras se
doblan con su forma, y cuando el lazo cruza el discriminante y la curva se
pellizca, la rotulación se pellizca con ella.

Y dónde cae cada hora no se reparte a ojo. La coordenada natural de una curva
elíptica es el **parámetro elíptico** `u = ∫ dx/2y`, que es en la que la ley de
grupo es sumar: `P + Q` es `u_P + u_Q`. Repartir las doce horas por igual en `u`
es repartirlas por igual **en el grupo**, así que esto es un dial de verdad —
la esfera de un reloj que resulta tener forma de curva elíptica. Y la cuenta
avanza también en `u`, así que a la una en punto está sobre el 1.

Con una salvedad honrada: la rama se va al infinito y la ventana la corta, así
que el dial es **el arco que se ve**, no el periodo entero. La cola desde el
borde hasta el infinito se lleva un tercio largo del semiperiodo, y repartiendo
por el periodo real cuatro de las doce horas caerían fuera de la pantalla.

La integral se hace por el punto medio de cada tramo: en la raíz `y` vale cero
y dividir por ella ahí daría infinito. Converge de todas formas —cerca de una
raíz simple `dx/y` va como `dx/√(x-r)`— y el muestreo por coseno que ya hacía
`_lazo` es justo el cambio de variable que la alisa.

**`pellizco`** — `rotulada`, pero respirando.

`eliptica` tarda **una hora** en dar la vuelta al lazo de parámetros, y con
razón: allí la forma **es** el reloj, el azimut del lazo es la hora. El precio
es que a velocidad real no se mueve nada — medido en el navegador, en un
segundo cambia el **1,1%** de los píxeles del dial, y buena parte son las
cifras.

En `rotulada` ese precio ya no hay por qué pagarlo, y esa es toda la idea de
esta variante. **La hora la da la cuenta sobre la cinta**, no la forma. Así que
la velocidad del lazo queda libre, y aquí se pone en **una vuelta por minuto**.
Cambia el **11,5%** de los píxeles por segundo: diez veces más viva, y sin
tocar ni un color.

Lo que eso destapa es el acontecimiento que `eliptica` esconde. El lazo cruza
el discriminante **dos veces por vuelta** —en las fases 0,389 y 0,611— y el
óvalo vive el 22% del recorrido. A una vuelta por hora eso es un nacimiento
cada media hora y no se ve nunca; a una por minuto es un latido: el óvalo se
desprende de la rama, vive trece segundos y se reabsorbe. Y la fase arranca
justo en el primer cruce, así que **la curva se pellizca cuando cambia el
minuto**: el segundero es la propia geometría.

Dos cosas de rendimiento, y las dos salen de medir y no de mirar. Hay sesenta
curvas a la vista y entre un paso y el siguiente **cincuenta y nueve son las
mismas**, una posición más viejas: van en un anillo y se calcula una por paso.
Y el color de cada hueco del anillo **no cambia nunca**, así que calcularlo
cada vez costaba —según el perfil— el **75%** del tiempo de la esfera, sesenta
llamadas a `hsv_arr` para sesenta colores fijos. Con las dos, 0,34 ms por paso
frente a los 3,97 de la primera versión: la esfera de geometría más barata del
banco, y la más viva.

**`bordada`** — la ley de grupo sobre `F_p`, bordada en el toro que **es** su
tablero.

Lo obvio era lo de `rotulada`: pegar la cinta a lo largo del recorrido. **No se
puede, y el número lo dice.** El recorrido son sesenta cuerdas de doscientos
píxeles, así que a cada una le toca un sesentavo de la etiqueta estirado cinco
veces —hasta catorce en la peor— y lo que sale es un destello blanco. Anclando
las doce horas en sus puntos del grupo y repartiendo el resto por longitud de
arco tampoco: los doceavos del recorrido tienen longitudes que se llevan **44 a
1**, así que unas horas se solapan y otras se van al otro extremo. No hay
reparametrización que lo arregle; el soporte es el que está mal.

Y el bueno estaba delante. **El tablero es un toro.** Los puntos viven en
`F_p × F_p`, y eso son dos círculos: `x` módulo `p` e `y` módulo `p`. El
cuadrado plano de `finita` es la mentira cómoda — corta el toro por dos sitios
y hace que las cuerdas se acaben en los bordes. Enrollado, **las cuerdas dan la
vuelta**: una recta del plano afín sobre `F_p` es una geodésica cerrada, y se la
ve serpentear por la superficie y volver por el otro lado. Cada cuerda se
levanta al recubridor universal por el camino más corto, que es lo que la hace
cruzar el borde en vez de cortarse ahí.

Sobre esa superficie la etiqueta se pega como en `rosca`, y ahí sí se lee.

### Tres cosas que salieron de mirar el resultado

**Los puntos sueltos no eran nada.** La primera versión dibujaba el conjunto de
puntos de `E(F_p)`: son del orden de `p`, así que sobre una retícula `p × p` se
leen como ruido. Lo que hace el dibujo son **las cuerdas**, no los puntos.

**El primer generador que aparece suele ser malo.** A las 5:41 el primer punto
de la curva sobre `F43` da un recorrido de **cuatro** pasos —una raya— y el
mejor da **51**. Ahora se buscan todos y se queda el de mayor orden: unos
milisegundos, una vez por minuto.

**La raya vertical del borde.** El trozo real se dibujaba subiendo por `+y` y
bajando por `-y`, que es lo que sale escribir. En el óvalo va bien, porque los
dos extremos son raíces y el salto mide cero; en la rama, que se corta donde
acaba la ventana, dejaba una barra luminosa pegada al borde. Ahora se entra por
la rama negativa, se pasa por la raíz y se sale por la positiva: trazo abierto,
sin segmento de cierre.

### Y una de rendimiento

`eliptica` es la primera esfera que **calcula geometría en cada fotograma** —
una curva que cambia de forma no es la misma imagen girada, así que no hay
sprite que valga. Son 6.400 vértices y costaba 3,4 ms por fotograma: unos 34 en
la Pi, justo el límite de los 30 fps sin margen.

Pero la familia da **una vuelta por hora**: a 30 fps son 108.000 fotogramas por
vuelta, y entre uno y el siguiente no se mueve nada que se pueda ver.
Recalculando dos veces por segundo salen 7.200 formas distintas por vuelta —de
sobra— y el coste medio pasa a **0,17 ms**. Veinte veces menos, sin tocar el
resultado.

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
