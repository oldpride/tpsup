// https://youtube.com/watch?v=h33Srr5J9nY
// ES6 array functions

function sum(a, b) {
    return a + b
}

let sum2 = (a, b) => a + b

console.log(sum(1, 2))
console.log(sum2(1, 2))

function isPositive(number) {
    return number >= 0
}

let isPositive2 = number => number >= 0

console.log(isPositive(-1))
console.log(isPositive2(-1))

function randomNumber() {
    return Math.random()
}

let randomNumber2 = () => Math.random()

console.log(randomNumber())
console.log(randomNumber2())

// document is only available on browser not on server (node js)

if (typeof window !== 'undefined') {
    console.log('You are on the browser')



} else {
    console.log('You are on the Node js server')

    //https://www.testim.io/blog/jsdom-a-guide-to-how-to-get-started-and-what-you-can-do/
    const jsdom = require("jsdom");
    const { JSDOM } = jsdom;
    html = '<!DOCTYPE html><body><p id="main">My First JSDOM!</p></body>';
    global.document = new JSDOM(html).window.document;
}

document.addEventListener('click', function () {
    console.log('Click')
})

document.addEventListener('click', () => console.log('Click'))