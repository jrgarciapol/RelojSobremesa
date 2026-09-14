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
# Se ejecuta en MODO ESCRITORIO, desde Konsole. La pantalla de la Deck es de
# 1280x800, así que a pantalla completa el dial sale de 800 px — el mismo
# tamaño con el que está medido todo el proyecto.
set -u

cd "$(dirname "$0")"
VENV=".venv"

# ---------------------------------------------------------------- preparar --
# Se busca un Python que YA sepa importar lo que hace falta antes de crear
# nada. Quien viene del simulador de conducción ya tiene un entorno con esta
# misma pila —pysdl2, pysdl2-dll, numpy— y montarle un segundo sería duplicar
# doscientos megas por gusto.
#
# Por orden: el que se diga a mano, el que esté activo en esta consola, el
# `.venv` de esta carpeta, el del simulador si está al lado, y el del sistema.
sirve() { [ -x "$1" ] && "$1" -c "import sdl2, numpy, PIL" >/dev/null 2>&1; }

# Si se pide uno a mano y no sirve, hay que decirlo: caer en silencio a otro
# entorno es la forma más rápida de pasarse media hora depurando el que no es.
if [ -n "${RELOJ_PYTHON:-}" ] && ! sirve "${RELOJ_PYTHON}"; then
    echo "AVISO: RELOJ_PYTHON=${RELOJ_PYTHON} no vale (no existe, o no importa"
    echo "       sdl2/numpy/PIL). Sigo buscando otro."
    "${RELOJ_PYTHON}" -c "import sdl2, numpy, PIL" 2>&1 | tail -3
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
CANDIDATOS+=("$(command -v python3 || true)")

PY=""
for cand in "${CANDIDATOS[@]}"; do
    if [ -n "$cand" ] && sirve "$cand"; then PY="$cand"; break; fi
done

if [ -n "$PY" ]; then
    echo "Uso el entorno que ya tienes:  $PY"
else
    if ! command -v python3 >/dev/null 2>&1; then
        echo "No encuentro python3. En SteamOS viene de serie; en otro Linux,"
        echo "instálalo con el gestor de paquetes de tu distribución."
        exit 1
    fi
    if [ ! -x "$VENV/bin/python" ]; then
        echo "No hay ningún entorno con la pila. Preparo uno aquí dentro..."
        if ! python3 -m venv "$VENV"; then
            echo
            echo "No se pudo crear el entorno virtual. Si la queja es de 'ensurepip':"
            echo "  python3 -m venv --without-pip $VENV"
            echo "  curl -sS https://bootstrap.pypa.io/get-pip.py | $VENV/bin/python"
            exit 1
        fi
        "$VENV/bin/python" -m pip install --quiet --upgrade pip
    fi
    PY="$VENV/bin/python"
    echo "Instalando dependencias (solo la primera vez)..."
    if ! "$PY" -m pip install -r requirements.txt; then
        echo "No se pudieron instalar. Mira el error de arriba."
        exit 1
    fi
fi
sleep 1

# ------------------------------------------------------------------- menú ---
while true; do
    clear
    cat <<'MENU'

  RELOJ DE SOBREMESA — Steam Deck
  ===============================

  1   Ventana         (empieza en disco, flechas para pasear)
  2   Pantalla completa
  3   Elegir una esfera concreta
  4   Ver todas en un PNG
  5   Pantalla completa a camara rapida  (una hora cada 6 segundos)
  6   Actualizar desde GitHub  (git pull)
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
        0) exit 0 ;;
    esac
done
