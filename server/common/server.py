from multiprocessing import Manager, Process
import signal
import socket
import logging
import string
import os

from common.utils import Bet, has_won, load_bets, store_bets
END_OF_BET=";"
FIELD_SEPARATOR=","
END_BATCH = "\n"
AGENCIES_NUM = 5
DONE = "DONE:"

class ServerSignalHandler:
    def __init__(self, server):
        signal.signal(signal.SIGTERM, self.close_all)
        signal.signal(signal.SIGINT, self.close_all)
        self.server = server

    def close_all(self, _signal, frame):
        logging.info('action: received {} | result: success | info: closing and shutting down [pid: {}]'.format(signal.Signals(_signal).name, os.getpid()))
        self.server.close_all()

class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._server_socket.setblocking(0)
        self.clients = {}
        self.processes = []
        self.stop = False
        

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """
        with Manager() as manager:
            shared = manager.dict()
            while True and self._server_socket is not None:
                if self.clients_done() and self.stop is False:
                    for p in self.processes:
                        p.join(None)
                        self.processes.remove(p)
                    self.clients = shared
                    self.do_draw()
                    break
                client_socket = self.__accept_new_connection()
                if client_socket is None:
                    continue
                self.start_client_connection(client_socket, shared)
                
    def start_client_connection(self, client_socket, shared_dict):
        p = Process(target=self.__handle_client_connection, args=(client_socket, shared_dict))
        self.processes.append(p)
        p.start()
    
    def __accept_new_connection(self):
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """
        if self._server_socket is None:
            return None
        try:
            c, addr = self._server_socket.accept()
            logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
        except:
            return None
        else:
            return c

    def __handle_client_connection(self, client_socket, clients):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        
        old_msg = ""
        try:
            while True:
                if self.stop is True:
                    close_socket(client_socket, "client")
                    return
                read = client_socket.recv(1024).decode('utf-8', 'ignore')
                if not read:
                    break
                msg = old_msg + read
                old_msg = msg
                try:
                    sep = msg.index(DONE)
                    client_id = msg[sep+len(DONE):]
                    cli_dict = clients
                    cli_dict.update({client_id:client_socket})
                    clients = cli_dict
                    return
                except:
                    try:
                        sep = msg.index(END_BATCH)             
                        batch = msg[:sep]   
                        old_msg = msg[sep+1:]
                        self.handle_message(batch, client_socket)
                    finally:
                        continue
                    
        except OSError as e:
            logging.error(f"action: receive_message | result: fail | error: {e}")


    def handle_message(self, msg: string, client_socket: socket):
        """
        Parses bet received from client and stores it

        Sends response to client
        """

        msg_list = msg.split(END_OF_BET)
        bets = []
        for msg in msg_list:
            bet = handle_bet(msg)
            if bet is None:
                break
            bets.append(bet)
        
        if len(bets) != len(msg_list):
            logging.error(f'action: apuesta_recibida | result: fail | cantidad: {len(msg_list)}')
        else:
            store_bets(bets)
            logging.info(f'action: apuesta_recibida | result: success | cantidad: {len(bets)}')

        self.send_response(client_socket, len(bets))
        
    def send_response(self, client_socket, bets_num: int):
        """
        Sends to client bet number saved
        """
        client_socket.sendall("{}\n".format(bets_num).encode('utf-8'))
    
    def close_all(self):
        self._server_socket = close_socket(self._server_socket, 'server')
        for p in self.processes:
            try:
                p.join()
            except:
                continue
        for (agency, conn) in self.clients.items():
            conn = close_socket(conn, agency)
            self.clients.update({agency: conn})
        self.stop = True
    
    def clients_done(self) -> bool: 
        return len(self.processes) == AGENCIES_NUM
            
    def do_draw(self):
        logging.info(f'action: sorteo | result: success')
        try: 
            bets = load_bets()
            winners = []
            for b in bets:
                if has_won(b):
                    winners.append(b)
        except:
            logging.info("no bets")
            if self.stop is True:
                return
        else:
            self.send_results(winners)
    
    def send_results(self, winners: list[Bet]):
        winsPerAgency = [0 for x in range(AGENCIES_NUM)]
        for win in winners:
            winsPerAgency[win.agency-1] += 1
        for agency, conn in self.clients.items():
            agency = int(agency)
            self.send_response(conn, winsPerAgency[agency-1])
            self.close_all()


def close_socket(sock: socket, name: string):
    if sock is not None:
        logging.info(f'action: closing socket | info: closing {name}')
        sock.close()
        sock = None
    return sock

def handle_bet(betStr: string):
    params = betStr.split(FIELD_SEPARATOR)
    if len(params) < 6:
        return None
    
    return Bet(params[0], params[1], params[2], params[3], params[4], params[5])
    