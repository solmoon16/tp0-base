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

## Parte 2: Repaso de Comunicaciones

### Ejercicio 5

Se agregó la estructura 'Bet' en el módulo del cliente, la cual se utiliza para crear apuestas que luego son enviadas al servidor. Para enviar mensajes al servidor y evitar tener un _short write_ se utiliza `Write` de la biblioteca .net de go. Esta función intenta escribir todos los bytes indicados, y solo devuelve error en caso de que no logre hacerlo; es decir, no existe el riesgo de que indique que la operación salió bien pero se escribieron menos bytes.

Para la lectura del socket, se mantuvo la estructura previamente utilizada, que intenta leer hasta el primer '\n' y devuelve un error en caso de que no lo logre.

Desde el lado del servidor, para evitar el _short read_ es necesario leer en loop hasta que se lee un string vacío, lo que indica que la conexión se cerró. Como el cliente cierra la conexión cuando termina de enviar su mensaje, el servidor obtiene la apuesta enviada. Para evitar el _short write_, se utiliza el método `sendall` que se encarga de escribir todo el buffer indicado o lanzar un error en caso contrario.

Cuando el servidor recibe una apuesta del cliente, la almacena utilizando la función `store_bet` y le envía al cliente el número de apuesta almacenado. Cuando el cliente lo recibe, si es el mismo número de apuesta que envió, deja constancia en el log. El cliente tiene un límite de tiempo de lectura, y en caso de que se supere considera que el servidor no le contestó a tiempo y que hubo un error en la comunicación.
