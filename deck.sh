#!/usr/bin/env bash
# Arrancar el reloj en una Steam Deck (o en cualquier Linux de escritorio).
#
# SteamOS tiene la raíz de solo lectura y en A/B: cada actualización del
# sistema escribe una imagen nueva en la partición dormida y arranca en ella,
# así que **todo lo que no esté en /home desaparece**. Por eso aquí no se
# instala nada en el sistema: se hace un entorno virtual dentro de la propia
# carpeta del proyecto, que vive en /home y sobrevive a las actualizaciones.
#
# Tampoco hace falta SDL2 del sistema: `pysdl2-dll` trae sus propios binarios
# dentro del paquete de Python. Ni `pacman`, ni `steamos-readonly disable`, ni
# nada que se rompa al actualizar.
#
#   chmod +x deck.sh
#   ./deck.sh
#
# Si ya tienes un entorno con esta pila —el del simulador de conducción, por
# ejemplo— lo encuentra y lo usa; para forzar uno concreto:
#
#   RELOJ_PYTHON=/ruta/al/python ./deck.sh
#
# El entorno del simulador tiene pysdl2, pysdl2-dll y numpy, pero **no
# Pillow**: aquel no dibuja texto y aquí las tipografías y la lámina PNG salen
# de PIL. Si aparece ese caso, el guion lo detecta y ofrece añadir el paquete
# ahí mismo —tres megas— en vez de montar un entorno nuevo de doscientos.
#
# Se ejecuta en MODO ESCRITORIO, desde Konsole. El reloj no usa el mando, así
# que no hay que darlo de alta en Steam como en el simulador (aquello era para
# que la Deck presentara el mando como gamepad). La pantalla es de 1280x800:
# a pantalla completa el dial se queda en min(1280, 800) = 800 px, el mismo
# tamaño con el que está medido todo el proyecto.
#
# Para llevar los archivos a la Deck, `git clone` en /home/deck y `git pull`
# para actualizar (opción 6 del menú).
set -u

cd "$(dirname "$0")"
VENV=".venv"

# ---------------------------------------------------------------- preparar --
# Se busca un Python que YA sepa importar lo que hace falta antes de crear
# nada. Quien viene del simulador de conducción ya tiene un entorno con casi
# esta misma pila y montarle un segundo sería duplicar doscientos megas por
# gusto.
#
# Por orden: el que se diga a mano, el que esté activo en esta consola, el
# `.venv` de esta carpeta, el del simulador si está al lado, y el del sistema.
nucleo() { [ -x "$1" ] && "$1" -c "import sdl2, numpy" >/dev/null 2>&1; }
sirve()  { [ -x "$1" ] && "$1" -c "import sdl2, numpy, PIL" >/dev/null 2>&1; }

# Si se pide uno a mano y no sirve, hay que decirlo: caer en silencio a otro
# entorno es la forma más rápida de pasarse media hora depurando el que no es.
# Que le falte solo Pillow no es "no sirve": eso lo arregla la segunda pasada
# unas líneas más abajo, y avisar aquí sería asustar por nada.
if [ -n "${RELOJ_PYTHON:-}" ] && ! nucleo "${RELOJ_PYTHON}"; then
    echo "AVISO: RELOJ_PYTHON=${RELOJ_PYTHON} no vale (no existe, o no importa"
    echo "       sdl2/numpy). Sigo buscando otro."
    "${RELOJ_PYTHON}" -c "import sdl2, numpy" 2>&1 | tail -3
    echo
fi

# Los candidatos se montan de uno en uno y solo si tienen sentido. Escribirlos
# como "${VIRTUAL_ENV:-}/bin/python" parece más corto y es un error: con la
# variable vacía queda "/bin/python", que en muchos sistemas existe, y entonces
# el guion anuncia que usa "el entorno que ya tienes" señalando a uno que nadie
# ha elegido.
CANDIDATOS=()
[ -n "${RELOJ_PYTHON:-}" ] && CANDIDATOS+=("$RELOJ_PYTHON")
[ -n "${VIRTUAL_ENV:-}" ] && CANDIDATOS+=("$VIRTUAL_ENV/bin/python")
CANDIDATOS+=("$VENV/bin/python")
for otro in ../CarDrivingSimulator ../cardrivingsimulator \
            "$HOME/CarDrivingSimulator" "$HOME/cardrivingsimulator"; do
    CANDIDATOS+=("$otro/.venv/bin/python" "$otro/venv/bin/python")
done
# Si el clon del simulador no está en ninguno de los sitios de arriba, se
# busca por su lanzador: el instalador deja siempre `jugar.sh` en la raíz del
# proyecto. Tres niveles desde /home/deck bastan y no se recorre el disco.
if command -v find >/dev/null 2>&1; then
    while IFS= read -r lanzador; do
        CANDIDATOS+=("$(dirname "$lanzador")/.venv/bin/python")
    done < <(find "$HOME" -maxdepth 3 -name jugar.sh -type f 2>/dev/null)
fi
CANDIDATOS+=("$(command -v python3 || true)")

PY=""
for cand in "${CANDIDATOS[@]}"; do
    if [ -n "$cand" ] && sirve "$cand"; then PY="$cand"; break; fi
done

# Segunda pasada: un entorno con sdl2 y numpy al que solo le falta Pillow. Es
# justo el del simulador. Añadirle un paquete es mejor que duplicar la pila,
# pero es SU entorno: se pregunta antes de tocarlo. El propio, no.
if [ -z "$PY" ]; then
    for cand in "${CANDIDATOS[@]}"; do
        [ -n "$cand" ] || continue
        nucleo "$cand" || continue
        echo "Encontrado un entorno con SDL2 y numpy:"
        echo "    $cand"
        echo "Le falta Pillow, que es lo que dibuja las tipografias y el PNG."
        if [ "$cand" = "$VENV/bin/python" ]; then
            resp=s
        else
            read -r -p "  Lo anado ahi? (s/N) " resp
        fi
        case "$resp" in
            s|S|si|SI|Si|y|Y)
                if "$cand" -m pip install --quiet Pillow && sirve "$cand"; then
                    PY="$cand"
                    break
                fi
                echo "No se pudo instalar Pillow ahi. Sigo buscando."
                echo
                ;;
        esac
    done
fi

if [ -n "$PY" ]; then
    echo "Uso el entorno que ya tienes:  $PY"
else
    if ! command -v python3 >/dev/null 2>&1; then
        echo "No encuentro python3. En SteamOS viene de serie; en otro Linux,"
        echo "instálalo con el gestor de paquetes de tu distribución."
        exit 1
    fi

    # Un entorno que estaba y ya no arranca casi siempre significa lo mismo:
    # una actualización de SteamOS cambió la versión de Python del sistema y
    # el venv, que enlaza contra /usr, se quedó apuntando a lo que ya no está.
    # No tiene arreglo fino; se rehace, que tarda un minuto.
    if [ -d "$VENV" ] && [ ! -x "$VENV/bin/python" ]; then
        echo "Hay un $VENV cuyo Python ya no funciona (típico después de una"
        echo "actualización de SteamOS: el entorno enlaza con el Python de"
        echo "/usr). Lo rehago."
        rm -rf "$VENV"
    fi

    if [ ! -x "$VENV/bin/python" ]; then
        echo "No hay ningún entorno con la pila. Preparo uno aquí dentro..."
        # En SteamOS hay Python 3 pero no pip ni ensurepip, así que `venv` a
        # secas o falla o sale sin pip. Se intenta lo normal y, si no, se crea
        # sin pip y se le inyecta el oficial: es lo que hace el instalador del
        # simulador y está probado en esta misma máquina.
        if ! python3 -m venv "$VENV" >/dev/null 2>&1 \
           || [ ! -x "$VENV/bin/pip" ]; then
            echo "Sin ensurepip (lo normal en SteamOS): lo monto sin pip y se"
            echo "lo pongo con el get-pip.py oficial."
            rm -rf "$VENV"
            if ! python3 -m venv --without-pip "$VENV"; then
                echo "No se pudo crear el entorno virtual. Mira el error."
                exit 1
            fi
            GETPIP="$(mktemp)"
            if command -v curl >/dev/null 2>&1; then
                curl -sS https://bootstrap.pypa.io/get-pip.py -o "$GETPIP"
            elif command -v wget >/dev/null 2>&1; then
                wget -qO "$GETPIP" https://bootstrap.pypa.io/get-pip.py
            else
                echo "No hay ni curl ni wget para bajar get-pip.py."
                exit 1
            fi
            if ! "$VENV/bin/python" "$GETPIP" --quiet; then
                echo "No se pudo instalar pip en el entorno."
                rm -f "$GETPIP"
                exit 1
            fi
            rm -f "$GETPIP"
        fi
    fi
    PY="$VENV/bin/python"
    echo "Instalando dependencias (solo la primera vez)..."
    if ! "$PY" -m pip install -r requirements.txt; then
        echo "No se pudieron instalar. Mira el error de arriba."
        exit 1
    fi
fi

# Un lanzador de una línea con el intérprete ya resuelto, para no repetir la
# búsqueda: sirve para el acceso directo del escritorio y, si algún día quieres
# verlo en Modo Juego, es lo que se añade a Steam como juego no-Steam.
cat > reloj.sh <<LANZADOR
#!/usr/bin/env bash
# Generado por deck.sh. Pantalla completa, sin menú.
cd "\$(dirname "\$0")"
exec "$PY" -m reloj "\$@"
LANZADOR
chmod +x reloj.sh

sleep 1

# ------------------------------------------------------------------- menú ---
while true; do
    clear
    cat <<'MENU'

  RELOJ DE SOBREMESA — Steam Deck
  ===============================

  1   Ventana         (empieza en disco, flechas para pasear)
  2   Pantalla completa                 (dial de 800 px en la Deck)
  3   Elegir una esfera concreta
  4   Ver todas en un PNG
  5   Pantalla completa a camara rapida  (una hora cada 6 segundos)
  6   Actualizar desde GitHub  (git pull)
  7   Comprobar la instalacion  (sin abrir pantalla)
  0   Salir

MENU
    read -r -p "  Que hago?  " op
    case "$op" in
        1) "$PY" -m reloj --ventana ;;
        2) "$PY" -m reloj ;;
        3)  clear
            "$PY" -m reloj --lista
            echo
            read -r -p "  Nombre de la esfera:  " cual
            [ -n "$cual" ] && "$PY" -m reloj --esfera "$cual"
            ;;
        4)  "$PY" -m reloj --lamina todas.png --esfera TODAS --lado 440
            command -v xdg-open >/dev/null 2>&1 && xdg-open todas.png
            ;;
        # La familia de `eliptica` da una vuelta por hora y la cámara de las
        # esferas 3D tarda varios minutos: a velocidad real no hay forma de
        # juzgar si el movimiento funciona.
        5) "$PY" -m reloj --velocidad 600 ;;
        6)  if command -v git >/dev/null 2>&1; then
                git pull
            else
                echo "No encuentro git. Baja el ZIP desde GitHub y descomprímelo."
            fi
            read -r -p "  (Intro para seguir) " _
            ;;
        # Con los controladores de mentira de SDL se comprueba la pila entera
        # sin necesidad de pantalla: vale por ssh y vale para saber si algo se
        # rompió sin tener que abrir el reloj a ver qué pasa.
        7)  clear
            echo "  Interprete:  $PY"
            SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy "$PY" - <<'COMPROBAR'
import ctypes
import numpy, PIL, sdl2
print("  numpy %s   Pillow %s" % (numpy.__version__, PIL.__version__))
if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) != 0:
    raise SystemExit("  SDL no arranca: " + sdl2.SDL_GetError().decode())
print("  SDL %d.%d.%d, driver de video %s"
      % (sdl2.SDL_MAJOR_VERSION, sdl2.SDL_MINOR_VERSION, sdl2.SDL_PATCHLEVEL,
         sdl2.SDL_GetCurrentVideoDriver().decode()))
sdl2.SDL_Quit()
from reloj.esferas import DISPONIBLES
print("  %d esferas en el catalogo" % len(DISPONIBLES))
COMPROBAR
            echo
            echo "  Y ahora la pantalla de verdad:"
            "$PY" - <<'PANTALLA'
import ctypes
import sdl2
if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO) != 0:
    print("  no hay pantalla disponible: " + sdl2.SDL_GetError().decode())
else:
    m = sdl2.SDL_DisplayMode()
    sdl2.SDL_GetCurrentDisplayMode(0, ctypes.byref(m))
    print("  %dx%d  ->  dial de %d px a pantalla completa"
          % (m.w, m.h, min(m.w, m.h)))
    sdl2.SDL_Quit()
PANTALLA
            read -r -p "  (Intro para seguir) " _
            ;;
        0) exit 0 ;;
    esac
done
