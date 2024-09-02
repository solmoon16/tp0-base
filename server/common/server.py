from multiprocessing import Pipe, Process
from multiprocessing.connection import wait
import select
import signal
import socket
import logging
import string

from common.utils import Bet, has_won, load_bets, store_bets
END_OF_BET=";"
FIELD_SEPARATOR=","
END_BATCH = "\n"
AGENCIES_NUM = 1
DONE = "DONE:"

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
        self._server_socket.setblocking(0)
        readable, _, _ = select.select([self._server_socket], [], [self._server_socket], 1) 
        self.readable = readable
        self.clients = {}
        self.processes = []
        self.pipes = []

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """
        
        while True and self._server_socket is not None:
            if self.clients_done():
                logging.info("done")
                for p in self.processes:
                    p.join()
                self.do_draw()
                break
            client_socket = self.__accept_new_connection()
            if client_socket is None:
                continue
            parent_conn, child_conn = Pipe(duplex=True)
            p = Process(target=self.__handle_client_connection, args=(client_socket, child_conn))
            self.processes.append(p)
            p.start()
            self.pipes.append(parent_conn)
            child_conn.close()
        
            
    
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
        except OSError:
            return None
        else:
            return c

    def __handle_client_connection(self, client_socket, pipe):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        
        old_msg = ""
        try:
            while True:
                if continue_connection(pipe) is False:
                    client_socket.close()
                    return
                read = client_socket.recv(1024).decode('utf-8', 'ignore')
                if not read:
                    break
                msg = old_msg + read
                old_msg = msg
                try:
                    sep = msg.index(DONE)
                    client_id = msg[sep+len(DONE):]
                    pipe.send({client_id:client_socket})
                    pipe.close()
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
        for p in self.pipes:
            try:
                p.send(False)
            except:
                continue
        for p in self.processes:
            try:
                p.join()
            except:
                continue
        for (agency, conn) in self.clients.items():
            close_socket(conn, agency)
    
    def clients_done(self) -> bool: 
        for p in wait(self.pipes, 0.5):
            try:
                msg = p.recv()
                logging.info(msg)
                self.clients.update(msg)
            except EOFError:
                logging.error("pipe closed")
                self.pipes.remove(p)
                return False
            except:
                return False

        return len(self.clients.keys()) == AGENCIES_NUM
            
    def do_draw(self):
        logging.info(f'action: sorteo | result: success')
        bets = load_bets()
        winners = []
        for b in bets:
            if has_won(b):
                winners.append(b)
        self.send_results(winners)
    
    def send_results(self, winners: list[Bet]):
        winsPerAgency = [0 for x in range(AGENCIES_NUM)]
        for win in winners:
            winsPerAgency[win.agency-1] += 1
        """ for (agency, conn) in self.clients.items():
            agency = int(agency)
            self.send_response(conn, winsPerAgency[agency-1])
            close_socket(conn, f"client{agency}") """
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
    
def continue_connection(pipe) -> bool:
      if pipe.poll(0.5):
          return pipe.recv
      return True  