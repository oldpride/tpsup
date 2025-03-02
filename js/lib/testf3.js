function f1() {
    console.log(`f1`);
}

// 'use strict';
let f2 = new Function('return f1()');
f2(); // f1
 