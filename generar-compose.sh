#!/usr/bin/bash
if [ "$#" -ne 2 ]; then
    echo "No se recibieron los dos parámetros esperados"
    exit 1
fi

case $2 in
'' | *[!0-9]*)
    echo "$2 no es un número"
    exit 1
    ;;
esac

echo "Nombre del archivo de salida: $1"
echo "Cantidad de clientes: $2"

dir=$(cd -P -- "$(dirname -- "$0")" && pwd -P)

python3 mi-generador.py $1 $2 $dir
