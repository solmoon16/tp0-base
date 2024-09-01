import signal
import socket
import logging
import string

from common.utils import Bet, store_bets

class ServerSignalHandler:
    def __init__(self, server):
        signal.signal(signal.SIGTERM, self.close_all)
        signal.signal(signal.SIGINT, self.close_all)
        self.server = server

    def close_all(self, _signal, frame):
        logging.info('action: received {} | result: success | info: closing and shutting down'.format(signal.Signals(_signal).name))
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

    def __handle_client_connection(self):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            while True:
                msg = self.client_socket.recv(1024).rstrip().decode('utf-8')
                if not msg:
                    break
                self.handle_message(msg)

        except OSError as e:
            logging.error("action: receive_message | result: fail | error: {e}")
        finally:
            close_socket(self.client_socket, 'client')

    def handle_message(self, msg: string):
        """
        Parses bet received from client and stores it

        Sends response to client
        """
        addr = self.client_socket.getpeername()
        logging.info(f'action: receive_message | result: success | ip: {addr[0]} | msg: {msg}')

        msg_list = msg.split(";")
        if len(msg_list) < 6:
            logging.error("action: apuesta_almacenada | result: fail | error: bet doesn't have all necessary information")
            return
            
        bet = Bet(msg_list[0], msg_list[1], msg_list[2], msg_list[3], msg_list[4], msg_list[5])
        store_bets([bet])
        logging.info(f'action: apuesta_almacenada | result: success | dni:{bet.document} | numero: {bet.number}')

        self.send_response(bet)

    def send_response(self, bet: Bet):
        """
        Sends to client bet number saved
        """
        self.client_socket.sendall("{}\n".format(bet.number).encode('utf-8'))
    
    def close_all(self):
        self._server_socket = close_socket(self._server_socket, 'server')
        self.client_socket = close_socket(self.client_socket, 'client')

def close_socket(sock: socket, name: string):
    if sock is not None:
        logging.info(f'action: closing socket | info: closing {name}')
        sock.close()
        sock = None
    sock