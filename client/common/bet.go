package common 

import(
	"os"
	"fmt"
)

type Bet struct {
	name string
	lastName string
	idNumber string 
	dateOfBirth string
	number string
	agency string
}

func NewBet() *Bet {
	name := os.Getenv("NOMBRE")
	lastName := os.Getenv("APELLIDO")
	idNumber := os.Getenv("DOCUMENTO")
	dateOfBirth := os.Getenv("NACIMIENTO")
	number := os.Getenv("NUMBER")

	if len(name) == 0 || len(lastName) == 0 || len(idNumber) == 0 || len(dateOfBirth) == 0 || len(number) == 0 {
		return nil
	}

	bet := &Bet{
		name: name, 
		lastName: lastName,
		idNumber: idNumber,
		dateOfBirth: dateOfBirth,
		number: number,
	}
	return bet
}

func (b Bet) String() string {
	return fmt.Sprintf("%v;%v;%v;%v;%v;%v", b.agency, b.name, b.lastName, b.idNumber, b.dateOfBirth, b.number)
}