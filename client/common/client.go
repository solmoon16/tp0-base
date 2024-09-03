package common

import (
	"bufio"
	"net"
	"time"
	"syscall"
	"os"
	"os/signal"
	"strings"
	"fmt"

	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")
const END_SERVER_MESSAGE = "\n"
const ESM_CHAR = '\n'
const PATH = "./.data/agency-"
const EXTENSION = ".csv"
const END_BATCH = '\n'
const BET_SEPARATOR = ";"
const FIELD_SEPARATOR = ","
const EMPTY_BATCH = "0"
const DONE = "DONE"
const MAX_READ = 5

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	ServerAddress string
	LoopAmount    int
	LoopPeriod    time.Duration
	BatchMaxAmount int
}

// Client Entity that encapsulates how
type Client struct {
	config ClientConfig
	conn   net.Conn
	stop chan bool
}

// If SIGTERM or SIGINT are received it sends true to the stop channel so that the client knows to finish executing
func signalHandler(stop chan bool, client_id string) {
	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGTERM, syscall.SIGINT)
	sig := <-sigs
	stop <- true
	log.Infof("action: received signal %v | result: success | info: closing socket | client_id: %v", sig, client_id)
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	stop := make(chan bool, 1)
	// waits for signal in different go routine
	go signalHandler(stop, config.ID)
	if config.BatchMaxAmount == 0 {
		config.BatchMaxAmount = 120
	}

	client := &Client{
		config: config,
		stop: stop,
	}
	return client
}

// CreateClientSocket Initializes client socket. In case of
// failure, error is printed in stdout/stderr and exit 1
// is returned
func (c *Client) CreateClientSocket() error {
	conn, err := net.Dial("tcp", c.config.ServerAddress)
	if err != nil {
		log.Criticalf(
			"action: connect | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		conn = nil
	}
	c.conn = conn
	return nil
}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() {

	if !c.stopClient() {
		c.handleConnection()
	}

	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}

func (c *Client) closeAll() {
	if c.conn != nil {c.conn.Close()}
}

// Opens connection with server, sends batch of bets and waits for confirmation
func (c *Client) handleConnection(msgID int) {
	// Create the connection the server in every loop iteration. Send an
	c.CreateClientSocket()

	if c.conn == nil {
		return
	}

	c.sendBets()
	c.waitWinner(1)
	c.conn.Close()
}

func (c*Client) stopClient() bool {
	select {
	case stop := <-c.stop:
		if stop {
			return true
		}
	default:
		return false
	}
	return false
}

func (c* Client) sendDone() {
	s := fmt.Sprintf("%s:%v", DONE, c.config.ID)
	_, err := c.conn.Write([]byte(s))
	if err != nil {
		log.Errorf("action: mensaje_enviado | result: fail | client_id: %v | error: error communicating with server (%v)", c.config.ID, err,)
	}

}

func (c *Client) waitWinner(read_amount int) {
	c.conn.SetReadDeadline(time.Now().Add(1 * time.Second))
	if read_amount == MAX_READ {
		log.Errorf("action: consulta_ganadores | result: fail | client_id: %v | error: error communicating with server",
			c.config.ID,
		)
		return
	}
	if c.stopClient() {
		c.closeAll()
		return
	}
	msg, err := bufio.NewReader(c.conn).ReadString(ESM_CHAR)
	if err != nil {
		log.Errorf("action: consulta_ganadores | result: fail | client_id: %v | error: error communicating with server (%v)",
			c.config.ID,
			err,
		)
		c.waitWinner(read_amount+1)
		return
	}
	log.Infof("action: consulta_ganadores | result: success | cant_ganadores: %v", msg)
}

// Reads response from server and logs answer
func (c *Client) readResponse(batchSize int) {
	// sets read deadline for socket with server
	c.conn.SetReadDeadline(time.Now().Add(c.config.LoopPeriod))
	if c.stopClient(){
		c.closeAll()
		return 
	}

	msg_read, err := bufio.NewReader(c.conn).ReadString('\n')
	
	if err != nil {
		log.Errorf("action: apuesta_enviada | result: fail | client_id: %v | error: error communicating with server (%v)",
			c.config.ID,
			err,
		)
		return
	}

	msg := strings.Trim(msg_read, END_SERVER_MESSAGE)

	if msg != fmt.Sprintf("%v", batchSize) {
		log.Errorf("action: apuesta_enviada | result: fail | client_id: %v | error: server could not process batch | cantidad: %v" ,
		c.config.ID, 
		msg,
		)
		return
	} 
	log.Infof("action: apuesta_enviada | result: success | cantidad: %v", msg)
}

func createBet(agency string, betStr string) *Bet {
	info := strings.Split(betStr, FIELD_SEPARATOR)
	if len(info) < 5 {
		return nil
	}
	return NewBet(agency, info[0], info[1], info[2], info[3], info[4])
}

// Sends 1 batch of bets to server
func (c *Client) sendBatch(batch []string) int{
	if c.stopClient() {
		c.closeAll()
		return 0
	}
	time.Sleep(c.config.LoopPeriod)
	join := strings.Join(batch, BET_SEPARATOR)
	b := fmt.Sprintf("%s\n", join)
	_, err := c.conn.Write([]byte(b))
	if err != nil {
		log.Errorf("action: apuesta_enviada | result: fail | client_id: %v | error: error communicating with server (%v)",
			c.config.ID,
			err,
		)
		return 0
	}
	return len(batch)
}

// Reads bets from file and sends 1 batch each time, skipping bets already sent before
func (c* Client) sendBets(batchNum int) {
	file := readBetsFile(c.config.ID)
	if file == nil {
		return
	}
	defer file.Close()

	var betsToSend[] string
	line := 0

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		if c.stopClient() {
			c.closeAll()
			return
		}
		if line%c.config.BatchMaxAmount==0 && line != 0{
			size := c.sendBatch(betsToSend)
			if size == 0 {
				return
			}
			c.readResponse(size)
			betsToSend = []string{}
		}
	
		betStr := scanner.Text()
		bet := createBet(c.config.ID, betStr)
		if bet == nil {
			log.Errorf("action: create_bet | result: fail | client_id: %v | error: bet in line %v had invalid parameters", c.config.ID, line)
			continue
		}
		betsToSend = append(betsToSend, bet.String())
		line += 1
	}

	if len(betsToSend) != 0{
		size := c.sendBatch(betsToSend)
		if size == 0{
			return
		}
		c.readResponse(size)
	}

	c.sendDone()
}

func readBetsFile(id string) *os.File {
	path := fmt.Sprintf("%v%v%v", PATH, id, EXTENSION)
	file, err := os.Open(path)
	if err != nil {
		log.Errorf("action: open_file | result: fail | client_id: %v | error: %v", 
			id,
			err,
		)
		return nil
	}
	return file
}