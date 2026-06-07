let display = document.getElementById('display');
let clear = document.getElementById('clear');
let backspace = document.getElementById('backspace');
let divide = document.getElementById('divide');
let multiply = document.getElementById('multiply');
let subtract = document.getElementById('subtract');
let add = document.getElementById('add');
let equals = document.getElementById('equals');
let zero = document.getElementById('zero');
let decimal = document.getElementById('decimal');
let one = document.getElementById('one');
let two = document.getElementById('two');
let three = document.getElementById('three');
let four = document.getElementById('four');
let five = document.getElementById('five');
let six = document.getElementById('six');
let seven = document.getElementById('seven');
let eight = document.getElementById('eight');
let nine = document.getElementById('nine');

let currentNumber = '';
let previousNumber = '';
let operation = '';

seven.addEventListener('click', () => {
    currentNumber += '7';
    display.value = currentNumber;
});

eight.addEventListener('click', () => {
    currentNumber += '8';
    display.value = currentNumber;
});

nine.addEventListener('click', () => {
    currentNumber += '9';
    display.value = currentNumber;
});

four.addEventListener('click', () => {
    currentNumber += '4';
    display.value = currentNumber;
});

five.addEventListener('click', () => {
    currentNumber += '5';
    display.value = currentNumber;
});

six.addEventListener('click', () => {
    currentNumber += '6';
    display.value = currentNumber;
});

one.addEventListener('click', () => {
    currentNumber += '1';
    display.value = currentNumber;
});

two.addEventListener('click', () => {
    currentNumber += '2';
    display.value = currentNumber;
});

three.addEventListener('click', () => {
    currentNumber += '3';
    display.value = currentNumber;
});

zero.addEventListener('click', () => {
    currentNumber += '0';
    display.value = currentNumber;
});

decimal.addEventListener('click', () => {
    if (!currentNumber.includes('.')) {
        currentNumber += '.';
        display.value = currentNumber;
    }
});

clear.addEventListener('click', () => {
    currentNumber = '';
    previousNumber = '';
    operation = '';
    display.value = '';
});

backspace.addEventListener('click', () => {
    currentNumber = currentNumber.slice(0, -1);
    display.value = currentNumber;
});

divide.addEventListener('click', () => {
    previousNumber = currentNumber;
    currentNumber = '';
    operation = '/';
});

multiply.addEventListener('click', () => {
    previousNumber = currentNumber;
    currentNumber = '';
    operation = '*';
});

subtract.addEventListener('click', () => {
    previousNumber = currentNumber;
    currentNumber = '';
    operation = '-';
});

add.addEventListener('click', () => {
    previousNumber = currentNumber;
    currentNumber = '';
    operation = '+';
});

equals.addEventListener('click', () => {
    let num1 = parseFloat(previousNumber);
    let num2 = parseFloat(currentNumber);
    let result;

    switch (operation) {
        case '+':
            result = num1 + num2;
            break;
        case '-':
            result = num1 - num2;
            break;
        case '*':
            result = num1 * num2;
            break;
        case '/':
            if (num2 !== 0) {
                result = num1 / num2;
            } else {
                result = 'Error';
            }
            break;
        default:
            result = 'Error';
    }

    display.value = result;
    currentNumber = '';
    previousNumber = '';
    operation = '';
});