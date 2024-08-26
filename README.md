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

### Ejercicio N°2

Para que los archivos de configuración sean inyectados en los contenedores y persistidos por fuera de la imagen se realizó un 'build mount' por cada archivo, montando así un archivo específico en un contenedor.

Si bien se realiza la operación en el DockerCompose con la clave 'volume', no es un volumen en sí ya que se está montando un solo archivo en cada caso, especificando las direcciones origen y destino.

También se eliminó la línea que copiaba el archivo de configuración del Dockerfile del cliente, y se creó un archivo .dockerignore para que no se copien los archivos de configuración cuando se reinician las imágenes de los contenedores. En caso contrario, como se copiaba toda la carpeta los archivos iban a ser copiados nuevamente.

El funcionamiento y ejecución es igual que antes, con la diferencia de que si se modifican los archivos de configuración no se hará un build de las imágenes.

### Ejercicio N°3

Se creó un script de bash `validar-echo-server.sh` que recibe por parámetro un mensaje para enviarle al servidor y corroborar que esté funcionando adecuadamente. En caso de que el servidor retorne el mismo mensaje, se imprime `action: test_echo_server | result: success` y en caso contrario `action: test_echo_server | result: fail`.

En caso de que el servidor esté apagado o la red no esté levantada, primero se imprimirá un error de docker informando la situación.

Para ejecutarlo hay que correr:

```bash
./validar-echo.server.sh $mensaje
```

### Ejercicio N°4

En este programa los recursos principales siendo utilizados son sockets que permiten comunicar al servidor con los clientes, por lo que ese es el recurso que hay que tener en cuenta en un _graceful shutdown_.

Desde el lado del servidor, cuando se recibe la señal SIGTERM, se notifica inmediatamente al servidor y se llama a la función que cierra y libera los recursos. En este caso, se cierra el socket del servidor por el cual escucha las conexiones entrantes y, si estaba en comunicación con algún cliente, cierra ese socket también.

El cliente solo tiene un socket abierto que abre y cierra cada vez que se conecta con el servidor. Cuando se recibe la señal SIGTERM, termina la conexión que tenía abierta y no vuelve a abrir otra. Si el socket que estaba utilizando queda abierto, se cierra.

Dado el caso de que haya más recursos a manejar en un futuro, las estructuras armadas ya dan lugar a que se libere todo lo utilizado por cada entidad.
