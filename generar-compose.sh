#!/usr/bin/bash
if [ "$#" -ne 2 ]; then
    echo "No se recibieron los dos parámetros esperados"
    exit 2
fi

case $2 in
'' | *[!0-9]*)
    echo "$2 no es un número"
    exit 2
    ;;
esac

echo "Nombre del archivo de salida: $1"
echo "Cantidad de clientes: $2"

#python3 mi-generador.py $1 $2
