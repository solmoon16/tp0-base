import signal
import socket
import logging


class ServerSignalHandler:
    def __init__(self, server):
        signal.signal(signal.SIGTERM, self.close_all)
        signal.signal(signal.SIGINT, self.close_all)
        self.server = server

    def close_all(self, _signal, frame):
        logging.info('action: received {} | info: closing and shutting down | result: success'.format(signal.Signals(_signal).name))
        self.server.close_all()

class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self.client_socket = None

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        # TODO: Modify this program to handle signal to graceful shutdown
        # the server
        while True:
            self.client_socket = self.__accept_new_connection()
            if self.client_socket is None:
                break
            self.__handle_client_connection()

    def __handle_client_connection(self):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            # TODO: Modify the receive to avoid short-reads
            msg = self.client_socket.recv(1024).rstrip().decode('utf-8')
            addr = self.client_socket.getpeername()
            logging.info(f'action: receive_message | result: success | ip: {addr[0]} | msg: {msg}')
            # TODO: Modify the send to avoid short-writes
            self.client_socket.send("{}\n".format(msg).encode('utf-8'))
        except OSError as e:
            logging.error("action: receive_message | result: fail | error: {e}")
        finally:
            self.client_socket.close()
            self.client_socket = None

    def __accept_new_connection(self):
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """
        # Connection arrived
        logging.info('action: accept_connections | result: in_progress')
        try:
            c, addr = self._server_socket.accept()
            logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
        except OSError:
            return None
        else:
            return c
    
    def close_all(self):
        logging.info('action: closing socket | info: closing server socket | result: in_progress')
        self._server_socket.close()
        if self.client_socket is not None:
            logging.info('action: closing socket | info: closing client socket | result: in_progress')
            self.client_socket.close()
            self.client_socket = None
