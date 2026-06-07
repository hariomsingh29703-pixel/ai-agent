let display = document.getElementById('display');
let clearButton = document.getElementById('clear');
let backspaceButton = document.getElementById('backspace');
let equalsButton = document.getElementById('equals');
let numberButtons = document.querySelectorAll('.buttons button');
let currentNumber = '';
let previousNumber = '';
let operator = '';

numberButtons.forEach(button => {
    button.addEventListener('click', () => {
        let number = button.textContent;
        currentNumber += number;
        display.value = currentNumber;
    });
});

clearButton.addEventListener('click', () => {
    currentNumber = '';
    previousNumber = '';
    operator = '';
    display.value = '';
});

backspaceButton.addEventListener('click', () => {
    currentNumber = currentNumber.slice(0, -1);
    display.value = currentNumber;
});

document.getElementById('add').addEventListener('click', () => {
    previousNumber = currentNumber;
    operator = 'add';
    currentNumber = '';
    display.value = '';
});

document.getElementById('subtract').addEventListener('click', () => {
    previousNumber = currentNumber;
    operator = 'subtract';
    currentNumber = '';
    display.value = '';
});

document.getElementById('multiply').addEventListener('click', () => {
    previousNumber = currentNumber;
    operator = 'multiply';
    currentNumber = '';
    display.value = '';
});

document.getElementById('divide').addEventListener('click', () => {
    previousNumber = currentNumber;
    operator = 'divide';
    currentNumber = '';
    display.value = '';
});
equalsButton.addEventListener('click', () => {
    let result;
    switch (operator) {
        case 'add':
            result = parseFloat(previousNumber) + parseFloat(currentNumber);
            break;
        case 'subtract':
            result = parseFloat(previousNumber) - parseFloat(currentNumber);
            break;
        case 'multiply':
            result = parseFloat(previousNumber) * parseFloat(currentNumber);
            break;
        case 'divide':
            result = parseFloat(previousNumber) / parseFloat(currentNumber);
            break;
        default:
            result = '';
    }
    display.value = result;
    currentNumber = result.toString();
    previousNumber = '';
    operator = '';
});
