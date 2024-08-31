from operator import index
import signal
import socket
import logging
import string

from common.utils import Bet, store_bets

END_BATCH = "\n"
BET_SEPARATOR = ";"

class ServerSignalHandler:
    def __init__(self, server):
        signal.signal(signal.SIGTERM, self.close_all)
        signal.signal(signal.SIGINT, self.close_all)
        self.server = server

    def close_all(self, _signal, frame):
        logging.info('action: received {} | info: closing and shutting down'.format(signal.Signals(_signal).name))
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
        while True and self._server_socket is not None:
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
        old_msg = ""
        try:
            while True and self.client_socket is not None:
                read = self.client_socket.recv(1024).decode('utf-8')
                if not read:
                    break
                msg = old_msg + read
                old_msg = read
                try:
                    sep = msg.index(END_BATCH)             
                    batch = msg[:sep]   
                    old_msg = msg[sep+1:]
                    self.handle_message(batch)
                finally:
                    continue
        
        except OSError as e:
            logging.error(f"action: receive_message | result: fail | error: {e}")
        finally:
            close_socket(self.client_socket, 'client')

    def handle_message(self, msg: string):
        """
        Parses bet received from client and stores it

        Sends response to client
        """

        msg_list = msg.split(BET_SEPARATOR)
        bets = []
        for msg in msg_list:
            bet = handle_bet(msg)
            if bet is None:
                break
            bets.append(bet)
        
        if len(bets) != len(msg_list):
            logging.error(f'action: apuesta_recibida | result: fail | cantidad: {len(msg_list)}')
            bets = []
        else:
            store_bets(bets)
            logging.info(f'action: apuesta_recibida | result: success | cantidad: {len(bets)}')
        
        self.send_response(bets)

    def send_response(self, bets: list[Bet]):
        """
        Sends to client bet number saved
        """
        self.client_socket.sendall("{}\n".format(len(bets)).encode('utf-8'))
    
    def close_all(self):
        self._server_socket = close_socket(self._server_socket, 'server')
        self.client_socket = close_socket(self.client_socket, 'client')

def close_socket(sock: socket, name: string):
    if sock is not None:
        logging.info(f'action: closing socket | info: closing {name}')
        sock.close()
        sock = None
    return sock

def handle_bet(betStr: string):
    params = betStr.split(",")
    if len(params) < 6:
        return None
    
    return Bet(params[0], params[1], params[2], params[3], params[4], params[5])
    