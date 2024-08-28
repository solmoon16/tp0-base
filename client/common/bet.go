package common 

import(
	"fmt"
	"time"
	"strconv"
)

const MAX_NAME_LENGTH = 32

type Bet struct {
	name string
	lastName string
	idNumber string 
	dateOfBirth string
	number string
	agency string
}

func NewBet(agency string, name string, lastName string, idNumber string, dateOfBirth string, number string) *Bet {

	if !namesAreValid(name, lastName) || !dateIsValid(dateOfBirth) || !numbersAreValid(idNumber, number){
		return nil
	}

	bet := &Bet{
		agency: agency,
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

func namesAreValid(name string, lastName string) bool {
	return len(name) > 0 && len(lastName) > 0 && len(name) <= MAX_NAME_LENGTH && len(lastName) <= MAX_NAME_LENGTH/2
}

func dateIsValid(dateStr string) bool {
	_, err := time.Parse("2006-01-02", dateStr)
	return len(dateStr) > 0 && err == nil
}

func numbersAreValid(idNumber string, number string) bool {
	_, err := strconv.Atoi(idNumber)
	_, err2 := strconv.Atoi(number)
	return err == nil && err2 == nil && len(idNumber) == 8
}