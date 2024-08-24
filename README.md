# TP0: Docker + Comunicaciones + Concurrencia

## Parte 1: Introducción a Docker

### Ejercicio N°1

Se realizó un script de bash que debe recibir como parámetros el nombre del archivo de salida que se espera obtener y cuántos clientes debe contener el DockerCompose.

A su vez, se hizo un subscript en Python; dado un diccionario con la configuración inicial, agrega la cantidad de clientes especificada y luego vuelca toda esa información en un archivo con el nombre recibido por parámetro.

Para ejecutar, entonces, basta con correr:

```bash
./generar-compose.sh $nombre_archivo $cant_clientes
```

En caso de que no se reciban ambos parámetros o la cantidad de clientes no sea un número, el script finalizará imprimiendo el error.
