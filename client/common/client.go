package common

import (
	"bufio"
	"net"
	"time"
	"syscall"
	"os"
	"os/signal"

	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")

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

func (c *Client) handleConnection(msgID int) {
	// Create the connection the server in every loop iteration. Send an
	c.createClientSocket()

	if c.conn == nil {
		c.stop<-true
		return
	}

	bet := NewBet()
	if bet == nil {
		c.stop<-true
		log.Errorf("action: create_bet | result: fail | client_id: %v | error: could not create bet",
			c.config.ID,
		)
		return
	}

	c.conn.Write([]byte(bet.String()))

	msg, err := bufio.NewReader(c.conn).ReadString('\n')
	c.conn.Close()

	if err != nil {
		log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return
	}

	log.Infof("action: receive_message | result: success | client_id: %v | msg: %v",
		c.config.ID,
		msg,
	)

	// Wait a time between sending one message and the next one
	time.Sleep(c.config.LoopPeriod)
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
