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

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	ServerAddress string
	LoopAmount    int
	LoopPeriod    time.Duration
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

	client := &Client{
		config: config,
		stop: stop,
	}
	return client
}

// CreateClientSocket Initializes client socket. In case of
// failure, error is printed in stdout/stderr and exit 1
// is returned
func (c *Client) createClientSocket() error {
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

func (c *Client) closeAll() {
	if c.conn != nil {c.conn.Close()}
}

// Opens connection with server, sends bet and waits for confirmation
func (c *Client) handleConnection(msgID int) {
	// Create the connection the server in every loop iteration. Send an
	c.createClientSocket()

	if c.conn == nil {
		return
	}

	bet, ok := c.sendBet() 
	if !ok {
		return
	}

	c.readResponse(bet)
	c.conn.Close()

	// Wait a time between sending one message and the next one
	time.Sleep(c.config.LoopPeriod)
}

// Reads response from server and logs answer
func (c *Client) readResponse(bet *Bet) {
	// sets read deadline for socket with server
	c.conn.SetReadDeadline(time.Now().Add(c.config.LoopPeriod))
	msg_read, err := bufio.NewReader(c.conn).ReadString(ESM_CHAR)
	
	if err != nil {
		log.Errorf("action: apuesta_enviada | result: fail | client_id: %v | error: error communicating with server (%v)",
			c.config.ID,
			err,
		)
		return
	}

	msg := strings.Trim(msg_read, END_SERVER_MESSAGE)

	if msg == bet.number {
		log.Infof("action: apuesta_enviada | result: success | dni: %v | numero: %v",
		bet.idNumber,
		msg,
		)
	} else {
		log.Infof("action: apuesta_enviada | result: fail | dni: %v | numero: %v | info: did not receive server confirmation" ,
		bet.idNumber,
		bet.number,
		)
	}
}

func createBet(agency string) *Bet {
	name := os.Getenv("NOMBRE")
	lastName := os.Getenv("APELLIDO")
	idNumber := os.Getenv("DOCUMENTO")
	dateOfBirth := os.Getenv("NACIMIENTO")
	number := os.Getenv("NUMERO")
	return NewBet(agency, name, lastName, idNumber, dateOfBirth, number)
}

// Creates a new Bet and sends it through the connection opened. Returns the bet created and true.
// If the bet couldn't be created returns nil and false.
func (c *Client) sendBet() (*Bet, bool) {

	bet := createBet(c.config.ID)
	if bet == nil {
		c.stop<-true
		log.Errorf("action: create_bet | result: fail | client_id: %v | error: could not create bet. ENV variables missing",
			c.config.ID,
		)
		return nil, false
	}
	
	bet.agency = c.config.ID
	s := fmt.Sprintf("%s;", bet.String())
	_, err := c.conn.Write([]byte(s))
	if err != nil {
		log.Errorf("action: send_message | result: fail | client_id: %v, error: %v", c.config.ID, err,)
		return nil, false
	}

	return bet, true
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
