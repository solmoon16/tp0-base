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

### Ejercicio 7

Para esta situación, se modificó la lógica de las agencias para que envíen, de a _batches_, todas sus apuestas al servidor en una única conexión. Una vez que la agencia termina de enviarle al servidor sus apuestas, le envía un mensaje indicando que finalizó y se queda esperando a que el servidor envíe quiénes son los ganadores.

El servidor, por otro lado, procesa las apuestas de cada agencia de forma sincrónica y, una vez que finaliza cada cliente, los guarda en un diccionario con el número de agencia y la conexión. Una vez que tiene a todos los clientes guardados, es decir que ya todos enviaron sus apuestas, realiza el sorteo utilizando las funciones `load_bets` y `has_won`, y le informa cada cliente cuántos ganadores hubo en su agencia. Finalizado esto, el servidor se cierra cerrando su socket y el de sus clientes.

Por otra parte, en la función `waitWinner` del cliente, el mismo se queda bloqueado en el socket del servidor intentando leer quiénes son los ganadores. Una vez que recibe la respuesta del servidor, deja en el log cuántos ganadores hubo y termina su ejecución.

Una diferencia del servidor en relación al ejercicio anterior es que ahora la lectura del socket del cliente tiene una nueva condición de corte. Además de finalizar si no lee nada porque se cerró el socket, con cada lectura corrobora si el cliente le mandó el mensaje "DONE:$agencia" para ver si puede continuar procesando las apuestas de otro cliente. En caso de que así sea, agrega a un diccionario el socket abierto para volver a utilizarlo luego de realizar el sorteo.

El número de agencias es enviado al servidor a través de una variable de entorno y, en caso de no recibir ningun número válido, se toma como _default_ 5 agencias. Esto se puede modificar a través de la variable de entorno enviada en el docker-compose o editando la constante AGENCIES_NUM en el archivo del servidor.

En la configuración del cliente se encuentra la variable "loop_period", la cual se utiliza para hacer una pausa entre cada batch enviado, dándole un tiempo al servidor a que reciba todo y pueda procesarlo de mejor manera.

Por lo tanto, se pueden configurar los siguientes valores para observar distintas situaciones:

- número de agencias a través de variable de entorno o editando la constante
- tiempo que pasa entre cada batch que se envía en el archivo de configuración del cliente

Otra diferencia en relación a ejercicios previos es el _graceful shutdown_ del cliente. Antes, el cliente se fijaba antes de comenzar una nueva conexión si había recibido una señal de cierre. Ahora, como el cliente puede quedar bloqueado en el socket esperando una respuesta del servidor, se agregó otra go rutina donde se revisa constantemente si se recibió una señal y, en caso de que se haya recibido, se cierra el socket. Esto fuerza a que todas las operaciones bloqueadas y futuras con el socket fallen con un error de "ErrClosed", y obliga al cliente a terminar su ejecución.

## Parte 3: Repaso de Concurrencia

### Ejercicio 8

Para agregarle paralelización al servidor, se utilizó la biblioteca `multiprocessing` de python. Por cada conexión con un cliente, se crea un proceso nuevo. Desde el proceso principal, una vez que se hayan creado tantos procesos como el número de agencias, se espera a que los procesos hijos terminen para realizar el sorteo.

Cada proceso hijo recibe un socket a través del cual se va a comunicar con el cliente. El cliente envía a través del socket todos los _batches_ de apuestas y un mensaje de finalización para indicar que terminó. Mientras, el proceso va procesando todas las apuestas y enviándolas por una cola. Cuando finaliza, guarda el socket del cliente junto con su número de agencia en un diccionario recibido por parámetro y finaliza.

El diccionario que reciben los procesos hijos es compartido y gestionado por un `Manager`, una estructura de Python que permite sincronizar información entre procesos y orquestarlos. Una vez que todos los procesos terminan, el proceso original accede a este diccionario y lo utiliza para obtener los sockets y avisarle a cada agencia quiénes fueron sus ganadores. Para realizar el sorteo, se utilizan las funciones `load_bets` y `has_won`.

A diferencia de los ejercicios anteriores, donde cada cliente se procesaba de forma secuencial, ahora el archivo donde se almacenan las apuestas pasa a ser un recurso compartido entre procesos. Por lo tanto, para evitar condiciones de carrera, se utiliza una cola compartida donde cada proceso hijo va enviando los _batch_ que procesa y el proceso padre va leyendo de la cola y guardando las apuestas. Para evitar que el proceso padre se bloquee leyendo, esto solo se hace una vez que ya fueron creados todos los procesos hijos. La cola es leída hasta que todos los procesos hijos envíen `None`, indicando que no enviarán más apuestas.

Se agregó un timeout al `get` de la cola ya que, en caso contrario, el servidor quedaría bloqueado y no se enteraría si llegó alguna señal de cierre.

Otro cambio en relación a los demás ejercicios es que se le agregó al servidor el campo `stop`, que se marca como True cuando se recibe alguna de las señales de cierre. Si bien los procesos hijos reciben las señales, con este flag pueden darse cuenta que deben finalizar y cerrar el socket que tienen con el cliente.

En el proceso padre se utilizan los mismos mecanismos que antes a la hora de hacer un _graceful shutdow_: una vez que se recibe la señal se cierran todos los sockets en uso y se espera a los procesos hijos.

Como en el ejercicio anterior, se pueden configurar el número de agencias a través de la variable de entorno y el tiempo que esperan los clientes entre cada envío de _batch_ a través de su archivo de configuración.

Para este ejercicio, no se editó al cliente.

## Aclaraciones post-demo

A partir de lo hablado, se realizaron los siguientes cambios:

- El `accept` del servidor se dejó bloqueante
- Se agregaron reintentos en la escritura del cliente en caso de que no se envíen todos los bytes necesarios o haya algún error, evitando un _short write_
- Se dejó más claro el `read` que hace el servidor al cliente. En el ejercicio 5 sí se está haciendo un _short read_, pero a partir del 6 ya se arregla. La versión más clara se encuentra en el ejercicio 8
