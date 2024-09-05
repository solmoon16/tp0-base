from multiprocessing import Manager, Process, Queue
import signal
import socket
import logging
import string
import os

from common.utils import Bet, has_won, load_bets, store_bets
END_OF_BET=";"
FIELD_SEPARATOR=","
END_BATCH = "\n"
DONE = "DONE:"
AGENCIES_NUM = int(os.getenv("AGENCIES", 5))

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
            shared_clients_dict = manager.dict()
            bets_queue = Queue()
            while True and self._server_socket is not None:
                if self.clients_done():
                    self.get_bets(bets_queue)
                    for p in self.processes:
                        p.join(None)
                        self.processes.remove(p)
                    self.clients = shared_clients_dict
                    self.do_draw()
                    break
                client_socket = self.__accept_new_connection()
                if client_socket is None:
                    continue
                self.start_client_connection(client_socket, shared_clients_dict, bets_queue)
                
    def start_client_connection(self, client_socket, shared_dict, bets_queue):
        """
        Starts new process to handle client
        """
        p = Process(target=self.__handle_client_connection, args=(client_socket, shared_dict, bets_queue))
        self.processes.append(p)
        p.start()
    
    def __accept_new_connection(self):
        """
        Accept new connections if there are any. 
        It's non-blocking and automatically returns if there aren't connections to accept.
        If there is a connection it's created, printed and returned
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

    def __handle_client_connection(self, client_socket, clients, bets):
        """
        Read message from a specific client socket until DONE message is received or client closes connection.
        Read message from a specific client socket until DONE message is received or client closes connection.

        Saves client socket and id in shared dictionary.
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
                # save bytes read until full batch is received
                msg = old_msg + read
                old_msg = msg
                try:
                    sep = msg.index(DONE)
                    client_id = msg[sep+len(DONE):]
                    cli_dict = clients
                    cli_dict.update({client_id:client_socket})
                    clients = cli_dict
                    bets.put(None)
                    bets.close()
                    return
                except:
                    try:
                        sep = msg.index(END_BATCH)             
                        batch = msg[:sep]   
                        old_msg = msg[sep+len(END_BATCH):]
                        self.handle_message(batch, client_socket, bets)
                    finally:
                        continue
                    
        except OSError as e:
            logging.error(f"action: receive_message | result: fail | error: {e}")


    def handle_message(self, msg: string, client_socket: socket, bets_queue):
        """
        Parses batch of bets received from client and sends it to parent process using queue.

        Sends response to client with how many bets in batch were processed.
        """
        bets_list = []
        msg_list = msg.split(END_OF_BET)
        for msg in msg_list:
            bet = handle_bet(msg)
            if bet is None:
                break
            bets_list.append(bet)
        
        if len(bets_list) != len(msg_list):
            logging.error(f'action: apuesta_recibida | result: fail | cantidad: {len(msg_list)}')
        else:
            logging.info(f'action: apuesta_recibida | result: success | cantidad: {len(bets_list)}')
            # full batch is sent to queue
            bets_queue.put(bets_list)

        self.send_response(client_socket, len(bets_list))
        
    def send_response(self, client_socket, bets_num: int):
        """
        Sends how many bets were stored to client
        """
        if client_socket is None:
            return
        client_socket.sendall("{}\n".format(bets_num).encode('utf-8'))
    
    def close_all(self):
        """
        Closes all server resources: sockets and waits for child processes to finish 
        """
        self._server_socket = close_socket(self._server_socket, 'server')
        for p in self.processes:
            p.join()
        for (agency, conn) in self.clients.items():
            conn = close_socket(conn, agency)
            self.clients.update({agency: conn})
        self.stop = True
    
    def clients_done(self) -> bool: 
        return len(self.processes) == AGENCIES_NUM
            
    def do_draw(self):
        """
        Loads bets and checks each one to see if there is a winner. 
        Sends results to agencies.
        """
        logging.info(f'action: sorteo | result: success')
        try: 
            bets = load_bets()
            winners = []
            for b in bets:
                if has_won(b):
                    winners.append(b)
        except:
            if self.stop is True:
                return
        else:
            self.send_results(winners)
    
    def send_results(self, winners: list[Bet]):
        wins_per_agency = [[] for _ in range(AGENCIES_NUM)]
        for win in winners:
            wins_per_agency[win.agency-1].append(win.document)
        for (agency, conn) in self.clients.items():
            agency = int(agency)
            try:
                self.send_response(conn, wins_per_agency[agency-1])
            finally:
                self.close_all()
    
    def get_bets(self, bets_queue):
        """
        Reads from queue to get bets from child processes until all of them are done receiving bets.
        """
        done = 0
        while done < 5 and self.stop is False:
            try:
                bets = bets_queue.get(1)
                if bets is None:
                    done += 1
            finally:
                if bets is not None and len(bets) > 0:
                    store_bets(bets)
        bets_queue.close()


def close_socket(sock: socket, name: string):
    if sock is not None:
        logging.info(f'action: closing socket | info: closing {name}')
        sock.close()
        sock = None
    return sock

def handle_bet(bet_str: string):
    """
    Creates bet from string received
    """
    params = bet_str.split(FIELD_SEPARATOR)
    if len(params) < 6:
        return None
    
    return Bet(params[0], params[1], params[2], params[3], params[4], params[5])
