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

Desde la raíz del repositorio, una sola vez:

```sh
pip install -r requirements.txt
```

Y ya:

```sh
python -m reloj                          # pantalla completa
python -m reloj --ventana                # en una ventana de 800
python -m reloj --lamina prueba.png --hora 10:09:38
python -m reloj --lamina hoja.png --hora 10:09 1:50 6:30 8:20
```

En Windows hay `run.bat`, que abre la ventana sin escribir nada. En Linux y en
la Pi, `python3` en vez de `python`.

Con `--lamina` no abre pantalla ni toca SDL: compone con Pillow y guarda un
PNG. Sirve para trabajar el diseño sin tener la Pi delante — y sin la Pi
siquiera.

`Esc` o `q` para salir.

## Cómo está montado

Tres piezas, y el reparto entre ellas es lo que hace que esto quepa en una Pi
Zero 2 W:

```
reloj/esferas/   dibujan UNA VEZ al arrancar y devuelven arrays numpy
reloj/lienzo     rasteriza a 4x con Pillow y reduce -> antialiasing de verdad
reloj/pantalla   sube los arrays a la tarjeta y los rota por hardware (SDL2)
reloj/lamina     los compone con Pillow, sin pantalla, para el PNG
```

**El coste de dibujar se paga entero al arrancar.** Por fotograma solo hay un
`RenderCopy` del fondo y un `RenderCopyEx` por aguja — que es una rotación
bilineal en la GPU, no un redibujado. Una aguja es la misma forma en los 360
grados, así que no hay ninguna razón para volver a rasterizarla.

Una esfera **no sabe nada de SDL**. Solo ofrece cuatro cosas:

```python
fondo(lado)    -> (lado, lado, 3) uint8      lo que no se mueve
piezas(lado)   -> {nombre: (lado, lado, 4)}  apuntando a las 12, pivote al centro
angulos(t)     -> {nombre: grados horarios}  t = segundos desde medianoche
ORDEN          -> los nombres, en orden de dibujo
```

Por eso el mismo código sirve para la pantalla y para el PNG.

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

## Esferas

| Carpeta | Origen | Qué gana en pantalla grande |
|---|---|---|
| `reloj/esferas/disco.py` | `Disco/` del Garmin | antialiasing real y **segundero de barrido** |

`disco.py` conserva la geometría exacta de la esfera del reloj, con las medidas
pasadas a **fracción del radio** para que valga igual en un monitor de 24" que
en una pantallita de 5". El segundero es nuevo: una esfera Connect IQ se
redibuja una vez por segundo, así que un barrido continuo era imposible allí.

## `modelos/`

La línea del personaje 3D (`Mira2.fbx`) queda aparcada aquí. Necesita dos cosas
que hoy no hay: una sesión con acceso al disco local, para las cuatro texturas
que el FBX pide (`BC.psd`, `sborka_03 - Default_Normal.png`, `MG_bc.tga`,
`MG_nm.tga`), y —si acaba siendo animada— una Pi 4 con Godot.

El modelo es de Pigcraft y va con licencia CC-BY: si llega a usarse, hay que
acreditarlo.
