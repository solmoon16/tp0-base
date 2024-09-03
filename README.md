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

Si bien se realiza la operación en el DockerCompose con la clave 'volume', no es un volumen en sí ya que se está montando un solo archivo en cada caso, especificando las direcciones origen y destino. Como origen, se obtiene el directorio en el cual se está ejecutando el script y luego se le agrega el path relativo, para obtener el path absoluto de cada archivo de configuración.

También se eliminó la línea que copiaba el archivo de configuración del Dockerfile del cliente, y se creó un archivo .dockerignore para que no se copien los archivos de configuración cuando se reinician las imágenes de los contenedores. En caso contrario, como se copiaba toda la carpeta los archivos iban a ser copiados nuevamente.

El funcionamiento y ejecución es igual que antes, con la diferencia de que si se modifican los archivos de configuración no se hará un build de las imágenes.

### Ejercicio N°3

Se creó un script de bash `validar-echo-server.sh` que envía un mensaje al servidor y corrobora que esté funcionando adecuadamente. En caso de que el servidor retorne el mismo mensaje, se imprime `action: test_echo_server | result: success` y en caso contrario `action: test_echo_server | result: fail`.

En caso de que el servidor esté apagado o la red no esté levantada, primero se imprimirá un error de docker informando la situación.

Para ejecutarlo hay que correr:

```bash
./validar-echo.server.sh $mensaje
```

Para cambiar el mensaje que se le envía al servidor hay que editar la variable `message` dentro del script.

### Ejercicio N°4

En este programa los recursos principales siendo utilizados son sockets que permiten comunicar al servidor con los clientes, por lo que ese es el recurso que hay que tener en cuenta en un _graceful shutdown_.

Desde el lado del servidor, cuando se recibe la señal SIGTERM, se notifica inmediatamente al servidor y se llama a la función que cierra y libera los recursos. En este caso, se cierra el socket del servidor por el cual escucha las conexiones entrantes y, si estaba en comunicación con algún cliente, cierra ese socket también. Como los sockets están cerrados, finaliza sus operaciones y termina el proceso.

El cliente solo tiene un socket abierto que abre y cierra cada vez que se conecta con el servidor. En una go rutina distinta, se está escuchando constantemente por las señales. Cuando llega alguna, se notifica al hilo principal a través de un canal que se lee antes de comenzar una nueva conexión. Por lo tanto, el cliente finaliza la conexión que tenía abierta y no vuelve a abrir otra. Si el socket que estaba utilizando queda abierto, se cierra.

Se puede probar corriendo los procesos y enviándoles la señal SIGTERM con el comando

```bash
kill -15 ${pid}
```

Al hacerlo, se puede observar que tanto el servidor como el cliente finalizan con código 0 e indican en el log qué sockets se están cerrando.

También se agregó un _graceful shutdown_ para la señal SIGINT, por lo que se puede observar el mismo comportamiento si se hace Ctrl+C en la terminal donde corren los procesos.

## Parte 2: Repaso de Comunicaciones

### Ejercicio 5

Se agregó la estructura 'Bet' en el módulo del cliente, la cual se utiliza para crear apuestas que luego son enviadas al servidor. Para enviar mensajes al servidor y evitar tener un _short write_ se utiliza `Write` de la biblioteca .net de go. Esta función intenta escribir todos los bytes indicados, y solo devuelve error en caso de que no logre hacerlo; es decir, no existe el riesgo de que indique que la operación salió bien pero se escribieron menos bytes.

Para la lectura del socket, se mantuvo la estructura previamente utilizada, que intenta leer hasta el primer '\n' y devuelve un error en caso de que no lo logre.

Desde el lado del servidor, para evitar el _short read_ es necesario leer en loop hasta que se lee un string vacío, lo que indica que la conexión se cerró. Como el cliente cierra la conexión cuando termina de enviar su mensaje, el servidor obtiene la apuesta enviada y no se queda esperando por más mensajes. Para evitar el _short write_, se utiliza el método `sendall` que se encarga de escribir todo el buffer indicado o lanzar un error en caso contrario.

Cuando el servidor recibe una apuesta del cliente, la almacena utilizando la función `store_bet` y le envía al cliente el número de apuesta almacenado. Cuando el cliente lo recibe deja constancia en el log. El cliente tiene un límite de tiempo de lectura, y en caso de que se supere considera que el servidor no le contestó a tiempo y que hubo un error en la comunicación.

Como parte del protocolo, a la hora de construir una apuesta, se revisa que se tenga toda la información necesaria y que tenga el formato indicado. Según un análisis realizado a los archivos .csv que contienen múltiples apuestas, se definieron tamaños máximos para el nombre y apellido de cada apuesta. Además, se verifica que la fecha de nacimiento esté en el formato indicado, que el documento tenga sentido (número y con 8 caracteres) y que el número de apuesta sea un número. En caso de que no se cumpla alguna de esas validaciones, no se crea la apuesta.

Por otro lado, el servidor mantiene un buffer de lectura de 1024 bytes. Como, según el análisis realizado previamente, todas las apuestas tienen un tamaño menor al mismo y se manda una apuesta por conexión, no es necesario aún considerar el caso de que la lectura de la apuesta no entre en el buffer.

Para enviar la información de la apuesta se utilizan las variables de entorno `NOMBRE`, `APELLIDO`, `DOCUMENTO`, `NACIMIENTO` y `NUMERO`; se definen en el archivo `docker-compose-dev.yaml` para poder ejecutar el contenedor del cliente. En caso de que falte alguna de las variables, la apuesta no se creará y no será enviada.

Si se recibe alguna de las señales de finalización (SIGTERM o SIGINT), en el caso del servidor se cierran ambos sockets y, una vez finalizada la operación que estaba realizando, sale y no continúa. En el caso del cliente, cuando se recibe alguna de las señales se le notifica al hilo principal a través de un canal que se lee antes de abrir una nueva conexión. Por lo tanto, el cliente finaliza la conexión que tenía y luego cierra todo en vez de abrir una nueva.

### Ejercicio 6

En este ejercicio, en vez de enviar una sola apuesta la idea es enviar apuestas en _batches_. Dados los tamaños definidos en el ejercicio anterior y la limitación de 8kb para un batch, se decidió que el tamaño máximo sea 120 apuestas por batch, acercándose al máximo definido y enviando de a múltiples apuestas, acelerando el procesamiento por parte del servidor.

Los clientes tienen loops cuyo tamaño se indica en el archivo de configuración. Por cada ejecución del loop, se envía un batch de apuestas al servidor. Para esto, se utiliza la función `sendBets`, que se encarga de abrir el archivo correspondiente de esa agencia y obtener las apuestas que corresponden a ese número de batch, salteando aquellas apuestas que ya fueron enviadas porque son de otro batch. Luego, une esas apuestas en un batch y se las envía al servidor para que este las procese. Para delimitar el fin de un batch e indicarle al servidor que ya se terminó de enviar, se utiliza el caracter '\n'.

Para poder leer el archivo correspondiente a cada cliente, se agregó un volumen para la carpeta .data en el contenedor del cliente. De esta forma, cada cliente puede acceder a la carpeta y, si se edita desde afuera, no es necesario reiniciar el contenedor.

Desde el lado del servidor, lee del socket del cliente constantemente hasta que el cliente lo cierra, indicando el fin de la conexión. Mientras lee, va guardando en un buffer propio todo el mensaje hasta que se encuentra con un '\n', ya que eso indica que recibió todo un batch. En ese caso, procesa todas las apuestas recibidas convirtiéndolas en objetos `Bet` y utilizando `store_bet` para almacenarlas. Si la conexión sigue abierta, sigue leyendo.

Luego de guardar todas las apuestas, el servidor le envía al cliente la cantidad de apuestas que procesó. En caso de que hayan sido menos que un batch, tanto cliente como servidor dejan logs indicando que hubo un error.

En este caso, el cliente ya no recibe más las apuestas por variable de entorno por lo que fueron eliminadas del docker-compose.

En el caso de que se conecten múltiples clientes al servidor, este procesará cada conexión de forma sincrónica e irá guardando cada batch que recibe. Al final, en el archivo `bets.csv` generado se encontrarán las apuestas de todas las agencias, no necesariamente ordenadas.
