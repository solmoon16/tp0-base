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
const PATH = "./.data/agency-"

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

func signalHandler(stop chan bool, client_id string) {
	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs, syscall.SIGTERM, syscall.SIGINT)
	sig := <-sigs
	stop <- true
	log.Infof("action: received signal %v | info: closing socket | client_id: %v", sig, client_id)
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	stop := make(chan bool, 1)
	// waits for signal in different go routine
	go signalHandler(stop, config.ID)

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
	conn.SetReadDeadline(time.Now().Add(2 * time.Second))
	c.conn = conn
	return nil
}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() {
	// There is an autoincremental msgID to identify every message sent
	// Messages if the message amount threshold has not been surpassed

	for msgID := 1; msgID <= c.config.LoopAmount; msgID++ {
		select {
		case stop := <-c.stop:
			if stop {
				c.closeAll()
				return
			}
		default:
			c.handleConnection(msgID)
		}
	}
	log.Infof("action: loop_finished | result: success | client_id: %v", c.config.ID)
}

func (c *Client) closeAll() {
	if c.conn != nil {c.conn.Close()}
}

// Opens connection with server, sends bet and waits for confirmation
func (c *Client) handleConnection(msgID int) {
	// Create the connection the server in every loop iteration. Send an
	c.CreateClientSocket()

	if c.conn == nil {
		c.stop<-true
		return
	}

	c.SendBets()
	c.conn.Close()

	// Wait a time between sending one message and the next one
	time.Sleep(c.config.LoopPeriod)
}

// Reads response from server and logs answer
func (c *Client) readResponse() {
	msg_read, err := bufio.NewReader(c.conn).ReadString('\n')
	
	if err != nil {
		log.Errorf("action: apuesta_enviada | result: fail | client_id: %v | error: error communicating with server (%v)",
			c.config.ID,
			err,
		)
		return
	}

	msg := strings.Trim(msg_read, "\n")

	if msg == "0" {
		log.Errorf("action: apuesta_enviada | result: fail | client_id: %v | error: server could not process batch" ,
		c.config.ID,
		)
	} 

}

func createBet(agency string, betStr string) *Bet {

	info := strings.Split(betStr, ",")
	if len(info) < 5 {
		return nil
	}
	return NewBet(agency, info[0], info[1], info[2], info[3], info[4])
}

func (c *Client) sendBatch(batch []string) int{
	b := strings.Join(batch, ";")
	c.conn.Write([]byte(b))
	return len(batch)
}

func (c *Client) SendBets() {
	file := readBetsFile(c.config.ID)
	defer file.Close()

	var betsToSend[] string
	line := 0

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		betStr := scanner.Text()
		line += 1
		bet := createBet(c.config.ID, betStr)
		if bet == nil {
			log.Errorf("action: create_bet | result: fail | client_id: %v | error: bet in line %v had invalid parameters", c.config.ID, line)
			continue
		}
		betsToSend = append(betsToSend, bet.String())
		if line % c.config.BatchMaxAmount == 0 {
			c.sendBatch(betsToSend)
			c.readResponse()
			betsToSend = []string{}
		}
	}

	if len(betsToSend) != 0 {
		c.sendBatch(betsToSend)
		c.readResponse()
	}
}

func readBetsFile(id string) *os.File {
	path := fmt.Sprintf("%v%v.csv", PATH, id)
	file, err := os.Open(path)
	if err != nil {
		log.Errorf("action: open_file | result: fail | client_id: %v | error: %v", 
			id,
			err,
		)
	}
	return file
}